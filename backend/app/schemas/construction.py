"""Pydantic response schemas."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_code: str
    project_name: str
    project_type: str
    client_name: str
    city: str
    start_date: str
    planned_finish: str
    actual_finish: Optional[str] = None
    status: str
    budget: float


class SupplierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_name: str
    category: str
    city: str
    status: str
    po_count: int = 0
    on_time_rate: Optional[float] = None


class DecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    meeting_id: int
    decision_date: str
    decision_text: str
    owner: str


class MeetingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    meeting_date: str
    title: str
    meeting_type: str


class MeetingWithDecisionsRead(MeetingRead):
    decisions: list[DecisionRead] = []


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pr_id: int
    project_id: int
    supplier_id: int
    po_number: str
    issue_date: str
    promised_delivery: str
    actual_delivery: Optional[str] = None
    status: str
    is_late: int
    delay_days: int
    delay_root_cause: Optional[str] = None


class NCRRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    supplier_id: Optional[int] = None
    subcontractor_id: Optional[int] = None
    ncr_type: str
    description: str
    root_cause: str
    issue_date: str
    status: str


class SafetyEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    subcontractor_id: int
    event_date: str
    severity: str
    description: str
    corrective_action: str