from __future__ import annotations

"""Schemas para reservaciones y pagos."""

from typing import List, Optional

from pydantic import BaseModel, Field


class PaymentInstructionsRequest(BaseModel):
    conversation_id: int = Field(..., gt=0)
    quote_id: int = Field(..., gt=0)
    currency: str = "PEN"


class BankAccountInfo(BaseModel):
    bank_name: str
    account_holder: str
    account_number: str
    cci: Optional[str] = None
    account_type: str
    currency: str


class PaymentInstructionsResponse(BaseModel):
    success: bool = True
    reservation_id: int
    amount: float
    currency: str
    bank_accounts: List[BankAccountInfo]
    instructions: str
    commercial_state: str


class VoucherRequest(BaseModel):
    conversation_id: int = Field(..., gt=0)
    voucher_reference: Optional[str] = None


class VoucherResponse(BaseModel):
    success: bool = True
    reservation_id: int
    commercial_state: str
    message: str
    handoff_triggered: bool = True
    handoff_reason: str = "Voucher recibido — requiere verificación humana"
