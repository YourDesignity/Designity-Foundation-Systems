# File: backend/utils/pdf_generator.py

import logging
import json
from io import BytesIO
from datetime import datetime

# ReportLab Imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# --- Logger Import ---
# Ensure this matches your project structure
from backend.utils.logger import setup_logger

# Initialize Logger
logger = setup_logger("PDFGenerator", log_file="logs/pdf_generator.log", level=logging.DEBUG)

def generate_payslip_pdf(data):
    """
    Generates a professional PDF based on the dictionary.
    Includes logic to display Overtime Hours in the salary table.
    """
    emp_name = data.get('name', 'Unknown')
    period = data.get('pay_period') or data.get('month') or "Unknown"
    
    logger.info(f"PDF START: Generating for '{emp_name}' (Period: {period})")

    buffer = BytesIO()
    
    try:
        # 1. Document Setup (A4 with standard margins)
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=40, leftMargin=40, 
            topMargin=40, bottomMargin=40
        )
        elements = []
        styles = getSampleStyleSheet()

        # --- Helper: Safe Money Formatter ---
        def fmt_money(val):
            try:
                if val is None or val == "":
                    return "0.000"
                return f"{float(val):,.3f}"
            except (ValueError, TypeError):
                return "0.000"

        # --- Custom Styles ---
        style_center = ParagraphStyle(name='Center', parent=styles['Normal'], alignment=TA_CENTER)
        style_right = ParagraphStyle(name='Right', parent=styles['Normal'], alignment=TA_RIGHT)
        style_heading_center = ParagraphStyle(name='HeadingCenter', parent=styles['Heading1'], alignment=TA_CENTER, textColor=colors.darkblue)
        
        # --- 2. Header Section ---
        elements.append(Paragraph("Montreal International Admin Software", style_heading_center))
        elements.append(Paragraph("123 Capital City, Kuwait", style_center))
        elements.append(Spacer(1, 0.3*inch))
        
        # Title & Period Table
        header_data = [
            [
                Paragraph(f"<b>PAYSLIP FOR PERIOD: {period}</b>", styles['Heading2']),
                Paragraph("<font color='red' size='9'>PRIVATE & CONFIDENTIAL</font>", style_right)
            ]
        ]
        t_header = Table(header_data, colWidths=[4*inch, 2.5*inch])
        t_header.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(t_header)
        elements.append(Spacer(1, 0.2*inch))

        # --- 3. Employee Info Grid ---
        # Shows Days Present vs Days Absent
        emp_data = [
            [
                f"Employee ID: {data.get('employee_id', 'N/A')}", 
                f"Designation: {data.get('designation', 'N/A')}"
            ],
            [
                f"Name: {emp_name}", 
                f"Days Present: {data.get('days_present', 0)} / {data.get('standard_work_days', 26)}"
            ],
            [
                "", 
                f"Days Absent: {data.get('days_absent', 0)}"
            ]
        ]

        t_info = Table(emp_data, colWidths=[3.5*inch, 3.5*inch])
        t_info.setStyle(TableStyle([
            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 11),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LINEBELOW', (0,0), (-1,-1), 1, colors.lightgrey),
        ]))
        elements.append(t_info)
        elements.append(Spacer(1, 0.4*inch))

        # --- 4. Salary Details Table ---
        # Columns: [Earnings Label, Amount, Deductions Label, Amount]
        
        table_data = [
            ["EARNINGS", "Amount (KWD)", "DEDUCTIONS", "Amount (KWD)"]
        ]
        
        # Row 1: Basic Salary vs Absence
        table_data.append([
            "Basic Salary (Contract)", 
            fmt_money(data.get('basic_salary_contract', 0)), 
            f"Absence/Leave Deduction ({data.get('days_absent', 0)} days)", 
            fmt_money(data.get('leave_deduction_amount', 0))
        ])

        # Row 2: Overtime (WITH HOURS) vs Penalties
        # Logic: Cleanly format hours (e.g. "5" instead of "5.0")
        ot_hrs = data.get('overtime_hours', 0)
        
        if ot_hrs > 0:
            # Use 'g' format to remove insignificant trailing zeros (5.0 -> 5, 5.5 -> 5.5)
            clean_hrs = f"{float(ot_hrs):g}"
            ot_label = f"Overtime Pay ({clean_hrs} hrs)" 
        else:
            ot_label = "Overtime Pay"

        table_data.append([
            ot_label, 
            fmt_money(data.get('overtime_salary', 0)), 
            "Penalties / Advances", 
            fmt_money(data.get('manual_deduction_amount', 0))
        ])

        # Row 3: Allowance
        table_data.append([
            "Allowance", 
            fmt_money(data.get('allowance', 0)), 
            "", 
            ""
        ])

        # Row 4: Totals
        table_data.append([
            "TOTAL EARNINGS", 
            fmt_money(data.get('gross_salary', 0)), 
            "TOTAL DEDUCTIONS", 
            fmt_money(data.get('total_deductions', 0))
        ])

        # Row 5: Net Pay (Spanning columns for emphasis)
        net_val = fmt_money(data.get('net_salary', 0))
        table_data.append(["NET PAYABLE SALARY", "", "", f"{net_val} KWD"])

        # Create Table Object
        t_salary = Table(table_data, colWidths=[2.5*inch, 1*inch, 2.5*inch, 1*inch])
        
        # Style the Salary Table
        t_salary.setStyle(TableStyle([
            # Header Row
            ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            
            # Column Alignments
            ('ALIGN', (0,1), (0,-1), 'LEFT'),  # Labels Left
            ('ALIGN', (1,1), (1,-1), 'RIGHT'), # Money Right
            ('ALIGN', (2,1), (2,-1), 'LEFT'),  # Labels Left
            ('ALIGN', (3,1), (3,-1), 'RIGHT'), # Money Right

            # Grid & Padding
            ('GRID', (0,0), (-1,-2), 0.5, colors.grey),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            
            # Totals Row (Grey Background)
            ('FONTNAME', (0,-2), (-1,-2), 'Helvetica-Bold'),
            ('BACKGROUND', (0,-2), (-1,-2), colors.whitesmoke),

            # Net Pay Row (Bottom Row)
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0,-1), (-1,-1), colors.darkblue),
            ('ALIGN', (-1,-1), (-1,-1), 'RIGHT'), 
            ('SPAN', (0,-1), (2,-1)), # Span the label across 3 cells
        ]))
        elements.append(t_salary)
        elements.append(Spacer(1, 0.8*inch))

        # --- 5. Footer Section ---
        footer_data = [
            ["__________________________", "__________________________"],
            ["Employer Signature", "Employee Signature"],
        ]
        t_footer = Table(footer_data, colWidths=[3.5*inch, 3.5*inch])
        t_footer.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(t_footer)

        elements.append(Spacer(1, 0.5*inch))
        gen_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elements.append(Paragraph(f"Generated by System on {gen_date}", style_center))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        logger.info("PDF SUCCESS: Document built successfully.")
        return buffer

    except Exception as e:
        logger.critical(f"PDF CRASH: Failed to generate PDF. Error: {e}", exc_info=True)
        raise