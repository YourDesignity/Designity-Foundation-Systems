import logging
from datetime import datetime
from typing import Dict, List, Optional

from backend.database import get_next_uid
from backend.models import DailyRoleFulfillment, RoleFulfillmentRecord
from backend.schemas import (
    DailyFulfillmentCreate,
    MonthlyRoleCostReport,
    RoleAssignmentRequest,
    SlotSwapRequest,
)
from backend.services.base_service import BaseService
from backend.services.contract_service import ContractService
from backend.services.employee_service import EmployeeService
from backend.utils.logger import setup_logger

logger = setup_logger("RoleContractsService", log_file="logs/role_contracts_service.log", level=logging.DEBUG)


class RoleContractsService(BaseService):
    """Business logic for role-based labour contracts and daily fulfillment."""

    def __init__(self, contract_service: Optional[ContractService] = None, employee_service: Optional[EmployeeService] = None):
        self.contract_service = contract_service or ContractService()
        self.employee_service = employee_service or EmployeeService()

    @staticmethod
    def _build_summary(fulfillment: DailyRoleFulfillment) -> None:
        fulfillment.total_roles_required = len(fulfillment.role_fulfillments)
        fulfillment.total_roles_filled = sum(1 for r in fulfillment.role_fulfillments if r.is_filled)
        fulfillment.total_daily_cost = sum(r.cost_applied for r in fulfillment.role_fulfillments)
        fulfillment.unfilled_slots = [r.slot_id for r in fulfillment.role_fulfillments if not r.is_filled]
        contract_slot_rate = {r.slot_id: r.daily_rate for r in fulfillment.role_fulfillments}
        fulfillment.shortage_cost_impact = sum(contract_slot_rate.get(s, 0.0) for s in fulfillment.unfilled_slots)

    async def _validate_no_double_booking(
        self,
        employee_id: int,
        work_date: datetime,
        exclude_fulfillment_id: Optional[int] = None,
    ) -> None:
        records = await DailyRoleFulfillment.find(DailyRoleFulfillment.date == work_date).to_list()
        for rec in records:
            if exclude_fulfillment_id and rec.uid == exclude_fulfillment_id:
                continue
            for rf in rec.role_fulfillments:
                if rf.employee_id == employee_id and rf.is_filled:
                    self.raise_conflict(
                        f"Employee {employee_id} is already assigned to slot '{rf.slot_id}' on this day"
                    )

    async def record_daily_fulfillment(self, payload: DailyFulfillmentCreate, current_user: dict) -> dict:
        work_date = self.coerce_datetime(payload.date)
        self.ensure_not_future(work_date, "Cannot record fulfillment for a future date")

        role = current_user.get("role")
        if role == "Site Manager":
            assigned_sites: List[int] = current_user.get("sites") or []
            if payload.site_id not in assigned_sites:
                self.raise_forbidden("You are not assigned to this site")

        contract = await self.contract_service.ensure_contract(payload.contract_id)

        existing = await DailyRoleFulfillment.find_one(
            DailyRoleFulfillment.contract_id == payload.contract_id,
            DailyRoleFulfillment.date == work_date,
        )
        if existing:
            self.raise_conflict(
                f"Fulfillment record already exists for contract {payload.contract_id} on this date "
                f"(uid={existing.uid}). Use PUT /{existing.uid}/assign or PUT /{existing.uid}/swap to update individual slots."
            )

        slot_designation = {s.slot_id: s.designation for s in contract.role_slots}
        filled_employees: Dict[int, str] = {}

        records: List[RoleFulfillmentRecord] = []
        for rf_data in payload.role_fulfillments:
            expected_designation = slot_designation.get(rf_data.slot_id)
            if expected_designation and rf_data.designation != expected_designation:
                self.raise_bad_request(
                    f"Slot '{rf_data.slot_id}' requires designation '{expected_designation}', got '{rf_data.designation}'"
                )

            if rf_data.is_filled and rf_data.employee_id is not None:
                if rf_data.employee_id in filled_employees:
                    self.raise_conflict(
                        f"Employee {rf_data.employee_id} cannot be assigned to both "
                        f"slot '{filled_employees[rf_data.employee_id]}' and '{rf_data.slot_id}' on the same day"
                    )
                filled_employees[rf_data.employee_id] = rf_data.slot_id

            cost_applied = rf_data.daily_rate if rf_data.is_filled else 0.0
            records.append(
                RoleFulfillmentRecord(
                    slot_id=rf_data.slot_id,
                    designation=rf_data.designation,
                    daily_rate=rf_data.daily_rate,
                    employee_id=rf_data.employee_id,
                    employee_name=rf_data.employee_name,
                    is_filled=rf_data.is_filled,
                    attendance_status=rf_data.attendance_status,
                    replacement_employee_id=rf_data.replacement_employee_id,
                    replacement_employee_name=rf_data.replacement_employee_name,
                    replacement_reason=rf_data.replacement_reason,
                    cost_applied=cost_applied,
                    payment_status=rf_data.payment_status,
                    notes=rf_data.notes,
                )
            )

        for emp_id in filled_employees:
            await self._validate_no_double_booking(emp_id, work_date)

        new_uid = await get_next_uid("daily_role_fulfillments")
        fulfillment = DailyRoleFulfillment(
            uid=new_uid,
            contract_id=payload.contract_id,
            site_id=payload.site_id,
            date=work_date,
            role_fulfillments=records,
            recorded_by_manager_id=payload.recorded_by_manager_id,
        )
        self._build_summary(fulfillment)
        await fulfillment.insert()

        logger.info("Daily fulfillment recorded: contract=%s date=%s uid=%s", payload.contract_id, work_date.date(), new_uid)
        return fulfillment.model_dump(mode="json")

    async def get_unfilled_slots(self) -> list[dict]:
        records = await DailyRoleFulfillment.find(
            DailyRoleFulfillment.total_roles_filled < DailyRoleFulfillment.total_roles_required
        ).sort("-date").to_list()
        return [r.model_dump(mode="json") for r in records]

    async def get_daily_fulfillment(self, contract_id: int, date_str: str) -> dict:
        work_date = self.parse_date_param(date_str)
        record = await DailyRoleFulfillment.find_one(
            DailyRoleFulfillment.contract_id == contract_id,
            DailyRoleFulfillment.date == work_date,
        )
        if not record:
            self.raise_not_found(f"No fulfillment record found for contract {contract_id} on {date_str}")
        return record.model_dump(mode="json")

    async def assign_employee_to_slot(self, fulfillment_id: int, payload: RoleAssignmentRequest) -> dict:
        fulfillment = await DailyRoleFulfillment.find_one(DailyRoleFulfillment.uid == fulfillment_id)
        if not fulfillment:
            self.raise_not_found("Fulfillment record not found")

        slot_record = next((r for r in fulfillment.role_fulfillments if r.slot_id == payload.slot_id), None)
        if not slot_record:
            self.raise_not_found(f"Slot '{payload.slot_id}' not found in this record")

        await self._validate_no_double_booking(payload.employee_id, fulfillment.date, exclude_fulfillment_id=fulfillment_id)

        contract = await self.contract_service.get_contract(fulfillment.contract_id)
        if contract:
            slot_designation = self.contract_service.get_slot_designation(contract, payload.slot_id)
            if slot_designation:
                await self.employee_service.validate_designation(payload.employee_id, slot_designation, "Employee")

        slot_record.employee_id = payload.employee_id
        slot_record.employee_name = payload.employee_name
        slot_record.is_filled = True
        slot_record.attendance_status = payload.attendance_status
        slot_record.cost_applied = slot_record.daily_rate
        if payload.notes:
            slot_record.notes = payload.notes

        self._build_summary(fulfillment)
        fulfillment.updated_at = datetime.now()
        await fulfillment.save()
        logger.info("Assigned employee to slot '%s' in fulfillment %d", payload.slot_id, fulfillment_id)
        return fulfillment.model_dump(mode="json")

    async def swap_employee_in_slot(self, fulfillment_id: int, payload: SlotSwapRequest) -> dict:
        fulfillment = await DailyRoleFulfillment.find_one(DailyRoleFulfillment.uid == fulfillment_id)
        if not fulfillment:
            self.raise_not_found("Fulfillment record not found")

        slot_record = next((r for r in fulfillment.role_fulfillments if r.slot_id == payload.slot_id), None)
        if not slot_record:
            self.raise_not_found(f"Slot '{payload.slot_id}' not found in this record")

        contract = await self.contract_service.get_contract(fulfillment.contract_id)
        if contract:
            slot_designation = self.contract_service.get_slot_designation(contract, payload.slot_id)
            if slot_designation:
                await self.employee_service.validate_designation(
                    payload.new_employee_id,
                    slot_designation,
                    "New employee",
                )

        await self._validate_no_double_booking(
            payload.new_employee_id,
            fulfillment.date,
            exclude_fulfillment_id=fulfillment_id,
        )

        slot_record.replacement_employee_id = slot_record.employee_id
        slot_record.replacement_employee_name = slot_record.employee_name
        slot_record.replacement_reason = payload.reason

        slot_record.employee_id = payload.new_employee_id
        slot_record.employee_name = payload.new_employee_name
        slot_record.is_filled = True
        slot_record.attendance_status = "Present"
        slot_record.cost_applied = slot_record.daily_rate

        self._build_summary(fulfillment)
        fulfillment.updated_at = datetime.now()
        await fulfillment.save()
        logger.info("Swapped employee in slot '%s' for fulfillment %d", payload.slot_id, fulfillment_id)
        return fulfillment.model_dump(mode="json")

    async def get_monthly_cost_report(self, contract_id: int, month: int, year: int) -> MonthlyRoleCostReport:
        if not (1 <= month <= 12):
            self.raise_bad_request("Month must be between 1 and 12")

        current_year = datetime.now().year
        if year < current_year - 10 or year > current_year + 10:
            self.raise_bad_request("Year is outside the valid range (±10 years from current year)")

        start_dt = datetime(year, month, 1)
        end_dt = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

        records = await DailyRoleFulfillment.find(
            DailyRoleFulfillment.contract_id == contract_id,
            DailyRoleFulfillment.date >= start_dt,
            DailyRoleFulfillment.date < end_dt,
        ).sort("+date").to_list()

        if not records:
            return MonthlyRoleCostReport(
                contract_id=contract_id,
                month=month,
                year=year,
                total_days_recorded=0,
                total_roles_required=0,
                total_roles_filled=0,
                total_cost=0.0,
                shortage_cost_impact=0.0,
                fulfillment_rate=0.0,
                cost_by_designation={},
                daily_breakdown=[],
            )

        total_required = sum(r.total_roles_required for r in records)
        total_filled = sum(r.total_roles_filled for r in records)
        total_cost = sum(r.total_daily_cost for r in records)
        total_shortage = sum(r.shortage_cost_impact for r in records)
        fulfillment_rate = (total_filled / total_required) if total_required > 0 else 0.0

        cost_by_designation: Dict[str, float] = {}
        for rec in records:
            for rf in rec.role_fulfillments:
                if rf.is_filled:
                    cost_by_designation[rf.designation] = cost_by_designation.get(rf.designation, 0.0) + rf.cost_applied

        daily_breakdown = [
            {
                "date": r.date.date().isoformat(),
                "total_required": r.total_roles_required,
                "total_filled": r.total_roles_filled,
                "total_cost": r.total_daily_cost,
                "shortage_cost_impact": r.shortage_cost_impact,
                "unfilled_slots": r.unfilled_slots,
            }
            for r in records
        ]

        return MonthlyRoleCostReport(
            contract_id=contract_id,
            month=month,
            year=year,
            total_days_recorded=len(records),
            total_roles_required=total_required,
            total_roles_filled=total_filled,
            total_cost=total_cost,
            shortage_cost_impact=total_shortage,
            fulfillment_rate=round(fulfillment_rate, 4),
            cost_by_designation=cost_by_designation,
            daily_breakdown=daily_breakdown,
        )
