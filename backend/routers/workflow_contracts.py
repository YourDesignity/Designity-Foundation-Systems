# backend/routers/workflow_contracts.py

import os
import logging
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.models import Project, Contract, Site
from backend.database import get_next_uid
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

# Contract documents storage directory
_CONTRACT_DOCS_DIR = os.path.join("backend", "uploads", "contracts")
os.makedirs(_CONTRACT_DOCS_DIR, exist_ok=True)

_MAX_CONTRACT_DOC_SIZE = 10 * 1024 * 1024  # 10 MB

router = APIRouter(
    prefix="/workflow/contracts",
    tags=["Workflow Contracts"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("WorkflowContractsRouter", log_file="logs/workflow_contracts_router.log", level=logging.DEBUG)

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
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create contracts")

    project = await Project.find_one(Project.uid == contract_data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from backend.models import CompanySettings
    settings = await CompanySettings.find_one(CompanySettings.uid == 1)

    new_uid = await get_next_uid("contracts")
    if settings and settings.auto_generate_contract_codes:
        prefix = settings.contract_code_prefix or "CNT"
        contract_code = f"{prefix}-{new_uid:03d}"
    else:
        contract_code = f"CNT-{new_uid:03d}"

    new_contract = Contract(
        uid=new_uid,
        contract_code=contract_code,
        contract_name=contract_data.contract_name,
        project_id=contract_data.project_id,
        project_name=project.project_name,
        start_date=contract_data.start_date,
        end_date=contract_data.end_date,
        contract_value=contract_data.contract_value,
        payment_terms=contract_data.payment_terms,
        contract_terms=contract_data.contract_terms,
        notes=contract_data.notes,
        created_by_admin_id=current_user.get("id")
    )

    await new_contract.insert()
    await new_contract.calculate_duration()

    if new_contract.uid not in project.contract_ids:
        project.contract_ids.append(new_contract.uid)
        await project.save()

    logger.info(f"Contract created: {contract_code} for project {project.project_code}")

    return new_contract.model_dump(mode='json')


@router.get("/", response_model=List[dict])
async def get_all_contracts(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all contracts. Optionally filter by project_id or status."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view contracts")

    filters = []
    if project_id:
        filters.append(Contract.project_id == project_id)
    if status:
        filters.append(Contract.status == status)

    if filters:
        contracts = await Contract.find(*filters).sort("+uid").to_list()
    else:
        contracts = await Contract.find_all().sort("+uid").to_list()

    for contract in contracts:
        await contract.calculate_duration()

    logger.info(f"Retrieved {len(contracts)} contracts")
    return [c.model_dump(mode='json') for c in contracts]


@router.get("/{contract_id}")
async def get_contract_details(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get detailed information about a specific contract."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view contract details")

    contract = await Contract.find_one(Contract.uid == contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    await contract.calculate_duration()

    sites = await Site.find(Site.contract_id == contract_id).to_list()

    return {
        "contract": contract.model_dump(mode='json'),
        "sites": [s.model_dump(mode='json') for s in sites]
    }


@router.put("/{contract_id}")
async def update_contract(
    contract_id: int,
    contract_update: ContractUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update contract details."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update contracts")

    contract = await Contract.find_one(Contract.uid == contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    update_data = contract_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(contract, key, value)

    contract.updated_at = datetime.now()

    if "start_date" in update_data or "end_date" in update_data:
        await contract.calculate_duration()
    else:
        await contract.save()

    logger.info(f"Contract {contract_id} updated")

    return contract.model_dump(mode='json')


@router.get("/{contract_id}/workforce-summary")
async def get_contract_workforce_summary(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get workforce and financial summary for a specific contract."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view contract summaries")

    contract = await Contract.find_one(Contract.uid == contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    await contract.calculate_duration()

    project = await Project.find_one(Project.uid == contract.project_id) if contract.project_id else None
    sites = await Site.find(Site.contract_id == contract_id).to_list()

    from backend.models import EmployeeAssignment, TemporaryAssignment

    company_count = await EmployeeAssignment.find(
        EmployeeAssignment.contract_id == contract_id,
        EmployeeAssignment.status == "Active"
    ).count()

    temp_assignments = []
    if contract.project_id:
        temp_assignments = await TemporaryAssignment.find(
            TemporaryAssignment.project_id == contract.project_id,
            TemporaryAssignment.status == "Active"
        ).to_list()

    total_temp_cost = sum(
        (ta.daily_rate or 0.0) * (ta.total_days or 0)
        for ta in temp_assignments
    )

    total_required = sum(s.required_workers for s in sites)
    total_assigned = sum(s.assigned_workers for s in sites)

    return {
        "contract": contract.model_dump(mode='json'),
        "project": project.model_dump(mode='json') if project else None,
        "sites": [s.model_dump(mode='json') for s in sites],
        "total_sites": len(sites),
        "total_required_workers": total_required,
        "total_assigned_workers": total_assigned,
        "company_employees": company_count,
        "temp_workers": len(temp_assignments),
        "total_temp_cost": total_temp_cost,
        "fulfillment_rate": (total_assigned / total_required * 100) if total_required > 0 else 0,
    }


# =============================================================================
# CONTRACT DOCUMENT UPLOAD / DOWNLOAD
# =============================================================================

_ALLOWED_CONTRACT_MIME = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post("/{contract_id}/upload-document")
async def upload_contract_document(
    contract_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    """Upload a document (PDF, image, Word) for a contract."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can upload contract documents")

    contract = await Contract.find_one(Contract.uid == contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    content = await file.read()

    if len(content) > _MAX_CONTRACT_DOC_SIZE:
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")

    content_type = file.content_type or ""
    if content_type not in _ALLOWED_CONTRACT_MIME:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed: PDF, JPEG, PNG, Word documents"
        )

    # Remove old document if it exists
    if contract.document_path and os.path.exists(contract.document_path):
        try:
            os.remove(contract.document_path)
        except OSError:
            pass

    # Build safe filename — strip directory components and keep only safe characters
    original_name = os.path.basename(file.filename or "document")
    safe_name = "".join(c for c in original_name if c.isalnum() or c in ('_', '-', '.'))
    if not safe_name:
        safe_name = "document.pdf"
    # Limit to a single extension (last dot segment)
    safe_name = safe_name[:100]

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    code = "".join(c for c in contract.contract_code if c.isalnum() or c in ('_', '-'))
    filename = f"{contract_id}_{code}_{timestamp}_{safe_name}"
    # Ensure filename contains no path separators
    filename = os.path.basename(filename)

    # Construct path and verify it resolves inside the allowed directory
    abs_storage_dir = os.path.realpath(_CONTRACT_DOCS_DIR)
    file_path = os.path.realpath(os.path.join(_CONTRACT_DOCS_DIR, filename))
    if not file_path.startswith(abs_storage_dir + os.sep):
        raise HTTPException(status_code=400, detail="Invalid filename")

    with open(file_path, "wb") as f:
        f.write(content)

    contract.document_path = file_path
    contract.document_name = original_name
    contract.updated_at = datetime.now()
    await contract.save()

    logger.info("Document uploaded for contract %s: %s", contract_id, filename)
    return {
        "message": "Document uploaded successfully",
        "document_name": original_name,
        "file_size": len(content),
    }


@router.get("/{contract_id}/download-document")
async def download_contract_document(
    request: Request,
    contract_id: int,
    token: Optional[str] = Query(None),
):
    """Download or preview the contract document."""
    from jose import jwt, JWTError
    from backend.security import SECRET_KEY, ALGORITHM

    raw_token = token
    if not raw_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[len("Bearer "):]

    if not raw_token:
        raise HTTPException(status_code=401, detail="Authentication token required")

    try:
        jwt.decode(raw_token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token")

    contract = await Contract.find_one(Contract.uid == contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if not contract.document_path or not os.path.exists(contract.document_path):
        logger.debug(
            "Download contract document: contract_id=%s path=%s exists=%s",
            contract_id,
            contract.document_path,
            os.path.exists(contract.document_path) if contract.document_path else False,
        )
        raise HTTPException(status_code=404, detail="No document found for this contract")

    logger.debug(
        "Serving contract document: contract_id=%s path=%s",
        contract_id,
        contract.document_path,
    )
    filename = contract.document_name or os.path.basename(contract.document_path)
    ext = os.path.splitext(filename)[1].lower()
    mime_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    media_type = mime_types.get(ext, "application/octet-stream")
    # Strip control characters (including CR/LF) and escape double-quotes to
    # prevent HTTP header injection.
    safe_filename = filename.replace("\r", "").replace("\n", "").replace('"', '\\"')
    return FileResponse(
        path=contract.document_path,
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{safe_filename}"'},
    )


@router.delete("/{contract_id}", status_code=204)
async def delete_contract(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a contract. Only allowed if no active sites exist."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can delete contracts")

    contract = await Contract.find_one(Contract.uid == contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    active_sites = await Site.find(
        Site.contract_id == contract_id,
        Site.status == "Active"
    ).count()

    if active_sites > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete contract with {active_sites} active site(s)."
        )

    project = await Project.find_one(Project.uid == contract.project_id)
    if project and contract.uid in project.contract_ids:
        project.contract_ids.remove(contract.uid)
        await project.save()

    await contract.delete()
    logger.info(f"Contract {contract_id} deleted")

    return None
