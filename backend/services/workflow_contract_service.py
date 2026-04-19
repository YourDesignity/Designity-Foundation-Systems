"""Service layer for workflow contract operations."""

import os
import logging
from datetime import datetime
from typing import Any, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")

_CONTRACT_DOCS_DIR = os.path.join("backend", "uploads", "contracts")
os.makedirs(_CONTRACT_DOCS_DIR, exist_ok=True)

_MAX_CONTRACT_DOC_SIZE = 10 * 1024 * 1024  # 10 MB

_ALLOWED_CONTRACT_MIME = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class WorkflowContractService(BaseService):
    """Business logic for workflow contract CRUD, document upload/download."""

    async def create_contract(self, contract_data: Any, current_user: dict) -> dict:
        from backend.models import Project, Contract, CompanySettings

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can create contracts")

        project = await Project.find_one(Project.uid == contract_data.project_id)
        if not project:
            self.raise_not_found("Project not found")

        settings = await CompanySettings.find_one(CompanySettings.uid == 1)

        new_uid = await self.get_next_uid("contracts")
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
            created_by_admin_id=current_user.get("id"),
        )

        await new_contract.insert()
        await new_contract.calculate_duration()

        if new_contract.uid not in project.contract_ids:
            project.contract_ids.append(new_contract.uid)
            await project.save()

        return new_contract.model_dump(mode="json")

    async def get_all_contracts(
        self, current_user: dict, project_id: Optional[int] = None, status_filter: Optional[str] = None
    ) -> list[dict]:
        from backend.models import Contract

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can view contracts")

        filters = []
        if project_id:
            filters.append(Contract.project_id == project_id)
        if status_filter:
            filters.append(Contract.status == status_filter)

        if filters:
            contracts = await Contract.find(*filters).sort("+uid").to_list()
        else:
            contracts = await Contract.find_all().sort("+uid").to_list()

        for contract in contracts:
            await contract.calculate_duration()

        return [c.model_dump(mode="json") for c in contracts]

    async def get_contract_details(self, contract_id: int, current_user: dict) -> dict:
        from backend.models import Contract, Site

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can view contract details")

        contract = await Contract.find_one(Contract.uid == contract_id)
        if not contract:
            self.raise_not_found("Contract not found")

        await contract.calculate_duration()

        sites = await Site.find(Site.contract_id == contract_id).to_list()

        return {
            "contract": contract.model_dump(mode="json"),
            "sites": [s.model_dump(mode="json") for s in sites],
        }

    async def update_contract(self, contract_id: int, contract_update: Any, current_user: dict) -> dict:
        from backend.models import Contract

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can update contracts")

        contract = await Contract.find_one(Contract.uid == contract_id)
        if not contract:
            self.raise_not_found("Contract not found")

        update_data = contract_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(contract, key, value)

        contract.updated_at = datetime.now()

        if "start_date" in update_data or "end_date" in update_data:
            await contract.calculate_duration()
        else:
            await contract.save()

        return contract.model_dump(mode="json")

    async def get_workforce_summary(self, contract_id: int, current_user: dict) -> dict:
        from backend.models import Contract, Project, Site, EmployeeAssignment, TemporaryAssignment

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can view contract summaries")

        contract = await Contract.find_one(Contract.uid == contract_id)
        if not contract:
            self.raise_not_found("Contract not found")

        await contract.calculate_duration()

        project = await Project.find_one(Project.uid == contract.project_id) if contract.project_id else None
        sites = await Site.find(Site.contract_id == contract_id).to_list()

        company_count = await EmployeeAssignment.find(
            EmployeeAssignment.contract_id == contract_id,
            EmployeeAssignment.status == "Active",
        ).count()

        temp_assignments = []
        if contract.project_id:
            temp_assignments = await TemporaryAssignment.find(
                TemporaryAssignment.project_id == contract.project_id,
                TemporaryAssignment.status == "Active",
            ).to_list()

        total_temp_cost = sum((ta.daily_rate or 0.0) * (ta.total_days or 0) for ta in temp_assignments)

        total_required = sum(s.required_workers for s in sites)
        total_assigned = sum(s.assigned_workers for s in sites)

        return {
            "contract": contract.model_dump(mode="json"),
            "project": project.model_dump(mode="json") if project else None,
            "sites": [s.model_dump(mode="json") for s in sites],
            "total_sites": len(sites),
            "total_required_workers": total_required,
            "total_assigned_workers": total_assigned,
            "company_employees": company_count,
            "temp_workers": len(temp_assignments),
            "total_temp_cost": total_temp_cost,
            "fulfillment_rate": (total_assigned / total_required * 100) if total_required > 0 else 0,
        }

    async def upload_document(self, contract_id: int, file: Any, current_user: dict) -> dict:
        from backend.models import Contract

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can upload contract documents")

        contract = await Contract.find_one(Contract.uid == contract_id)
        if not contract:
            self.raise_not_found("Contract not found")

        content = await file.read()

        if len(content) > _MAX_CONTRACT_DOC_SIZE:
            self.raise_bad_request("File size must be less than 10MB")

        content_type = file.content_type or ""
        if content_type not in _ALLOWED_CONTRACT_MIME:
            self.raise_bad_request("Invalid file type. Allowed: PDF, JPEG, PNG, Word documents")

        if contract.document_path and os.path.exists(contract.document_path):
            try:
                os.remove(contract.document_path)
            except OSError:
                pass

        original_name = os.path.basename(file.filename or "document")
        safe_name = "".join(c for c in original_name if c.isalnum() or c in ("_", "-", "."))
        if not safe_name:
            safe_name = "document.pdf"
        safe_name = safe_name[:100]

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        code = "".join(c for c in contract.contract_code if c.isalnum() or c in ("_", "-"))
        filename = f"{contract_id}_{code}_{timestamp}_{safe_name}"
        filename = os.path.basename(filename)

        abs_storage_dir = os.path.realpath(_CONTRACT_DOCS_DIR)
        file_path = os.path.realpath(os.path.join(_CONTRACT_DOCS_DIR, filename))
        if not file_path.startswith(abs_storage_dir + os.sep):
            self.raise_bad_request("Invalid filename")

        with open(file_path, "wb") as f:
            f.write(content)

        contract.document_path = file_path
        contract.document_name = original_name
        contract.updated_at = datetime.now()
        await contract.save()

        return {
            "message": "Document uploaded successfully",
            "document_name": original_name,
            "file_size": len(content),
        }

    async def download_document(self, contract_id: int, raw_token: Optional[str]) -> dict:
        from backend.models import Contract

        if not raw_token:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Authentication token required")

        from jose import jwt, JWTError
        from backend.security import SECRET_KEY, ALGORITHM

        try:
            jwt.decode(raw_token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid or expired authentication token")

        contract = await Contract.find_one(Contract.uid == contract_id)
        if not contract:
            self.raise_not_found("Contract not found")

        if not contract.document_path or not os.path.exists(contract.document_path):
            self.raise_not_found("No document found for this contract")

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
        safe_filename = filename.replace("\r", "").replace("\n", "").replace('"', '\\"')

        return {
            "path": contract.document_path,
            "filename": filename,
            "media_type": media_type,
            "safe_filename": safe_filename,
        }

    async def delete_contract(self, contract_id: int, current_user: dict) -> None:
        from backend.models import Contract, Project, Site

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can delete contracts")

        contract = await Contract.find_one(Contract.uid == contract_id)
        if not contract:
            self.raise_not_found("Contract not found")

        active_sites = await Site.find(
            Site.contract_id == contract_id,
            Site.status == "Active",
        ).count()

        if active_sites > 0:
            self.raise_bad_request(f"Cannot delete contract with {active_sites} active site(s).")

        project = await Project.find_one(Project.uid == contract.project_id)
        if project and contract.uid in project.contract_ids:
            project.contract_ids.remove(contract.uid)
            await project.save()

        await contract.delete()
