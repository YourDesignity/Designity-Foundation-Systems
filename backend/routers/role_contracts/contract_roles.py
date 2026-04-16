# backend/routers/contract_roles.py
"""
Contract Role Slots API
-----------------------
Manage fixed role slot definitions (e.g. 5 Drivers, 10 Cleaners) for Labour contracts.

Endpoints
---------
POST   /contract-roles/configure           – Define/replace all role slots for a contract
GET    /contract-roles/{contract_id}        – Get role configuration for a contract
PUT    /contract-roles/{contract_id}/slots  – Add or update individual slots
DELETE /contract-roles/{contract_id}/slots/{slot_id} – Remove a slot
"""

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from backend.models import Contract, ContractRoleSlot
from backend.schemas import (
    ConfigureRoleSlotsRequest,
    ContractRoleSlotCreate,
    ContractRoleSlotUpdate,
)
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/contract-roles",
    tags=["Contract Role Slots"],
    dependencies=[Depends(get_current_active_user)],
)

logger = setup_logger("ContractRolesRouter", log_file="logs/contract_roles.log", level=logging.DEBUG)


def _admin_only(current_user: dict) -> None:
    """Raise 403 if caller is not SuperAdmin or Admin."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can manage contract role slots")


# ---------------------------------------------------------------------------
# POST /contract-roles/configure
# ---------------------------------------------------------------------------

@router.post("/configure", status_code=status.HTTP_200_OK)
async def configure_role_slots(
    payload: ConfigureRoleSlotsRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Define (or fully replace) the role slots for a Labour contract.

    * Slot IDs must be unique within the contract.
    * Daily rate must be > 0.
    * Replaces all existing slots; use PUT …/slots to add/update incrementally.
    """
    _admin_only(current_user)

    contract = await Contract.find_one(Contract.uid == payload.contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Validate uniqueness of slot_ids
    slot_ids = [s.slot_id for s in payload.slots]
    if len(slot_ids) != len(set(slot_ids)):
        raise HTTPException(status_code=400, detail="Slot IDs must be unique within the contract")

    # Validate daily rates
    for s in payload.slots:
        if s.daily_rate <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Daily rate for slot '{s.slot_id}' must be greater than 0",
            )

    contract.role_slots = [
        ContractRoleSlot(
            slot_id=s.slot_id,
            designation=s.designation,
            daily_rate=s.daily_rate,
        )
        for s in payload.slots
    ]
    contract.contract_type = "Labour"
    contract.recalculate_role_summary()
    contract.updated_at = datetime.now()
    await contract.save()

    logger.info(
        f"Configured {len(contract.role_slots)} role slots for contract {contract.contract_code}"
    )
    return contract.model_dump(mode="json")


# ---------------------------------------------------------------------------
# GET /contract-roles/list
# ---------------------------------------------------------------------------

@router.get("/list")
async def list_all_contract_roles(
    current_user: dict = Depends(get_current_active_user),
):
    """
    Return all Labour contracts with their role slot configurations.

    Used by the frontend to display the contract overview screen.
    """
    contracts = await Contract.find(Contract.contract_type == "Labour").to_list()

    logger.info(f"Retrieved {len(contracts)} Labour contracts for role list")

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


# ---------------------------------------------------------------------------
# GET /contract-roles/{contract_id}
# ---------------------------------------------------------------------------

@router.get("/{contract_id}")
async def get_role_configuration(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Return the role slot configuration for a contract."""
    contract = await Contract.find_one(Contract.uid == contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    return {
        "contract_id": contract.uid,
        "contract_code": contract.contract_code,
        "contract_type": contract.contract_type,
        "total_role_slots": contract.total_role_slots,
        "total_daily_cost": contract.total_daily_cost,
        "roles_by_designation": contract.roles_by_designation,
        "role_slots": [s.model_dump() for s in contract.role_slots],
    }


# ---------------------------------------------------------------------------
# PUT /contract-roles/{contract_id}/slots
# ---------------------------------------------------------------------------

@router.put("/{contract_id}/slots", status_code=status.HTTP_200_OK)
async def upsert_role_slots(
    contract_id: int,
    slots: List[ContractRoleSlotCreate],
    current_user: dict = Depends(get_current_active_user),
):
    """
    Add new slots or update existing ones (matched by slot_id).
    Slots not included in the request body are left untouched.
    """
    _admin_only(current_user)

    contract = await Contract.find_one(Contract.uid == contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    for slot_data in slots:
        if slot_data.daily_rate <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Daily rate for slot '{slot_data.slot_id}' must be greater than 0",
            )

    # Build lookup from existing slots
    existing: dict[str, ContractRoleSlot] = {s.slot_id: s for s in contract.role_slots}

    for slot_data in slots:
        if slot_data.slot_id in existing:
            # Update existing slot
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

    logger.info(f"Upserted slots for contract {contract.contract_code}: {[s.slot_id for s in slots]}")
    return contract.model_dump(mode="json")


# ---------------------------------------------------------------------------
# DELETE /contract-roles/{contract_id}/slots/{slot_id}
# ---------------------------------------------------------------------------

@router.delete("/{contract_id}/slots/{slot_id}", status_code=status.HTTP_200_OK)
async def delete_role_slot(
    contract_id: int,
    slot_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Remove a single role slot from a contract."""
    _admin_only(current_user)

    contract = await Contract.find_one(Contract.uid == contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    original_count = len(contract.role_slots)
    contract.role_slots = [s for s in contract.role_slots if s.slot_id != slot_id]

    if len(contract.role_slots) == original_count:
        raise HTTPException(status_code=404, detail=f"Slot '{slot_id}' not found in contract")

    contract.recalculate_role_summary()
    contract.updated_at = datetime.now()
    await contract.save()

    logger.info(f"Deleted slot '{slot_id}' from contract {contract.contract_code}")
    return {"message": f"Slot '{slot_id}' removed successfully"}
