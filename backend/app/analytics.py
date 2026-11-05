"""MoMo Loop analytics: cash-out boundaries, acceptance gaps, opportunity ranking."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CASHOUT_WINDOW_MIN = 30
RECOVERY_RATE_DEFAULT = 0.35  # share of cash-out value that could shift to digital
NATIONAL_LABELS = {"", "south africa", "national", "all", "za", "rsa"}


@lru_cache(maxsize=1)
def load_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load analytics frames from PostgreSQL (CSV is only used for bootstrap/import)."""
    from .ingest import frames_from_postgres

    tx, locs, merchants = frames_from_postgres()
    if tx.empty and locs.empty:
        # Fallback during first boot before ingest completes
        tx = pd.read_csv(DATA_DIR / "transactions.csv")
        locs = pd.read_csv(DATA_DIR / "locations.csv")
        merchants = pd.read_csv(DATA_DIR / "merchants.csv")
        tx["timestamp"] = pd.to_datetime(tx["timestamp"], utc=True, errors="coerce")
        tx["amount"] = pd.to_numeric(tx["amount"], errors="coerce").fillna(0)
        tx["minutes_after_inflow"] = pd.to_numeric(tx["minutes_after_inflow"], errors="coerce")
        merchants["accepts_momo"] = merchants["accepts_momo"].astype(str)
        merchants["is_planted_gap"] = (
            merchants["is_planted_gap"].astype(str).str.lower().isin(["true", "1", "yes"])
        )
        locs["urban"] = locs["urban"].astype(str).str.lower().isin(["true", "1", "yes"])
    return tx, locs, merchants


def refresh_analytics_cache() -> dict[str, Any]:
    """Clear caches and rematerialise opportunity rankings from Postgres."""
    from .jobs import run_nightly_refresh

    return run_nightly_refresh(detail="Manual analytics refresh")


def is_national_scope(region: str | None, role: str | None = None) -> bool:
    if role == "admin":
        return True
    return (region or "").strip().lower() in NATIONAL_LABELS


def data_freshness() -> dict[str, Any]:
    from sqlalchemy import select

    from .database import SessionLocal
    from .models import DataRefreshMeta

    with SessionLocal() as db:
        meta = db.scalar(select(DataRefreshMeta).limit(1))
        if meta and meta.last_refreshed:
            return {
                "last_refreshed": meta.last_refreshed.isoformat(),
                "source": meta.source or "postgres",
                "dataset_label": meta.dataset_label or "South Africa MoMo sample",
            }

    # Fallback before first refresh metadata row exists
    path = DATA_DIR / "transactions.csv"
    last = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    return {
        "last_refreshed": last,
        "source": "postgres",
        "dataset_label": "South Africa MoMo sample",
    }


def scope_meta(region: str | None, role: str | None = None) -> dict[str, Any]:
    national = is_national_scope(region, role)
    label = "South Africa" if national else (region or "").strip()
    return {
        "region": label,
        "national": national,
        **data_freshness(),
    }


def scoped_frames(
    region: str | None = None,
    role: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    tx, locs, merchants = load_frames()
    meta = scope_meta(region, role)
    if meta["national"]:
        return tx, locs, merchants, meta

    target = meta["region"].lower()
    locs = locs[locs["region"].astype(str).str.lower() == target].copy()
    loc_ids = set(locs["location_id"].tolist())
    tx = tx[tx["location_id"].isin(loc_ids)].copy()
    merchants = merchants[merchants["location_id"].isin(loc_ids)].copy()
    return tx, locs, merchants, meta


def _boundary_cashouts(tx: pd.DataFrame) -> pd.DataFrame:
    """Cash-outs linked to an inflow within the detection window (probable boundaries)."""
    mask = (
        (tx["transaction_type"] == "cash-out")
        & tx["related_inflow_id"].notna()
        & (tx["related_inflow_id"].astype(str).str.len() > 0)
        & (tx["minutes_after_inflow"].notna())
        & (tx["minutes_after_inflow"] <= CASHOUT_WINDOW_MIN)
    )
    return tx.loc[mask].copy()


def overview(region: str | None = None, role: str | None = None) -> dict[str, Any]:
    tx, locs, merchants, meta = scoped_frames(region, role)
    boundaries = _boundary_cashouts(tx)

    total_value = float(tx["amount"].sum())
    cashout_value = float(tx.loc[tx["transaction_type"] == "cash-out", "amount"].sum())
    merchant_pay_value = float(
        tx.loc[tx["transaction_type"] == "merchant payment", "amount"].sum()
    )
    boundary_value = float(boundaries["amount"].sum())
    inflows = tx[tx["transaction_type"].isin(["P2P", "cash-in"])]
    inflow_value = float(inflows["amount"].sum()) or 1.0

    accepting = int((merchants["accepts_momo"] == "Yes").sum())
    non_accepting = int((merchants["accepts_momo"] == "No").sum())
    opportunities = int(
        merchants.groupby(["location_id", "merchant_category"])
        .apply(lambda g: (g["accepts_momo"] == "No").any(), include_groups=False)
        .sum()
    ) if len(merchants) else 0

    by_day = (
        tx.assign(day=tx["timestamp"].dt.date.astype(str))
        .groupby(["day", "transaction_type"], as_index=False)["amount"]
        .sum()
    )
    trend = []
    for day, group in by_day.groupby("day"):
        row = {"day": day}
        for _, r in group.iterrows():
            row[r["transaction_type"]] = round(float(r["amount"]), 2)
        trend.append(row)

    return {
        "scope": meta,
        "kpis": {
            "total_transaction_value": round(total_value, 2),
            "cash_out_value": round(cashout_value, 2),
            "boundary_cash_out_value": round(boundary_value, 2),
            "digital_merchant_payments": round(merchant_pay_value, 2),
            "estimated_leakage_rate": round(boundary_value / inflow_value, 4) if len(tx) else 0.0,
            "cash_out_after_inflow_rate": round(
                len(boundaries) / max(len(inflows), 1), 4
            ),
            "transaction_count": int(len(tx)),
            "customer_count": int(tx["customer_id"].nunique()) if len(tx) else 0,
            "merchant_count": int(len(merchants)),
            "accepting_merchants": accepting,
            "non_accepting_merchants": non_accepting,
            "potential_opportunities": opportunities,
            "location_count": int(len(locs)),
            "estimated_recoverable_value": round(boundary_value * RECOVERY_RATE_DEFAULT, 2),
        },
        "trend": trend[-30:],
        "disclaimer": (
            "Rapid cash-out after inflow indicates a probable acceptance boundary, not confirmed "
            "merchant rejection. Recoverable value estimates depend on the stated assumptions."
        ),
    }


def boundaries(
    location_id: str | None = None,
    category: str | None = None,
    limit: int = 40,
    region: str | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    tx, locs, merchants, meta = scoped_frames(region, role)
    b = _boundary_cashouts(tx)
    if location_id:
        b = b[b["location_id"] == location_id]
    if category:
        b = b[b["merchant_category"] == category]

    loc_map = locs.set_index("location_id")[["name", "region"]].to_dict("index")

    agg = (
        b.groupby(["location_id", "merchant_category"], as_index=False)
        .agg(
            boundary_count=("transaction_id", "count"),
            boundary_value=("amount", "sum"),
            affected_customers=("customer_id", "nunique"),
            avg_minutes=("minutes_after_inflow", "mean"),
        )
        .sort_values("boundary_value", ascending=False)
    )

    hotspots = []
    for _, row in agg.iterrows():
        info = loc_map.get(row["location_id"], {})
        coverage = merchants[
            (merchants["location_id"] == row["location_id"])
            & (merchants["merchant_category"] == row["merchant_category"])
        ]
        accept_rate = (
            float((coverage["accepts_momo"] == "Yes").mean()) if len(coverage) else 0.0
        )
        hotspots.append(
            {
                "location_id": row["location_id"],
                "location_name": info.get("name", row["location_id"]),
                "region": info.get("region", ""),
                "merchant_category": row["merchant_category"],
                "boundary_count": int(row["boundary_count"]),
                "boundary_value": round(float(row["boundary_value"]), 2),
                "affected_customers": int(row["affected_customers"]),
                "avg_minutes_to_cashout": round(float(row["avg_minutes"]), 1),
                "merchant_acceptance_rate": round(accept_rate, 3),
            }
        )

    journeys = []
    sample = b.sort_values("amount", ascending=False).head(limit)
    inflows = tx.set_index("transaction_id")
    for _, row in sample.iterrows():
        inflow = None
        rid = str(row.get("related_inflow_id", ""))
        if rid and rid in inflows.index:
            inflow = inflows.loc[rid]
        info = loc_map.get(row["location_id"], {})
        journeys.append(
            {
                "cashout_id": row["transaction_id"],
                "customer_id": row["customer_id"],
                "inflow_type": None if inflow is None else str(inflow["transaction_type"]),
                "inflow_amount": None if inflow is None else round(float(inflow["amount"]), 2),
                "cashout_amount": round(float(row["amount"]), 2),
                "minutes_after_inflow": int(row["minutes_after_inflow"]),
                "location_id": row["location_id"],
                "location_name": info.get("name", row["location_id"]),
                "merchant_category": row["merchant_category"]
                if pd.notna(row["merchant_category"])
                else "",
                "timestamp": row["timestamp"].strftime("%Y-%m-%d %H:%M"),
            }
        )

    G = nx.DiGraph()
    for _, row in b.iterrows():
        cat = row["merchant_category"] if pd.notna(row["merchant_category"]) else "Unknown"
        node_a = f"inflow:{row['location_id']}"
        node_b = f"gap:{row['location_id']}:{cat}"
        if G.has_edge(node_a, node_b):
            G[node_a][node_b]["weight"] += float(row["amount"])
            G[node_a][node_b]["count"] += 1
        else:
            G.add_edge(node_a, node_b, weight=float(row["amount"]), count=1)

    centrality = []
    if G.number_of_nodes():
        scores = nx.betweenness_centrality(G, weight="weight")
        for node, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:15]:
            centrality.append({"node": node, "betweenness": round(score, 4)})

    return {
        "scope": meta,
        "window_minutes": CASHOUT_WINDOW_MIN,
        "total_boundaries": int(len(b)),
        "total_boundary_value": round(float(b["amount"].sum()), 2) if len(b) else 0.0,
        "hotspots": hotspots[:50],
        "journeys": journeys,
        "graph_centrality": centrality,
        "disclaimer": (
            "Highlighted journeys are probable cash-out boundaries inferred from "
            f"wallet inflow followed by cash-out within {CASHOUT_WINDOW_MIN} minutes."
        ),
    }


def _opportunity_frame(region: str | None = None, role: str | None = None) -> tuple[pd.DataFrame, dict]:
    tx, locs, merchants, meta = scoped_frames(region, role)
    b = _boundary_cashouts(tx)

    if locs.empty:
        empty = pd.DataFrame(
            columns=[
                "location_id",
                "merchant_category",
                "merchant_count",
                "accepting_count",
                "planted_gap",
                "acceptance_rate",
                "acceptance_gap",
                "boundary_count",
                "boundary_value",
                "affected_customers",
                "name",
                "region",
                "lat",
                "lng",
                "urban",
                "feasibility",
                "score",
                "estimated_recoverable",
            ]
        )
        return empty, meta

    coverage = (
        merchants.groupby(["location_id", "merchant_category"], as_index=False)
        .agg(
            merchant_count=("merchant_id", "count"),
            accepting_count=("accepts_momo", lambda s: int((s == "Yes").sum())),
            planted_gap=("is_planted_gap", "any"),
        )
    )
    coverage["acceptance_rate"] = coverage["accepting_count"] / coverage["merchant_count"].clip(
        lower=1
    )
    coverage["acceptance_gap"] = 1.0 - coverage["acceptance_rate"]

    demand = (
        b.groupby(["location_id", "merchant_category"], as_index=False)
        .agg(
            boundary_count=("transaction_id", "count"),
            boundary_value=("amount", "sum"),
            affected_customers=("customer_id", "nunique"),
        )
    )

    opp = coverage.merge(demand, on=["location_id", "merchant_category"], how="left")
    opp["boundary_count"] = opp["boundary_count"].fillna(0).astype(int)
    opp["boundary_value"] = opp["boundary_value"].fillna(0.0)
    opp["affected_customers"] = opp["affected_customers"].fillna(0).astype(int)

    opp = opp.merge(locs[["location_id", "name", "region", "lat", "lng", "urban"]], on="location_id")
    opp["feasibility"] = opp.apply(
        lambda r: 0.85 if r["urban"] else (0.65 if r["merchant_count"] >= 2 else 0.45),
        axis=1,
    )

    max_val = opp["boundary_value"].max() or 1.0
    max_cust = opp["affected_customers"].max() or 1.0
    max_freq = opp["boundary_count"].max() or 1.0

    opp["score"] = (
        0.40 * (opp["boundary_value"] / max_val)
        + 0.20 * (opp["affected_customers"] / max_cust)
        + 0.15 * (opp["boundary_count"] / max_freq)
        + 0.15 * opp["acceptance_gap"]
        + 0.10 * opp["feasibility"]
    ) * 100

    opp["estimated_recoverable"] = opp["boundary_value"] * RECOVERY_RATE_DEFAULT * opp["feasibility"]
    opp = opp.sort_values("score", ascending=False)
    return opp, meta


def opportunities(
    limit: int = 25,
    region: str | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    opp, meta = _opportunity_frame(region, role)
    rows = []
    for rank, (_, r) in enumerate(opp.head(limit).iterrows(), start=1):
        reasons = []
        if r["boundary_value"] > 0:
            reasons.append(
                f"R{r['boundary_value']:,.0f} in probable boundary cash-outs "
                f"({int(r['boundary_count'])} events, {int(r['affected_customers'])} customers)"
            )
        reasons.append(
            f"Acceptance coverage {r['acceptance_rate']*100:.0f}% "
            f"({int(r['accepting_count'])}/{int(r['merchant_count'])} merchants)"
        )
        reasons.append(
            f"Onboarding feasibility {'high' if r['feasibility'] >= 0.8 else 'moderate' if r['feasibility'] >= 0.6 else 'lower'} "
            f"({'urban' if r['urban'] else 'peri-urban/rural'} market)"
        )
        rows.append(
            {
                "rank": rank,
                "location_id": r["location_id"],
                "location_name": r["name"],
                "region": r["region"],
                "lat": float(r["lat"]),
                "lng": float(r["lng"]),
                "merchant_category": r["merchant_category"],
                "opportunity_score": round(float(r["score"]), 1),
                "boundary_value": round(float(r["boundary_value"]), 2),
                "boundary_count": int(r["boundary_count"]),
                "affected_customers": int(r["affected_customers"]),
                "acceptance_rate": round(float(r["acceptance_rate"]), 3),
                "acceptance_gap": round(float(r["acceptance_gap"]), 3),
                "feasibility": round(float(r["feasibility"]), 2),
                "estimated_recoverable": round(float(r["estimated_recoverable"]), 2),
                "is_planted_gap": bool(r["planted_gap"]),
                "reasons": reasons,
            }
        )

    planted = opp[opp["planted_gap"] == True] if len(opp) else opp  # noqa: E712
    top_n = set(zip(opp.head(10)["location_id"], opp.head(10)["merchant_category"])) if len(opp) else set()
    planted_pairs = (
        set(zip(planted["location_id"], planted["merchant_category"])) if len(planted) else set()
    )
    hit_rate = len(top_n & planted_pairs) / max(len(planted_pairs), 1)

    return {
        "scope": meta,
        "opportunities": rows,
        "scoring": {
            "weights": {
                "recoverable_value": 0.40,
                "affected_customers": 0.20,
                "boundary_frequency": 0.15,
                "acceptance_gap": 0.15,
                "feasibility": 0.10,
            },
            "recovery_rate_assumption": RECOVERY_RATE_DEFAULT,
            "ranking_quality_vs_planted_gaps": round(hit_rate, 3),
            "note": (
                "Ranking quality reflects how often known acceptance gaps appear among the "
                "top ten recommendations. Scores use transparent business rules."
            ),
        },
    }


def opportunities_csv(region: str | None = None, role: str | None = None, limit: int = 100) -> str:
    data = opportunities(limit=limit, region=region, role=role)
    cols = [
        "rank",
        "location_id",
        "location_name",
        "region",
        "merchant_category",
        "opportunity_score",
        "boundary_value",
        "boundary_count",
        "affected_customers",
        "acceptance_rate",
        "acceptance_gap",
        "feasibility",
        "estimated_recoverable",
        "is_planted_gap",
    ]
    rows = data["opportunities"]
    lines = [",".join(cols)]
    for r in rows:
        lines.append(
            ",".join(
                str(r.get(c, "")).replace(",", " ") if not isinstance(r.get(c), bool) else str(r.get(c))
                for c in cols
            )
        )
    return "\n".join(lines) + "\n"


def map_points(region: str | None = None, role: str | None = None) -> dict[str, Any]:
    opp, meta = _opportunity_frame(region, role)
    if opp.empty:
        return {"scope": meta, "points": []}
    locs = (
        opp.groupby(["location_id", "name", "region", "lat", "lng"], as_index=False)
        .agg(
            total_boundary_value=("boundary_value", "sum"),
            total_score=("score", "max"),
            opportunity_count=("merchant_category", "count"),
        )
    )
    points = []
    for _, r in locs.iterrows():
        points.append(
            {
                "location_id": r["location_id"],
                "name": r["name"],
                "region": r["region"],
                "lat": float(r["lat"]),
                "lng": float(r["lng"]),
                "boundary_value": round(float(r["total_boundary_value"]), 2),
                "top_score": round(float(r["total_score"]), 1),
                "opportunity_count": int(r["opportunity_count"]),
            }
        )
    return {"scope": meta, "points": points}


def simulate(
    location_id: str | None = None,
    category: str | None = None,
    recovery_rate: float = RECOVERY_RATE_DEFAULT,
    merchants_to_onboard: int = 5,
    region: str | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    recovery_rate = max(0.05, min(0.9, recovery_rate))
    merchants_to_onboard = max(1, min(50, merchants_to_onboard))
    opp, meta = _opportunity_frame(region, role)

    filtered = opp.copy()
    if location_id:
        filtered = filtered[filtered["location_id"] == location_id]
    if category:
        filtered = filtered[filtered["merchant_category"] == category]

    if filtered.empty:
        return {
            "scope": meta,
            "error": "No matching opportunities for the selected filters.",
            "baseline": {},
            "projected": {},
        }

    baseline_boundary = float(filtered["boundary_value"].sum())
    tx, _, _, _ = scoped_frames(region, role)
    mp = tx[tx["transaction_type"] == "merchant payment"]
    if location_id:
        mp = mp[mp["location_id"] == location_id]
    if category:
        mp = mp[mp["merchant_category"] == category]
    baseline_merchant = float(mp["amount"].sum())

    capture = 1 - (1 - recovery_rate) ** (merchants_to_onboard / 5)
    shifted = baseline_boundary * capture
    projected_merchant = baseline_merchant + shifted
    projected_boundary = max(0.0, baseline_boundary - shifted)

    top = filtered.sort_values("score", ascending=False).head(5)
    targets = [
        {
            "location_name": r["name"],
            "merchant_category": r["merchant_category"],
            "score": round(float(r["score"]), 1),
            "boundary_value": round(float(r["boundary_value"]), 2),
        }
        for _, r in top.iterrows()
    ]

    return {
        "scope": meta,
        "filters": {
            "location_id": location_id,
            "category": category,
            "recovery_rate": recovery_rate,
            "merchants_to_onboard": merchants_to_onboard,
        },
        "baseline": {
            "boundary_cash_out_value": round(baseline_boundary, 2),
            "digital_merchant_payments": round(baseline_merchant, 2),
        },
        "projected": {
            "boundary_cash_out_value": round(projected_boundary, 2),
            "digital_merchant_payments": round(projected_merchant, 2),
            "value_retained": round(shifted, 2),
            "retention_lift_pct": round(
                (shifted / baseline_merchant * 100) if baseline_merchant else 0.0, 1
            ),
            "effective_capture_rate": round(capture, 3),
        },
        "priority_targets": targets,
        "assumptions": [
            f"{recovery_rate*100:.0f}% of cash-out value at risk is treated as potentially recoverable through merchant payments.",
            "Additional merchant onboarding has diminishing returns.",
            "Figures are illustrative planning estimates, not a revenue forecast.",
            f"Results are limited to {meta['region']}.",
        ],
    }


def filters(region: str | None = None, role: str | None = None) -> dict[str, Any]:
    _, locs, merchants, meta = scoped_frames(region, role)
    return {
        "scope": meta,
        "locations": [
            {
                "location_id": r["location_id"],
                "name": r["name"],
                "region": r["region"],
            }
            for _, r in locs.iterrows()
        ],
        "categories": sorted(merchants["merchant_category"].unique().tolist()) if len(merchants) else [],
    }


def location_in_scope(
    location_id: str,
    region: str | None = None,
    role: str | None = None,
) -> bool:
    _, locs, _, meta = scoped_frames(region, role)
    if meta["national"]:
        return True
    return location_id in set(locs["location_id"].tolist())
