"""Service layer for invoice operations."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class InvoiceService(BaseService):
    """Invoice CRUD and lifecycle operations."""

    async def create_invoice(self, payload: Any):
        from backend.models import Invoice

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("invoices")
        invoice = Invoice(**data)
        await invoice.insert()
        return invoice

    async def get_invoice_by_id(self, invoice_id: int):
        from backend.models import Invoice

        invoice = await Invoice.find_one(Invoice.uid == invoice_id)
        if not invoice:
            self.raise_not_found(f"Invoice {invoice_id} not found")
        return invoice

    async def get_invoices(self):
        from backend.models import Invoice

        return await Invoice.find_all().sort("+uid").to_list()

    async def update_invoice(self, invoice_id: int, payload: Any):
        invoice = await self.get_invoice_by_id(invoice_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(invoice, field, value)
        await invoice.save()
        return invoice

    async def delete_invoice(self, invoice_id: int) -> bool:
        invoice = await self.get_invoice_by_id(invoice_id)
        await invoice.delete()
        return True
