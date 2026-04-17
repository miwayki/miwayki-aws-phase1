from __future__ import annotations

"""Schemas para leads."""

from typing import List, Optional

from pydantic import BaseModel, Field


class LeadUpsertRequest(BaseModel):
    conversation_id: int = Field(..., gt=0)
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    destination: Optional[str] = None
    travel_dates: Optional[str] = None
    party_size: Optional[int] = Field(None, ge=1)
    group_type: Optional[str] = None
    budget_range: Optional[str] = None
    urgency: Optional[str] = None
    special_requirements: Optional[str] = None


class LeadResponse(BaseModel):
    success: bool = True
    lead_id: int
    conversation_id: int
    commercial_state: str
    is_new: bool
    fields_updated: List[str] = []
    lead_score: int = 0
    lead_temperature: str = "cold"
