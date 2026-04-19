"""Service layer for employee attendance operations."""

import calendar
import logging
from datetime import date
from io import BytesIO
from typing import Any, Optional
import traceback

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class AttendanceService(BaseService):
    """Business logic for attendance write/read and monthly calculations."""

    @staticmethod
    def _to_dict(payload: Any) -> dict:
        return payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

    @staticmethod
    def _draw_branding_header(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#1B2631"))
        canvas.rect(0, doc.pagesize[1] - 1.1 * inch, doc.pagesize[0], 1.1 * inch, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 20)
        canvas.drawString(0.5 * inch, doc.pagesize[1] - 0.5 * inch, "MONTREAL INTERNATIONAL")
        canvas.setFont("Helvetica", 9)
        canvas.drawString(0.5 * inch, doc.pagesize[1] - 0.75 * inch, "GENERAL TRADING & CONTRACTING W.L.L")
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawRightString(doc.pagesize[0] - 0.5 * inch, doc.pagesize[1] - 0.6 * inch, "DAILY ATTENDANCE REPORT")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        footer_line = "Montreal International GTC | Mekka Street, Fahaheel, Kuwait | Phone: +965 XXXX XXXX"
        canvas.drawCentredString(doc.pagesize[0] / 2, 0.4 * inch, footer_line)
        canvas.restoreState()

    async def get_attendance_by_date(self, attendance_date: str):
        from backend.models import Attendance

        return await Attendance.find(Attendance.date == attendance_date).to_list()

    async def get_attendance_by_month(self, year: int, month: int):
        from backend.models import Attendance

        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day:02d}"
        return await Attendance.find(Attendance.date >= start_date, Attendance.date <= end_date).to_list()

    async def sync_attendance_batch(self, payload: Any) -> dict:
        from backend.models import Attendance

        data = self._to_dict(payload)
        records = data.get("records", [])
        for record in records:
            if hasattr(record, "model_dump"):
                record = record.model_dump(exclude_unset=True)
            existing = await Attendance.find_one(
                Attendance.employee_uid == record.get("employee_id"),
                Attendance.date == record.get("date"),
            )
            if existing:
                existing.status = record.get("status")
                existing.shift = record.get("shift")
                existing.overtime_hours = record.get("overtime_hours") or 0
                await existing.save()
            else:
                new_uid = await self.get_next_uid("attendance")
                await Attendance(
                    uid=new_uid,
                    employee_uid=record.get("employee_id"),
                    date=record.get("date"),
                    status=record.get("status"),
                    shift=record.get("shift"),
                    overtime_hours=record.get("overtime_hours") or 0,
                ).insert()
        return {"message": "Attendance records synced"}

    async def generate_attendance_pdf(self, attendance_date: str) -> bytes:
        from backend.models import Attendance, Employee

        try:
            records = await Attendance.find(Attendance.date == attendance_date).to_list()
            employees = await Employee.find_all().to_list()
            emp_map = {e.uid: e.name for e in employees}

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.4 * inch, bottomMargin=0.8 * inch)
            styles = getSampleStyleSheet()
            elements = []
            date_style = ParagraphStyle("DateStyle", parent=styles["Normal"], fontSize=11, textColor=colors.black, spaceAfter=20)
            elements.append(Paragraph(f"<b>DATE:</b> {attendance_date}", date_style))

            table_data = [["ID", "EMPLOYEE NAME", "STATUS", "SHIFT", "OVERTIME"]]
            for r in sorted(records, key=lambda x: x.employee_uid):
                table_data.append(
                    [
                        f"{r.employee_uid:02d}",
                        emp_map.get(r.employee_uid, "Unknown Employee").upper(),
                        r.status.upper(),
                        (r.shift or "N/A").upper(),
                        f"{r.overtime_hours} HRS",
                    ]
                )

            attendance_table = Table(table_data, colWidths=[0.6 * inch, 2.7 * inch, 1.2 * inch, 1.1 * inch, 1.1 * inch])
            attendance_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                        ("TOPPADDING", (0, 0), (-1, 0), 10),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
                        ("ALIGN", (1, 1), (1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            elements.append(attendance_table)
            doc.build(elements, onFirstPage=self._draw_branding_header, onLaterPages=self._draw_branding_header)
            pdf_out = buffer.getvalue()
            buffer.close()
            return pdf_out
        except Exception:
            traceback.print_exc()
            raise

    async def mark_attendance(self, payload: Any):
        """
        Upsert attendance record(s).

        Validations:
        - Dates cannot be in the future
        - employee_uid is required for each row

        Args:
            payload: Either a single attendance payload or batch payload with `records`

        Returns:
            Operation summary containing created/updated counts
        """
        from backend.models import Attendance

        data = self._to_dict(payload)
        records = data.get("records")
        if records is None:
            records = [data]

        created = 0
        updated = 0
        output = []

        for record in records:
            employee_uid = record.get("employee_uid", record.get("employee_id"))
            if employee_uid is None:
                self.raise_bad_request("employee_uid is required")

            work_date = record.get("date")
            if not work_date:
                self.raise_bad_request("date is required")

            try:
                parsed_work_date = date.fromisoformat(work_date)
            except ValueError:
                self.raise_bad_request("Invalid date format. Please use YYYY-MM-DD.")

            if parsed_work_date > date.today():
                self.raise_bad_request("Cannot mark attendance for future dates")

            site_uid = record.get("site_uid")
            existing_filters = [
                Attendance.employee_uid == employee_uid,
                Attendance.date == work_date,
            ]
            if site_uid is not None:
                existing_filters.append(Attendance.site_uid == site_uid)
            existing = await Attendance.find_one(*existing_filters)
            if existing:
                existing.status = record.get("status", existing.status)
                existing.shift = record.get("shift", existing.shift)
                existing.overtime_hours = record.get("overtime_hours", existing.overtime_hours or 0)
                existing.recorded_by_manager_id = record.get("recorded_by_manager_id", existing.recorded_by_manager_id)
                existing.recorded_by_manager_name = record.get("recorded_by_manager_name", existing.recorded_by_manager_name)
                existing.is_substitute = record.get("is_substitute", existing.is_substitute)
                existing.leave_type = record.get("leave_type", existing.leave_type)
                existing.leave_reason = record.get("leave_reason", existing.leave_reason)
                existing.notes = record.get("notes", existing.notes)
                await existing.save()
                updated += 1
                output.append(existing.model_dump(mode="json"))
            else:
                new_record = Attendance(
                    uid=await self.get_next_uid("attendance"),
                    employee_uid=employee_uid,
                    site_uid=site_uid,
                    date=work_date,
                    status=record.get("status", "Present"),
                    shift=record.get("shift", "Morning"),
                    overtime_hours=record.get("overtime_hours", 0),
                    recorded_by_manager_id=record.get("recorded_by_manager_id"),
                    recorded_by_manager_name=record.get("recorded_by_manager_name"),
                    is_substitute=record.get("is_substitute", False),
                    leave_type=record.get("leave_type"),
                    leave_reason=record.get("leave_reason"),
                    notes=record.get("notes"),
                )
                await new_record.insert()
                created += 1
                output.append(new_record.model_dump(mode="json"))

        logger.info("Attendance marked: created=%s updated=%s", created, updated)
        return {"created": created, "updated": updated, "records": output}

    async def calculate_monthly_attendance(self, year: int, month: int, employee_id: Optional[int] = None) -> dict:
        """
        Calculate monthly attendance summary.

        Args:
            year: Year
            month: Month (1-12)
            employee_id: Optional employee filter

        Returns:
            Monthly summary with status counters
        """
        from backend.models import Attendance

        if not (1 <= month <= 12):
            self.raise_bad_request("Month must be between 1 and 12")

        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day:02d}"

        filters = [Attendance.date >= start_date, Attendance.date <= end_date]
        if employee_id is not None:
            filters.append(Attendance.employee_uid == employee_id)

        records = await Attendance.find(*filters).to_list()

        by_status: dict[str, int] = {}
        overtime_total = 0
        for record in records:
            by_status[record.status] = by_status.get(record.status, 0) + 1
            overtime_total += int(record.overtime_hours or 0)

        return {
            "year": year,
            "month": month,
            "employee_id": employee_id,
            "total_records": len(records),
            "by_status": by_status,
            "total_overtime_hours": overtime_total,
        }

    async def get_absent_employees(self, attendance_date: str, site_id: Optional[int] = None) -> list[dict]:
        """
        Get employees marked absent for a date.

        Args:
            attendance_date: Date in YYYY-MM-DD
            site_id: Optional site filter

        Returns:
            List of absent employee summaries
        """
        from backend.models import Attendance, Employee

        filters = [Attendance.date == attendance_date, Attendance.status == "Absent"]
        if site_id is not None:
            filters.append(Attendance.site_uid == site_id)

        records = await Attendance.find(*filters).to_list()
        results: list[dict] = []
        for record in records:
            employee = await Employee.find_one(Employee.uid == record.employee_uid)
            results.append(
                {
                    "employee_id": record.employee_uid,
                    "employee_name": employee.name if employee else None,
                    "date": record.date,
                    "site_id": record.site_uid,
                    "shift": record.shift,
                    "leave_type": record.leave_type,
                    "leave_reason": record.leave_reason,
                }
            )
        return results

    async def get_attendance_by_id(self, attendance_id: int):
        from backend.models import Attendance

        record = await Attendance.find_one(Attendance.uid == attendance_id)
        if not record:
            self.raise_not_found(f"Attendance {attendance_id} not found")
        return record

    async def get_attendance_for_employee(self, employee_id: int):
        from backend.models import Attendance

        return await Attendance.find(Attendance.employee_uid == employee_id).sort("-date").to_list()

    async def update_attendance(self, attendance_id: int, payload: Any):
        record = await self.get_attendance_by_id(attendance_id)
        data = self._to_dict(payload)
        for field, value in data.items():
            setattr(record, field, value)
        await record.save()
        return record

    async def delete_attendance(self, attendance_id: int) -> bool:
        record = await self.get_attendance_by_id(attendance_id)
        await record.delete()
        return True
