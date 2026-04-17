from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from backend.services.vehicles.vehicle_service import VehicleService
from backend.services.vehicles.trip_log_service import TripLogService
from backend.services.vehicles.maintenance_service import MaintenanceService

router = APIRouter(prefix="/vehicles", tags=["Vehicle Management"])

_vehicle_svc = VehicleService()
_trip_svc = TripLogService()
_maint_svc = MaintenanceService()

# --- SCHEMAS ---
class TripStartRequest(BaseModel):
    vehicle_uid: int
    driver_name: str
    purpose: str
    start_condition: str

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

# --- 2. TRIPS ---
@router.get("/trips")
async def get_trips():
    return await _trip_svc.get_all_trips()

@router.post("/trip/start")
async def start_trip(req: TripStartRequest):
    return await _trip_svc.start_trip(
        vehicle_id=req.vehicle_uid,
        driver_name=req.driver_name,
        purpose=req.purpose,
        start_condition=req.start_condition,
    )

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