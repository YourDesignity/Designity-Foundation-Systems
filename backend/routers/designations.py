# backend/routers/designations.py

import logging
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

# --- Imports ---
from backend.database import get_next_uid
from backend.models import Designation
from backend import schemas
from backend.security import get_current_active_user

# !!! FIXED IMPORT PATH BELOW (was backend.logger) !!!
from backend.utils.logger import setup_logger 

router = APIRouter(
    prefix="/designations",
    tags=["Designations"]
)

# --- Initialize Logger ---
logger = setup_logger("DesignationsRouter", log_file="logs/designations_router.log", level=logging.DEBUG)

# =============================================================================
# 1. GET ALL DESIGNATIONS
# =============================================================================

@router.get("/", response_model=List[schemas.DesignationResponse])
async def get_designations(current_user: dict = Depends(get_current_active_user)):
    """Fetch all designations."""
    logger.info("ENDPOINT START: GET /designations")
    
    try:
        # 1. DB Fetch
        designations = await Designation.find_all().to_list()
        
        # 2. Deep Inspection (Log the raw list)
        # mode='json' handles ObjectId conversion automatically
        raw_dump = [d.model_dump(mode='json') for d in designations]
        logger.debug(f"DB FETCH: Retrieved {len(designations)} records.\nDATA:\n{json.dumps(raw_dump, indent=2)}")
        
        return designations

    except Exception as e:
        logger.critical(f"DB ERROR in GET /designations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# =============================================================================
# 2. CREATE DESIGNATION
# =============================================================================

@router.post("/", response_model=schemas.DesignationResponse)
async def create_designation(designation: schemas.DesignationCreate, current_user: dict = Depends(get_current_active_user)):
    """Create a new designation."""
    logger.info(f"ENDPOINT START: POST /designations. Payload: '{designation.title}'")

    # 1. Duplicate Check Logic
    existing = await Designation.find_one(Designation.title == designation.title)
    if existing:
        logger.warning(f"VALIDATION FAILURE: Designation '{designation.title}' already exists (UID: {existing.uid}).")
        raise HTTPException(status_code=400, detail="Designation already exists")

    try:
        # 2. Creation Logic
        new_uid = await get_next_uid("designations")
        
        new_desig = Designation(uid=new_uid, title=designation.title)
        
        # Log the object structure before inserting
        log_structure = new_desig.model_dump(mode='json')
        logger.debug(f"DB INSERT PREP:\n{json.dumps(log_structure, indent=2)}")
        
        await new_desig.insert()
        
        logger.info(f"SUCCESS: Created designation '{designation.title}' with UID {new_uid}.")
        return new_desig

    except Exception as e:
        logger.error(f"DB ERROR in CREATE designation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# =============================================================================
# 3. DELETE DESIGNATION
# =============================================================================

@router.delete("/{designation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_designation(designation_id: int, current_user: dict = Depends(get_current_active_user)):
    """Delete a designation."""
    logger.warning(f"ENDPOINT START: DELETE /designations/{designation_id} (Destructive Action)")

    # 1. Lookup
    desig = await Designation.find_one(Designation.uid == designation_id)
    if not desig:
        logger.warning(f"DELETE FAILED: Designation UID {designation_id} not found.")
        raise HTTPException(status_code=404, detail="Designation not found")
    
    # 2. Audit Snapshot
    # Before deleting, we log the exact data we are destroying.
    snapshot = desig.model_dump(mode='json')
    logger.warning(f"AUDIT SNAPSHOT - DELETING RECORD:\n{json.dumps(snapshot, indent=2)}")
    
    try:
        await desig.delete()
        logger.info(f"SUCCESS: Designation UID {designation_id} permanently deleted.")
        return None
        
    except Exception as e:
        logger.critical(f"DB ERROR in DELETE designation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")