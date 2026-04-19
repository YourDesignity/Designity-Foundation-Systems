# backend/routers/workflow_contracts.py

import logging
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.security import get_current_active_user
from backend.services.workflow_contract_service import WorkflowContractService
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/workflow/contracts",
    tags=["Workflow Contracts"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("WorkflowContractsRouter", log_file="logs/workflow_contracts_router.log", level=logging.DEBUG)
service = WorkflowContractService()

# ===== SCHEMAS =====

class ContractCreate(BaseModel):
    project_id: int
    contract_name: Optional[str] = None
    start_date: date
    end_date: date
    contract_value: float
    payment_terms: Optional[str] = None
    contract_terms: Optional[str] = None
    notes: Optional[str] = None

class ContractUpdate(BaseModel):
    contract_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    contract_value: Optional[float] = None
    payment_terms: Optional[str] = None
    contract_terms: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None

# ===== ENDPOINTS =====

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_contract(
    contract_data: ContractCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new contract under a project."""
    result = await service.create_contract(contract_data, current_user)
    logger.info("Contract created for project %s", contract_data.project_id)
    return result


@router.get("/", response_model=List[dict])
async def get_all_contracts(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all contracts. Optionally filter by project_id or status."""
    result = await service.get_all_contracts(current_user, project_id=project_id, status_filter=status)
    logger.info("Retrieved %d contracts", len(result))
    return result


@router.get("/{contract_id}")
async def get_contract_details(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get detailed information about a specific contract."""
    return await service.get_contract_details(contract_id, current_user)


@router.put("/{contract_id}")
async def update_contract(
    contract_id: int,
    contract_update: ContractUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update contract details."""
    result = await service.update_contract(contract_id, contract_update, current_user)
    logger.info("Contract %s updated", contract_id)
    return result


@router.get("/{contract_id}/workforce-summary")
async def get_contract_workforce_summary(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get workforce and financial summary for a specific contract."""
    return await service.get_workforce_summary(contract_id, current_user)


@router.post("/{contract_id}/upload-document")
async def upload_contract_document(
    contract_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    """Upload a document (PDF, image, Word) for a contract."""
    result = await service.upload_document(contract_id, file, current_user)
    logger.info("Document uploaded for contract %s", contract_id)
    return result


@router.get("/{contract_id}/download-document")
async def download_contract_document(
    request: Request,
    contract_id: int,
    token: Optional[str] = Query(None),
):
    """Download or preview the contract document."""
    raw_token = token
    if not raw_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[len("Bearer "):]

    doc_info = await service.download_document(contract_id, raw_token)
    return FileResponse(
        path=doc_info["path"],
        filename=doc_info["filename"],
        media_type=doc_info["media_type"],
        headers={"Content-Disposition": f'inline; filename="{doc_info["safe_filename"]}"'},
    )


@router.delete("/{contract_id}", status_code=204)
async def delete_contract(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a contract. Only allowed if no active sites exist."""
    await service.delete_contract(contract_id, current_user)
    logger.info("Contract %s deleted", contract_id)
    return None
