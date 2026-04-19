"""Service layer for legacy ContractSpec router operations."""

from datetime import datetime

from backend.models import ContractSpec as Contract, ProjectExpense
from backend.services.base_service import BaseService


class ContractSpecService(BaseService):
    """CRUD and expense logging for ContractSpec records."""

    async def get_contracts(self):
        return await Contract.find_all().sort("-created_at").to_list()

    async def add_contract(self, contract: Contract):
        contract.uid = await self.get_next_uid("contracts")
        if contract.contract_type == "GOODS_STORAGE" and contract.items:
            contract.total_value = sum((item.quantity * item.unit_rate) for item in contract.items)
        await contract.create()
        return contract

    async def add_project_expense(self, uid: int, expense: ProjectExpense):
        contract = await Contract.find_one(Contract.uid == uid)
        if not contract:
            self.raise_not_found("Contract not found")

        expense.uid = await self.get_next_uid("project_expenses")
        if not expense.date:
            expense.date = datetime.now()
        if not contract.expenses:
            contract.expenses = []
        contract.expenses.append(expense)
        await contract.save()
        return contract

    async def delete_contract(self, uid: int):
        contract = await Contract.find_one(Contract.uid == uid)
        if not contract:
            self.raise_not_found("Contract not found")
        await contract.delete()
        return {"message": "Contract deleted"}
