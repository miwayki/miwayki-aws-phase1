from __future__ import annotations

"""Schemas para catálogo de tours."""

from typing import List, Optional

from pydantic import BaseModel


class VariantItem(BaseModel):
    code: str
    name: str
    price_adjustment_pen: float
    duration_days: Optional[int] = None


class TourItem(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    base_price_pen: float
    duration_days: int
    min_pax: int
    max_pax: int
    includes: Optional[str] = None
    excludes: Optional[str] = None
    variants: List[VariantItem] = []


class CatalogResponse(BaseModel):
    success: bool = True
    tours: List[TourItem]
    count: int
