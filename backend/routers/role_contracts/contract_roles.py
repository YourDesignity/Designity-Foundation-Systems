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
from typing import List

from fastapi import APIRouter, Depends, status

from backend.schemas import (
    ConfigureRoleSlotsRequest,
    ContractRoleSlotCreate,
    ContractRoleSlotUpdate,
)
from backend.security import get_current_active_user
from backend.services.role_contracts.contract_role_service import ContractRoleService
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/contract-roles",
    tags=["Contract Role Slots"],
    dependencies=[Depends(get_current_active_user)],
)

logger = setup_logger("ContractRolesRouter", log_file="logs/contract_roles.log", level=logging.DEBUG)
service = ContractRoleService()


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
    result = await service.configure_role_slots(payload, current_user)
    logger.info("Configured role slots for contract %s", payload.contract_id)
    return result


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
    result = await service.list_all_contract_roles()
    logger.info("Retrieved %d Labour contracts for role list", len(result["contracts"]))
    return result


# ---------------------------------------------------------------------------
# GET /contract-roles/{contract_id}
# ---------------------------------------------------------------------------

@router.get("/{contract_id}")
async def get_role_configuration(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Return the role slot configuration for a contract."""
    return await service.get_role_configuration(contract_id)


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
    result = await service.upsert_role_slots(contract_id, slots, current_user)
    logger.info("Upserted slots for contract %s", contract_id)
    return result


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
    result = await service.delete_role_slot(contract_id, slot_id, current_user)
    logger.info("Deleted slot '%s' from contract %s", slot_id, contract_id)
    return result
