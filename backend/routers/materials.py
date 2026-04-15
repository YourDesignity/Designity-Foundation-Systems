# backend/routers/materials.py
"""
Material Management Router
Handles Materials, Suppliers, Purchase Orders, and Stock Movements
for inventory-based project costing.
"""

import os
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.models import Material, Supplier, PurchaseOrder, PurchaseOrderItem, MaterialMovement
from backend.database import get_next_uid
from backend.security import get_current_active_user
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
    return await Material.find_all().sort("name").to_list()


@router.get("/{material_id}")
async def get_material(material_id: int):
    """Get a single material by ID."""
    material = await Material.find_one(Material.uid == material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_material(
    data: MaterialCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new material."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create materials")

    # Check for duplicate material_code
    existing = await Material.find_one(Material.material_code == data.material_code)
    if existing:
        raise HTTPException(status_code=400, detail=f"Material code '{data.material_code}' already exists")

    material = Material(
        uid=await get_next_uid("materials"),
        material_code=data.material_code,
        name=data.name,
        category=data.category,
        unit_of_measure=data.unit_of_measure,
        current_stock=0.0,
        minimum_stock=data.minimum_stock,
        unit_cost=data.unit_cost,
        description=data.description,
    )
    await material.create()
    logger.info("Material created: %s (%s)", material.name, material.material_code)
    return material


@router.put("/{material_id}")
async def update_material(
    material_id: int,
    data: MaterialUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update material details."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update materials")

    material = await Material.find_one(Material.uid == material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(material, key, value)
    material.updated_at = datetime.now()
    await material.save()
    return material


@router.delete("/{material_id}")
async def delete_material(
    material_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a material (only if no stock)."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can delete materials")

    material = await Material.find_one(Material.uid == material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    await material.delete()
    return {"message": "Material deleted"}


@router.post("/{material_id}/stock-adjustment")
async def adjust_stock(
    material_id: int,
    data: StockAdjustment,
    current_user: dict = Depends(get_current_active_user)
):
    """Record a stock IN or OUT movement."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can adjust stock")

    if data.movement_type not in ("IN", "OUT"):
        raise HTTPException(status_code=400, detail="movement_type must be 'IN' or 'OUT'")

    material = await Material.find_one(Material.uid == material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    if data.movement_type == "OUT" and material.current_stock < data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    # Update stock
    if data.movement_type == "IN":
        material.current_stock += data.quantity
    else:
        material.current_stock -= data.quantity
    material.updated_at = datetime.now()
    await material.save()

    # Record movement
    movement = MaterialMovement(
        uid=await get_next_uid("material_movements"),
        material_id=material_id,
        material_name=material.name,
        movement_type=data.movement_type,
        quantity=data.quantity,
        unit_cost=data.unit_cost or material.unit_cost,
        total_cost=(data.unit_cost or material.unit_cost) * data.quantity,
        reference_type=data.reference_type,
        reference_id=data.reference_id,
        reference_code=data.reference_code,
        notes=data.notes,
        performed_by_admin_id=current_user.get("uid"),
    )
    await movement.create()

    return {"message": "Stock updated", "current_stock": material.current_stock, "movement": movement}


@router.get("/{material_id}/movements")
async def get_material_movements(material_id: int):
    """Get all stock movements for a material."""
    movements = await MaterialMovement.find(
        MaterialMovement.material_id == material_id
    ).sort("-created_at").to_list()
    return movements


@router.post("/use-on-contract")
async def use_material_on_contract(
    data: ContractMaterialUsage,
    current_user: dict = Depends(get_current_active_user)
):
    """Record material usage on a contract (OUT movement)."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can record material usage")

    material = await Material.find_one(Material.uid == data.material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    if material.current_stock < data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock for this usage")

    # Deduct stock
    material.current_stock -= data.quantity
    material.updated_at = datetime.now()
    await material.save()

    # Record movement
    movement = MaterialMovement(
        uid=await get_next_uid("material_movements"),
        material_id=data.material_id,
        material_name=material.name,
        movement_type="OUT",
        quantity=data.quantity,
        unit_cost=material.unit_cost,
        total_cost=material.unit_cost * data.quantity,
        reference_type="contract_usage",
        reference_id=data.contract_id,
        reference_code=data.contract_code,
        notes=data.notes,
        performed_by_admin_id=current_user.get("uid"),
    )
    await movement.create()

    return {
        "message": "Material usage recorded",
        "current_stock": material.current_stock,
        "cost": movement.total_cost,
    }


# =============================================================================
# SUPPLIER ENDPOINTS
# =============================================================================

@suppliers_router.get("/", response_model=List[Supplier])
async def get_suppliers():
    """Get all suppliers."""
    return await Supplier.find_all().sort("name").to_list()


@suppliers_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_supplier(
    data: SupplierCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new supplier."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create suppliers")

    existing = await Supplier.find_one(Supplier.supplier_code == data.supplier_code)
    if existing:
        raise HTTPException(status_code=400, detail=f"Supplier code '{data.supplier_code}' already exists")

    supplier = Supplier(
        uid=await get_next_uid("suppliers"),
        **data.model_dump()
    )
    await supplier.create()
    return supplier


@suppliers_router.put("/{supplier_id}")
async def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update supplier details."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update suppliers")

    supplier = await Supplier.find_one(Supplier.uid == supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    for key, value in data.model_dump(exclude_none=True).items():
        setattr(supplier, key, value)
    supplier.updated_at = datetime.now()
    await supplier.save()
    return supplier


@suppliers_router.delete("/{supplier_id}")
async def delete_supplier(
    supplier_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a supplier."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can delete suppliers")

    supplier = await Supplier.find_one(Supplier.uid == supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    await supplier.delete()
    return {"message": "Supplier deleted"}


# =============================================================================
# PURCHASE ORDER ENDPOINTS
# =============================================================================

@purchase_orders_router.get("/")
async def get_purchase_orders(status_filter: Optional[str] = None):
    """Get all purchase orders, optionally filtered by status."""
    if status_filter:
        orders = await PurchaseOrder.find(PurchaseOrder.status == status_filter).sort("-created_at").to_list()
    else:
        orders = await PurchaseOrder.find_all().sort("-created_at").to_list()
    return orders


@purchase_orders_router.get("/{po_id}")
async def get_purchase_order(po_id: int):
    """Get a single purchase order."""
    po = await PurchaseOrder.find_one(PurchaseOrder.uid == po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


@purchase_orders_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    data: PurchaseOrderCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new purchase order."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create purchase orders")

    supplier = await Supplier.find_one(Supplier.uid == data.supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Build items with material details
    po_items = []
    total_amount = 0.0
    for item in data.items:
        mat = await Material.find_one(Material.uid == item.material_id)
        if not mat:
            raise HTTPException(status_code=404, detail=f"Material {item.material_id} not found")
        total_cost = item.quantity * item.unit_cost
        total_amount += total_cost
        po_items.append(PurchaseOrderItem(
            material_id=item.material_id,
            material_name=mat.name,
            material_code=mat.material_code,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            total_cost=total_cost,
        ))

    uid = await get_next_uid("purchase_orders")
    po_number = f"PO-{uid:04d}"

    expected_delivery = None
    if data.expected_delivery:
        try:
            expected_delivery = datetime.fromisoformat(data.expected_delivery)
        except ValueError:
            pass

    po = PurchaseOrder(
        uid=uid,
        po_number=po_number,
        supplier_id=data.supplier_id,
        supplier_name=supplier.name,
        items=po_items,
        total_amount=total_amount,
        status="pending",
        notes=data.notes,
        ordered_by_admin_id=current_user.get("uid"),
        expected_delivery=expected_delivery,
    )
    await po.create()
    logger.info("Purchase order created: %s", po.po_number)
    return po


@purchase_orders_router.post("/{po_id}/receive")
async def receive_purchase_order(
    po_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Mark a purchase order as received and update material stock."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can receive purchase orders")

    po = await PurchaseOrder.find_one(PurchaseOrder.uid == po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if po.status == "received":
        raise HTTPException(status_code=400, detail="Purchase order already received")

    # Update stock for each item
    for item in po.items:
        material = await Material.find_one(Material.uid == item.material_id)
        if material:
            old_stock = material.current_stock
            old_cost = material.unit_cost
            new_qty = item.quantity
            new_cost = item.unit_cost

            # Weighted average cost calculation
            if new_cost > 0:
                total_qty = old_stock + new_qty
                if total_qty > 0:
                    material.unit_cost = ((old_stock * old_cost) + (new_qty * new_cost)) / total_qty
                else:
                    material.unit_cost = new_cost

            material.current_stock += new_qty
            material.updated_at = datetime.now()
            await material.save()

            # Record stock IN movement
            movement = MaterialMovement(
                uid=await get_next_uid("material_movements"),
                material_id=item.material_id,
                material_name=item.material_name,
                movement_type="IN",
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                total_cost=item.total_cost,
                reference_type="purchase_order",
                reference_id=po.uid,
                reference_code=po.po_number,
                notes=f"Received from PO {po.po_number}",
                performed_by_admin_id=current_user.get("uid"),
            )
            await movement.create()

    po.status = "received"
    po.received_at = datetime.now()
    po.updated_at = datetime.now()
    await po.save()

    logger.info("Purchase order received: %s", po.po_number)
    return {"message": f"Purchase order {po.po_number} received successfully", "po": po}


@purchase_orders_router.delete("/{po_id}")
async def delete_purchase_order(
    po_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a pending purchase order."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can delete purchase orders")

    po = await PurchaseOrder.find_one(PurchaseOrder.uid == po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if po.status == "received":
        raise HTTPException(status_code=400, detail="Cannot delete a received purchase order")

    await po.delete()
    return {"message": "Purchase order deleted"}
