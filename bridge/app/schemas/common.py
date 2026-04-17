from __future__ import annotations

"""Schemas base compartidos."""

from typing import Optional

from pydantic import BaseModel


class SuccessResponse(BaseModel):
    success: bool = True


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
    details: Optional[dict] = None
