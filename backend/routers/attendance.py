import logging
import traceback
import calendar
from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import List
from io import BytesIO

# PDF Generation Imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from backend import schemas
from backend.models import Attendance, DutyAssignment, Admin, Employee
from backend.database import get_next_uid
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger 

router = APIRouter(prefix="/attendance", tags=["Attendance"], dependencies=[Depends(get_current_active_user)])
logger = setup_logger("AttendanceRouter", log_file="logs/attendance.log", level=logging.DEBUG)

# =============================================================================
# 1. MONTREAL INTERNATIONAL PDF BRANDING (FROM INVOICE)
# =============================================================================
def draw_branding_header(canvas, doc):
    canvas.saveState()
    
    # Draw the dark header bar (matching your invoice screenshot)
    canvas.setFillColor(colors.HexColor("#1B2631"))
    canvas.rect(0, doc.pagesize[1] - 1.1*inch, doc.pagesize[0], 1.1*inch, fill=1)
    
    # Company Name (White, Bold)
    canvas.setFillColor(colors.white)
    canvas.setFont('Helvetica-Bold', 20)
    canvas.drawString(0.5*inch, doc.pagesize[1] - 0.5*inch, "MONTREAL INTERNATIONAL")
    
    # Subtitle (White, smaller)
    canvas.setFont('Helvetica', 9)
    canvas.drawString(0.5*inch, doc.pagesize[1] - 0.75*inch, "GENERAL TRADING & CONTRACTING W.L.L")
    
    # Report Title on the Right side of the dark bar
    canvas.setFont('Helvetica-Bold', 12)
    canvas.drawRightString(doc.pagesize[0] - 0.5*inch, doc.pagesize[1] - 0.6*inch, "DAILY ATTENDANCE REPORT")
    
    # Footer info
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.grey)
    footer_line = "Montreal International GTC | Mekka Street, Fahaheel, Kuwait | Phone: +965 XXXX XXXX"
    canvas.drawCentredString(doc.pagesize[0]/2, 0.4*inch, footer_line)
    
    canvas.restoreState()

# =============================================================================
# 2. STANDARD ENDPOINTS (Ensures UI List works)
# =============================================================================

@router.get("/by-date/{date}")
async def get_attendance_by_date(date: str, current_user: dict = Depends(get_current_active_user)):
    try:
        # Frontend needs this to show the employees in the cards
        return await Attendance.find(Attendance.date == date).to_list()
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Database fetch error")

@router.get("/by-month/{year}/{month}/")
async def get_attendance_by_month(year: int, month: int, current_user: dict = Depends(get_current_active_user)):
    try:
        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day:02d}"
        return await Attendance.find(Attendance.date >= start_date, Attendance.date <= end_date).to_list()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Monthly fetch error")

@router.post("/update/")
async def update_attendance(data: schemas.AttendanceUpdateBatch, current_user: dict = Depends(get_current_active_user)):
    try:
        for record in data.records:
            existing = await Attendance.find_one(Attendance.employee_uid == record.employee_id, Attendance.date == record.date)
            if existing:
                existing.status = record.status
                existing.shift = record.shift
                existing.overtime_hours = record.overtime_hours or 0
                await existing.save()
            else:
                new_uid = await get_next_uid("attendance")
                await Attendance(
                    uid=new_uid,
                    employee_uid=record.employee_id,
                    date=record.date,
                    status=record.status,
                    shift=record.shift,
                    overtime_hours=record.overtime_hours or 0
                ).insert()
        return {"message": "Attendance records synced"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Update failed")

# =============================================================================
# 3. PROFESSIONAL DAILY PDF EXPORT
# =============================================================================

@router.get("/export-pdf/{date}")
async def export_attendance_pdf(date: str):
    try:
        # 1. Fetch records for the date and employee info for names
        records = await Attendance.find(Attendance.date == date).to_list()
        employees = await Employee.find_all().to_list()
        emp_map = {e.uid: e.name for e in employees}

        # 2. Setup the Document
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            topMargin=1.4*inch, # Extra space for the dark bar
            bottomMargin=0.8*inch
        )
        
        styles = getSampleStyleSheet()
        elements = []
        
        # Date Paragraph
        date_style = ParagraphStyle('DateStyle', parent=styles['Normal'], fontSize=11, textColor=colors.black, spaceAfter=20)
        elements.append(Paragraph(f"<b>DATE:</b> {date}", date_style))

        # 3. Create Table Data
        # Custom Header for Attendance
        table_data = [["ID", "EMPLOYEE NAME", "STATUS", "SHIFT", "OVERTIME"]]
        
        # Add Rows
        sorted_records = sorted(records, key=lambda x: x.employee_uid)
        for r in sorted_records:
            table_data.append([
                f"{r.employee_uid:02d}",
                emp_map.get(r.employee_uid, "Unknown Employee").upper(),
                r.status.upper(),
                (r.shift or "N/A").upper(),
                f"{r.overtime_hours} HRS"
            ])

        # 4. Table Styling (Branded but separate from invoice)
        attendance_table = Table(table_data, colWidths=[0.6*inch, 2.7*inch, 1.2*inch, 1.1*inch, 1.1*inch])
        attendance_table.setStyle(TableStyle([
            # Table Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2C3E50")), # Professional Navy
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            
            # Grid and Row styling
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'), # Employee Name Left Aligned
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(attendance_table)

        # 5. Build PDF using the Branding Header Template
        doc.build(elements, onFirstPage=draw_branding_header, onLaterPages=draw_branding_header)
        
        pdf_out = buffer.getvalue()
        buffer.close()

        return Response(
            content=pdf_out,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Attendance_Report_{date}.pdf"}
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="PDF engine error")