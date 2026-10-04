"""Managed-host entry point: migrate before serving; use Render's assigned port."""

import os
import subprocess
import sys


def main():
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    port = int(os.environ.get("PORT", "8000"))
    workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
    os.execvp(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
            "--workers",
            str(workers),
            "--proxy-headers",
            "--forwarded-allow-ips",
            "*",
        ],
    )


if __name__ == "__main__":
    main()
