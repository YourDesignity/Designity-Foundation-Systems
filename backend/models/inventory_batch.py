"""
Inventory Batch and Workshop Job models.

Phase 8 — Arrival-based inventory logging.
Phase 9 — Workshop repair job tracking.
"""

from datetime import datetime
from typing import List, Optional

from beanie import Document
from pydantic import BaseModel, Field, field_validator

from backend.models.base import MemoryNode, _coerce_date_to_datetime


# ─── Batch Item ───────────────────────────────────────────────────────────────

class BatchItem(BaseModel):
    """A single item within an inventory arrival batch."""

    uid: int
    catalogue_item_id: int           # References ItemCatalogue.uid
    catalogue_item_name: str         # Denormalized for display
    category: str                    # Denormalized
    unit: str                        # Denormalized (pcs / kg / etc.)
    quantity: float

    # Condition on arrival — set by manager
    condition: str = "GOOD"          # GOOD | DAMAGED | NEEDS_REPAIR
    condition_notes: Optional[str] = None

    # Workshop linkage
    repair_requested: bool = False
    workshop_job_id: Optional[int] = None


# ─── Inventory Batch ─────────────────────────────────────────────────────────

class InventoryBatch(Document, MemoryNode):
    """
    An arrival event logged by a site manager.
    One batch = one delivery/collection at a site on a given day.
    """

    batch_code: str                  # BATCH-001
    contract_id: int                 # REQUIRED — must belong to a contract
    site_id: int
    project_id: int                  # Denormalized

    logged_by_manager_id: int
    logged_at: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = None
    status: str = "OPEN"             # OPEN | CLOSED

    items: List[BatchItem] = []

    # Computed summary
    total_items: int = 0
    total_good: int = 0
    total_damaged: int = 0
    total_needs_repair: int = 0

    @field_validator("logged_at", mode="before")
    @classmethod
    def coerce_logged_at(cls, v):
        return _coerce_date_to_datetime(v)

    def recalculate_summary(self) -> None:
        self.total_items        = len(self.items)
        self.total_good         = sum(1 for i in self.items if i.condition == "GOOD")
        self.total_damaged      = sum(1 for i in self.items if i.condition == "DAMAGED")
        self.total_needs_repair = sum(1 for i in self.items if i.condition == "NEEDS_REPAIR")

    class Settings:
        name = "inventory_batches"
        indexes = [
            "uid", "batch_code", "contract_id",
            "site_id", "project_id", "logged_by_manager_id", "status",
        ]


# ─── Workshop Job ─────────────────────────────────────────────────────────────

class WorkshopJob(Document, MemoryNode):
    """
    A repair job created from a damaged or needs-repair BatchItem.
    Purely internal — company fixes items for the client.
    Optionally flagged as client-facing repair (client_repair).
    """

    job_code: str                    # WS-001
    batch_id: int
    batch_item_uid: int              # The specific BatchItem uid
    contract_id: int
    site_id: int
    project_id: int                  # Denormalized

    item_name: str                   # Denormalized from BatchItem
    category: str
    quantity_for_repair: float
    condition_on_arrival: str        # DAMAGED | NEEDS_REPAIR

    assigned_employee_ids: List[int] = []
    assigned_employee_names: List[str] = []

    status: str = "PENDING"          # PENDING | IN_PROGRESS | FIXED | SCRAPPED | CLIENT_REPAIR
    priority: str = "MEDIUM"         # LOW | MEDIUM | HIGH | URGENT

    is_client_repair: bool = False   # Admin-only flag
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

    created_by_manager_id: int
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator("started_at", "completed_at", "created_at", "updated_at", mode="before")
    @classmethod
    def coerce_dates(cls, v):
        return _coerce_date_to_datetime(v)

    class Settings:
        name = "workshop_jobs"
        indexes = [
            "uid", "job_code", "batch_id", "contract_id",
            "site_id", "project_id", "status", "priority",
            "assigned_employee_ids",
        ]


# ─── Item Catalogue ───────────────────────────────────────────────────────────

class ItemCatalogue(Document, MemoryNode):
    """
    Admin-managed predefined item list.
    Managers pick from this catalogue when logging batch arrivals.
    """

    name: str
    category: str
    unit: str
    description: Optional[str] = None
    is_active: bool = True
    created_by_admin_id: Optional[int] = None
    updated_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "item_catalogue"
        indexes = ["uid", "name", "category", "is_active"]
