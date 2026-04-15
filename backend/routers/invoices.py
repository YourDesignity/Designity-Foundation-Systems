from fastapi import APIRouter, HTTPException, Response
from typing import List
from backend.models import Invoice
from backend.database import get_next_uid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
import io
import traceback

router = APIRouter(prefix="/invoices", tags=["Invoices"])

@router.get("/", response_model=List[Invoice])
async def get_all_invoices():
    return await Invoice.find_all().sort("-created_at").to_list()

@router.post("/")
async def create_invoice(invoice: Invoice):
    invoice.uid = await get_next_uid("invoices")
    invoice.invoice_no = f"INV-2026-{1000 + invoice.uid}"
    await invoice.create()
    return invoice

@router.patch("/{uid}/pay")
async def pay_invoice(uid: int):
    invoice = await Invoice.find_one(Invoice.uid == uid)
    if not invoice: raise HTTPException(404, "Invoice not found")
    invoice.status = "Paid"
    await invoice.save()
    return invoice

@router.get("/{uid}/pdf")
async def generate_invoice_pdf(uid: int):
    try:
        invoice = await Invoice.find_one(Invoice.uid == uid)
        if not invoice: 
            raise HTTPException(status_code=404, detail="Invoice record missing")

        # Data Sanitization
        inv_no = str(invoice.invoice_no or "N/A")
        inv_date = str(invoice.date or "N/A")
        client = str(invoice.client_name or "Valued Client")
        amount_val = float(invoice.total_amount or 0)
        
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        w, h = A4

        # --- THEME COLORS ---
        primary_color = HexColor("#1e293b") # Professional Dark Blue/Slate
        accent_color = HexColor("#f8fafc")  # Light Background

        # 1. TOP HEADER BRANDING
        p.setFillColor(primary_color)
        p.rect(0, h - 80, w, 80, stroke=0, fill=1) # Top Bar
        
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 24)
        p.drawString(50, h - 45, "MONTREAL INTERNATIONAL")
        p.setFont("Helvetica", 12)
        p.drawString(50, h - 60, "GENERAL TRADING & CONTRACTING W.L.L")

        # 2. INVOICE TITLE & INFO
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 28)
        p.drawRightString(w - 50, h - 130, "TAX INVOICE")
        
        # Meta Data Box
        p.setFont("Helvetica-Bold", 10)
        p.drawRightString(w - 140, h - 155, "INVOICE NO:")
        p.drawRightString(w - 140, h - 170, "DATE:")
        p.drawRightString(w - 140, h - 185, "PROJECT REF:")
        
        p.setFont("Helvetica", 10)
        p.drawString(w - 130, h - 155, inv_no)
        p.drawString(w - 130, h - 170, inv_date)
        p.drawString(w - 130, h - 185, f"PROJ-{invoice.project_uid}")

        # 3. CLIENT DETAILS (BILL TO)
        p.setStrokeColor(primary_color)
        p.setLineWidth(1)
        p.line(50, h - 210, w - 50, h - 210)
        
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, h - 230, "BILL TO:")
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, h - 250, client)
        p.setFont("Helvetica", 10)
        p.drawString(50, h - 265, "Kuwait Business District")

        # 4. MAIN ITEMS TABLE
        table_top = h - 320
        
        # Header Row
        p.setFillColor(primary_color)
        p.rect(50, table_top, w - 100, 30, fill=1, stroke=0)
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(65, table_top + 10, "DESCRIPTION / SERVICE SPECIFICATION")
        p.drawRightString(w - 65, table_top + 10, "TOTAL (KWD)")

        # Content Row
        p.setFillColor(colors.black)
        p.setFont("Helvetica", 11)
        p.drawString(65, table_top - 30, f"Operational Services for Project ID: {invoice.project_uid}")
        p.drawRightString(w - 65, table_top - 30, "{:,.3f}".format(amount_val))
        
        # Borders
        p.setStrokeColor(colors.lightgrey)
        p.rect(50, table_top - 100, w - 100, 100, fill=0, stroke=1) # Table Border

        # 5. TOTAL SECTION
        p.setFillColor(accent_color)
        p.rect(w - 250, table_top - 150, 200, 40, fill=1, stroke=1)
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(w - 240, table_top - 140, "GRAND TOTAL")
        p.drawRightString(w - 65, table_top - 140, "{:,.3f} KWD".format(amount_val))

        # 6. SIGNATURE & TERMS
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, 180, "TERMS & CONDITIONS")
        p.setFont("Helvetica", 9)
        p.drawString(50, 165, "1. Payment is due within 15 days of invoice date.")
        p.drawString(50, 152, "2. Please include Invoice Number on your remittance.")
        p.drawString(50, 139, "3. This is a system-generated document and does not require a physical signature.")

        # Signature Line
        p.line(w - 200, 100, w - 50, 100)
        p.drawRightString(w - 75, 85, "Authorized Signatory")

        # Footer
        p.setFont("Helvetica-Oblique", 8)
        p.setFillColor(colors.grey)
        p.drawCentredString(w/2, 40, "Montreal International GTC | Mekka Street, Fahaheel, Kuwait | Phone: +965 XXXX XXXX")

        p.showPage()
        p.save()
        pdf_out = buffer.getvalue()
        buffer.close()

        return Response(
            content=pdf_out,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Invoice_{inv_no}.pdf",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="PDF Layout Engine Error")