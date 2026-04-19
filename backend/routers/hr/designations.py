# backend/routers/hr/designations.py

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from backend import schemas
from backend.security import get_current_active_user
from backend.services.hr.designation_service import DesignationService
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/designations",
    tags=["Designations"]
)

logger = setup_logger("DesignationsRouter", log_file="logs/designations_router.log", level=logging.DEBUG)
service = DesignationService()

# =============================================================================
# 1. GET ALL DESIGNATIONS
# =============================================================================

@router.get("/", response_model=List[schemas.DesignationResponse])
async def get_designations(current_user: dict = Depends(get_current_active_user)):
    """Fetch all designations."""
    try:
        return await service.get_designations()
    except Exception as e:
        logger.critical(f"DB ERROR in GET /designations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# =============================================================================
# 2. CREATE DESIGNATION
# =============================================================================

@router.post("/", response_model=schemas.DesignationResponse)
async def create_designation(designation: schemas.DesignationCreate, current_user: dict = Depends(get_current_active_user)):
    """Create a new designation."""
    try:
        return await service.create_designation(designation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DB ERROR in CREATE designation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# =============================================================================
# 3. DELETE DESIGNATION
# =============================================================================

@router.delete("/{designation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_designation(designation_id: int, current_user: dict = Depends(get_current_active_user)):
    """Delete a designation."""
    try:
        await service.delete_designation(designation_id)
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"DB ERROR in DELETE designation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")