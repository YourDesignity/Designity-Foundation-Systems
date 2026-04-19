"""Unit tests for the configurable salary calculation engine (Phase 5B).

These tests exercise the pure-Python helper methods of
``ConfigurableSalaryCalculator`` and the ``SalaryConfig`` Pydantic schema
**without** requiring a live MongoDB connection.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.models.salary_config import (
    BonusRule,
    DeductionRule,
    OvertimeRule,
    PeriodModifier,
    SalaryConfig,
)
from backend.services.salary.configurable_calculator import ConfigurableSalaryCalculator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def calc() -> ConfigurableSalaryCalculator:
    return ConfigurableSalaryCalculator()


@pytest.fixture()
def ramadan_config() -> SalaryConfig:
    """Ramadan 2026 bonus configuration (20 % of base + allowances)."""
    return SalaryConfig(
        attendance_required=True,
        pro_rate_on_absence=True,
        overtime=OvertimeRule(enabled=True, multiplier=1.5),
        period_modifiers=[
            PeriodModifier(
                name="ramadan_bonus_2026",
                start_date=date(2026, 3, 1),
                end_date=date(2026, 3, 30),
                modifier_type="percentage",
                value=20.0,
                applies_to=["base_salary", "allowances"],
            )
        ],
        deductions=[
            DeductionRule(
                name="absence_deduction",
                deduction_type="per_occurrence",
                value=50.0,
                condition="absence",
                max_deduction_per_month=500.0,
            )
        ],
        bonuses=[
            BonusRule(
                name="perfect_attendance",
                bonus_type="fixed_amount",
                value=200.0,
                condition="perfect_attendance",
            )
        ],
        allowances={"transport": 100.0, "food": 50.0, "housing": 300.0},
    )


# ---------------------------------------------------------------------------
# SalaryConfig schema tests
# ---------------------------------------------------------------------------


class TestSalaryConfigSchema:
    def test_default_config(self):
        cfg = SalaryConfig()
        assert cfg.attendance_required is True
        assert cfg.pro_rate_on_absence is True
        assert cfg.overtime.enabled is True
        assert cfg.overtime.multiplier == 1.5
        assert cfg.period_modifiers == []
        assert cfg.deductions == []
        assert cfg.bonuses == []
        assert cfg.allowances == {}

    def test_period_modifier_applies_to_default(self):
        pm = PeriodModifier(
            name="test",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            modifier_type="percentage",
            value=10.0,
        )
        assert "base_salary" in pm.applies_to
        assert "allowances" in pm.applies_to

    def test_ramadan_config_parses_correctly(self, ramadan_config):
        assert len(ramadan_config.period_modifiers) == 1
        assert ramadan_config.period_modifiers[0].name == "ramadan_bonus_2026"
        assert ramadan_config.period_modifiers[0].value == 20.0
        assert len(ramadan_config.bonuses) == 1
        assert len(ramadan_config.deductions) == 1
        assert ramadan_config.allowances["transport"] == 100.0


# ---------------------------------------------------------------------------
# _is_in_period tests
# ---------------------------------------------------------------------------


class TestIsInPeriod:
    def _modifier(self, start: date, end: date) -> PeriodModifier:
        return PeriodModifier(
            name="test",
            start_date=start,
            end_date=end,
            modifier_type="percentage",
            value=10.0,
        )

    def test_month_overlaps_start_of_period(self, calc):
        """March 2026 overlaps with a period starting mid-March."""
        mod = self._modifier(date(2026, 3, 15), date(2026, 4, 15))
        assert calc._is_in_period(3, 2026, mod) is True

    def test_month_completely_inside_period(self, calc):
        mod = self._modifier(date(2026, 2, 1), date(2026, 4, 30))
        assert calc._is_in_period(3, 2026, mod) is True

    def test_month_before_period(self, calc):
        mod = self._modifier(date(2026, 4, 1), date(2026, 4, 30))
        assert calc._is_in_period(3, 2026, mod) is False

    def test_month_after_period(self, calc):
        mod = self._modifier(date(2026, 1, 1), date(2026, 2, 28))
        assert calc._is_in_period(3, 2026, mod) is False

    def test_ramadan_march_2026_is_in_period(self, calc, ramadan_config):
        modifier = ramadan_config.period_modifiers[0]
        assert calc._is_in_period(3, 2026, modifier) is True

    def test_ramadan_april_2026_not_in_period(self, calc, ramadan_config):
        modifier = ramadan_config.period_modifiers[0]
        assert calc._is_in_period(4, 2026, modifier) is False

    def test_ramadan_february_2026_not_in_period(self, calc, ramadan_config):
        modifier = ramadan_config.period_modifiers[0]
        assert calc._is_in_period(2, 2026, modifier) is False


# ---------------------------------------------------------------------------
# _apply_period_modifier tests
# ---------------------------------------------------------------------------


class TestApplyPeriodModifier:
    def _modifier(self, mtype: str, value: float, applies_to=None) -> PeriodModifier:
        return PeriodModifier(
            name="test",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 30),
            modifier_type=mtype,
            value=value,
            applies_to=applies_to or ["base_salary", "allowances"],
        )

    def test_percentage_base_and_allowances(self, calc):
        mod = self._modifier("percentage", 20.0)
        result = calc._apply_period_modifier(mod, base_amount=1000.0, total_allowances=450.0)
        assert result == pytest.approx(290.0)  # 20 % of 1450

    def test_percentage_base_only(self, calc):
        mod = self._modifier("percentage", 20.0, applies_to=["base_salary"])
        result = calc._apply_period_modifier(mod, base_amount=1000.0, total_allowances=450.0)
        assert result == pytest.approx(200.0)

    def test_percentage_allowances_only(self, calc):
        mod = self._modifier("percentage", 10.0, applies_to=["allowances"])
        result = calc._apply_period_modifier(mod, base_amount=1000.0, total_allowances=500.0)
        assert result == pytest.approx(50.0)

    def test_fixed_amount(self, calc):
        mod = self._modifier("fixed_amount", 500.0)
        result = calc._apply_period_modifier(mod, base_amount=1000.0, total_allowances=0.0)
        assert result == 500.0

    def test_unknown_modifier_type_returns_zero(self, calc):
        mod = self._modifier("unknown_type", 100.0)
        result = calc._apply_period_modifier(mod, base_amount=1000.0, total_allowances=0.0)
        assert result == 0.0

    def test_ramadan_20_percent_on_1000_salary_450_allowances(self, calc, ramadan_config):
        modifier = ramadan_config.period_modifiers[0]
        result = calc._apply_period_modifier(modifier, 1000.0, 450.0)
        assert result == pytest.approx(290.0)


# ---------------------------------------------------------------------------
# _calculate_bonus tests
# ---------------------------------------------------------------------------


class TestCalculateBonus:
    @pytest.mark.asyncio
    async def test_perfect_attendance_bonus_no_absences(self, calc):
        rule = BonusRule(
            name="perfect_attendance",
            bonus_type="fixed_amount",
            value=200.0,
            condition="perfect_attendance",
        )
        breakdown = {"attendance": {"absent_days": 0, "total_days": 26}}
        result = await calc._calculate_bonus(rule, 1, 3, 2026, breakdown)
        assert result == 200.0

    @pytest.mark.asyncio
    async def test_no_bonus_when_absences_present(self, calc):
        rule = BonusRule(
            name="perfect_attendance",
            bonus_type="fixed_amount",
            value=200.0,
            condition="perfect_attendance",
        )
        breakdown = {"attendance": {"absent_days": 2, "total_days": 26}}
        result = await calc._calculate_bonus(rule, 1, 3, 2026, breakdown)
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_no_bonus_when_no_attendance_data(self, calc):
        rule = BonusRule(
            name="perfect_attendance",
            bonus_type="fixed_amount",
            value=200.0,
            condition="perfect_attendance",
        )
        breakdown = {}
        result = await calc._calculate_bonus(rule, 1, 3, 2026, breakdown)
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_no_bonus_when_zero_total_days(self, calc):
        """Should not award attendance bonus if no attendance records at all."""
        rule = BonusRule(
            name="perfect_attendance",
            bonus_type="fixed_amount",
            value=200.0,
            condition="perfect_attendance",
        )
        breakdown = {"attendance": {"absent_days": 0, "total_days": 0}}
        result = await calc._calculate_bonus(rule, 1, 3, 2026, breakdown)
        assert result == 0.0


# ---------------------------------------------------------------------------
# _calculate_deduction tests
# ---------------------------------------------------------------------------


class TestCalculateDeduction:
    @pytest.mark.asyncio
    async def test_per_occurrence_absence(self, calc):
        rule = DeductionRule(
            name="absence",
            deduction_type="per_occurrence",
            value=50.0,
            condition="absence",
            max_deduction_per_month=500.0,
        )
        breakdown = {"attendance": {"absent_days": 3}}
        result = await calc._calculate_deduction(rule, 1, 3, 2026, breakdown)
        assert result == pytest.approx(150.0)

    @pytest.mark.asyncio
    async def test_per_occurrence_capped_at_max(self, calc):
        rule = DeductionRule(
            name="absence",
            deduction_type="per_occurrence",
            value=50.0,
            condition="absence",
            max_deduction_per_month=100.0,
        )
        breakdown = {"attendance": {"absent_days": 10}}
        result = await calc._calculate_deduction(rule, 1, 3, 2026, breakdown)
        assert result == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_no_deduction_when_no_absences(self, calc):
        rule = DeductionRule(
            name="absence",
            deduction_type="per_occurrence",
            value=50.0,
            condition="absence",
        )
        breakdown = {"attendance": {"absent_days": 0}}
        result = await calc._calculate_deduction(rule, 1, 3, 2026, breakdown)
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_unknown_condition_returns_zero(self, calc):
        rule = DeductionRule(
            name="mystery",
            deduction_type="per_occurrence",
            value=50.0,
            condition="unknown_condition",
        )
        breakdown = {"attendance": {"absent_days": 5}}
        result = await calc._calculate_deduction(rule, 1, 3, 2026, breakdown)
        assert result == 0.0


# ---------------------------------------------------------------------------
# Full calculate_monthly_salary integration test (mocked DB)
# ---------------------------------------------------------------------------


def _make_mock_employee_class(emp_instance):
    """
    Build a minimal mock class that satisfies Beanie's field-comparison
    protocol without requiring a live MongoDB connection.

    ``Employee.uid == employee_id`` is used as a query filter inside the
    calculator.  To avoid the AttributeError raised when Beanie is not
    initialised, we replace the whole ``Employee`` class with a lightweight
    MagicMock whose ``uid`` attribute is itself a MagicMock (so ``==`` works)
    and whose ``find_one`` is an async mock that returns ``emp_instance``.
    """
    mock_cls = MagicMock()
    mock_cls.uid = MagicMock()  # supports __eq__ via MagicMock
    mock_cls.find_one = AsyncMock(return_value=emp_instance)
    return mock_cls


class TestCalculateMonthlySalaryIntegration:
    """
    Tests for calculate_monthly_salary with all DB calls mocked.
    Validates the end-to-end arithmetic of the configurable engine.
    """

    def _make_employee(self, basic_salary=1000.0, allowance=0.0):
        emp = MagicMock()
        emp.uid = 1
        emp.name = "Test Employee"
        emp.basic_salary = basic_salary
        emp.allowance = allowance
        return emp

    @pytest.mark.asyncio
    async def test_basic_salary_no_config(self, calc):
        emp = self._make_employee(1000.0, 0.0)
        mock_cls = _make_mock_employee_class(emp)

        with patch("backend.models.hr.Employee", mock_cls), \
             patch.object(calc, "_get_attendance_data", new=AsyncMock(
                 return_value={"total_days": 26, "present_days": 26, "absent_days": 0, "rate": 1.0}
             )):
            result = await calc.calculate_monthly_salary(1, 99, 3, 2026)

        assert result["base_salary"] == 1000.0
        assert result["total"] == pytest.approx(1000.0)

    @pytest.mark.asyncio
    async def test_ramadan_bonus_march_2026(self, calc, ramadan_config):
        """
        Scenario:
          - base_salary = 1000, employee allowance = 0
          - config allowances: transport=100, food=50, housing=300 → 450
          - full attendance (rate=1.0) → no pro-rating
          - Ramadan modifier: 20 % of (1000 + 450) = 290
          - Perfect attendance bonus = 200
          - Absent days = 0 → deduction = 0
          - Expected total = 1000 + 450 + 290 + 200 = 1940
        """
        emp = self._make_employee(1000.0, 0.0)
        mock_cls = _make_mock_employee_class(emp)

        attendance_data = {
            "total_days": 26,
            "present_days": 26,
            "absent_days": 0,
            "rate": 1.0,
        }

        with patch("backend.models.hr.Employee", mock_cls), \
             patch.object(calc, "_get_attendance_data", new=AsyncMock(return_value=attendance_data)):
            result = await calc.calculate_monthly_salary(1, 99, 3, 2026, ramadan_config)

        assert result["period_modifiers"]["ramadan_bonus_2026"] == pytest.approx(290.0)
        assert result["bonuses"]["perfect_attendance"] == 200.0
        assert result["deductions"] == {}
        assert result["total"] == pytest.approx(1940.0)

    @pytest.mark.asyncio
    async def test_absence_deduction(self, calc, ramadan_config):
        """
        Scenario (outside Ramadan – April):
          - base_salary = 1000, no employee allowance
          - config allowances: transport=100, food=50, housing=300 → 450
          - 3 absent days, 23 present, rate = 23/26
          - pro-rating: base = 1000 * (23/26), allowances = 450 * (23/26)
          - No period modifier (April outside Ramadan 2026)
          - No perfect attendance bonus (3 absences)
          - Deduction: 3 * 50 = 150
        """
        emp = self._make_employee(1000.0, 0.0)
        mock_cls = _make_mock_employee_class(emp)
        rate = 23 / 26
        attendance_data = {
            "total_days": 26,
            "present_days": 23,
            "absent_days": 3,
            "rate": rate,
        }

        with patch("backend.models.hr.Employee", mock_cls), \
             patch.object(calc, "_get_attendance_data", new=AsyncMock(return_value=attendance_data)):
            result = await calc.calculate_monthly_salary(1, 99, 4, 2026, ramadan_config)

        prorated_base = 1000.0 * rate
        prorated_allowances = 450.0 * rate
        deduction = 150.0  # 3 * 50

        expected_total = prorated_base + prorated_allowances - deduction
        assert result["total"] == pytest.approx(expected_total, rel=1e-6)
        assert result["deductions"]["absence_deduction"] == pytest.approx(150.0)
        assert result["bonuses"] == {}

    @pytest.mark.asyncio
    async def test_allowances_applied_correctly(self, calc):
        """Config allowances + employee default allowance should both appear."""
        emp = self._make_employee(500.0, 100.0)  # employee has 100 allowance
        mock_cls = _make_mock_employee_class(emp)

        config = SalaryConfig(
            attendance_required=False,
            allowances={"transport": 50.0, "food": 30.0},
        )

        with patch("backend.models.hr.Employee", mock_cls):
            result = await calc.calculate_monthly_salary(1, 99, 3, 2026, config)

        assert result["allowances"]["transport"] == 50.0
        assert result["allowances"]["food"] == 30.0
        assert result["allowances"]["default"] == 100.0
        assert result["total"] == pytest.approx(500.0 + 100.0 + 50.0 + 30.0)

    @pytest.mark.asyncio
    async def test_employee_not_found_returns_error(self, calc):
        mock_cls = _make_mock_employee_class(None)
        with patch("backend.models.hr.Employee", mock_cls):
            result = await calc.calculate_monthly_salary(999, 1, 3, 2026)

        assert result["total"] == 0.0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_multiple_period_modifiers_overlap(self, calc):
        """Two overlapping period modifiers should both be applied."""
        emp = self._make_employee(1000.0, 0.0)
        mock_cls = _make_mock_employee_class(emp)

        config = SalaryConfig(
            attendance_required=False,
            period_modifiers=[
                PeriodModifier(
                    name="mod_a",
                    start_date=date(2026, 3, 1),
                    end_date=date(2026, 3, 31),
                    modifier_type="fixed_amount",
                    value=100.0,
                ),
                PeriodModifier(
                    name="mod_b",
                    start_date=date(2026, 2, 15),
                    end_date=date(2026, 3, 15),
                    modifier_type="fixed_amount",
                    value=200.0,
                ),
            ],
        )

        with patch("backend.models.hr.Employee", mock_cls):
            result = await calc.calculate_monthly_salary(1, 99, 3, 2026, config)

        assert result["period_modifiers"]["mod_a"] == 100.0
        assert result["period_modifiers"]["mod_b"] == 200.0
        assert result["total"] == pytest.approx(1000.0 + 100.0 + 200.0)

    @pytest.mark.asyncio
    async def test_max_deduction_limit_applied(self, calc):
        """Deduction should be capped at max_deduction_per_month."""
        emp = self._make_employee(2000.0, 0.0)
        mock_cls = _make_mock_employee_class(emp)

        config = SalaryConfig(
            attendance_required=True,
            pro_rate_on_absence=False,
            deductions=[
                DeductionRule(
                    name="absence_deduction",
                    deduction_type="per_occurrence",
                    value=100.0,
                    condition="absence",
                    max_deduction_per_month=300.0,
                )
            ],
        )

        attendance_data = {
            "total_days": 26,
            "present_days": 16,
            "absent_days": 10,  # 10 × 100 = 1000, capped at 300
            "rate": 16 / 26,
        }

        with patch("backend.models.hr.Employee", mock_cls), \
             patch.object(calc, "_get_attendance_data", new=AsyncMock(return_value=attendance_data)):
            result = await calc.calculate_monthly_salary(1, 99, 4, 2026, config)

        assert result["deductions"]["absence_deduction"] == pytest.approx(300.0)
        assert result["total"] == pytest.approx(2000.0 - 300.0)

    @pytest.mark.asyncio
    async def test_overtime_placeholder_returns_zero(self, calc):
        emp = self._make_employee(1000.0, 0.0)
        mock_cls = _make_mock_employee_class(emp)
        config = SalaryConfig(
            attendance_required=False,
            overtime=OvertimeRule(enabled=True, multiplier=1.5),
        )
        with patch("backend.models.hr.Employee", mock_cls):
            result = await calc.calculate_monthly_salary(1, 99, 3, 2026, config)

        assert result["overtime"] == 0.0
        assert result["breakdown"]["overtime"]["multiplier"] == 1.5
