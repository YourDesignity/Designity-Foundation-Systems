"""Vehicle management models."""

from datetime import datetime
from typing import Annotated, Optional

from beanie import Document, Indexed

from backend.models.base import MemoryNode


class Vehicle(Document, MemoryNode):
    model: str
    plate: Annotated[str, Indexed(unique=True)]
    type: str
    status: str = "Available"
    current_mileage: float = 0.0
    registration_expiry: Optional[str] = None
    insurance_expiry: Optional[str] = None
    pollution_expiry: Optional[str] = None

    class Settings:
        name = "vehicles"


class TripLog(Document, MemoryNode):
    vehicle_uid: int
    vehicle_plate: Optional[str] = None
    driver_name: str
    out_time: Optional[datetime] = None
    in_time: Optional[datetime] = None
    purpose: str
    status: str = "Ongoing"
    start_mileage: float = 0.0
    end_mileage: float = 0.0
    start_condition: str = "Good"
    end_condition: Optional[str] = None

    class Settings:
        name = "vehicle_trips"


class VehicleExpense(Document, MemoryNode):
    vehicle_uid: int
    vehicle_plate: Optional[str] = None
    driver_name: str
    category: str
    amount: float
    date: str
    description: Optional[str] = None

    class Settings:
        name = "vehicle_expenses"


class MaintenanceLog(Document, MemoryNode):
    vehicle_uid: int
    vehicle_plate: Optional[str] = None
    service_type: str
    cost: float
    service_date: str
    next_due_date: Optional[str] = None
    notes: Optional[str] = None

    class Settings:
        name = "vehicle_maintenance"


class FuelLog(Document, MemoryNode):
    vehicle_uid: int
    vehicle_plate: Optional[str] = None
    date: str
    liters: float
    cost: float
    odometer: float
    filled_by: Optional[str] = None

    class Settings:
        name = "vehicle_fuel"
