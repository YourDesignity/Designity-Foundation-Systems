from datetime import date, datetime, time, timedelta
from typing import List, Optional

from backend.models import Contract
from backend.services.base_service import BaseService


class ContractService(BaseService):
    """Contract-related business operations."""

    async def get_contract(self, contract_id: int) -> Optional[Contract]:
        return await Contract.find_one(Contract.uid == contract_id)

    async def ensure_contract(self, contract_id: int) -> Contract:
        contract = await self.get_contract(contract_id)
        if not contract:
            self.raise_not_found("Contract not found")
        return contract

    @staticmethod
    def get_slot_designation(contract: Contract, slot_id: str) -> Optional[str]:
        slot = next((s for s in contract.role_slots if s.slot_id == slot_id), None)
        return slot.designation if slot else None

    @staticmethod
    def calculate_duration_days(contract: Contract) -> int:
        return (contract.end_date - contract.start_date).days

    async def get_expiring_contracts(self, within_days: int = 30) -> List[Contract]:
        today = datetime.combine(date.today(), time.min)
        window_end = today + timedelta(days=within_days)
        return await Contract.find(
            Contract.status == "Active",
            Contract.end_date >= today,
            Contract.end_date <= window_end,
        ).to_list()
