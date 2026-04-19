import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from pydantic import BaseModel

from backend.models.vehicles import Vehicle, TripLog
from backend.security import get_current_active_user
from backend.services.vehicles.vehicle_service import VehicleService
from backend.services.vehicles.trip_log_service import TripLogService
from backend.services.vehicles.maintenance_service import MaintenanceService

router = APIRouter(prefix="/vehicles", tags=["Vehicle Management"])

_vehicle_svc = VehicleService()
_trip_svc = TripLogService()
_maint_svc = MaintenanceService()

VEHICLE_PHOTOS_DIR = os.path.join("backend", "uploads", "vehicle_photos")
os.makedirs(VEHICLE_PHOTOS_DIR, exist_ok=True)

# --- SCHEMAS ---
class TripStartRequest(BaseModel):
    vehicle_uid: int
    driver_name: str
    purpose: str
    start_condition: str
    # Optional: link trip to a contract/site
    contract_id: Optional[int] = None
    contract_code: Optional[str] = None
    site_id: Optional[int] = None
    site_name: Optional[str] = None
    driver_employee_uid: Optional[int] = None

class ExpenseRequest(BaseModel):
    vehicle_uid: int
    driver_name: str
    category: str
    amount: float
    date: str
    description: Optional[str] = None

# --- 1. VEHICLES ---
@router.get("/")
async def get_all_vehicles():
    return await _vehicle_svc.get_all_vehicles()

@router.post("/")
async def add_vehicle(vehicle_data: dict):
    return await _vehicle_svc.register_vehicle(vehicle_data)

@router.post("/{vehicle_uid}/photos")
async def upload_vehicle_photo(
    vehicle_uid: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user),
):
    """Upload a picture for a vehicle. Returns the updated vehicle."""
    vehicle = await Vehicle.find_one(Vehicle.uid == vehicle_uid)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    # Use a server-generated UUID path — no user-controlled data in the filename
    filename = f"veh_{uuid.uuid4().hex}.jpg"
    file_path = os.path.join(VEHICLE_PHOTOS_DIR, filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    url = f"/uploads/vehicle_photos/{filename}"
    vehicle.image_urls.append(url)
    await vehicle.save()
    return {"message": "Photo uploaded", "url": url, "image_urls": vehicle.image_urls}

@router.delete("/{vehicle_uid}/photos")
async def delete_vehicle_photo(
    vehicle_uid: int,
    url: str = Query(...),
    current_user: dict = Depends(get_current_active_user),
):
    """Remove a photo URL from a vehicle."""
    vehicle = await Vehicle.find_one(Vehicle.uid == vehicle_uid)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    vehicle.image_urls = [u for u in vehicle.image_urls if u != url]
    await vehicle.save()
    return {"message": "Photo removed", "image_urls": vehicle.image_urls}

# --- 2. TRIPS ---
@router.get("/trips")
async def get_trips():
    return await _trip_svc.get_all_trips()

@router.post("/trip/start")
async def start_trip(req: TripStartRequest):
    trip = await _trip_svc.start_trip(
        vehicle_id=req.vehicle_uid,
        driver_name=req.driver_name,
        purpose=req.purpose,
        start_condition=req.start_condition,
    )
    # Attach contract/site info to the trip if provided
    if req.contract_id or req.site_id:
        trip_doc = await TripLog.find_one(TripLog.uid == trip.get("uid") if isinstance(trip, dict) else trip.uid)
        if trip_doc:
            if req.contract_id:
                trip_doc.contract_id = req.contract_id
                trip_doc.contract_code = req.contract_code
            if req.site_id:
                trip_doc.site_id = req.site_id
                trip_doc.site_name = req.site_name
            if req.driver_employee_uid:
                trip_doc.driver_employee_uid = req.driver_employee_uid
            await trip_doc.save()
    return trip

@router.post("/trip/end/{trip_uid}")
async def end_trip(trip_uid: int, end_mileage: float, end_condition: str):
    return await _trip_svc.end_trip(
        trip_id=trip_uid,
        end_mileage=end_mileage,
        end_condition=end_condition,
    )

# --- 3. MAINTENANCE ---
@router.get("/maintenance")
async def get_maintenance_logs():
    return await _maint_svc.get_all_maintenance_logs()

@router.post("/maintenance")
async def add_maintenance(log: dict):
    return await _maint_svc.add_maintenance_log(log)

# --- 4. FUEL ---
@router.get("/fuel")
async def get_fuel_logs():
    return await _maint_svc.get_all_fuel_logs()

@router.post("/fuel")
async def add_fuel_log(log: dict):
    return await _maint_svc.add_fuel_log(log)

# --- 5. EXPENSES ---
@router.get("/expenses")
async def get_all_expenses():
    return await _vehicle_svc.get_all_expenses()

@router.post("/expense")
async def add_expense(req: ExpenseRequest):
    return await _vehicle_svc.add_expense(req)
