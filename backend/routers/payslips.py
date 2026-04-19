import logging
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# --- Imports ---
from backend.security import get_current_active_user
from backend.services.hr.payslip_service import PayslipService
from backend.utils.audit import log_audit
from backend.utils.logger import setup_logger 

router = APIRouter(
    prefix="/payslips",
    tags=["Payslips"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("PayslipsRouter", log_file="logs/payslips_router.log", level=logging.DEBUG)
service = PayslipService()

class PayslipRequest(BaseModel):
    employee_ids: List[int]
    pay_period: str

# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/calculate")
async def calculate_payslips_preview(
    request: PayslipRequest,
    current_user: dict = Depends(get_current_active_user),
):
    logger.info(f"ENDPOINT START: POST /payslips/calculate. Batch Size: {len(request.employee_ids)}")
    try:
        processed_payslips = await service.calculate_payslips_preview(request.employee_ids, request.pay_period)

        # Audit log
        try:
            await log_audit(
                user=current_user,
                action="payroll_generated",
                category="payroll",
                entity_type="payslip",
                description=(
                    f"{current_user.get('name', 'Unknown')} generated payslips for "
                    f"{len(request.employee_ids)} employee(s) — period: {request.pay_period}"
                ),
            )
        except Exception:
            pass

        return {
            "status": "success",
            "message": f"Calculated {len(processed_payslips)} payslips.",
            "payslips_data": processed_payslips
        }
    except Exception as e:
        logger.critical(f"BATCH CALCULATION CRASH: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{employee_id}")
async def download_payslip_pdf(employee_id: int, month: str):
    try:
        payslip_data, pdf_buffer = await service.generate_payslip_pdf(employee_id, month)
        filename = f"Payslip_{payslip_data['name']}_{payslip_data['pay_period']}.pdf"
        
        return StreamingResponse(
            pdf_buffer, 
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.critical(f"PDF ERROR: {e}")
        raise
