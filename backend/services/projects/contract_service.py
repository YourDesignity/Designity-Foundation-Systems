"""Service layer for project contract operations."""

import logging
from datetime import date, datetime, timedelta
from typing import Any, List, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class ContractService(BaseService):
    """Business logic for contract lifecycle and role-slot configuration."""

    async def create_contract(self, payload: Any, created_by_admin_id: int | None = None):
        """
        Create a new contract linked to a project.

        Validations:
        - Project must exist
        - start_date/end_date are required
        - Contract code is generated from company settings

        Args:
            payload: Contract payload
            created_by_admin_id: Admin UID creating the contract

        Returns:
            Created contract document
        """
        from backend.models import CompanySettings, Contract, Project

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        project_id = data.get("project_id")
        if project_id is None:
            self.raise_bad_request("project_id is required")

        project = await Project.find_one(Project.uid == project_id)
        if not project:
            self.raise_not_found("Project not found")

        settings = await CompanySettings.find_one(CompanySettings.uid == 1)
        new_uid = await self.get_next_uid("contracts")
        prefix = (settings.contract_code_prefix if settings and settings.auto_generate_contract_codes else "CNT") or "CNT"
        contract_code = f"{prefix}-{new_uid:03d}"

        contract = Contract(
            uid=new_uid,
            contract_code=contract_code,
            contract_name=data.get("contract_name"),
            contract_type=data.get("contract_type", "Labour"),
            project_id=project_id,
            project_name=project.project_name,
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            contract_value=float(data.get("contract_value", 0.0)),
            payment_terms=data.get("payment_terms"),
            contract_terms=data.get("contract_terms"),
            notes=data.get("notes"),
            created_by_admin_id=created_by_admin_id or data.get("created_by_admin_id"),
        )
        await contract.insert()
        await contract.calculate_duration()

        if contract.uid not in project.contract_ids:
            project.contract_ids.append(contract.uid)
            await project.save()

        logger.info("Contract created: %s (ID: %s)", contract.contract_code, contract.uid)
        return contract

    async def configure_role_slots(self, contract_id: int, slots: list[Any]):
        """
        Define/replace role slots for a labour contract.

        Validations:
        - Contract must exist
        - slot_id values must be unique
        - daily_rate must be > 0

        Args:
            contract_id: Contract UID
            slots: Slot payload list

        Returns:
            Updated contract document
        """
        from backend.models import Contract, ContractRoleSlot

        contract = await Contract.find_one(Contract.uid == contract_id)
        if not contract:
            self.raise_not_found("Contract not found")

        normalized_slots = [s.model_dump(exclude_unset=True) if hasattr(s, "model_dump") else dict(s) for s in slots]
        slot_ids = [s.get("slot_id") for s in normalized_slots]
        if len(slot_ids) != len(set(slot_ids)):
            self.raise_bad_request("Slot IDs must be unique within the contract")

        for slot in normalized_slots:
            if float(slot.get("daily_rate", 0)) <= 0:
                self.raise_bad_request(f"Daily rate for slot '{slot.get('slot_id')}' must be greater than 0")

        contract.role_slots = [
            ContractRoleSlot(
                slot_id=slot["slot_id"],
                designation=slot["designation"],
                daily_rate=float(slot["daily_rate"]),
            )
            for slot in normalized_slots
        ]
        contract.contract_type = "Labour"
        contract.recalculate_role_summary()
        contract.updated_at = datetime.now()
        await contract.save()

        logger.info("Configured %s role slots for contract %s", len(contract.role_slots), contract_id)
        return contract

    async def get_expiring_contracts(self, within_days: int = 30) -> List[Any]:
        """
        Get active contracts expiring within a time window.

        Args:
            within_days: Positive number of days from today

        Returns:
            List of expiring contracts
        """
        from backend.models import Contract

        if within_days < 0:
            self.raise_bad_request("within_days must be >= 0")

        today = datetime.combine(date.today(), datetime.min.time())
        window_end = today + timedelta(days=within_days)
        return await Contract.find(
            Contract.status == "Active",
            Contract.end_date >= today,
            Contract.end_date <= window_end,
        ).to_list()

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
        if "start_date" in data or "end_date" in data:
            await contract.calculate_duration()
        else:
            await contract.save()
        logger.info("Contract updated: ID %s", contract_id)
        return contract

    async def delete_contract(self, contract_id: int) -> bool:
        contract = await self.ensure_contract(contract_id)
        await contract.delete()
        logger.info("Contract deleted: ID %s", contract_id)
        return True

    @staticmethod
    def get_slot_designation(contract, slot_id: str) -> Optional[str]:
        slot = next((s for s in contract.role_slots if s.slot_id == slot_id), None)
        return slot.designation if slot else None

    @staticmethod
    def calculate_duration_days(contract) -> int:
        return (contract.end_date - contract.start_date).days
