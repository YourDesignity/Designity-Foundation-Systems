# backend/routers/schedules.py

import logging
import json
from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pymongo.errors import DuplicateKeyError

# --- Imports ---
from backend.database import get_next_uid
from backend.models import Schedule, Site
from backend.schemas import ScheduleCreate
from backend.security import get_current_active_user, require_permission
from backend.utils.logger import setup_logger 

router = APIRouter(
    prefix="/schedules",
    tags=["Schedule Management"],
    dependencies=[Depends(get_current_active_user)]
)

# --- Initialize Logger ---
logger = setup_logger("SchedulesRouter", log_file="logs/schedules_router.log", level=logging.DEBUG)

# =============================================================================
# 1. BULK CREATE SCHEDULES
# =============================================================================

@router.post("/bulk", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("schedule:edit"))])
async def create_bulk_schedules(schedule_data: ScheduleCreate):
    """
    Creates schedule records for multiple employees over a date range.
    Handles duplicates gracefully.
    """
    try:
        start = date.fromisoformat(schedule_data.start_date)
        end = date.fromisoformat(schedule_data.end_date)
    except ValueError:
        logger.error(f"DATE PARSE ERROR: Start='{schedule_data.start_date}', End='{schedule_data.end_date}'")
        raise HTTPException(status_code=400, detail="Invalid date format. Please use YYYY-MM-DD.")

    # Log Intent
    delta = end - start
    days_count = delta.days + 1
    total_ops = days_count * len(schedule_data.employee_ids)
    
    logger.info(f"ENDPOINT START: POST /schedules/bulk")
    logger.info(f"BULK OP: {len(schedule_data.employee_ids)} Employees over {days_count} Days. Total Operations: {total_ops}")
    logger.debug(f"PARAMS: Site={schedule_data.site_id}, Task='{schedule_data.task}', Shift='{schedule_data.shift_type}'")

    success_count = 0
    skipped_count = 0

    # Loop through every day in the range
    for i in range(days_count):
        current_date_obj = start + timedelta(days=i)
        current_date_str = current_date_obj.isoformat()
        
        for emp_id in schedule_data.employee_ids:
            try:
                # 1. Generate ID
                new_uid = await get_next_uid("schedules")
                
                # 2. Prepare Document
                new_schedule = Schedule(
                    uid=new_uid,
                    employee_uid=emp_id,
                    site_uid=schedule_data.site_id,
                    work_date=current_date_str,
                    task=schedule_data.task,
                    shift_type=schedule_data.shift_type
                )
                
                # 3. Insert
                await new_schedule.insert()
                success_count += 1
                
            except DuplicateKeyError:
                # Expected behavior: Schedule already exists for this person on this day
                skipped_count += 1
                # Detailed trace for debugging specific collisions
                # logger.debug(f"DUPLICATE DETECTED: Emp {emp_id} on {current_date_str} (Skipping)")
                continue
            except Exception as e:
                logger.error(f"INSERT ERROR: Emp {emp_id} on {current_date_str}: {e}")
                continue

    summary = {
        "status": "success", 
        "message": f"Processed request. Created {success_count} records. Skipped {skipped_count} duplicates."
    }
    
    logger.info(f"BATCH COMPLETE: Success={success_count}, Skipped={skipped_count}, Total={success_count+skipped_count}")
    return summary

# =============================================================================
# 2. READ SCHEDULES (With Filtering)
# =============================================================================

@router.get("/", response_model=List[dict])
async def get_schedules(
    start_date: str,
    end_date: str,
    site_id: Optional[int] = Query(None),
    employee_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Retrieves schedules based on permissions.
    """
    logger.info(f"ENDPOINT START: GET /schedules. Range: {start_date} to {end_date}")
    
    # 1. Base Query Construction
    query: Dict[str, Any] = {
        "work_date": {"$gte": start_date, "$lte": end_date}
    }
    
    # 2. Permission Filtering Logic
    user_perms = current_user.get("perms", [])
    user_role = current_user.get("role", "Unknown")
    
    logger.debug(f"ACCESS CHECK: User Role='{user_role}'")

    if 'employee:view_all' in user_perms:
        # SuperAdmin/Admin
        logger.debug("PERMISSION: Admin access (View All)")
        if site_id:
            query["site_uid"] = site_id
            
    elif 'schedule:view_assigned' in user_perms:
        # Site Manager
        managed_site_ids = current_user.get("sites", [])
        logger.debug(f"PERMISSION: Manager access. Restricted to Sites: {managed_site_ids}")
        
        if not managed_site_ids:
            logger.warning("Manager has NO assigned sites. Returning empty list.")
            return [] 
            
        if site_id:
            if site_id not in managed_site_ids:
                logger.warning(f"SECURITY ALERT: Manager tried accessing Site {site_id} (Not Assigned).")
                raise HTTPException(status_code=403, detail="Forbidden: Access to this site denied.")
            query["site_uid"] = site_id
        else:
            query["site_uid"] = {"$in": managed_site_ids}
    else:
        logger.error(f"SECURITY BLOCK: User {current_user.get('email')} has no view permissions.")
        raise HTTPException(status_code=403, detail="Permission denied")

    # 3. Employee Filter
    if employee_id:
        query["employee_uid"] = employee_id

    # Log the exact Mongo Query for debugging
    logger.debug(f"MONGO QUERY:\n{json.dumps(query, indent=2, default=str)}")

    # 4. Execute Query
    schedules = await Schedule.find(query).sort("work_date").to_list()
    
    if not schedules:
        logger.info("DB FETCH: No schedules found matching query.")
        return []

    # 5. Manual Join: Fetch Site Names
    # Get all unique site UIDs referenced in these schedules
    unique_site_uids = list(set(s.site_uid for s in schedules))
    sites = await Site.find(Site.uid.in_(unique_site_uids)).to_list()
    
    # Create Lookup Map
    site_map = {s.uid: s.name for s in sites}
    logger.debug(f"JOIN LOGIC: Mapped {len(unique_site_uids)} unique sites to {len(schedules)} schedule records.")

    # 6. Construct Response
    results = []
    for sched in schedules:
        results.append({
            "id": sched.uid,
            "employee_id": sched.employee_uid,
            "site_id": sched.site_uid,
            "site_name": site_map.get(sched.site_uid, "Unknown Site"),
            "work_date": sched.work_date,
            "task": sched.task,
            "shift_type": sched.shift_type
        })
        
    # Log a sample of the response
    if results:
        logger.debug(f"RESPONSE PREVIEW (First 2 Items):\n{json.dumps(results[:2], indent=2)}")
        
    return results