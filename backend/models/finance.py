"""Finance and invoicing models."""

from typing import List, Optional

from beanie import Document
from pydantic import BaseModel

from backend.models.base import MemoryNode


class InvoiceItem(BaseModel):
    description: str
    quantity: float
    unit_rate: float
    total: float


class Invoice(Document, MemoryNode):
    invoice_no: Optional[str] = None  # FIXED: Made optional for 422 error
    project_uid: int
    client_name: str
    date: str
    due_date: str
    items: List[InvoiceItem] = []
    total_amount: float
    status: str = "Unpaid"

    class Settings:
        name = "invoices"
