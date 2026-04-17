"""Service layer for invoice operations."""

import logging
from datetime import date, datetime
from typing import Any, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class InvoiceService(BaseService):
    """Invoice management and tracking."""

    # ====================================================================
    # HELPERS
    # ====================================================================

    @staticmethod
    def _to_dict(payload: Any) -> dict:
        return payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

    @staticmethod
    def _parse_date(value: Any, field_name: str) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                pass
        raise ValueError(f"{field_name} must be a valid ISO date (YYYY-MM-DD)")

    # ====================================================================
    # LIFECYCLE OPERATIONS
    # ====================================================================

    async def generate_invoice(self, payload: Any):
        """
        Generate a new invoice.

        Validations:
        - Invoice number must be unique
        - total_amount must be greater than zero
        - date and due_date must be valid dates
        - due_date cannot be before date

        Args:
            payload: Invoice create payload (dict/schema)

        Returns:
            Created Invoice document

        Raises:
            HTTPException 400: Validation errors
            HTTPException 404: Related contract not found (if provided)
        """
        from backend.models import Contract, Invoice

        data = self._to_dict(payload)

        try:
            invoice_date = self._parse_date(data.get("date"), "date")
            due_date = self._parse_date(data.get("due_date"), "due_date")
        except ValueError as exc:
            self.raise_bad_request(str(exc))

        if due_date < invoice_date:
            self.raise_bad_request("due_date cannot be before date")

        total_amount = float(data.get("total_amount", 0) or 0)
        if total_amount <= 0:
            self.raise_bad_request("total_amount must be greater than zero")

        project_uid = int(data.get("project_uid", 0) or 0)
        if project_uid <= 0:
            self.raise_bad_request("project_uid must be a positive integer")

        client_name = str(data.get("client_name") or "").strip()
        if not client_name:
            self.raise_bad_request("client_name is required")

        contract_id = data.get("contract_id")
        if contract_id is not None:
            contract = await Contract.find_one(Contract.uid == contract_id)
            if not contract:
                self.raise_not_found("Contract not found")

        new_uid = await self.get_next_uid("invoices")
        invoice_no = data.get("invoice_no") or f"INV-{invoice_date.year}-{1000 + new_uid}"

        existing = await Invoice.find_one(Invoice.invoice_no == invoice_no)
        if existing:
            self.raise_bad_request(f"Invoice number '{invoice_no}' already exists")

        invoice = Invoice(
            uid=new_uid,
            invoice_no=invoice_no,
            project_uid=project_uid,
            client_name=client_name,
            date=invoice_date.isoformat(),
            due_date=due_date.isoformat(),
            items=data.get("items") or [],
            total_amount=total_amount,
            status=data.get("status") or "Unpaid",
            specs={
                **(data.get("specs") or {}),
                **({"contract_id": contract_id} if contract_id is not None else {}),
            },
        )
        await invoice.insert()
        logger.info("Invoice created: %s (ID: %s)", invoice.invoice_no, invoice.uid)
        return invoice

    async def get_invoice_by_id(self, invoice_id: int):
        """
        Retrieve an invoice by UID.

        Validations:
        - Invoice must exist

        Args:
            invoice_id: Invoice UID

        Returns:
            Invoice document

        Raises:
            HTTPException 404: Invoice not found
        """
        from backend.models import Invoice

        invoice = await Invoice.find_one(Invoice.uid == invoice_id)
        if not invoice:
            self.raise_not_found("Invoice not found")
        return invoice

    async def get_invoice_by_number(self, invoice_no: str):
        """
        Retrieve an invoice by invoice number.

        Validations:
        - invoice_no must not be empty
        - Invoice must exist

        Args:
            invoice_no: Invoice number (e.g., INV-2026-1001)

        Returns:
            Invoice document

        Raises:
            HTTPException 400: Invalid input
            HTTPException 404: Invoice not found
        """
        from backend.models import Invoice

        normalized = (invoice_no or "").strip()
        if not normalized:
            self.raise_bad_request("invoice_no is required")

        invoice = await Invoice.find_one(Invoice.invoice_no == normalized)
        if not invoice:
            self.raise_not_found("Invoice not found")
        return invoice

    async def send_invoice(self, invoice_id: int):
        """
        Mark an invoice as sent.

        Validations:
        - Invoice must exist
        - Paid/voided invoices cannot be sent

        Args:
            invoice_id: Invoice UID

        Returns:
            Updated Invoice document

        Raises:
            HTTPException 400: Invalid status transition
            HTTPException 404: Invoice not found
        """
        invoice = await self.get_invoice_by_id(invoice_id)
        if invoice.status in {"Paid", "Voided"}:
            self.raise_bad_request("Only unpaid invoices can be sent")

        invoice.status = "Sent"
        await invoice.save()
        logger.info("Invoice sent: %s (ID: %s)", invoice.invoice_no, invoice.uid)
        return invoice

    async def mark_invoice_paid(self, invoice_id: int, payment_date: Optional[Any] = None):
        """
        Mark an invoice as paid and record payment metadata.

        Validations:
        - Invoice must exist
        - Voided invoices cannot be paid

        Args:
            invoice_id: Invoice UID
            payment_date: Optional payment date (ISO string/date/datetime)

        Returns:
            Updated Invoice document

        Raises:
            HTTPException 400: Invalid status transition or payment date
            HTTPException 404: Invoice not found
        """
        invoice = await self.get_invoice_by_id(invoice_id)
        if invoice.status == "Voided":
            self.raise_bad_request("Voided invoice cannot be marked as paid")

        paid_on = date.today()
        if payment_date is not None:
            try:
                paid_on = self._parse_date(payment_date, "payment_date")
            except ValueError as exc:
                self.raise_bad_request(str(exc))

        invoice.status = "Paid"
        invoice.specs = {**(invoice.specs or {}), "paid_at": paid_on.isoformat()}
        await invoice.save()
        logger.info("Invoice paid: %s (ID: %s)", invoice.invoice_no, invoice.uid)
        return invoice

    async def void_invoice(self, invoice_id: int, reason: Optional[str] = None):
        """
        Void/cancel an invoice.

        Validations:
        - Invoice must exist
        - Paid invoices cannot be voided

        Args:
            invoice_id: Invoice UID
            reason: Optional reason for voiding

        Returns:
            Updated Invoice document

        Raises:
            HTTPException 400: Invalid status transition
            HTTPException 404: Invoice not found
        """
        invoice = await self.get_invoice_by_id(invoice_id)
        if invoice.status == "Paid":
            self.raise_bad_request("Paid invoice cannot be voided")

        invoice.status = "Voided"
        if reason:
            invoice.specs = {**(invoice.specs or {}), "void_reason": reason}
        await invoice.save()
        logger.warning("Invoice voided: %s (ID: %s)", invoice.invoice_no, invoice.uid)
        return invoice

    # ====================================================================
    # QUERIES & REPORTS
    # ====================================================================

    async def get_unpaid_invoices(self) -> list:
        """Return all unpaid/sent/overdue invoices sorted by due date."""
        invoices = await self.get_invoices()
        return [inv for inv in invoices if inv.status not in {"Paid", "Voided"}]

    async def get_overdue_invoices(self, as_of_date: Optional[Any] = None) -> list:
        """Return unpaid invoices whose due_date is before the given date."""
        reference = date.today()
        if as_of_date is not None:
            try:
                reference = self._parse_date(as_of_date, "as_of_date")
            except ValueError as exc:
                self.raise_bad_request(str(exc))

        overdue = []
        for inv in await self.get_unpaid_invoices():
            try:
                due = self._parse_date(inv.due_date, "due_date")
            except ValueError:
                continue
            if due < reference:
                overdue.append(inv)
        return overdue

    async def get_contract_invoices(self, contract_id: int) -> list:
        """
        Return invoices related to one contract.

        Matching strategy:
        - invoices with specs.contract_id == contract_id
        - fallback to project_uid == contract.project_id
        """
        from backend.models import Contract, Invoice

        contract = await Contract.find_one(Contract.uid == contract_id)
        if not contract:
            self.raise_not_found("Contract not found")

        invoices = await Invoice.find_all().sort("-created_at").to_list()
        return [
            inv
            for inv in invoices
            if (inv.specs or {}).get("contract_id") == contract_id or inv.project_uid == contract.project_id
        ]

    async def calculate_outstanding_amount(self, contract_id: Optional[int] = None) -> float:
        """Calculate total unpaid amount, optionally scoped to a contract."""
        invoices = await (self.get_contract_invoices(contract_id) if contract_id is not None else self.get_unpaid_invoices())
        return float(sum(float(inv.total_amount or 0) for inv in invoices if inv.status not in {"Paid", "Voided"}))

    async def get_revenue_report(self, start_date: Any, end_date: Any) -> dict:
        """
        Build a revenue summary for a date range using paid invoices.

        Returns:
            Dict with count, total_revenue, and invoice rows
        """
        try:
            start = self._parse_date(start_date, "start_date")
            end = self._parse_date(end_date, "end_date")
        except ValueError as exc:
            self.raise_bad_request(str(exc))

        if end < start:
            self.raise_bad_request("end_date cannot be before start_date")

        paid_rows = []
        for inv in await self.get_invoices():
            if inv.status != "Paid":
                continue
            try:
                inv_date = self._parse_date(inv.date, "date")
            except ValueError:
                continue
            if start <= inv_date <= end:
                paid_rows.append(inv)

        return {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "invoice_count": len(paid_rows),
            "total_revenue": float(sum(float(inv.total_amount or 0) for inv in paid_rows)),
            "invoices": [
                {
                    "invoice_id": inv.uid,
                    "invoice_no": inv.invoice_no,
                    "date": inv.date,
                    "amount": float(inv.total_amount or 0),
                    "client_name": inv.client_name,
                }
                for inv in paid_rows
            ],
        }

    async def get_invoice_aging_report(self, as_of_date: Optional[Any] = None) -> dict:
        """Return invoice aging buckets for unpaid invoices."""
        reference = date.today()
        if as_of_date is not None:
            try:
                reference = self._parse_date(as_of_date, "as_of_date")
            except ValueError as exc:
                self.raise_bad_request(str(exc))

        buckets = {
            "current": 0.0,
            "1_30_days": 0.0,
            "31_60_days": 0.0,
            "61_90_days": 0.0,
            "over_90_days": 0.0,
        }

        for inv in await self.get_unpaid_invoices():
            amount = float(inv.total_amount or 0)
            try:
                due = self._parse_date(inv.due_date, "due_date")
            except ValueError:
                buckets["current"] += amount
                continue

            days_overdue = (reference - due).days
            if days_overdue <= 0:
                buckets["current"] += amount
            elif days_overdue <= 30:
                buckets["1_30_days"] += amount
            elif days_overdue <= 60:
                buckets["31_60_days"] += amount
            elif days_overdue <= 90:
                buckets["61_90_days"] += amount
            else:
                buckets["over_90_days"] += amount

        return {
            "as_of_date": reference.isoformat(),
            "buckets": buckets,
            "total_outstanding": float(sum(buckets.values())),
        }

    async def calculate_total_revenue(self, month: int, year: int) -> float:
        """Calculate total paid invoice revenue for one month."""
        if month < 1 or month > 12:
            self.raise_bad_request("month must be between 1 and 12")
        if year < 2000 or year > 2100:
            self.raise_bad_request("year is outside valid range")

        total = 0.0
        for inv in await self.get_invoices():
            if inv.status != "Paid":
                continue
            try:
                inv_date = self._parse_date(inv.date, "date")
            except ValueError:
                continue
            if inv_date.month == month and inv_date.year == year:
                total += float(inv.total_amount or 0)
        return float(total)

    # ====================================================================
    # BACKWARD-COMPAT HELPERS
    # ====================================================================

    async def create_invoice(self, payload: Any):
        """Backward-compatible wrapper for generate_invoice."""
        return await self.generate_invoice(payload)

    async def get_invoices(self):
        """Get all invoices sorted by most recent creation."""
        from backend.models import Invoice

        return await Invoice.find_all().sort("-created_at").to_list()

    async def update_invoice(self, invoice_id: int, payload: Any):
        """Backward-compatible generic invoice update."""
        invoice = await self.get_invoice_by_id(invoice_id)
        data = self._to_dict(payload)

        if "total_amount" in data and float(data["total_amount"] or 0) <= 0:
            self.raise_bad_request("total_amount must be greater than zero")

        if "date" in data:
            data["date"] = self._parse_date(data["date"], "date").isoformat()
        if "due_date" in data:
            data["due_date"] = self._parse_date(data["due_date"], "due_date").isoformat()

        for field, value in data.items():
            setattr(invoice, field, value)
        await invoice.save()
        logger.info("Invoice updated: %s (ID: %s)", invoice.invoice_no, invoice.uid)
        return invoice

    async def delete_invoice(self, invoice_id: int) -> bool:
        """Delete invoice record by ID."""
        invoice = await self.get_invoice_by_id(invoice_id)
        await invoice.delete()
        logger.warning("Invoice deleted: %s (ID: %s)", invoice.invoice_no, invoice.uid)
        return True
