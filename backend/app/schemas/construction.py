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