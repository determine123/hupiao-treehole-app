"""Transactional application-data snapshots; restore only into an empty, migrated database."""

import argparse
import gzip
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone

from sqlalchemy import MetaData, create_engine, select, text

FORMAT = "hupiao-data-v1"


def catalog(connection):
    metadata = MetaData()
    metadata.reflect(connection)
    revisions = []
    if "alembic_version" in metadata.tables:
        revisions = sorted(
            connection.scalars(select(metadata.tables["alembic_version"].c.version_num))
        )
    tables = [
        table for table in metadata.sorted_tables if table.name != "alembic_version"
    ]
    return tables, revisions


def export_snapshot(engine, destination):
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Backup destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    counts = {}
    try:
        with engine.connect() as connection:
            if engine.dialect.name == "postgresql":
                connection = connection.execution_options(
                    isolation_level="REPEATABLE READ"
                )
            with connection.begin():
                if engine.dialect.name == "postgresql":
                    connection.execute(text("SET TRANSACTION READ ONLY"))
                elif engine.dialect.name == "sqlite":
                    connection.exec_driver_sql("BEGIN")
                else:
                    raise ValueError("Unsupported database dialect")
                tables, revisions = catalog(connection)
                header = {
                    "format": FORMAT,
                    "created": datetime.now(timezone.utc).isoformat(),
                    "revisions": revisions,
                    "tables": {
                        table.name: list(table.columns.keys()) for table in tables
                    },
                }
                with tempfile.NamedTemporaryFile(
                    dir=destination.parent, delete=False
                ) as raw:
                    temporary = Path(raw.name)
                with gzip.open(temporary, "wt", encoding="utf-8") as output:
                    output.write(json.dumps(header) + "\n")
                    for table in tables:
                        counts[table.name] = 0
                        query = select(table).order_by(*table.primary_key.columns)
                        for row in connection.execute(
                            query.execution_options(yield_per=500)
                        ):
                            output.write(
                                json.dumps(
                                    {"table": table.name, "values": list(row)},
                                    ensure_ascii=False,
                                )
                                + "\n"
                            )
                            counts[table.name] += 1
                    output.write(json.dumps({"counts": counts}) + "\n")
        # Complete compression and the source transaction before publishing the file.
        with temporary.open("rb+") as file:
            os.fsync(file.fileno())
        # Same-directory hard link publishes atomically and refuses an existing name.
        os.link(temporary, destination)
        return counts
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def read_header(source):
    header = json.loads(source.readline())
    if header.get("format") != FORMAT or not isinstance(header.get("tables"), dict):
        raise ValueError("Unsupported snapshot format")
    return header


def restore_snapshot(engine, snapshot):
    # This is intentionally not an overwrite/migration command.
    with (
        gzip.open(snapshot, "rt", encoding="utf-8") as source,
        engine.begin() as connection,
    ):
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        elif engine.dialect.name != "postgresql":
            raise ValueError("Unsupported database dialect")
        header = read_header(source)
        tables, revisions = catalog(connection)
        schema = {table.name: list(table.columns.keys()) for table in tables}
        if schema != header["tables"] or revisions != header.get("revisions"):
            raise ValueError(
                "Migrate the empty destination to the snapshot schema first"
            )
        if engine.dialect.name == "postgresql" and tables:
            # Prevent concurrent writes while checking and restoring the empty destination.
            quoted = ", ".join(
                connection.dialect.identifier_preparer.quote(table.name)
                for table in tables
            )
            connection.execute(
                text("LOCK TABLE " + quoted + " IN ACCESS EXCLUSIVE MODE")
            )
        for table in tables:
            if connection.execute(select(table).limit(1)).first() is not None:
                raise ValueError("Restore destination must be empty")
        by_name = {table.name: table for table in tables}
        counts = {table.name: 0 for table in tables}
        complete = False
        for line in source:
            record = json.loads(line)
            if complete:
                raise ValueError("Unexpected records after snapshot footer")
            if "counts" in record:
                if record["counts"] != counts:
                    raise ValueError("Snapshot row count mismatch")
                complete = True
                continue
            name, values = record["table"], record["values"]
            if name not in by_name or len(values) != len(schema[name]):
                raise ValueError("Invalid snapshot row")
            connection.execute(
                by_name[name].insert().values(dict(zip(schema[name], values)))
            )
            counts[name] += 1
        if not complete:
            raise ValueError("Incomplete snapshot")
        return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["export", "restore-empty"])
    parser.add_argument(
        "path", help="Private snapshot file path; never commit or publish it"
    )
    args = parser.parse_args()
    url = os.environ.get("HUPIAO_DATABASE_URL", "")
    if not url:
        parser.error("Set HUPIAO_DATABASE_URL privately in the environment")
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url[len(prefix) :]
            break
    engine = None
    try:
        engine = create_engine(url, pool_pre_ping=True)
        counts = (
            export_snapshot(engine, args.path)
            if args.operation == "export"
            else restore_snapshot(engine, args.path)
        )
        print(json.dumps({"operation": args.operation, "counts": counts}))
    except Exception:
        # Driver exceptions may include SQL parameters or connection credentials.
        parser.exit(
            1,
            "Snapshot operation failed; no successful backup/restore is claimed. Check private diagnostics and destination.\n",
        )
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
