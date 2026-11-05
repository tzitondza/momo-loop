"""Load anonymised MoMo datasets into PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .analytics import DATA_DIR
from .database import SessionLocal, engine
from .models import (
    LocationRecord,
    MerchantRecord,
    TransactionRecord,
    utcnow,
)

DATASET_MODELS = {
    "locations": LocationRecord,
    "merchants": MerchantRecord,
    "transactions": TransactionRecord,
}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _prepare_locations(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "urban" not in out.columns:
        out["urban"] = False
    out["urban"] = out["urban"].map(_as_bool)
    out["lat"] = pd.to_numeric(out["lat"], errors="coerce").fillna(0.0)
    out["lng"] = pd.to_numeric(out["lng"], errors="coerce").fillna(0.0)
    out["location_id"] = out["location_id"].astype(str)
    out["name"] = out["name"].astype(str)
    out["region"] = out["region"].astype(str)
    return out[["location_id", "name", "region", "lat", "lng", "urban"]]


def _prepare_merchants(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "is_planted_gap" not in out.columns:
        out["is_planted_gap"] = False
    out["is_planted_gap"] = out["is_planted_gap"].map(_as_bool)
    out["accepts_momo"] = out["accepts_momo"].astype(str)
    out["merchant_id"] = out["merchant_id"].astype(str)
    out["name"] = out["name"].astype(str)
    out["location_id"] = out["location_id"].astype(str)
    out["merchant_category"] = out["merchant_category"].astype(str)
    return out[
        ["merchant_id", "name", "location_id", "merchant_category", "accepts_momo", "is_planted_gap"]
    ]


def _prepare_transactions(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for optional in (
        "merchant_category",
        "merchant_id",
        "merchant_accepts_momo",
        "related_inflow_id",
        "minutes_after_inflow",
    ):
        if optional not in out.columns:
            out[optional] = ""
    out["amount"] = pd.to_numeric(out["amount"], errors="coerce").fillna(0.0)
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce", utc=True)
    out = out[out["timestamp"].notna()].copy()
    out["minutes_after_inflow"] = pd.to_numeric(out["minutes_after_inflow"], errors="coerce")
    for col in (
        "transaction_id",
        "customer_id",
        "transaction_type",
        "location_id",
        "merchant_category",
        "merchant_id",
        "merchant_accepts_momo",
        "related_inflow_id",
    ):
        out[col] = out[col].fillna("").astype(str)
    return out[
        [
            "transaction_id",
            "customer_id",
            "transaction_type",
            "amount",
            "timestamp",
            "location_id",
            "merchant_category",
            "merchant_id",
            "merchant_accepts_momo",
            "related_inflow_id",
            "minutes_after_inflow",
        ]
    ]


PREPARE = {
    "locations": _prepare_locations,
    "merchants": _prepare_merchants,
    "transactions": _prepare_transactions,
}


def replace_dataset_dataframe(dataset: str, df: pd.DataFrame, db: Session | None = None) -> int:
    dataset = dataset.strip().lower()
    if dataset not in DATASET_MODELS:
        raise ValueError("Unknown dataset")

    prepared = PREPARE[dataset](df)
    model = DATASET_MODELS[dataset]
    close = False
    if db is None:
        db = SessionLocal()
        close = True
    try:
        db.execute(delete(model))
        rows = prepared.to_dict(orient="records")
        # Convert NaN minutes to None
        if dataset == "transactions":
            for row in rows:
                val = row.get("minutes_after_inflow")
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    row["minutes_after_inflow"] = None
                ts = row.get("timestamp")
                if hasattr(ts, "to_pydatetime"):
                    row["timestamp"] = ts.to_pydatetime()
        if rows:
            db.bulk_insert_mappings(model, rows)
        db.commit()
        return len(rows)
    except Exception:
        db.rollback()
        raise
    finally:
        if close:
            db.close()


def dataset_counts(db: Session | None = None) -> dict[str, int]:
    close = False
    if db is None:
        db = SessionLocal()
        close = True
    try:
        return {
            "locations": int(db.scalar(select(func.count()).select_from(LocationRecord)) or 0),
            "merchants": int(db.scalar(select(func.count()).select_from(MerchantRecord)) or 0),
            "transactions": int(db.scalar(select(func.count()).select_from(TransactionRecord)) or 0),
        }
    finally:
        if close:
            db.close()


def ingest_csv_file(dataset: str, path: Path, db: Session | None = None) -> int:
    df = pd.read_csv(path)
    return replace_dataset_dataframe(dataset, df, db=db)


def ingest_csv_bytes(dataset: str, raw: bytes, db: Session | None = None) -> int:
    df = pd.read_csv(BytesIO(raw))
    return replace_dataset_dataframe(dataset, df, db=db)


def bootstrap_from_csv(force: bool = False) -> dict[str, Any]:
    """Load seed CSVs into Postgres when tables are empty (or force=True)."""
    init_needed = force
    counts = dataset_counts()
    if not force and counts["transactions"] == 0:
        init_needed = True
    if not init_needed:
        return {"status": "skipped", "reason": "postgres already populated", **counts}

    loaded = {}
    with SessionLocal() as db:
        for dataset in ("locations", "merchants", "transactions"):
            path = DATA_DIR / f"{dataset}.csv"
            if not path.exists():
                loaded[dataset] = 0
                continue
            loaded[dataset] = ingest_csv_file(dataset, path, db=db)
    return {"status": "loaded", **loaded, **dataset_counts()}


def frames_from_postgres() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read analytics frames directly from PostgreSQL."""
    locs = pd.read_sql_table("locations", con=engine)
    merchants = pd.read_sql_table("merchants", con=engine)
    tx = pd.read_sql_table("transactions", con=engine)

    if not tx.empty:
        tx["timestamp"] = pd.to_datetime(tx["timestamp"], utc=True, errors="coerce")
        # analytics expects naive/comparable timestamps; keep timezone-aware OK for pandas
        tx["amount"] = pd.to_numeric(tx["amount"], errors="coerce").fillna(0)
        tx["minutes_after_inflow"] = pd.to_numeric(tx["minutes_after_inflow"], errors="coerce")
    if not merchants.empty:
        merchants["accepts_momo"] = merchants["accepts_momo"].astype(str)
        merchants["is_planted_gap"] = merchants["is_planted_gap"].map(_as_bool)
    if not locs.empty:
        locs["urban"] = locs["urban"].map(_as_bool)
    return tx, locs, merchants
