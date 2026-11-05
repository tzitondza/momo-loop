"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    region: str
    permissions: list[str]

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ScenarioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    notes: str = ""
    location_id: str | None = None
    category: str | None = None
    recovery_rate: float = Field(default=0.35, ge=0.05, le=0.9)
    merchants_to_onboard: int = Field(default=5, ge=1, le=50)


class ScenarioOut(BaseModel):
    id: int
    name: str
    notes: str
    location_id: str | None
    category: str | None
    recovery_rate: float
    merchants_to_onboard: int
    baseline_boundary_value: float
    projected_value_retained: float
    projected_merchant_payments: float
    retention_lift_pct: float
    created_at: datetime
    updated_at: datetime
    owner_email: str | None = None
    owner_name: str | None = None

    model_config = {"from_attributes": True}


class PipelineCreate(BaseModel):
    location_id: str = Field(min_length=1, max_length=50)
    location_name: str = Field(min_length=1, max_length=200)
    region: str = ""
    merchant_category: str = Field(min_length=1, max_length=100)
    opportunity_score: float = 0.0
    boundary_value: float = 0.0
    estimated_recoverable: float = 0.0
    affected_customers: int = 0
    notes: str = ""
    assignee_name: str = ""


class PipelineUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    assignee_name: str | None = None


class PipelineOut(BaseModel):
    id: int
    location_id: str
    location_name: str
    region: str
    merchant_category: str
    opportunity_score: float
    boundary_value: float
    estimated_recoverable: float
    affected_customers: int
    status: str
    assignee_name: str
    notes: str
    created_at: datetime
    updated_at: datetime
    owner_email: str | None = None
    owner_name: str | None = None

    model_config = {"from_attributes": True}


class AuditOut(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: str
    detail: str
    created_at: datetime
    user_email: str | None = None

    model_config = {"from_attributes": True}
