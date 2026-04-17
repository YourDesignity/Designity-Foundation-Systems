"""Service layer for purchase order operations."""

import logging
import os
from datetime import date, datetime
from typing import Any, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class PurchaseOrderService(BaseService):
    """Purchase-order lifecycle, receiving, and reporting logic."""

    @staticmethod
    def _to_dict(payload: Any) -> dict:
        return payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

    @staticmethod
    def _parse_date(value: Any) -> Optional[datetime]:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    # ====================================================================
    # PO CREATION & WORKFLOW
    # ====================================================================

    async def create_purchase_order(self, payload: Any, created_by: Optional[int] = None):
        """Create purchase order draft with supplier/material validation."""
        from backend.models import Material, PurchaseOrder, PurchaseOrderItem, Supplier

        data = self._to_dict(payload)
        supplier_id = data.get("supplier_id")
        if supplier_id is None:
            self.raise_bad_request("supplier_id is required")

        supplier = await Supplier.find_one(Supplier.uid == supplier_id)
        if not supplier:
            self.raise_not_found("Supplier not found")

        item_inputs = data.get("items", [])
        if not item_inputs:
            self.raise_bad_request("Purchase order must include at least one item")

        po_items = []
        total_amount = 0.0
        for item in item_inputs:
            row = item.model_dump(exclude_unset=True) if hasattr(item, "model_dump") else dict(item)
            material = await Material.find_one(Material.uid == row.get("material_id"))
            if not material:
                self.raise_not_found(f"Material {row.get('material_id')} not found")

            quantity = float(row.get("quantity", 0.0))
            unit_cost = float(row.get("unit_cost", 0.0))
            if quantity <= 0:
                self.raise_bad_request("Item quantity must be greater than 0")
            if unit_cost < 0:
                self.raise_bad_request("Item unit_cost cannot be negative")

            total_cost = round(quantity * unit_cost, 3)
            total_amount += total_cost
            po_items.append(
                PurchaseOrderItem(
                    material_id=material.uid,
                    material_name=material.name,
                    material_code=material.material_code,
                    quantity=quantity,
                    unit_cost=unit_cost,
                    total_cost=total_cost,
                )
            )

        uid = await self.get_next_uid("purchase_orders")
        po = PurchaseOrder(
            uid=uid,
            po_number=f"PO-{uid:04d}",
            supplier_id=supplier.uid,
            supplier_name=supplier.name,
            items=po_items,
            total_amount=round(total_amount, 3),
            status="draft",
            notes=data.get("notes"),
            ordered_by_admin_id=created_by if created_by is not None else data.get("ordered_by_admin_id"),
            expected_delivery=self._parse_date(data.get("expected_delivery")),
        )
        await po.insert()
        logger.info("Purchase order created: %s", po.po_number)
        return po

    async def submit_purchase_order(self, po_id: int, submitted_by: Optional[int] = None):
        """Submit PO for approval."""
        po = await self.get_purchase_order_by_id(po_id)
        if po.status not in {"draft", "rejected"}:
            self.raise_bad_request("Only draft/rejected purchase orders can be submitted")

        po.status = "pending"
        po.updated_at = datetime.now()
        specs = dict(po.specs or {})
        specs["submitted_by"] = submitted_by
        specs["submitted_at"] = datetime.now().isoformat()
        po.specs = specs
        await po.save()
        return po

    async def approve_purchase_order(self, po_id: int, approver_role: str, approver_id: Optional[int] = None):
        """Approve submitted PO after authority check."""
        po = await self.get_purchase_order_by_id(po_id)
        if po.status not in {"pending", "pending_approval"}:
            self.raise_bad_request("Only pending purchase orders can be approved")

        if not self.check_approval_authority(approver_role, po.total_amount):
            self.raise_forbidden("No approval authority for this amount")

        po.status = "approved"
        po.updated_at = datetime.now()
        specs = dict(po.specs or {})
        specs["approved_by"] = approver_id
        specs["approved_role"] = approver_role
        specs["approved_at"] = datetime.now().isoformat()
        po.specs = specs
        await po.save()
        logger.info("Purchase order approved: %s", po.po_number)
        return po

    async def reject_purchase_order(self, po_id: int, reason: str, rejected_by: Optional[int] = None):
        """Reject PO with reason."""
        po = await self.get_purchase_order_by_id(po_id)
        if po.status not in {"pending", "pending_approval", "approved"}:
            self.raise_bad_request("Only pending/approved purchase orders can be rejected")

        po.status = "rejected"
        po.updated_at = datetime.now()
        specs = dict(po.specs or {})
        specs["rejected_by"] = rejected_by
        specs["rejected_at"] = datetime.now().isoformat()
        specs["rejection_reason"] = reason
        po.specs = specs
        await po.save()
        return po

    async def receive_purchase_order(self, po_id: int, received_by: Optional[int] = None):
        """Receive entire PO and update stock/movements."""
        po = await self.get_purchase_order_by_id(po_id)
        if po.status == "received":
            self.raise_bad_request("Purchase order already received")

        for item in po.items:
            await self._receive_item(po, item, item.quantity, received_by)

        po.status = "received"
        po.received_at = datetime.now()
        po.updated_at = datetime.now()
        specs = dict(po.specs or {})
        specs["received_by"] = received_by
        specs["received_at"] = datetime.now().isoformat()
        po.specs = specs
        await po.save()

        logger.info("Purchase order received: %s", po.po_number)
        return po

    # ====================================================================
    # READ OPERATIONS
    # ====================================================================

    async def get_purchase_order_by_id(self, po_id: int):
        """Get PO by UID."""
        from backend.models import PurchaseOrder

        po = await PurchaseOrder.find_one(PurchaseOrder.uid == po_id)
        if not po:
            self.raise_not_found("Purchase order not found")
        return po

    async def get_purchase_order_by_number(self, po_number: str):
        """Get PO by po_number."""
        from backend.models import PurchaseOrder

        po = await PurchaseOrder.find_one(PurchaseOrder.po_number == po_number)
        if not po:
            self.raise_not_found("Purchase order not found")
        return po

    async def get_pending_purchase_orders(self):
        """List POs awaiting processing."""
        from backend.models import PurchaseOrder

        return await PurchaseOrder.find(PurchaseOrder.status == "pending").sort("-created_at").to_list()

    async def get_supplier_purchase_orders(self, supplier_id: int):
        """List POs for a supplier."""
        from backend.models import PurchaseOrder, Supplier

        supplier = await Supplier.find_one(Supplier.uid == supplier_id)
        if not supplier:
            self.raise_not_found("Supplier not found")
        return await PurchaseOrder.find(PurchaseOrder.supplier_id == supplier_id).sort("-created_at").to_list()

    async def get_purchase_orders_awaiting_approval(self):
        """Get approval queue."""
        from backend.models import PurchaseOrder

        return await PurchaseOrder.find(PurchaseOrder.status.in_(["pending", "pending_approval"])).sort("-created_at").to_list()

    def check_approval_authority(self, approver_role: str, total_amount: float) -> bool:
        """Check approval authority by role and amount thresholds."""
        admin_limit = float(os.getenv("PO_ADMIN_APPROVAL_LIMIT", "5000"))
        manager_limit = float(os.getenv("PO_MANAGER_APPROVAL_LIMIT", "1000"))
        role = (approver_role or "").strip().lower()
        if role == "superadmin":
            return True
        if role == "admin":
            return total_amount <= admin_limit
        if role in {"site manager", "manager"}:
            return total_amount <= manager_limit
        return False

    # ====================================================================
    # RECEIVING OPERATIONS
    # ====================================================================

    async def partial_receive(self, po_id: int, received_items: list[dict], received_by: Optional[int] = None):
        """Receive selected quantities from PO."""
        po = await self.get_purchase_order_by_id(po_id)
        if po.status in {"received", "cancelled", "rejected"}:
            self.raise_bad_request("Purchase order cannot be partially received in current state")

        item_map = {item.material_id: item for item in po.items}
        for row in received_items:
            material_id = int(row.get("material_id"))
            qty = float(row.get("quantity", 0.0))
            if qty <= 0:
                self.raise_bad_request("Received quantity must be greater than 0")

            if material_id not in item_map:
                self.raise_bad_request(f"Material {material_id} is not part of this PO")

            po_item = item_map[material_id]
            if qty > po_item.quantity:
                self.raise_bad_request(f"Received quantity exceeds ordered quantity for material {material_id}")

            await self._receive_item(po, po_item, qty, received_by)

        total_received = sum(float(r.get("quantity", 0.0)) for r in received_items)
        total_ordered = sum(item.quantity for item in po.items)

        po.status = "received" if total_received >= total_ordered else "partial"
        po.received_at = datetime.now() if po.status == "received" else po.received_at
        po.updated_at = datetime.now()
        specs = dict(po.specs or {})
        specs["last_partial_receive"] = datetime.now().isoformat()
        specs["received_by"] = received_by
        po.specs = specs
        await po.save()
        return po

    async def get_overdue_purchase_orders(self, as_of: Optional[date] = None):
        """Find pending/approved POs past expected delivery date."""
        from backend.models import PurchaseOrder

        current_day = as_of or date.today()
        orders = await PurchaseOrder.find(PurchaseOrder.status.in_(["pending", "approved", "partial"])) .to_list()

        overdue = []
        for order in orders:
            if order.expected_delivery and order.expected_delivery.date() < current_day:
                overdue.append(order)
        return overdue

    # ====================================================================
    # REPORTS
    # ====================================================================

    async def calculate_total_po_value(
        self,
        start_date: date,
        end_date: date,
        supplier_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> dict:
        """Calculate PO value for a date range."""
        from backend.models import PurchaseOrder

        if end_date < start_date:
            self.raise_bad_request("end_date must be on/after start_date")

        filters = []
        if supplier_id is not None:
            filters.append(PurchaseOrder.supplier_id == supplier_id)
        if status is not None:
            filters.append(PurchaseOrder.status == status)

        orders = await (PurchaseOrder.find(*filters).to_list() if filters else PurchaseOrder.find_all().to_list())
        selected = [o for o in orders if start_date <= o.created_at.date() <= end_date]
        total = round(sum(order.total_amount for order in selected), 3)

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "supplier_id": supplier_id,
            "status": status,
            "po_count": len(selected),
            "total_value": total,
        }

    async def get_po_status_summary(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> dict:
        """Get grouped PO counts/values by status."""
        from backend.models import PurchaseOrder

        orders = await PurchaseOrder.find_all().to_list()
        if start_date or end_date:
            filtered = []
            for order in orders:
                order_day = order.created_at.date()
                if start_date and order_day < start_date:
                    continue
                if end_date and order_day > end_date:
                    continue
                filtered.append(order)
            orders = filtered

        summary: dict[str, dict[str, float]] = {}
        for order in orders:
            bucket = summary.setdefault(order.status, {"count": 0, "total_value": 0.0})
            bucket["count"] += 1
            bucket["total_value"] += order.total_amount

        return {
            status: {"count": row["count"], "total_value": round(row["total_value"], 3)}
            for status, row in summary.items()
        }

    # --------------------------------------------------------------------
    # INTERNAL HELPERS
    # --------------------------------------------------------------------

    async def _receive_item(self, po, po_item, quantity: float, received_by: Optional[int]):
        from backend.models import Material
        from backend.services.materials.material_service import MaterialService

        material = await Material.find_one(Material.uid == po_item.material_id)
        if not material:
            self.raise_not_found(f"Material {po_item.material_id} not found")

        material_service = MaterialService()
        await material_service.add_stock(
            material_id=material.uid,
            quantity=quantity,
            unit_cost=po_item.unit_cost,
            notes=f"Received from PO {po.po_number}",
            reference_type="purchase_order",
            reference_id=po.uid,
            reference_code=po.po_number,
            performed_by=received_by,
        )

    # --------------------------------------------------------------------
    # Backward compatible aliases
    # --------------------------------------------------------------------

    async def get_purchase_orders(self):
        """Backward-compatible list helper."""
        from backend.models import PurchaseOrder

        return await PurchaseOrder.find_all().sort("-created_at").to_list()

    async def update_purchase_order(self, po_id: int, payload: Any):
        """Backward-compatible direct update helper."""
        po = await self.get_purchase_order_by_id(po_id)
        data = self._to_dict(payload)
        for key, value in data.items():
            setattr(po, key, value)
        po.updated_at = datetime.now()
        await po.save()
        return po

    async def delete_purchase_order(self, po_id: int) -> bool:
        """Backward-compatible delete helper for non-received POs."""
        po = await self.get_purchase_order_by_id(po_id)
        if po.status == "received":
            self.raise_bad_request("Cannot delete a received purchase order")
        await po.delete()
        logger.info("Purchase order deleted: %s", po.po_number)
        return True
