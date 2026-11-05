"""CLI entrypoint for scheduled/manual analytics refresh.

Example cron:
  0 2 * * * cd /path/to/backend && .venv/bin/python -m scripts.refresh_analytics
"""

from __future__ import annotations

from app.database import init_db
from app.ingest import bootstrap_from_csv
from app.jobs import run_nightly_refresh


def main() -> None:
    init_db()
    bootstrap_from_csv(force=False)
    result = run_nightly_refresh(detail="CLI refresh job")
    print(result)


if __name__ == "__main__":
    main()
