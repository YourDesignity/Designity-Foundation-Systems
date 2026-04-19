"""Service layer for contract role slot operations."""

import logging
from datetime import datetime
from typing import Any, List

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class ContractRoleService(BaseService):
    """Business logic for contract role slot configuration."""

    @staticmethod
    def _admin_only(current_user: dict) -> None:
        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Only Admins can manage contract role slots")

    async def configure_role_slots(self, payload: Any, current_user: dict) -> dict:
        from backend.models import Contract, ContractRoleSlot

        self._admin_only(current_user)

        contract = await Contract.find_one(Contract.uid == payload.contract_id)
        if not contract:
            self.raise_not_found("Contract not found")

        slot_ids = [s.slot_id for s in payload.slots]
        if len(slot_ids) != len(set(slot_ids)):
            self.raise_bad_request("Slot IDs must be unique within the contract")

        for s in payload.slots:
            if s.daily_rate <= 0:
                self.raise_bad_request(f"Daily rate for slot '{s.slot_id}' must be greater than 0")

        contract.role_slots = [
            ContractRoleSlot(slot_id=s.slot_id, designation=s.designation, daily_rate=s.daily_rate)
            for s in payload.slots
        ]
        contract.contract_type = "DEDICATED_STAFF"
        contract.recalculate_role_summary()
        contract.updated_at = datetime.now()
        await contract.save()

        return contract.model_dump(mode="json")

    async def list_all_contract_roles(self) -> dict:
        from backend.models import Contract

        contracts = await Contract.find(Contract.contract_type == "DEDICATED_STAFF").to_list()

        return {
            "contracts": [
                {
                    "contract_id": contract.uid,
                    "contract_code": contract.contract_code,
                    "contract_type": contract.contract_type,
                    "total_role_slots": contract.total_role_slots,
                    "total_daily_cost": contract.total_daily_cost,
                    "roles_by_designation": contract.roles_by_designation,
                    "role_slots": [s.model_dump() for s in contract.role_slots],
                }
                for contract in contracts
            ]
        }

    async def get_role_configuration(self, contract_id: int) -> dict:
        from backend.models import Contract

        contract = await Contract.find_one(Contract.uid == contract_id)
        if not contract:
            self.raise_not_found("Contract not found")

        return {
            "contract_id": contract.uid,
            "contract_code": contract.contract_code,
            "contract_type": contract.contract_type,
            "total_role_slots": contract.total_role_slots,
            "total_daily_cost": contract.total_daily_cost,
            "roles_by_designation": contract.roles_by_designation,
            "role_slots": [s.model_dump() for s in contract.role_slots],
        }

    async def upsert_role_slots(self, contract_id: int, slots: List[Any], current_user: dict) -> dict:
        from backend.models import Contract, ContractRoleSlot

        self._admin_only(current_user)

        contract = await Contract.find_one(Contract.uid == contract_id)
        if not contract:
            self.raise_not_found("Contract not found")

        for slot_data in slots:
            if slot_data.daily_rate <= 0:
                self.raise_bad_request(f"Daily rate for slot '{slot_data.slot_id}' must be greater than 0")

        existing: dict[str, ContractRoleSlot] = {s.slot_id: s for s in contract.role_slots}

        for slot_data in slots:
            if slot_data.slot_id in existing:
                existing[slot_data.slot_id].designation = slot_data.designation
                existing[slot_data.slot_id].daily_rate = slot_data.daily_rate
            else:
                existing[slot_data.slot_id] = ContractRoleSlot(
                    slot_id=slot_data.slot_id,
                    designation=slot_data.designation,
                    daily_rate=slot_data.daily_rate,
                )

        contract.role_slots = list(existing.values())
        contract.recalculate_role_summary()
        contract.updated_at = datetime.now()
        await contract.save()

        return contract.model_dump(mode="json")

    async def delete_role_slot(self, contract_id: int, slot_id: str, current_user: dict) -> dict:
        from backend.models import Contract

        self._admin_only(current_user)

        contract = await Contract.find_one(Contract.uid == contract_id)
        if not contract:
            self.raise_not_found("Contract not found")

        original_count = len(contract.role_slots)
        contract.role_slots = [s for s in contract.role_slots if s.slot_id != slot_id]

        if len(contract.role_slots) == original_count:
            self.raise_not_found(f"Slot '{slot_id}' not found in contract")

        contract.recalculate_role_summary()
        contract.updated_at = datetime.now()
        await contract.save()

        return {"message": f"Slot '{slot_id}' removed successfully"}
