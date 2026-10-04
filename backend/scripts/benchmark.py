"""Reproducible local API test; no production access or fabricated load claims."""

import json, time, statistics, concurrent.futures, argparse
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine, Session
from app.models import User, Post
from app.security import digest
from app.schemas import TERMS

parser = argparse.ArgumentParser()
parser.add_argument("--posts", type=int, default=10000)
parser.add_argument("--requests", type=int, default=200)
args = parser.parse_args()
if engine.dialect.name != "sqlite" or "benchmark" not in str(engine.url):
    raise SystemExit("Set DATABASE_URL to a separate benchmark SQLite database")
Base.metadata.create_all(engine)
with Session() as session:
    user = User(secret_hash=digest("benchmark-token"), terms=TERMS)
    session.add(user)
    session.flush()
    session.add_all(
        [
            Post(
                owner=user.id,
                title="Benchmark record " + str(i),
                body="Synthetic local performance fixture.",
                category="情绪树洞",
                status="active",
                created=1700000000000 + i,
            )
            for i in range(args.posts)
        ]
    )
    session.commit()
client = TestClient(app)
headers = {"Authorization": "Bearer benchmark-token"}


def request(_):
    start = time.perf_counter()
    r = client.get("/posts", headers=headers)
    assert r.status_code == 200, r.text
    assert len(r.json()["posts"]) == 20
    return (time.perf_counter() - start) * 1000


for i in range(10):
    request(i)
start = time.perf_counter()
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    latencies = list(pool.map(request, range(args.requests)))
seconds = time.perf_counter() - start
ordered = sorted(latencies)
print(
    json.dumps(
        {
            "database": engine.dialect.name,
            "synthetic_posts": args.posts,
            "requests": args.requests,
            "client_threads": 8,
            "elapsed_seconds": round(seconds, 3),
            "requests_per_second": round(args.requests / seconds, 2),
            "p50_ms": round(statistics.median(latencies), 2),
            "p95_ms": round(ordered[int(len(ordered) * 0.95) - 1], 2),
            "scope": "local SQLite TestClient; excludes network, PostgreSQL and Redis",
        },
        ensure_ascii=False,
        indent=2,
    )
)
