from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from backend.models import Vehicle, TripLog, MaintenanceLog, FuelLog, VehicleExpense
from backend.database import get_next_uid

router = APIRouter(prefix="/vehicles", tags=["Vehicle Management"])

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
@router.get("/", response_model=List[Vehicle])
async def get_all_vehicles():
    return await Vehicle.find_all().to_list()

@router.post("/")
async def add_vehicle(vehicle_data: Vehicle):
    # Case-insensitive plate check
    existing = await Vehicle.find_one(Vehicle.plate == vehicle_data.plate.upper())
    if existing: 
        raise HTTPException(status_code=400, detail=f"Plate {vehicle_data.plate} already exists in the system")
    
    vehicle_data.uid = await get_next_uid("vehicles")
    vehicle_data.plate = vehicle_data.plate.upper() # Standardize to Uppercase
    vehicle_data.status = "Available"
    await vehicle_data.create()
    return vehicle_data

# --- 2. TRIPS ---
@router.get("/trips", response_model=List[TripLog])
async def get_trips():
    return await TripLog.find_all().sort("-out_time").to_list()

@router.post("/trip/start")
async def start_trip(req: TripStartRequest):
    vehicle = await Vehicle.find_one(Vehicle.uid == req.vehicle_uid)
    if not vehicle: raise HTTPException(404, "Vehicle not found")
    vehicle.status = "On Trip"
    await vehicle.save()
    new_trip = TripLog(
        uid=await get_next_uid("vehicle_trips"),
        vehicle_uid=req.vehicle_uid,
        vehicle_plate=vehicle.plate,
        driver_name=req.driver_name,
        purpose=req.purpose,
        start_condition=req.start_condition,
        out_time=datetime.now(),
        status="Ongoing",
        start_mileage=vehicle.current_mileage
    )
    await new_trip.create()
    return new_trip

@router.post("/trip/end/{trip_uid}")
async def end_trip(trip_uid: int, end_mileage: float, end_condition: str):
    trip = await TripLog.find_one(TripLog.uid == trip_uid)
    if not trip: raise HTTPException(404, "Trip not found")
    trip.in_time = datetime.now()
    trip.status = "Completed"
    trip.end_mileage = end_mileage
    trip.end_condition = end_condition
    await trip.save()
    vehicle = await Vehicle.find_one(Vehicle.uid == trip.vehicle_uid)
    if vehicle:
        vehicle.status = "Available"
        vehicle.current_mileage = max(end_mileage, vehicle.current_mileage)
        await vehicle.save()
    return {"message": "Trip ended"}

# --- 3. MAINTENANCE ---
@router.get("/maintenance", response_model=List[MaintenanceLog])
async def get_maintenance_logs():
    return await MaintenanceLog.find_all().sort("-service_date").to_list()

@router.post("/maintenance")
async def add_maintenance(log: MaintenanceLog):
    vehicle = await Vehicle.find_one(Vehicle.uid == log.vehicle_uid)
    if not vehicle: raise HTTPException(404, "Vehicle not found")
    log.uid = await get_next_uid("vehicle_maintenance")
    log.vehicle_plate = vehicle.plate
    await log.create()
    return log

# --- 4. FUEL ---
@router.get("/fuel", response_model=List[FuelLog])
async def get_fuel_logs():
    return await FuelLog.find_all().sort("-date").to_list()

@router.post("/fuel")
async def add_fuel_log(log: FuelLog):
    vehicle = await Vehicle.find_one(Vehicle.uid == log.vehicle_uid)
    if not vehicle: raise HTTPException(404, "Vehicle not found")
    log.uid = await get_next_uid("vehicle_fuel")
    log.vehicle_plate = vehicle.plate
    if log.odometer > vehicle.current_mileage:
        vehicle.current_mileage = log.odometer
        await vehicle.save()
    await log.create()
    return log

# --- 5. EXPENSES ---
@router.get("/expenses", response_model=List[VehicleExpense])
async def get_all_expenses():
    return await VehicleExpense.find_all().sort("-date").to_list()

@router.post("/expense")
async def add_expense(req: ExpenseRequest):
    vehicle = await Vehicle.find_one(Vehicle.uid == req.vehicle_uid)
    if not vehicle: raise HTTPException(404, "Vehicle not found")
    expense = VehicleExpense(
        uid=await get_next_uid("vehicle_expenses"),
        vehicle_uid=req.vehicle_uid,
        vehicle_plate=vehicle.plate,
        driver_name=req.driver_name,
        category=req.category,
        amount=req.amount,
        date=req.date,
        description=req.description
    )
    await expense.create()
    return expense