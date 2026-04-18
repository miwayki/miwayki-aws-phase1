from __future__ import annotations

"""Schemas para leads."""

from typing import List, Optional, Any

from pydantic import BaseModel, Field, field_validator


class LeadUpsertRequest(BaseModel):
    conversation_id: Optional[int] = Field(1, description="ID de conversacion de Chatwoot. Default: 1.")
    
    @field_validator('conversation_id', mode='before')
    @classmethod
    def parse_conv_id(cls, v: Any) -> int:
        if isinstance(v, str):
            if v.startswith("chatwoot-") or v.startswith("cw2-"):
                v = v.replace("chatwoot-", "").replace("cw2-", "")
            try:
                return int(v)
            except ValueError:
                return 1
        if v is None:
            return 1
        return int(v)
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
