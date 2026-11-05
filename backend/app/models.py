"""ORM models for users and saved scenarios."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

ROLES = ("viewer", "analyst", "acquisition_lead", "admin")

# What each role can access
PIPELINE_STATUSES = (
    "identified",
    "reviewing",
    "assigned",
    "onboarded",
    "measured",
)

ROLE_PERMISSIONS = {
    "viewer": {"overview", "boundaries", "map", "filters"},
    "analyst": {
        "overview",
        "boundaries",
        "map",
        "filters",
        "opportunities",
        "simulate",
        "pipeline_view",
    },
    "acquisition_lead": {
        "overview",
        "boundaries",
        "map",
        "filters",
        "opportunities",
        "simulate",
        "scenarios",
        "pipeline_view",
        "pipeline",
    },
    "admin": {
        "overview",
        "boundaries",
        "map",
        "filters",
        "opportunities",
        "simulate",
        "scenarios",
        "pipeline_view",
        "pipeline",
        "users",
        "config",
    },
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="viewer")
    region: Mapped[str] = mapped_column(String(100), default="South Africa")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    scenarios: Mapped[list["Scenario"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    pipeline_items: Mapped[list["PipelineItem"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, default="")
    location_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recovery_rate: Mapped[float] = mapped_column(Float, default=0.35)
    merchants_to_onboard: Mapped[int] = mapped_column(Integer, default=5)
    baseline_boundary_value: Mapped[float] = mapped_column(Float, default=0.0)
    projected_value_retained: Mapped[float] = mapped_column(Float, default=0.0)
    projected_merchant_payments: Mapped[float] = mapped_column(Float, default=0.0)
    retention_lift_pct: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    owner: Mapped[User] = relationship(back_populates="scenarios")


class PipelineItem(Base):
    """Merchant acquisition opportunity tracked through an onboarding workflow."""

    __tablename__ = "pipeline_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    location_id: Mapped[str] = mapped_column(String(50), index=True)
    location_name: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(100), default="")
    merchant_category: Mapped[str] = mapped_column(String(100), index=True)
    opportunity_score: Mapped[float] = mapped_column(Float, default=0.0)
    boundary_value: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_recoverable: Mapped[float] = mapped_column(Float, default=0.0)
    affected_customers: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="identified", index=True)
    assignee_name: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    owner: Mapped[User] = relationship(back_populates="pipeline_items")


class AuditEvent(Base):
    """Lightweight activity trail for pipeline and scenario actions."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(50), default="")
    entity_id: Mapped[str] = mapped_column(String(50), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LocationRecord(Base):
    __tablename__ = "locations"

    location_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(100), index=True)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    urban: Mapped[bool] = mapped_column(Boolean, default=False)


class MerchantRecord(Base):
    __tablename__ = "merchants"

    merchant_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    location_id: Mapped[str] = mapped_column(String(50), index=True)
    merchant_category: Mapped[str] = mapped_column(String(100), index=True)
    accepts_momo: Mapped[str] = mapped_column(String(20), default="No")
    is_planted_gap: Mapped[bool] = mapped_column(Boolean, default=False)


class TransactionRecord(Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(50), index=True)
    transaction_type: Mapped[str] = mapped_column(String(50), index=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    location_id: Mapped[str] = mapped_column(String(50), index=True)
    merchant_category: Mapped[str] = mapped_column(String(100), default="")
    merchant_id: Mapped[str] = mapped_column(String(50), default="")
    merchant_accepts_momo: Mapped[str] = mapped_column(String(20), default="")
    related_inflow_id: Mapped[str] = mapped_column(String(50), default="")
    minutes_after_inflow: Mapped[float | None] = mapped_column(Float, nullable=True)


class OpportunitySnapshot(Base):
    """Materialised opportunity ranking produced by the refresh job."""

    __tablename__ = "opportunity_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    location_id: Mapped[str] = mapped_column(String(50), index=True)
    location_name: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(100), index=True)
    merchant_category: Mapped[str] = mapped_column(String(100), index=True)
    opportunity_score: Mapped[float] = mapped_column(Float, default=0.0)
    boundary_value: Mapped[float] = mapped_column(Float, default=0.0)
    boundary_count: Mapped[int] = mapped_column(Integer, default=0)
    affected_customers: Mapped[int] = mapped_column(Integer, default=0)
    acceptance_rate: Mapped[float] = mapped_column(Float, default=0.0)
    acceptance_gap: Mapped[float] = mapped_column(Float, default=0.0)
    feasibility: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_recoverable: Mapped[float] = mapped_column(Float, default=0.0)
    is_planted_gap: Mapped[bool] = mapped_column(Boolean, default=False)
    lat: Mapped[float] = mapped_column(Float, default=0.0)
    lng: Mapped[float] = mapped_column(Float, default=0.0)
    refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class DataRefreshMeta(Base):
    __tablename__ = "data_refresh_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(100), default="postgres")
    dataset_label: Mapped[str] = mapped_column(String(200), default="South Africa MoMo sample")
    last_refreshed: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    location_count: Mapped[int] = mapped_column(Integer, default=0)
    merchant_count: Mapped[int] = mapped_column(Integer, default=0)
    opportunity_count: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[str] = mapped_column(Text, default="")
