"""Material inventory and procurement models."""

from datetime import datetime
from typing import List, Optional

from beanie import Document
from pydantic import BaseModel, field_validator

from backend.models.base import MemoryNode, _coerce_date_to_datetime


class Material(Document, MemoryNode):
    """Material master data for inventory-based project costing."""

    material_code: str
    name: str
    category: str = "raw_material"  # "raw_material" | "finished_good" | "consumable" | "tool"
    unit_of_measure: str = "pcs"  # "pcs", "kg", "m", "m2", "m3", "ltr", "roll"
    current_stock: float = 0.0
    minimum_stock: float = 0.0
    unit_cost: float = 0.0
    description: Optional[str] = None

    class Settings:
        name = "materials"
        indexes = ["uid", "material_code", "name", "category"]


class Supplier(Document, MemoryNode):
    """Supplier / vendor master data."""

    supplier_code: str
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

    class Settings:
        name = "suppliers"
        indexes = ["uid", "supplier_code", "name"]


class PurchaseOrderItem(BaseModel):
    material_id: int
    material_name: Optional[str] = None
    material_code: Optional[str] = None
    quantity: float
    unit_cost: float
    total_cost: float = 0.0


class PurchaseOrder(Document, MemoryNode):
    """Purchase order for procuring materials from a supplier."""

    po_number: str
    supplier_id: int
    supplier_name: Optional[str] = None
    items: List[PurchaseOrderItem] = []
    total_amount: float = 0.0
    status: str = "pending"  # "pending" | "received" | "partial" | "cancelled"
    notes: Optional[str] = None
    ordered_by_admin_id: Optional[int] = None
    expected_delivery: Optional[datetime] = None
    received_at: Optional[datetime] = None

    @field_validator("expected_delivery", "received_at", mode="before")
    @classmethod
    def coerce_po_dates(cls, v):
        return _coerce_date_to_datetime(v)

    class Settings:
        name = "purchase_orders"
        indexes = ["uid", "po_number", "supplier_id", "status"]


class MaterialMovement(Document, MemoryNode):
    """Tracks stock IN/OUT movements for each material."""

    material_id: int
    material_name: Optional[str] = None
    movement_type: str  # "IN" | "OUT"
    quantity: float
    unit_cost: float = 0.0
    total_cost: float = 0.0
    reference_type: Optional[str] = None  # "purchase_order" | "contract_usage" | "adjustment"
    reference_id: Optional[int] = None  # PO uid or contract uid
    reference_code: Optional[str] = None  # PO number or contract code
    notes: Optional[str] = None
    performed_by_admin_id: Optional[int] = None

    class Settings:
        name = "material_movements"
        indexes = ["uid", "material_id", "movement_type", "reference_id"]
