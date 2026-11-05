"""MoMo Loop Intelligence API with auth, roles, and saved scenarios."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import analytics
from .auth import (
    CurrentUser,
    authenticate_user,
    create_access_token,
    require_permission,
)
from .pdf_export import build_opportunities_pdf
from .uploads import validate_and_save_csv
from .database import get_db, init_db
from .models import (
    PIPELINE_STATUSES,
    ROLE_PERMISSIONS,
    AuditEvent,
    PipelineItem,
    Scenario,
    User,
)
from .ratelimit import clear_attempts, too_many_attempts
from .schemas import (
    AuditOut,
    LoginResponse,
    PipelineCreate,
    PipelineOut,
    PipelineUpdate,
    ScenarioCreate,
    ScenarioOut,
    UserOut,
)
from .ingest import bootstrap_from_csv
from .jobs import run_nightly_refresh, start_scheduler, stop_scheduler
from .seed import seed_users

app = FastAPI(
    title="MoMo Loop API",
    description="Cash-out boundary intelligence for MTN MoMo merchant acceptance expansion.",
    version="0.7.0",
)

_cors_raw = os.getenv(
    "CORS_ORIGINS",
    "http://127.0.0.1:5173,http://localhost:5173",
)
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]
if CORS_ORIGINS == ["*"]:
    allow_origins = ["*"]
    allow_credentials = False
else:
    allow_origins = CORS_ORIGINS
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    seed_users()
    bootstrap_from_csv(force=False)
    # Ensure opportunity snapshots + freshness metadata exist
    run_nightly_refresh(detail="Startup analytics refresh")
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        region=user.region,
        permissions=sorted(ROLE_PERMISSIONS.get(user.role, set())),
    )


def scenario_out(row: Scenario) -> ScenarioOut:
    return ScenarioOut(
        id=row.id,
        name=row.name,
        notes=row.notes or "",
        location_id=row.location_id,
        category=row.category,
        recovery_rate=row.recovery_rate,
        merchants_to_onboard=row.merchants_to_onboard,
        baseline_boundary_value=row.baseline_boundary_value,
        projected_value_retained=row.projected_value_retained,
        projected_merchant_payments=row.projected_merchant_payments,
        retention_lift_pct=row.retention_lift_pct,
        created_at=row.created_at,
        updated_at=row.updated_at,
        owner_email=row.owner.email if row.owner else None,
        owner_name=row.owner.full_name if row.owner else None,
    )


def pipeline_out(row: PipelineItem) -> PipelineOut:
    return PipelineOut(
        id=row.id,
        location_id=row.location_id,
        location_name=row.location_name,
        region=row.region or "",
        merchant_category=row.merchant_category,
        opportunity_score=row.opportunity_score,
        boundary_value=row.boundary_value,
        estimated_recoverable=row.estimated_recoverable,
        affected_customers=row.affected_customers,
        status=row.status,
        assignee_name=row.assignee_name or "",
        notes=row.notes or "",
        created_at=row.created_at,
        updated_at=row.updated_at,
        owner_email=row.owner.email if row.owner else None,
        owner_name=row.owner.full_name if row.owner else None,
    )


def log_event(
    db: Session,
    *,
    user: User | None,
    action: str,
    entity_type: str,
    entity_id: str | int,
    detail: str = "",
) -> None:
    db.add(
        AuditEvent(
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            detail=detail,
        )
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "product": "MoMo Loop", "auth": True}


@app.post("/api/auth/login", response_model=LoginResponse)
def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    client_host = request.client.host if request.client else "unknown"
    rate_key = f"{client_host}:{form.username.lower().strip()}"
    if too_many_attempts(rate_key, limit=8, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again in a minute.",
        )

    user = authenticate_user(db, form.username, form.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    clear_attempts(rate_key)
    token = create_access_token(subject=user.email, role=user.role)
    return LoginResponse(access_token=token, user=user_out(user))


@app.get("/api/auth/me", response_model=UserOut)
def me(user: CurrentUser):
    return user_out(user)


@app.get("/api/meta")
def get_meta(user: CurrentUser):
    return analytics.scope_meta(user.region, user.role)


@app.get("/api/overview")
def get_overview(user: Annotated[User, Depends(require_permission("overview"))]):
    return analytics.overview(region=user.region, role=user.role)


@app.get("/api/boundaries")
def get_boundaries(
    user: Annotated[User, Depends(require_permission("boundaries"))],
    location_id: str | None = None,
    category: str | None = None,
    limit: int = Query(40, ge=1, le=100),
):
    return analytics.boundaries(
        location_id=location_id,
        category=category,
        limit=limit,
        region=user.region,
        role=user.role,
    )


@app.get("/api/opportunities")
def get_opportunities(
    user: Annotated[User, Depends(require_permission("opportunities"))],
    limit: int = Query(25, ge=1, le=100),
):
    return analytics.opportunities(limit=limit, region=user.region, role=user.role)


@app.get("/api/opportunities/export")
def export_opportunities(
    user: Annotated[User, Depends(require_permission("opportunities"))],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(100, ge=1, le=500),
    format: str = Query("csv", pattern="^(csv|pdf)$"),
):
    scope = analytics.scope_meta(user.region, user.role)
    slug = scope["region"].replace(" ", "-").lower()

    if format == "pdf":
        payload = analytics.opportunities(limit=limit, region=user.region, role=user.role)
        pdf_bytes = build_opportunities_pdf(payload)
        log_event(
            db,
            user=user,
            action="opportunities.exported",
            entity_type="opportunities",
            entity_id=scope["region"],
            detail=f"PDF export ({limit} rows) for {scope['region']}",
        )
        db.commit()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="momo-loop-opportunities-{slug}.pdf"'
            },
        )

    csv_text = analytics.opportunities_csv(
        region=user.region, role=user.role, limit=limit
    )
    log_event(
        db,
        user=user,
        action="opportunities.exported",
        entity_type="opportunities",
        entity_id=scope["region"],
        detail=f"CSV export ({limit} rows) for {scope['region']}",
    )
    db.commit()
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="momo-loop-opportunities-{slug}.csv"'
        },
    )


@app.get("/api/map")
def get_map(user: Annotated[User, Depends(require_permission("map"))]):
    return analytics.map_points(region=user.region, role=user.role)


@app.get("/api/simulate")
def get_simulate(
    user: Annotated[User, Depends(require_permission("simulate"))],
    location_id: str | None = None,
    category: str | None = None,
    recovery_rate: float = Query(0.35, ge=0.05, le=0.9),
    merchants_to_onboard: int = Query(5, ge=1, le=50),
):
    return analytics.simulate(
        location_id=location_id,
        category=category,
        recovery_rate=recovery_rate,
        merchants_to_onboard=merchants_to_onboard,
        region=user.region,
        role=user.role,
    )


@app.get("/api/filters")
def get_filters(user: Annotated[User, Depends(require_permission("filters"))]):
    return analytics.filters(region=user.region, role=user.role)


@app.get("/api/scenarios", response_model=list[ScenarioOut])
def list_scenarios(
    user: Annotated[User, Depends(require_permission("scenarios"))],
    db: Annotated[Session, Depends(get_db)],
):
    q = db.query(Scenario).order_by(Scenario.updated_at.desc())
    if user.role != "admin":
        q = q.filter(Scenario.user_id == user.id)
    return [scenario_out(row) for row in q.all()]


@app.post("/api/scenarios", response_model=ScenarioOut, status_code=201)
def create_scenario(
    body: ScenarioCreate,
    user: Annotated[User, Depends(require_permission("scenarios"))],
    db: Annotated[Session, Depends(get_db)],
):
    if body.location_id and not analytics.location_in_scope(
        body.location_id, user.region, user.role
    ):
        raise HTTPException(status_code=403, detail="Location outside your regional scope")

    result = analytics.simulate(
        location_id=body.location_id or None,
        category=body.category or None,
        recovery_rate=body.recovery_rate,
        merchants_to_onboard=body.merchants_to_onboard,
        region=user.region,
        role=user.role,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    row = Scenario(
        user_id=user.id,
        name=body.name.strip(),
        notes=body.notes.strip(),
        location_id=body.location_id or None,
        category=body.category or None,
        recovery_rate=body.recovery_rate,
        merchants_to_onboard=body.merchants_to_onboard,
        baseline_boundary_value=result["baseline"]["boundary_cash_out_value"],
        projected_value_retained=result["projected"]["value_retained"],
        projected_merchant_payments=result["projected"]["digital_merchant_payments"],
        retention_lift_pct=result["projected"]["retention_lift_pct"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_event(
        db,
        user=user,
        action="scenario.created",
        entity_type="scenario",
        entity_id=row.id,
        detail=row.name,
    )
    db.commit()
    return scenario_out(row)


@app.delete("/api/scenarios/{scenario_id}", status_code=204)
def delete_scenario(
    scenario_id: int,
    user: Annotated[User, Depends(require_permission("scenarios"))],
    db: Annotated[Session, Depends(get_db)],
):
    row = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if user.role != "admin" and row.user_id != user.id:
        raise HTTPException(status_code=403, detail="Cannot delete another user's scenario")
    log_event(
        db,
        user=user,
        action="scenario.deleted",
        entity_type="scenario",
        entity_id=scenario_id,
        detail=row.name,
    )
    db.delete(row)
    db.commit()
    return None


@app.get("/api/pipeline", response_model=list[PipelineOut])
def list_pipeline(
    user: Annotated[User, Depends(require_permission("pipeline_view"))],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status"),
):
    q = db.query(PipelineItem).order_by(PipelineItem.updated_at.desc())
    if status_filter:
        q = q.filter(PipelineItem.status == status_filter)
    if not analytics.is_national_scope(user.region, user.role):
        q = q.filter(PipelineItem.region == user.region)
    return [pipeline_out(row) for row in q.all()]


@app.post("/api/pipeline", response_model=PipelineOut, status_code=201)
def create_pipeline_item(
    body: PipelineCreate,
    user: Annotated[User, Depends(require_permission("pipeline"))],
    db: Annotated[Session, Depends(get_db)],
):
    if not analytics.location_in_scope(body.location_id, user.region, user.role):
        raise HTTPException(status_code=403, detail="Location outside your regional scope")

    existing = (
        db.query(PipelineItem)
        .filter(
            PipelineItem.location_id == body.location_id,
            PipelineItem.merchant_category == body.merchant_category,
            PipelineItem.status.in_(["identified", "reviewing", "assigned"]),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="This location × category is already active in the pipeline",
        )

    row = PipelineItem(
        user_id=user.id,
        location_id=body.location_id,
        location_name=body.location_name.strip(),
        region=body.region.strip(),
        merchant_category=body.merchant_category.strip(),
        opportunity_score=body.opportunity_score,
        boundary_value=body.boundary_value,
        estimated_recoverable=body.estimated_recoverable,
        affected_customers=body.affected_customers,
        status="identified",
        assignee_name=body.assignee_name.strip(),
        notes=body.notes.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_event(
        db,
        user=user,
        action="pipeline.created",
        entity_type="pipeline_item",
        entity_id=row.id,
        detail=f"{row.location_name} · {row.merchant_category}",
    )
    db.commit()
    return pipeline_out(row)


@app.patch("/api/pipeline/{item_id}", response_model=PipelineOut)
def update_pipeline_item(
    item_id: int,
    body: PipelineUpdate,
    user: Annotated[User, Depends(require_permission("pipeline"))],
    db: Annotated[Session, Depends(get_db)],
):
    row = db.query(PipelineItem).filter(PipelineItem.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline item not found")

    changes = []
    if body.status is not None:
        if body.status not in PIPELINE_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Use one of: {', '.join(PIPELINE_STATUSES)}",
            )
        if body.status != row.status:
            changes.append(f"status {row.status} → {body.status}")
            row.status = body.status
    if body.notes is not None and body.notes != row.notes:
        row.notes = body.notes.strip()
        changes.append("notes updated")
    if body.assignee_name is not None and body.assignee_name != row.assignee_name:
        row.assignee_name = body.assignee_name.strip()
        changes.append(f"assignee → {row.assignee_name or 'unassigned'}")

    log_event(
        db,
        user=user,
        action="pipeline.updated",
        entity_type="pipeline_item",
        entity_id=row.id,
        detail="; ".join(changes) or "no changes",
    )
    db.commit()
    db.refresh(row)
    return pipeline_out(row)


@app.delete("/api/pipeline/{item_id}", status_code=204)
def delete_pipeline_item(
    item_id: int,
    user: Annotated[User, Depends(require_permission("pipeline"))],
    db: Annotated[Session, Depends(get_db)],
):
    row = db.query(PipelineItem).filter(PipelineItem.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline item not found")
    log_event(
        db,
        user=user,
        action="pipeline.deleted",
        entity_type="pipeline_item",
        entity_id=item_id,
        detail=f"{row.location_name} · {row.merchant_category}",
    )
    db.delete(row)
    db.commit()
    return None


@app.get("/api/audit", response_model=list[AuditOut])
def list_audit(
    _user: Annotated[User, Depends(require_permission("pipeline_view"))],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(30, ge=1, le=100),
):
    rows = db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit).all()
    out = []
    for row in rows:
        owner = db.query(User).filter(User.id == row.user_id).first() if row.user_id else None
        out.append(
            AuditOut(
                id=row.id,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                detail=row.detail or "",
                created_at=row.created_at,
                user_email=owner.email if owner else None,
            )
        )
    return out


@app.get("/api/assignees")
def list_assignees(
    _user: Annotated[User, Depends(require_permission("pipeline"))],
    db: Annotated[Session, Depends(get_db)],
):
    rows = (
        db.query(User)
        .filter(User.is_active.is_(True))
        .order_by(User.full_name)
        .all()
    )
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "region": u.region,
        }
        for u in rows
    ]


@app.get("/api/users", response_model=list[UserOut])
def list_users(
    _user: Annotated[User, Depends(require_permission("users"))],
    db: Annotated[Session, Depends(get_db)],
):
    return [user_out(u) for u in db.query(User).order_by(User.email).all()]


@app.post("/api/admin/refresh-data")
def refresh_data(
    user: Annotated[User, Depends(require_permission("config"))],
    db: Annotated[Session, Depends(get_db)],
):
    result = run_nightly_refresh(detail=f"Manual refresh by {user.email}")
    log_event(
        db,
        user=user,
        action="data.refreshed",
        entity_type="dataset",
        entity_id="postgres",
        detail=(
            f"Refreshed {result['transaction_count']} transactions, "
            f"{result['location_count']} locations, {result['merchant_count']} merchants, "
            f"{result['opportunity_count']} opportunity snapshots"
        ),
    )
    db.commit()
    return result


@app.post("/api/admin/upload")
async def upload_dataset(
    user: Annotated[User, Depends(require_permission("config"))],
    db: Annotated[Session, Depends(get_db)],
    dataset: Annotated[str, Form()],
    file: UploadFile = File(...),
):
    raw = await file.read()
    try:
        result = validate_and_save_csv(dataset, raw, file.filename or "upload.csv")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_event(
        db,
        user=user,
        action="data.uploaded",
        entity_type="dataset",
        entity_id=result["dataset"],
        detail=f"Uploaded {result['filename']} ({result['rows']} rows)",
    )
    db.commit()
    return {"status": "ok", **result}


@app.get("/api/admin/config")
def get_config(user: Annotated[User, Depends(require_permission("config"))]):
    meta = analytics.scope_meta(user.region, user.role)
    return {
        "product": "MoMo Loop",
        "version": app.version,
        "auth": "jwt",
        "cors_origins": CORS_ORIGINS,
        "scope": meta,
        "roles": sorted(ROLE_PERMISSIONS.keys()),
        "pipeline_statuses": list(PIPELINE_STATUSES),
        "upload_datasets": ["transactions", "merchants", "locations"],
        "data_store": "postgresql",
        "nightly_refresh": "02:00 UTC",
    }


# ---------------------------------------------------------------------------
# Production: serve the built React app from the same origin as the API
# ---------------------------------------------------------------------------
_STATIC_CANDIDATES: list[Path] = []
_frontend_dist_env = os.getenv("FRONTEND_DIST", "").strip()
if _frontend_dist_env:
    _STATIC_CANDIDATES.append(Path(_frontend_dist_env))
_STATIC_CANDIDATES.extend(
    [
        Path(__file__).resolve().parents[2] / "frontend" / "dist",
        Path("/app/frontend/dist"),
    ]
)
STATIC_DIR = next((p for p in _STATIC_CANDIDATES if (p / "index.html").exists()), None)

if STATIC_DIR is not None:
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        """SPA router fallback — never shadows /api/* routes registered above."""
        if full_path.startswith("api/") or full_path in {"docs", "openapi.json", "redoc"}:
            raise HTTPException(status_code=404, detail="Not found")
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
