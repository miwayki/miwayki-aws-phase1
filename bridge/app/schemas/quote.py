from __future__ import annotations

"""Schemas para cotización."""

from datetime import date
from enum import Enum
from typing import List, Optional, Any

from pydantic import BaseModel, Field, field_validator


class GroupType(str, Enum):
    individual = "individual"
    family = "family"
    school = "school"
    corporate = "corporate"


class QuoteRequest(BaseModel):
    conversation_id: Optional[int] = Field(1, description="ID de conversacion de Chatwoot. Default: 1.")
    
    @field_validator('conversation_id', mode='before')
    @classmethod
    def parse_conv_id(cls, v: Any) -> int:
        if isinstance(v, str):
            v = v.replace('chatwoot-', '').replace('cw2-', '')
            try:
                return int(v)
            except ValueError:
                return 1
        if v is None:
            return 1
        return int(v)
    tour_code: str = Field(..., min_length=1)
    variant_code: Optional[str] = None
    travel_date: date
    party_size: int = Field(..., ge=1)
    group_type: GroupType = GroupType.individual


class QuoteBreakdownResponse(BaseModel):
    base_price_per_person: float
    base_total: float
    season_name: Optional[str] = None
    season_adjustment: float = 0.0
    holiday_name: Optional[str] = None
    holiday_adjustment: float = 0.0
    group_adjustment: float = 0.0
    group_rules_applied: List[str] = []
    exception_adjustment: float = 0.0
    exceptions_applied: List[str] = []
    total_price_pen: float
    per_person_pen: float


class QuoteResponse(BaseModel):
    success: bool = True
    quote_id: int
    tour_name: str
    variant_name: Optional[str] = None
    travel_date: str
    party_size: int
    breakdown: QuoteBreakdownResponse
    valid_until: str
    message: str
    handoff_triggered: bool = False
    handoff_reason: Optional[str] = None
