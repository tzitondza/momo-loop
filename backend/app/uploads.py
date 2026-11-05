"""Validate and import anonymised batch CSV uploads into PostgreSQL."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

from .analytics import DATA_DIR, refresh_analytics_cache
from .ingest import replace_dataset_dataframe

REQUIRED_COLUMNS = {
    "transactions": [
        "transaction_id",
        "customer_id",
        "transaction_type",
        "amount",
        "timestamp",
        "location_id",
    ],
    "merchants": [
        "merchant_id",
        "name",
        "location_id",
        "merchant_category",
        "accepts_momo",
    ],
    "locations": [
        "location_id",
        "name",
        "region",
        "lat",
        "lng",
    ],
}

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


def _backup_dir() -> Path:
    path = DATA_DIR / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_and_save_csv(dataset: str, raw: bytes, filename: str) -> dict[str, Any]:
    dataset = dataset.strip().lower()
    if dataset not in REQUIRED_COLUMNS:
        raise ValueError("Please select transactions, merchants or locations.")
    if not filename.lower().endswith(".csv"):
        raise ValueError("Only CSV files can be imported.")
    if len(raw) == 0:
        raise ValueError("The selected file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("The file exceeds the 20 MB import limit.")

    try:
        df = pd.read_csv(BytesIO(raw))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Unable to read the CSV file: {exc}") from exc

    if df.empty:
        raise ValueError("The CSV file contains no data rows.")

    required = REQUIRED_COLUMNS[dataset]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    if dataset == "transactions":
        if "amount" in df.columns:
            amounts = pd.to_numeric(df["amount"], errors="coerce")
            if amounts.isna().all():
                raise ValueError("amount column must contain numeric values")
        if "transaction_type" in df.columns:
            types = set(df["transaction_type"].astype(str).str.lower().unique())
            if not types & {"p2p", "cash-out", "cash-in", "merchant payment"}:
                raise ValueError(
                    "transaction_type should include MoMo types such as P2P, cash-out, merchant payment"
                )
    if dataset == "locations":
        for col in ("lat", "lng"):
            vals = pd.to_numeric(df[col], errors="coerce")
            if vals.isna().any():
                raise ValueError(f"{col} must be numeric for all rows")

    # Optional archive copy for rollback
    target = DATA_DIR / f"{dataset}.csv"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if target.exists():
        backup = _backup_dir() / f"{dataset}.{stamp}.csv"
        shutil.copy2(target, backup)

    if dataset == "transactions":
        for optional in (
            "merchant_category",
            "merchant_id",
            "merchant_accepts_momo",
            "related_inflow_id",
            "minutes_after_inflow",
        ):
            if optional not in df.columns:
                df[optional] = ""
    if dataset == "merchants" and "is_planted_gap" not in df.columns:
        df["is_planted_gap"] = "False"
    if dataset == "locations" and "urban" not in df.columns:
        df["urban"] = "False"

    # Keep a local archive of the latest import and load into Postgres
    df.to_csv(target, index=False)
    rows = replace_dataset_dataframe(dataset, df)
    freshness = refresh_analytics_cache()
    return {
        "dataset": dataset,
        "rows": rows,
        "columns": list(df.columns),
        "filename": filename,
        "saved_as": "postgresql",
        **freshness,
    }
