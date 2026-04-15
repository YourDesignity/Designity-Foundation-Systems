from fastapi import APIRouter, HTTPException
from typing import List
from backend.models import ContractSpec as Contract, ProjectExpense
from backend.database import get_next_uid
from datetime import datetime

router = APIRouter(prefix="/contracts", tags=["Contracts"])

@router.get("/", response_model=List[Contract])
async def get_contracts():
    return await Contract.find_all().sort("-created_at").to_list()

@router.post("/")
async def add_contract(contract: Contract):
    contract.uid = await get_next_uid("contracts")
    # Auto-calculate total value from PO items if provided
    if contract.contract_type == "Goods & Services" and contract.items:
        contract.total_value = sum((item.quantity * item.unit_rate) for item in contract.items)
    
    await contract.create()
    return contract

# API to Log Expenses (Stops offline theft)
@router.post("/{uid}/expense")
async def add_project_expense(uid: int, expense: ProjectExpense):
    contract = await Contract.find_one(Contract.uid == uid)
    if not contract:
        raise HTTPException(status_code=404, detail="Project not found")
    
    expense.uid = await get_next_uid("project_expenses")
    # Ensure date is set if missing
    if not expense.date:
        expense.date = datetime.now()
        
    if not contract.expenses:
        contract.expenses = []
        
    contract.expenses.append(expense)
    await contract.save()
    return contract

@router.delete("/{uid}")
async def delete_contract(uid: int):
    contract = await Contract.find_one(Contract.uid == uid)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    await contract.delete()
    return {"message": "Project deleted"}