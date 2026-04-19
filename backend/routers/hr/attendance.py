import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import List

from backend import schemas
from backend.security import get_current_active_user
from backend.services.hr.attendance_service import AttendanceService
from backend.utils.audit import log_audit
from backend.utils.logger import setup_logger 

router = APIRouter(prefix="/attendance", tags=["Attendance"], dependencies=[Depends(get_current_active_user)])
logger = setup_logger("AttendanceRouter", log_file="logs/attendance.log", level=logging.DEBUG)
service = AttendanceService()

# =============================================================================
# 2. STANDARD ENDPOINTS (Ensures UI List works)
# =============================================================================

@router.get("/by-date/{date}")
async def get_attendance_by_date(date: str, current_user: dict = Depends(get_current_active_user)):
    try:
        return await service.get_attendance_by_date(date)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Database fetch error")

@router.get("/by-month/{year}/{month}/")
async def get_attendance_by_month(year: int, month: int, current_user: dict = Depends(get_current_active_user)):
    try:
        return await service.get_attendance_by_month(year, month)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Monthly fetch error")

@router.post("/update/")
async def update_attendance(data: schemas.AttendanceUpdateBatch, current_user: dict = Depends(get_current_active_user)):
    try:
        result = await service.sync_attendance_batch(data)

        # Audit log
        try:
            record_count = len(data.records) if hasattr(data, "records") else 0
            await log_audit(
                user=current_user,
                action="attendance_marked",
                category="attendance",
                entity_type="attendance",
                description=(
                    f"{current_user.get('name', 'Unknown')} marked attendance "
                    f"for {record_count} employee(s)"
                ),
            )
        except Exception:
            pass

        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Update failed")

# =============================================================================
# 3. PROFESSIONAL DAILY PDF EXPORT
# =============================================================================

@router.get("/export-pdf/{date}")
async def export_attendance_pdf(date: str):
    try:
        pdf_out = await service.generate_attendance_pdf(date)

        return Response(
            content=pdf_out,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Attendance_Report_{date}.pdf"}
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="PDF engine error")
