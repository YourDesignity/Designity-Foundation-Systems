import traceback

from fastapi import APIRouter, HTTPException, Response
from typing import List

from backend.models import Invoice
from backend.services.finance.invoice_service import InvoiceService

router = APIRouter(prefix="/invoices", tags=["Invoices"])

_service = InvoiceService()


@router.get("/", response_model=List[Invoice])
async def get_all_invoices():
    return await _service.get_invoices()


@router.post("/")
async def create_invoice(invoice: Invoice):
    return await _service.create_invoice_basic(invoice)


@router.patch("/{uid}/pay")
async def pay_invoice(uid: int):
    return await _service.mark_invoice_paid(uid)


@router.get("/{uid}/pdf")
async def generate_invoice_pdf(uid: int):
    try:
        pdf_out = await _service.generate_invoice_pdf(uid)
        invoice = await _service.get_invoice_by_id(uid)
        inv_no = str(invoice.invoice_no or "N/A")
        return Response(
            content=pdf_out,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Invoice_{inv_no}.pdf",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except HTTPException:
        raise
    except Exception:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="PDF Layout Engine Error")