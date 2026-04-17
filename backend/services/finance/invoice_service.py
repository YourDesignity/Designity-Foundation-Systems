"""Service layer for invoice operations."""

import logging
from datetime import date, datetime
from typing import Any, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")
# Keep invoice numbers aligned with existing INV-YYYY-1xxx format used by routers/UI.
INVOICE_NUMBER_OFFSET = 1000


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
        invoice_no = data.get("invoice_no") or f"INV-{invoice_date.year}-{INVOICE_NUMBER_OFFSET + new_uid}"

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
        """Return unpaid invoices whose due_date is strictly before the given date."""
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

        by_project = await Invoice.find(Invoice.project_uid == contract.project_id).sort("-created_at").to_list()
        by_contract_spec = await Invoice.find({"specs.contract_id": contract_id}).sort("-created_at").to_list()

        merged: dict[int, Any] = {}
        for inv in by_project:
            merged[inv.uid] = inv
        for inv in by_contract_spec:
            merged[inv.uid] = inv
        return sorted(merged.values(), key=lambda row: row.created_at, reverse=True)

    async def calculate_outstanding_amount(self, contract_id: Optional[int] = None) -> float:
        """Calculate total unpaid amount, optionally scoped to a contract."""
        invoices = await (self.get_contract_invoices(contract_id) if contract_id is not None else self.get_unpaid_invoices())
        return sum(float(inv.total_amount or 0) for inv in invoices if inv.status not in {"Paid", "Voided"})

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

    async def create_invoice_basic(self, invoice):
        """Simple invoice creation matching original router behavior."""
        from backend.models import Invoice

        invoice.uid = await self.get_next_uid("invoices")
        invoice.invoice_no = f"INV-2026-{INVOICE_NUMBER_OFFSET + invoice.uid}"
        await invoice.create()
        logger.info("Invoice created (basic): %s (ID: %s)", invoice.invoice_no, invoice.uid)
        return invoice

    async def generate_invoice_pdf(self, invoice_id: int) -> bytes:
        """Generate a professional PDF for an invoice and return raw bytes."""
        import io
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.colors import HexColor

        invoice = await self.get_invoice_by_id(invoice_id)

        inv_no = str(invoice.invoice_no or "N/A")
        inv_date = str(invoice.date or "N/A")
        client = str(invoice.client_name or "Valued Client")
        amount_val = float(invoice.total_amount or 0)

        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        w, h = A4

        primary_color = HexColor("#1e293b")
        accent_color = HexColor("#f8fafc")

        # TOP HEADER BRANDING
        p.setFillColor(primary_color)
        p.rect(0, h - 80, w, 80, stroke=0, fill=1)

        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 24)
        p.drawString(50, h - 45, "MONTREAL INTERNATIONAL")
        p.setFont("Helvetica", 12)
        p.drawString(50, h - 60, "GENERAL TRADING & CONTRACTING W.L.L")

        # INVOICE TITLE & INFO
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 28)
        p.drawRightString(w - 50, h - 130, "TAX INVOICE")

        p.setFont("Helvetica-Bold", 10)
        p.drawRightString(w - 140, h - 155, "INVOICE NO:")
        p.drawRightString(w - 140, h - 170, "DATE:")
        p.drawRightString(w - 140, h - 185, "PROJECT REF:")

        p.setFont("Helvetica", 10)
        p.drawString(w - 130, h - 155, inv_no)
        p.drawString(w - 130, h - 170, inv_date)
        p.drawString(w - 130, h - 185, f"PROJ-{invoice.project_uid}")

        # CLIENT DETAILS (BILL TO)
        p.setStrokeColor(primary_color)
        p.setLineWidth(1)
        p.line(50, h - 210, w - 50, h - 210)

        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, h - 230, "BILL TO:")
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, h - 250, client)
        p.setFont("Helvetica", 10)
        p.drawString(50, h - 265, "Kuwait Business District")

        # MAIN ITEMS TABLE
        table_top = h - 320

        p.setFillColor(primary_color)
        p.rect(50, table_top, w - 100, 30, fill=1, stroke=0)
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(65, table_top + 10, "DESCRIPTION / SERVICE SPECIFICATION")
        p.drawRightString(w - 65, table_top + 10, "TOTAL (KWD)")

        p.setFillColor(colors.black)
        p.setFont("Helvetica", 11)
        p.drawString(65, table_top - 30, f"Operational Services for Project ID: {invoice.project_uid}")
        p.drawRightString(w - 65, table_top - 30, "{:,.3f}".format(amount_val))

        p.setStrokeColor(colors.lightgrey)
        p.rect(50, table_top - 100, w - 100, 100, fill=0, stroke=1)

        # TOTAL SECTION
        p.setFillColor(accent_color)
        p.rect(w - 250, table_top - 150, 200, 40, fill=1, stroke=1)
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(w - 240, table_top - 140, "GRAND TOTAL")
        p.drawRightString(w - 65, table_top - 140, "{:,.3f} KWD".format(amount_val))

        # SIGNATURE & TERMS
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, 180, "TERMS & CONDITIONS")
        p.setFont("Helvetica", 9)
        p.drawString(50, 165, "1. Payment is due within 15 days of invoice date.")
        p.drawString(50, 152, "2. Please include Invoice Number on your remittance.")
        p.drawString(50, 139, "3. This is a system-generated document and does not require a physical signature.")

        p.line(w - 200, 100, w - 50, 100)
        p.drawRightString(w - 75, 85, "Authorized Signatory")

        # Footer
        p.setFont("Helvetica-Oblique", 8)
        p.setFillColor(colors.grey)
        p.drawCentredString(w / 2, 40, "Montreal International GTC | Mekka Street, Fahaheel, Kuwait | Phone: +965 XXXX XXXX")

        p.showPage()
        p.save()
        pdf_out = buffer.getvalue()
        buffer.close()
        return pdf_out

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
