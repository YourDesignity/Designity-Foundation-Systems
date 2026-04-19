# backend/routers/sites.py

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from backend.schemas import SiteCreate, SiteUpdate
from backend.security import get_current_active_user
from backend.services.projects.site_service import SiteService
from backend.utils.logger import setup_logger 

router = APIRouter(
    prefix="/sites",
    tags=["Site Management"],
    dependencies=[Depends(get_current_active_user)]
)

# --- Initialize Logger ---
logger = setup_logger("SitesRouter", log_file="logs/sites_router.log", level=logging.DEBUG)
service = SiteService()

# =============================================================================
# 1. READ ALL SITES
# =============================================================================

@router.get("/", response_model=List[dict])
async def get_all_sites():
    """
    Retrieves active sites.
    Maps 'manager_uid' (DB) back to 'site_manager' (Name) for Frontend compatibility.
    """
    logger.info("ENDPOINT START: GET /sites")
    
    try:
        results = await service.get_active_sites_for_listing()
        logger.debug(f"DB FETCH: Retrieved {len(results)} active sites.")
        return results

    except Exception as e:
        logger.critical(f"CRITICAL ERROR in GET /sites: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# =============================================================================
# 2. CREATE SITE
# =============================================================================

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_site(site_data: SiteCreate):
    """
    Creates a new site.
    Resolves 'site_manager' name to an internal UID.
    """
    logger.info(f"ENDPOINT START: POST /sites. Name: '{site_data.name}'")

    try:
        result = await service.create_legacy_site(site_data)
        logger.info(f"SUCCESS: Created Site {result['site_id']} ('{site_data.name}').")
        return result

    except Exception as e:
        logger.error(f"DB ERROR in CREATE SITE: {e}")
        raise

# =============================================================================
# 3. DELETE SITE
# =============================================================================

@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(site_id: int):
    """
    Deletes a site.
    Cleanup: Also removes this site from any Admin's assigned list.
    """
    logger.warning(f"ENDPOINT START: DELETE /sites/{site_id} (Destructive Action)")

    try:
        await service.delete_legacy_site(site_id)
        logger.info(f"SUCCESS: Site {site_id} deleted permanently.")
        return None

    except Exception as e:
        logger.critical(f"DELETE ERROR for Site {site_id}: {e}", exc_info=True)
        raise
