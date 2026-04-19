"""Goods & Storage Contract — collect, store, and track materials."""

from calendar import monthrange
from datetime import datetime
from typing import Any, Dict, List

from backend.models.contracts.base_contract import BaseContract, ContractType


class GoodsContract(BaseContract):
    """
    Goods & Storage Contract (was: Goods Supply Contract).
    Handles arrival-based inventory logging, item condition tracking,
    and workshop repair jobs for damaged items.
    """

    item_catalogue_ids: List[int] = []       # Which catalogue items apply to this contract
    workshop_enabled: bool = True             # Internal repair workshop
    client_repair_enabled: bool = False       # Optional: repair for client

    # Legacy fields kept for backward compat
    material_items: List[Dict[str, Any]] = []
    delivery_schedule: List[Dict[str, Any]] = []

    def __init__(self, **data: Any) -> None:
        data.setdefault("enabled_modules", ["inventory", "workshop", "materials"])
        data.setdefault("salary_strategy", "none")
        data.setdefault("contract_type", ContractType.GOODS_STORAGE)
        super().__init__(**data)

    async def calculate_monthly_cost(self, month: int, year: int) -> float:
        from backend.models.materials import MaterialMovement
        _, last_day = monthrange(year, month)
        start = datetime(year, month, 1)
        end = datetime(year, month, last_day, 23, 59, 59)
        movements = await MaterialMovement.find(
            MaterialMovement.contract_id == self.uid,
            MaterialMovement.movement_type == "OUT",
            MaterialMovement.created_at >= start,
            MaterialMovement.created_at <= end,
        ).to_list()
        return sum(m.total_cost or 0 for m in movements)

    async def calculate_employee_salary(self, employee_id: int, month: int, year: int) -> float:
        return 0.0

    async def get_required_resources(self) -> Dict[str, Any]:
        return {"catalogue_items": self.item_catalogue_ids}

    async def validate_fulfillment(self, date: datetime) -> Dict[str, Any]:
        return {"fulfilled": True, "message": "Goods fulfillment validation not yet implemented"}
