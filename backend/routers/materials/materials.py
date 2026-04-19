# backend/routers/materials.py
"""
Material Management Router
Handles Materials, Suppliers, Purchase Orders, and Stock Movements
for inventory-based project costing.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.models import Material, Supplier
from backend.security import get_current_active_user
from backend.services.materials.material_service import MaterialService
from backend.services.materials.supplier_service import SupplierService
from backend.services.materials.purchase_order_service import PurchaseOrderService
from backend.utils.logger import setup_logger

logger = setup_logger("MaterialsRouter", log_file="logs/materials_router.log", level=logging.DEBUG)

router = APIRouter(
    prefix="/materials",
    tags=["Materials"],
    dependencies=[Depends(get_current_active_user)]
)

suppliers_router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"],
    dependencies=[Depends(get_current_active_user)]
)

purchase_orders_router = APIRouter(
    prefix="/purchase-orders",
    tags=["Purchase Orders"],
    dependencies=[Depends(get_current_active_user)]
)

_material_svc = MaterialService()
_supplier_svc = SupplierService()
_po_svc = PurchaseOrderService()


# =============================================================================
# SCHEMAS
# =============================================================================

class MaterialCreate(BaseModel):
    material_code: str
    name: str
    category: str = "raw_material"
    unit_of_measure: str = "pcs"
    minimum_stock: float = 0.0
    unit_cost: float = 0.0
    description: Optional[str] = None


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit_of_measure: Optional[str] = None
    minimum_stock: Optional[float] = None
    unit_cost: Optional[float] = None
    description: Optional[str] = None


class StockAdjustment(BaseModel):
    movement_type: str   # "IN" | "OUT"
    quantity: float
    unit_cost: float = 0.0
    notes: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    reference_code: Optional[str] = None


class SupplierCreate(BaseModel):
    supplier_code: str
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class POItemCreate(BaseModel):
    material_id: int
    quantity: float
    unit_cost: float


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    items: List[POItemCreate]
    notes: Optional[str] = None
    expected_delivery: Optional[str] = None


class ContractMaterialUsage(BaseModel):
    material_id: int
    quantity: float
    contract_id: int
    contract_code: Optional[str] = None
    notes: Optional[str] = None


# =============================================================================
# MATERIAL ENDPOINTS
# =============================================================================

@router.get("/", response_model=List[Material])
async def get_materials():
    """Get all materials."""
    return await _material_svc.get_all_materials()


@router.get("/{material_id}")
async def get_material(material_id: int):
    """Get a single material by ID."""
    return await _material_svc.get_material_by_id(material_id)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_material(
    data: MaterialCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new material."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create materials")
    return await _material_svc.create_material(data)


@router.put("/{material_id}")
async def update_material(
    material_id: int,
    data: MaterialUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update material details."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update materials")
    return await _material_svc.update_material(material_id, data)


@router.delete("/{material_id}")
async def delete_material(
    material_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a material (only if no stock)."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can delete materials")
    return await _material_svc.hard_delete_material(material_id)


@router.post("/{material_id}/stock-adjustment")
async def adjust_stock(
    material_id: int,
    data: StockAdjustment,
    current_user: dict = Depends(get_current_active_user)
):
    """Record a stock IN or OUT movement."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can adjust stock")
    result = await _material_svc.adjust_stock(
        material_id=material_id,
        movement_type=data.movement_type,
        quantity=data.quantity,
        unit_cost=data.unit_cost or None,
        reason=data.notes,
        performed_by=current_user.get("uid"),
        reference_type=data.reference_type,
        reference_id=data.reference_id,
        reference_code=data.reference_code,
    )
    return {
        "message": "Stock updated",
        "current_stock": result["material"].current_stock,
        "movement": result["movement"],
    }


@router.get("/{material_id}/movements")
async def get_material_movements(material_id: int):
    """Get all stock movements for a material."""
    return await _material_svc.get_material_movements(material_id)


@router.get("/contract/{contract_id}/usage")
async def get_contract_material_usage(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get all material movements (usage) for a contract.
    Accessible by Admins and Site Managers.
    """
    from backend.models.materials import MaterialMovement, Material

    movements = await MaterialMovement.find(
        MaterialMovement.reference_id == contract_id,
        MaterialMovement.reference_type == "contract_usage",
    ).sort(-MaterialMovement.created_at).to_list()

    result = []
    for m in movements:
        material = await Material.find_one(Material.uid == m.material_id)
        result.append({
            "uid": m.uid,
            "material_id": m.material_id,
            "material_name": m.material_name or (material.name if material else f"Material {m.material_id}"),
            "movement_type": m.movement_type,
            "quantity": m.quantity,
            "unit_cost": m.unit_cost,
            "total_cost": m.total_cost,
            "notes": m.notes,
            "performed_by": m.performed_by_admin_id,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return result


@router.post("/use-on-contract")
async def use_material_on_contract(
    data: ContractMaterialUsage,
    current_user: dict = Depends(get_current_active_user)
):
    """Record material usage on a contract (OUT movement). Managers can also record usage."""
    role = current_user.get("role", "")
    if role not in ["SuperAdmin", "Admin", "Site Manager"]:
        raise HTTPException(status_code=403, detail="Only Admins and Managers can record material usage")
    return await _material_svc.use_material_on_contract(
        material_id=data.material_id,
        quantity=data.quantity,
        contract_id=data.contract_id,
        contract_code=data.contract_code,
        notes=data.notes,
        performed_by=current_user.get("uid"),
    )


# =============================================================================
# SUPPLIER ENDPOINTS
# =============================================================================

@suppliers_router.get("/", response_model=List[Supplier])
async def get_suppliers():
    """Get all suppliers."""
    return await _supplier_svc.get_all_suppliers()


@suppliers_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_supplier(
    data: SupplierCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new supplier."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create suppliers")
    return await _supplier_svc.create_supplier(data)


@suppliers_router.put("/{supplier_id}")
async def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update supplier details."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update suppliers")
    return await _supplier_svc.update_supplier(supplier_id, data)


@suppliers_router.delete("/{supplier_id}")
async def delete_supplier(
    supplier_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a supplier."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can delete suppliers")
    return await _supplier_svc.remove_supplier(supplier_id)


# =============================================================================
# PURCHASE ORDER ENDPOINTS
# =============================================================================

@purchase_orders_router.get("/")
async def get_purchase_orders(status_filter: Optional[str] = None):
    """Get all purchase orders, optionally filtered by status."""
    return await _po_svc.get_all_purchase_orders(status_filter)


@purchase_orders_router.get("/{po_id}")
async def get_purchase_order(po_id: int):
    """Get a single purchase order."""
    return await _po_svc.get_purchase_order_by_id(po_id)


@purchase_orders_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    data: PurchaseOrderCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new purchase order."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create purchase orders")
    return await _po_svc.create_purchase_order(data, created_by=current_user.get("uid"))


@purchase_orders_router.post("/{po_id}/receive")
async def receive_purchase_order(
    po_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Mark a purchase order as received and update material stock."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can receive purchase orders")
    po = await _po_svc.receive_purchase_order(po_id, received_by=current_user.get("uid"))
    return {"message": f"Purchase order {po.po_number} received successfully", "po": po}


@purchase_orders_router.delete("/{po_id}")
async def delete_purchase_order(
    po_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a pending purchase order."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can delete purchase orders")
    await _po_svc.delete_purchase_order(po_id)
    return {"message": "Purchase order deleted"}
