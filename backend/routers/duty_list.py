import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from backend import schemas
from backend.models import DutyAssignment, Admin, Employee
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger 

router = APIRouter(
    prefix="/duty_list",
    tags=["Duty List"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("DutyListRouter", log_file="logs/duty_list.log", level=logging.DEBUG)

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_duty_assignment(assignments: List[schemas.DutyAssignmentCreate], current_user: dict = Depends(get_current_active_user)):
    if current_user.get("role") not in ["SuperAdmin", "Admin", "Site Manager"]:
        raise HTTPException(status_code=403, detail="Only Admins and Site Managers can assign workforce duties.")

    try:
        for item in assignments:
            # Update the employee's permanent manager_id
            employee = await Employee.find_one(Employee.uid == item.employee_id)
            if employee:
                employee.manager_id = item.manager_id
                await employee.save()
                logger.info(f"Employee {item.employee_id} permanently assigned to Manager {item.manager_id}")

            # Upsert duty assignment (one active assignment per employee)
            existing = await DutyAssignment.find_one(
                DutyAssignment.employee_id == item.employee_id
            )

            if existing:
                existing.site_id = item.site_id
                existing.manager_id = item.manager_id
                existing.start_date = item.start_date
                existing.end_date = item.end_date
                await existing.save()
                logger.info(f"Updated duty assignment for Employee {item.employee_id}")
            else:
                new_duty = DutyAssignment(
                    employee_id=item.employee_id,
                    site_id=item.site_id,
                    manager_id=item.manager_id,
                    start_date=item.start_date,
                    end_date=item.end_date
                )
                await new_duty.insert()
                logger.info(f"Created new duty assignment for Employee {item.employee_id}")

        return {"message": "Duty assigned to employees successfully"}
    except Exception as e:
        logger.error(f"POST Duty Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save assignments.")

@router.get("/{date}")
async def get_duty_list_by_date(date: str, current_user: dict = Depends(get_current_active_user)):
    try:
        user_role = current_user.get("role")
        user_email = current_user.get("sub")

        me = await Admin.find_one(Admin.email == user_email)

        if user_role in ["SuperAdmin", "Admin"]:
            # Return all assignments active on this date
            return await DutyAssignment.find(
                DutyAssignment.start_date <= date,
                DutyAssignment.end_date >= date
            ).to_list()

        if not me:
            return []

        # Return manager's assignments active on this date
        return await DutyAssignment.find(
            DutyAssignment.manager_id == me.uid,
            DutyAssignment.start_date <= date,
            DutyAssignment.end_date >= date
        ).to_list()
    except Exception as e:
        logger.error(f"GET Duty Error: {e}")
        return []

@router.delete("/{id}")
async def delete_duty_assignment(id: str):
    try:
        record = await DutyAssignment.get(id)
        if not record: 
            raise HTTPException(status_code=404, detail="Assignment not found")
        await record.delete()
        return {"message": "Assignment removed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Delete failed")