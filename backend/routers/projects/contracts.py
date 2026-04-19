from fastapi import APIRouter
from typing import List
from backend.models import ContractSpec as Contract, ProjectExpense
from backend.services.projects.contract_spec_service import ContractSpecService

router = APIRouter(prefix="/contracts", tags=["Contracts"])
service = ContractSpecService()

@router.get("/", response_model=List[Contract])
async def get_contracts():
    return await service.get_contracts()

@router.post("/")
async def add_contract(contract: Contract):
    return await service.add_contract(contract)

# API to Log Expenses (Stops offline theft)
@router.post("/{uid}/expense")
async def add_project_expense(uid: int, expense: ProjectExpense):
    return await service.add_project_expense(uid, expense)

@router.delete("/{uid}")
async def delete_contract(uid: int):
    return await service.delete_contract(uid)
