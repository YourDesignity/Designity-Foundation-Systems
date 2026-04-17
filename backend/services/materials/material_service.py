"""Service layer for material operations."""

import logging
from datetime import date, datetime
from typing import Any, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class MaterialService(BaseService):
    """Material master, stock, and valuation logic."""

    @staticmethod
    def _to_dict(payload: Any) -> dict:
        return payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

    @staticmethod
    def _parse_day_from_datetime(value: datetime) -> date:
        return value.date() if isinstance(value, datetime) else value

    # ====================================================================
    # MATERIAL CRUD
    # ====================================================================

    async def create_material(self, payload: Any):
        """Create material with unique material_code."""
        from backend.models import Material

        data = self._to_dict(payload)
        material_code = str(data.get("material_code", "")).strip()
        name = str(data.get("name", "")).strip()
        if not material_code:
            self.raise_bad_request("material_code is required")
        if not name:
            self.raise_bad_request("name is required")

        existing = await Material.find_one(Material.material_code == material_code)
        if existing:
            self.raise_bad_request(f"Material code '{material_code}' already exists")

        uid = await self.get_next_uid("materials")
        material = Material(
            uid=uid,
            material_code=material_code,
            name=name,
            category=data.get("category", "raw_material"),
            unit_of_measure=data.get("unit_of_measure", "pcs"),
            current_stock=float(data.get("current_stock", 0.0)),
            minimum_stock=float(data.get("minimum_stock", 0.0)),
            unit_cost=float(data.get("unit_cost", 0.0)),
            description=data.get("description"),
            is_active=True,
        )
        await material.insert()

        logger.info("Material created: %s (%s)", material.name, material.material_code)
        return material

    async def update_material(self, material_id: int, payload: Any):
        """Update material details."""
        material = await self.get_material_by_id(material_id)
        data = self._to_dict(payload)

        if "material_code" in data:
            duplicate = await self.get_material_by_code(data["material_code"], raise_if_missing=False)
            if duplicate and duplicate.uid != material.uid:
                self.raise_bad_request(f"Material code '{data['material_code']}' already exists")

        for key, value in data.items():
            setattr(material, key, value)
        material.updated_at = datetime.now()
        await material.save()

        logger.info("Material updated: %s", material_id)
        return material

    async def delete_material(self, material_id: int, deleted_by: Optional[int] = None):
        """Soft-delete material by setting is_active False."""
        material = await self.get_material_by_id(material_id)
        material.is_active = False
        material.updated_at = datetime.now()
        await material.save()

        logger.warning("Material deactivated: %s by user %s", material.material_code, deleted_by)
        return material

    async def get_material_by_id(self, material_id: int):
        """Get material by UID."""
        from backend.models import Material

        material = await Material.find_one(Material.uid == material_id)
        if not material:
            self.raise_not_found("Material not found")
        return material

    async def get_material_by_code(self, material_code: str, raise_if_missing: bool = True):
        """Get material by material code."""
        from backend.models import Material

        material = await Material.find_one(Material.material_code == material_code)
        if not material and raise_if_missing:
            self.raise_not_found("Material not found")
        return material

    async def get_all_materials(self, category: Optional[str] = None, status: Optional[str] = None):
        """Get materials with category/active-status filters."""
        from backend.models import Material

        filters = []
        if category:
            filters.append(Material.category == category)
        if status == "active":
            filters.append(Material.is_active == True)
        elif status == "inactive":
            filters.append(Material.is_active == False)
        return await (Material.find(*filters).sort("name").to_list() if filters else Material.find_all().sort("name").to_list())

    # ====================================================================
    # STOCK OPERATIONS
    # ====================================================================

    async def add_stock(
        self,
        material_id: int,
        quantity: float,
        unit_cost: Optional[float] = None,
        notes: Optional[str] = None,
        reference_type: Optional[str] = "adjustment",
        reference_id: Optional[int] = None,
        reference_code: Optional[str] = None,
        performed_by: Optional[int] = None,
    ):
        """Increase stock and create IN movement."""
        if quantity <= 0:
            self.raise_bad_request("quantity must be greater than 0")
        material = await self.get_material_by_id(material_id)

        effective_cost = unit_cost if unit_cost is not None else material.unit_cost
        if effective_cost < 0:
            self.raise_bad_request("unit_cost cannot be negative")

        if unit_cost is not None:
            old_total_value = material.current_stock * material.unit_cost
            new_total_value = quantity * unit_cost
            new_qty = material.current_stock + quantity
            material.unit_cost = (old_total_value + new_total_value) / new_qty if new_qty > 0 else material.unit_cost

        material.current_stock += quantity
        material.updated_at = datetime.now()
        await material.save()

        movement = await self.record_material_movement(
            material_id=material.uid,
            movement_type="IN",
            quantity=quantity,
            unit_cost=effective_cost,
            notes=notes,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_code=reference_code,
            performed_by=performed_by,
        )

        logger.info("Stock added: %s +%s", material.material_code, quantity)
        return {"material": material, "movement": movement}

    async def deduct_stock(
        self,
        material_id: int,
        quantity: float,
        notes: Optional[str] = None,
        reference_type: Optional[str] = "contract_usage",
        reference_id: Optional[int] = None,
        reference_code: Optional[str] = None,
        performed_by: Optional[int] = None,
    ):
        """Decrease stock and create OUT movement."""
        if quantity <= 0:
            self.raise_bad_request("quantity must be greater than 0")

        material = await self.get_material_by_id(material_id)
        if material.current_stock < quantity:
            self.raise_bad_request("Insufficient stock quantity")

        material.current_stock -= quantity
        material.updated_at = datetime.now()
        await material.save()

        movement = await self.record_material_movement(
            material_id=material.uid,
            movement_type="OUT",
            quantity=quantity,
            unit_cost=material.unit_cost,
            notes=notes,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_code=reference_code,
            performed_by=performed_by,
        )

        logger.info("Stock deducted: %s -%s", material.material_code, quantity)
        return {"material": material, "movement": movement}

    async def adjust_stock(
        self,
        material_id: int,
        movement_type: str,
        quantity: float,
        unit_cost: Optional[float] = None,
        reason: Optional[str] = None,
        performed_by: Optional[int] = None,
    ):
        """Manually adjust stock using IN/OUT movement semantics."""
        movement = movement_type.upper().strip()
        if movement not in {"IN", "OUT"}:
            self.raise_bad_request("movement_type must be IN or OUT")

        if movement == "IN":
            return await self.add_stock(
                material_id=material_id,
                quantity=quantity,
                unit_cost=unit_cost,
                notes=reason,
                reference_type="adjustment",
                performed_by=performed_by,
            )
        return await self.deduct_stock(
            material_id=material_id,
            quantity=quantity,
            notes=reason,
            reference_type="adjustment",
            performed_by=performed_by,
        )

    async def record_material_movement(
        self,
        material_id: int,
        movement_type: str,
        quantity: float,
        unit_cost: Optional[float] = None,
        notes: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        reference_code: Optional[str] = None,
        performed_by: Optional[int] = None,
    ):
        """Persist a stock movement record."""
        from backend.models import MaterialMovement

        material = await self.get_material_by_id(material_id)
        movement = movement_type.upper().strip()
        if movement not in {"IN", "OUT"}:
            self.raise_bad_request("movement_type must be IN or OUT")

        effective_cost = unit_cost if unit_cost is not None else material.unit_cost
        uid = await self.get_next_uid("material_movements")
        row = MaterialMovement(
            uid=uid,
            material_id=material.uid,
            material_name=material.name,
            movement_type=movement,
            quantity=quantity,
            unit_cost=effective_cost,
            total_cost=round(quantity * effective_cost, 3),
            reference_type=reference_type,
            reference_id=reference_id,
            reference_code=reference_code,
            notes=notes,
            performed_by_admin_id=performed_by,
        )
        await row.insert()
        return row

    async def get_material_movements(
        self,
        material_id: int,
        movement_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ):
        """Get movement history for a material with optional filters."""
        from backend.models import MaterialMovement

        await self.get_material_by_id(material_id)
        filters = [MaterialMovement.material_id == material_id]
        if movement_type:
            filters.append(MaterialMovement.movement_type == movement_type.upper())

        rows = await MaterialMovement.find(*filters).sort("-created_at").to_list()
        result = []
        for row in rows:
            movement_day = self._parse_day_from_datetime(row.created_at)
            if start_date and movement_day < start_date:
                continue
            if end_date and movement_day > end_date:
                continue
            result.append(row)
        return result

    # ====================================================================
    # ALERTS & REPORTS
    # ====================================================================

    async def get_low_stock_materials(self):
        """Get materials below minimum stock."""
        materials = await self.get_all_materials(status="active")
        return [m for m in materials if m.current_stock <= m.minimum_stock and m.current_stock > 0]

    async def get_out_of_stock_materials(self):
        """Get materials with zero/negative stock."""
        materials = await self.get_all_materials(status="active")
        return [m for m in materials if m.current_stock <= 0]

    async def send_stock_alerts(self) -> dict:
        """Compose low-stock/out-of-stock alert payload."""
        low_stock = await self.get_low_stock_materials()
        out_of_stock = await self.get_out_of_stock_materials()
        return {
            "low_stock_count": len(low_stock),
            "out_of_stock_count": len(out_of_stock),
            "low_stock_materials": low_stock,
            "out_of_stock_materials": out_of_stock,
        }

    async def calculate_material_value(self, material_id: int) -> dict:
        """Calculate current inventory value for one material."""
        material = await self.get_material_by_id(material_id)
        value = round(material.current_stock * material.unit_cost, 3)
        return {
            "material_id": material.uid,
            "material_code": material.material_code,
            "material_name": material.name,
            "quantity": material.current_stock,
            "unit_cost": material.unit_cost,
            "value": value,
        }

    async def get_total_inventory_value(self) -> dict:
        """Calculate total value across active inventory."""
        materials = await self.get_all_materials(status="active")
        rows = [await self.calculate_material_value(m.uid) for m in materials]
        total = round(sum(row["value"] for row in rows), 3)
        return {"total_inventory_value": total, "material_count": len(rows), "materials": rows}

    async def get_material_usage_report(
        self,
        start_date: date,
        end_date: date,
        material_id: Optional[int] = None,
    ) -> dict:
        """Report OUT movements over a date range."""
        from backend.models import MaterialMovement

        if end_date < start_date:
            self.raise_bad_request("end_date must be on/after start_date")

        filters = [MaterialMovement.movement_type == "OUT"]
        if material_id is not None:
            filters.append(MaterialMovement.material_id == material_id)

        rows = await MaterialMovement.find(*filters).sort("-created_at").to_list()
        items = []
        for row in rows:
            movement_day = self._parse_day_from_datetime(row.created_at)
            if movement_day < start_date or movement_day > end_date:
                continue
            items.append(
                {
                    "movement_id": row.uid,
                    "material_id": row.material_id,
                    "material_name": row.material_name,
                    "quantity": row.quantity,
                    "unit_cost": row.unit_cost,
                    "total_cost": row.total_cost,
                    "date": row.created_at.isoformat(),
                    "reference_type": row.reference_type,
                    "reference_code": row.reference_code,
                }
            )

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_records": len(items),
            "total_quantity": round(sum(item["quantity"] for item in items), 3),
            "total_cost": round(sum(item["total_cost"] for item in items), 3),
            "items": items,
        }

    # --------------------------------------------------------------------
    # Backward compatible aliases
    # --------------------------------------------------------------------

    async def get_materials(self):
        """Backward-compatible alias for get_all_materials."""
        return await self.get_all_materials()
