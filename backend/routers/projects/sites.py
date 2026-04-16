# backend/routers/sites.py

import logging
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from beanie import WriteRules

# --- Imports ---
from backend.database import get_next_uid
from backend.models import Site, Admin, Schedule
from backend.schemas import SiteCreate, SiteUpdate
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger 

router = APIRouter(
    prefix="/sites",
    tags=["Site Management"],
    dependencies=[Depends(get_current_active_user)]
)

# --- Initialize Logger ---
logger = setup_logger("SitesRouter", log_file="logs/sites_router.log", level=logging.DEBUG)

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
        # 1. Fetch Sites
        sites = await Site.find(Site.is_active == True).sort(+Site.name).to_list()
        logger.debug(f"DB FETCH: Retrieved {len(sites)} active sites.")
        
        # 2. Manual Join (Optimization)
        # Fetch all managers involved in one go to avoid N+1 query problem
        manager_uids = [s.manager_uid for s in sites if s.manager_uid]
        managers = []
        if manager_uids:
            managers = await Admin.find(Admin.uid.in_(manager_uids)).to_list()
        
        # Create a lookup map: UID -> Full Name
        manager_map = {m.uid: m.full_name for m in managers}
        logger.debug(f"JOIN LOGIC: Mapped {len(manager_map)} unique managers to sites.")
        
        # 3. Construct Response
        results = []
        for site in sites:
            # Resolve the name
            mgr_name = manager_map.get(site.manager_uid) if site.manager_uid else None
            
            results.append({
                "id": site.uid,
                "name": site.name,
                "location": site.location,
                "site_manager": mgr_name, # Frontend expects string name
                "description": site.description,
                "phone": site.phone,
                "is_active": site.is_active
            })
        
        # Log the final output for debugging frontend issues
        if results:
            logger.debug(f"RESPONSE PREVIEW (First item):\n{json.dumps(results[0], indent=2)}")
            
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
    
    # 1. Check Name Uniqueness
    existing = await Site.find_one(Site.name == site_data.name)
    if existing:
        logger.warning(f"VALIDATION ERROR: Site Name '{site_data.name}' already taken by UID {existing.uid}.")
        raise HTTPException(status_code=400, detail=f"The site name '{site_data.name}' is already taken.")
    
    # 2. Resolve Manager Name -> UID
    manager_uid = None
    if site_data.site_manager:
        logger.debug(f"LOGIC: Resolving manager name '{site_data.site_manager}' to UID...")
        
        # Find admin by exact name match
        admin = await Admin.find_one(Admin.full_name == site_data.site_manager)
        if admin:
            manager_uid = admin.uid
            logger.debug(f"LOGIC: Match Found! Name '{site_data.site_manager}' -> UID {manager_uid}")
        else:
            logger.warning(f"LOGIC: Manager '{site_data.site_manager}' NOT FOUND in DB. Site will be created without a manager.")
            # Note: If admin not found by name, we proceed with None

    try:
        # 3. Create Document
        new_uid = await get_next_uid("sites")
        new_site = Site(
            uid=new_uid,
            name=site_data.name,
            location=site_data.location,
            manager_uid=manager_uid,
            description=site_data.description,
            phone=site_data.phone,
            is_active=True
        )
        
        # Log before insert
        doc_dump = new_site.model_dump(mode='json')
        logger.debug(f"DB INSERT PREP:\n{json.dumps(doc_dump, indent=2)}")
        
        await new_site.insert()
        logger.info(f"SUCCESS: Created Site {new_uid} ('{site_data.name}').")
        
        return {"status": "success", "site_id": new_uid}

    except Exception as e:
        logger.error(f"DB ERROR in CREATE SITE: {e}")
        raise HTTPException(status_code=500, detail="Failed to create site")

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

    site = await Site.find_one(Site.uid == site_id)
    if not site:
        logger.warning(f"DELETE FAILED: Site {site_id} not found.")
        raise HTTPException(status_code=404, detail="Site Not Found")

    # Audit Snapshot
    snapshot = site.model_dump(mode='json')
    logger.warning(f"AUDIT SNAPSHOT - Deleting Site:\n{json.dumps(snapshot, indent=2)}")

    try:
        # 1. Clean up Admin Assignments (The "Surgical" part)
        # Find all admins who have this site in their assigned list
        admins_with_access = await Admin.find(Admin.assigned_site_uids == site_id).to_list()
        
        cleanup_count = 0
        for admin in admins_with_access:
            if site_id in admin.assigned_site_uids:
                admin.assigned_site_uids.remove(site_id)
                await admin.save()
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"CLEANUP: Removed Site {site_id} access from {cleanup_count} managers.")

        # 2. Delete the Site
        await site.delete()
        logger.info(f"SUCCESS: Site {site_id} deleted permanently.")
        
        return None

    except Exception as e:
        logger.critical(f"DELETE ERROR for Site {site_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")