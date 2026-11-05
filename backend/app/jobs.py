"""Refresh jobs: rematerialise opportunity rankings and update freshness metadata."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import delete, select

from . import analytics
from .database import SessionLocal
from .models import DataRefreshMeta, OpportunitySnapshot, utcnow

_scheduler: BackgroundScheduler | None = None


def update_refresh_meta(
    *,
    source: str = "postgres",
    detail: str = "",
    transaction_count: int = 0,
    location_count: int = 0,
    merchant_count: int = 0,
    opportunity_count: int = 0,
) -> DataRefreshMeta:
    with SessionLocal() as db:
        meta = db.scalar(select(DataRefreshMeta).limit(1))
        if meta is None:
            meta = DataRefreshMeta(id=1)
            db.add(meta)
        meta.source = source
        meta.dataset_label = "South Africa MoMo sample"
        meta.last_refreshed = utcnow()
        meta.transaction_count = transaction_count
        meta.location_count = location_count
        meta.merchant_count = merchant_count
        meta.opportunity_count = opportunity_count
        meta.detail = detail
        db.commit()
        db.refresh(meta)
        return meta


def get_refresh_meta() -> dict[str, Any]:
    with SessionLocal() as db:
        meta = db.scalar(select(DataRefreshMeta).limit(1))
        if meta is None:
            return {
                "last_refreshed": datetime.now(timezone.utc).isoformat(),
                "source": "postgres",
                "dataset_label": "South Africa MoMo sample",
                "transaction_count": 0,
                "location_count": 0,
                "merchant_count": 0,
                "opportunity_count": 0,
            }
        return {
            "last_refreshed": meta.last_refreshed.isoformat() if meta.last_refreshed else None,
            "source": meta.source,
            "dataset_label": meta.dataset_label,
            "transaction_count": meta.transaction_count,
            "location_count": meta.location_count,
            "merchant_count": meta.merchant_count,
            "opportunity_count": meta.opportunity_count,
            "detail": meta.detail,
        }


def materialize_opportunities() -> int:
    """Recompute national opportunity rankings into opportunity_snapshots."""
    analytics.load_frames.cache_clear()
    opp_df, _meta = analytics._opportunity_frame(region="South Africa", role="admin")
    now = utcnow()
    rows = []
    for _, r in opp_df.iterrows():
        rows.append(
            {
                "location_id": str(r["location_id"]),
                "location_name": str(r["name"]),
                "region": str(r["region"]),
                "merchant_category": str(r["merchant_category"]),
                "opportunity_score": float(r["score"]),
                "boundary_value": float(r["boundary_value"]),
                "boundary_count": int(r["boundary_count"]),
                "affected_customers": int(r["affected_customers"]),
                "acceptance_rate": float(r["acceptance_rate"]),
                "acceptance_gap": float(r["acceptance_gap"]),
                "feasibility": float(r["feasibility"]),
                "estimated_recoverable": float(r["estimated_recoverable"]),
                "is_planted_gap": bool(r["planted_gap"]),
                "lat": float(r["lat"]),
                "lng": float(r["lng"]),
                "refreshed_at": now,
            }
        )

    with SessionLocal() as db:
        db.execute(delete(OpportunitySnapshot))
        if rows:
            db.bulk_insert_mappings(OpportunitySnapshot, rows)
        db.commit()
    return len(rows)


def run_nightly_refresh(detail: str = "Scheduled nightly refresh") -> dict[str, Any]:
    """Full analytics refresh: reload frames from Postgres and rematerialise rankings."""
    analytics.load_frames.cache_clear()
    tx, locs, merchants = analytics.load_frames()
    opportunity_count = materialize_opportunities()
    meta = update_refresh_meta(
        source="postgres",
        detail=detail,
        transaction_count=int(len(tx)),
        location_count=int(len(locs)),
        merchant_count=int(len(merchants)),
        opportunity_count=opportunity_count,
    )
    analytics.load_frames.cache_clear()
    return {
        "status": "ok",
        "last_refreshed": meta.last_refreshed.isoformat(),
        "source": meta.source,
        "dataset_label": meta.dataset_label,
        "transaction_count": meta.transaction_count,
        "location_count": meta.location_count,
        "merchant_count": meta.merchant_count,
        "opportunity_count": meta.opportunity_count,
        "detail": meta.detail,
    }


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_nightly_refresh,
        trigger="cron",
        hour=2,
        minute=0,
        id="momo_loop_nightly_refresh",
        replace_existing=True,
        kwargs={"detail": "Scheduled nightly refresh (02:00 UTC)"},
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
