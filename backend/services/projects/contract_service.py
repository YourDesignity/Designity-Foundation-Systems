"""Service layer for contract operations."""

from datetime import date, datetime, timedelta
from typing import Any, List, Optional

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class ContractService(BaseService):
    """Contract-related business operations."""

    async def create_contract(self, payload: Any):
        from backend.models import Contract

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("contracts")
        contract = Contract(**data)
        await contract.insert()
        return contract

    async def get_contract(self, contract_id: int) -> Optional[Any]:
        from backend.models import Contract

        return await Contract.find_one(Contract.uid == contract_id)

    async def ensure_contract(self, contract_id: int):
        contract = await self.get_contract(contract_id)
        if not contract:
            self.raise_not_found("Contract not found")
        return contract

    async def get_contracts(self):
        from backend.models import Contract

        return await Contract.find_all().sort("+uid").to_list()

    async def update_contract(self, contract_id: int, payload: Any):
        contract = await self.ensure_contract(contract_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(contract, field, value)
        await contract.save()
        return contract

    async def delete_contract(self, contract_id: int) -> bool:
        contract = await self.ensure_contract(contract_id)
        await contract.delete()
        return True

    @staticmethod
    def get_slot_designation(contract, slot_id: str) -> Optional[str]:
        slot = next((s for s in contract.role_slots if s.slot_id == slot_id), None)
        return slot.designation if slot else None

    @staticmethod
    def calculate_duration_days(contract) -> int:
        return (contract.end_date - contract.start_date).days

    async def get_expiring_contracts(self, within_days: int = 30) -> List[Any]:
        from backend.models import Contract

        today = datetime.combine(date.today(), datetime.min.time())
        window_end = today + timedelta(days=within_days)
        return await Contract.find(
            Contract.status == "Active",
            Contract.end_date >= today,
            Contract.end_date <= window_end,
        ).to_list()
