"""Payroll-related models."""

from typing import Optional

from beanie import Document

from backend.models.base import MemoryNode


class Overtime(Document, MemoryNode):
    employee_uid: Optional[int] = None
    date: str
    hours: float
    type: str
    reason: Optional[str] = None

    class Settings:
        name = "overtime"


class Deduction(Document, MemoryNode):
    employee_uid: Optional[int] = None
    pay_period: str
    amount: float
    reason: Optional[str] = None

    class Settings:
        name = "deductions"
