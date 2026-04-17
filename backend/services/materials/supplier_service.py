"""Service layer for supplier operations."""

import logging
from datetime import date, datetime
from typing import Any, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class SupplierService(BaseService):
    """Supplier master and performance logic."""

    @staticmethod
    def _to_dict(payload: Any) -> dict:
        return payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

    @staticmethod
    def _in_range(dt_value: datetime, start_date: Optional[date], end_date: Optional[date]) -> bool:
        day = dt_value.date()
        if start_date and day < start_date:
            return False
        if end_date and day > end_date:
            return False
        return True

    # ====================================================================
    # CRUD OPERATIONS
    # ====================================================================

    async def create_supplier(self, payload: Any):
        """Create supplier with unique supplier_code."""
        from backend.models import Supplier

        data = self._to_dict(payload)
        supplier_code = str(data.get("supplier_code", "")).strip()
        name = str(data.get("name", "")).strip()
        if not supplier_code:
            self.raise_bad_request("supplier_code is required")
        if not name:
            self.raise_bad_request("name is required")

        existing = await Supplier.find_one(Supplier.supplier_code == supplier_code)
        if existing:
            self.raise_bad_request(f"Supplier code '{supplier_code}' already exists")

        uid = await self.get_next_uid("suppliers")
        supplier = Supplier(uid=uid, supplier_code=supplier_code, name=name, **{k: v for k, v in data.items() if k not in {"supplier_code", "name"}})
        supplier.specs = {
            "ratings": [],
            "material_links": [],
        }
        await supplier.insert()
        logger.info("Supplier created: %s (%s)", supplier.name, supplier_code)
        return supplier

    async def update_supplier(self, supplier_id: int, payload: Any):
        """Update supplier details."""
        supplier = await self.get_supplier_by_id(supplier_id)
        data = self._to_dict(payload)

        if "supplier_code" in data:
            duplicate = await self.get_supplier_by_code(data["supplier_code"], raise_if_missing=False)
            if duplicate and duplicate.uid != supplier.uid:
                self.raise_bad_request(f"Supplier code '{data['supplier_code']}' already exists")

        for key, value in data.items():
            setattr(supplier, key, value)
        supplier.updated_at = datetime.now()
        await supplier.save()
        logger.info("Supplier updated: %s", supplier_id)
        return supplier

    async def deactivate_supplier(self, supplier_id: int, deactivated_by: Optional[int] = None):
        """Soft-delete supplier."""
        supplier = await self.get_supplier_by_id(supplier_id)
        supplier.is_active = False
        supplier.updated_at = datetime.now()
        await supplier.save()
        logger.warning("Supplier deactivated: %s by user %s", supplier_id, deactivated_by)
        return supplier

    async def get_supplier_by_id(self, supplier_id: int):
        """Get supplier by UID."""
        from backend.models import Supplier

        supplier = await Supplier.find_one(Supplier.uid == supplier_id)
        if not supplier:
            self.raise_not_found("Supplier not found")
        return supplier

    async def get_supplier_by_code(self, supplier_code: str, raise_if_missing: bool = True):
        """Get supplier by supplier code."""
        from backend.models import Supplier

        supplier = await Supplier.find_one(Supplier.supplier_code == supplier_code)
        if not supplier and raise_if_missing:
            self.raise_not_found("Supplier not found")
        return supplier

    async def get_all_suppliers(self, active_only: Optional[bool] = None):
        """List suppliers with optional active filter."""
        from backend.models import Supplier

        filters = []
        if active_only is True:
            filters.append(Supplier.is_active == True)
        elif active_only is False:
            filters.append(Supplier.is_active == False)
        return await (Supplier.find(*filters).sort("name").to_list() if filters else Supplier.find_all().sort("name").to_list())

    # ====================================================================
    # RATINGS & PERFORMANCE
    # ====================================================================

    async def rate_supplier(self, supplier_id: int, rating: float, review: Optional[str] = None, rated_by: Optional[int] = None):
        """Attach a rating/review to supplier metadata."""
        if rating < 0 or rating > 5:
            self.raise_bad_request("rating must be between 0 and 5")

        supplier = await self.get_supplier_by_id(supplier_id)
        specs = dict(supplier.specs or {})
        ratings = list(specs.get("ratings", []))
        ratings.append(
            {
                "rating": round(float(rating), 2),
                "review": review,
                "rated_by": rated_by,
                "rated_at": datetime.now().isoformat(),
            }
        )
        specs["ratings"] = ratings
        supplier.specs = specs
        supplier.updated_at = datetime.now()
        await supplier.save()

        avg_rating = round(sum(r["rating"] for r in ratings) / len(ratings), 3)
        return {"supplier_id": supplier.uid, "average_rating": avg_rating, "ratings_count": len(ratings)}

    async def get_top_suppliers(self, limit: int = 5):
        """Return top suppliers by average rating."""
        suppliers = await self.get_all_suppliers(active_only=True)
        ranked = []
        for supplier in suppliers:
            ratings = list((supplier.specs or {}).get("ratings", []))
            if ratings:
                avg = sum(item["rating"] for item in ratings) / len(ratings)
                ranked.append({"supplier": supplier, "average_rating": round(avg, 3), "ratings_count": len(ratings)})

        ranked.sort(key=lambda item: (item["average_rating"], item["ratings_count"]), reverse=True)
        return ranked[: max(0, limit)]

    async def calculate_supplier_performance(
        self,
        supplier_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Calculate on-time and quality metrics from PO/ratings."""
        from backend.models import PurchaseOrder

        supplier = await self.get_supplier_by_id(supplier_id)
        orders = await PurchaseOrder.find(PurchaseOrder.supplier_id == supplier.uid).to_list()
        orders = [o for o in orders if self._in_range(o.created_at, start_date, end_date)]

        delivered = [o for o in orders if o.status in {"received", "partial"}]
        on_time_deliveries = 0
        for order in delivered:
            if order.expected_delivery and order.received_at and order.received_at <= order.expected_delivery:
                on_time_deliveries += 1

        ratings = list((supplier.specs or {}).get("ratings", []))
        avg_rating = round(sum(item["rating"] for item in ratings) / len(ratings), 3) if ratings else 0.0
        on_time_rate = round((on_time_deliveries / len(delivered)) * 100, 2) if delivered else 0.0

        return {
            "supplier_id": supplier.uid,
            "supplier_name": supplier.name,
            "total_orders": len(orders),
            "delivered_orders": len(delivered),
            "on_time_deliveries": on_time_deliveries,
            "on_time_percentage": on_time_rate,
            "quality_rating": avg_rating,
            "ratings_count": len(ratings),
        }

    # ====================================================================
    # MATERIAL LINKING
    # ====================================================================

    async def link_material_to_supplier(
        self,
        supplier_id: int,
        material_id: int,
        unit_cost: float,
        lead_time_days: Optional[int] = None,
        is_preferred: bool = False,
    ):
        """Store supplier-material pricing metadata."""
        from backend.models import Material

        if unit_cost < 0:
            self.raise_bad_request("unit_cost cannot be negative")

        supplier = await self.get_supplier_by_id(supplier_id)
        material = await Material.find_one(Material.uid == material_id)
        if not material:
            self.raise_not_found("Material not found")

        specs = dict(supplier.specs or {})
        links = list(specs.get("material_links", []))
        links = [row for row in links if row.get("material_id") != material_id]
        links.append(
            {
                "material_id": material.uid,
                "material_code": material.material_code,
                "material_name": material.name,
                "unit_cost": unit_cost,
                "lead_time_days": lead_time_days,
                "is_preferred": is_preferred,
                "updated_at": datetime.now().isoformat(),
            }
        )
        specs["material_links"] = links
        supplier.specs = specs
        supplier.updated_at = datetime.now()
        await supplier.save()
        return {"supplier_id": supplier.uid, "material_id": material.uid, "unit_cost": unit_cost}

    async def get_supplier_materials(self, supplier_id: int):
        """Get materials configured for supplier."""
        supplier = await self.get_supplier_by_id(supplier_id)
        return list((supplier.specs or {}).get("material_links", []))

    async def get_material_suppliers(self, material_id: int):
        """Get suppliers linked to a material."""
        suppliers = await self.get_all_suppliers(active_only=True)
        rows = []
        for supplier in suppliers:
            for link in (supplier.specs or {}).get("material_links", []):
                if link.get("material_id") == material_id:
                    rows.append({"supplier_id": supplier.uid, "supplier_name": supplier.name, **link})
        return rows

    # ====================================================================
    # SPEND REPORTING
    # ====================================================================

    async def calculate_supplier_spend(
        self,
        supplier_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Calculate total spend against one supplier."""
        from backend.models import PurchaseOrder

        supplier = await self.get_supplier_by_id(supplier_id)
        orders = await PurchaseOrder.find(PurchaseOrder.supplier_id == supplier.uid).to_list()
        filtered = [o for o in orders if self._in_range(o.created_at, start_date, end_date)]
        total_spend = round(sum(o.total_amount for o in filtered), 3)
        return {
            "supplier_id": supplier.uid,
            "supplier_name": supplier.name,
            "order_count": len(filtered),
            "total_spend": total_spend,
        }

    async def get_supplier_purchase_history(self, supplier_id: int, status: Optional[str] = None):
        """Get supplier purchase order history."""
        from backend.models import PurchaseOrder

        await self.get_supplier_by_id(supplier_id)
        filters = [PurchaseOrder.supplier_id == supplier_id]
        if status:
            filters.append(PurchaseOrder.status == status)
        return await PurchaseOrder.find(*filters).sort("-created_at").to_list()

    # --------------------------------------------------------------------
    # Backward compatible aliases
    # --------------------------------------------------------------------

    async def get_suppliers(self):
        """Backward-compatible alias for get_all_suppliers."""
        return await self.get_all_suppliers()

    async def delete_supplier(self, supplier_id: int) -> bool:
        """Backward-compatible alias for deactivate_supplier."""
        await self.deactivate_supplier(supplier_id)
        return True
