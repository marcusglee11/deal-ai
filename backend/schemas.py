# backend/schemas.py

from typing import List, Dict, Any
from pydantic import BaseModel, Field, validator

class CashflowEntry(BaseModel):
    period: str              # e.g., "2023-Q4" or "2023-12-31"
    ebitda: float
    revenue: float
    opex: float

    @validator("ebitda")
    def ebitda_non_negative(cls, v):
        if v < 0:
            raise ValueError("EBITDA must be ≥ 0")
        return v

class DebtInstrument(BaseModel):
    name: str
    amount: float
    interest_rate: float

class ParsedDocument(BaseModel):
    filename: str
    file_id: str
    text: str = ""                                 # full extracted text
    tables: List[Dict[str, Any]] = Field(default_factory=list)   # list of parsed tables as list-of-dicts
    cashflow: List[CashflowEntry] = Field(default_factory=list)
    debt_schedule: List[DebtInstrument] = Field(default_factory=list)

class DealData(BaseModel):
    deal_id: str
    documents: List[ParsedDocument]
