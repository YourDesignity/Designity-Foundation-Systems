"""Unit tests for the Phase 5C modular contract workflow system.

These tests exercise the ModuleRegistry and each ContractModule implementation
**without** requiring a live MongoDB connection.  All database calls are mocked.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.modules.registry import ModuleRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_contract(uid: int = 1, contract_code: str = "TEST-001"):
    """Return a lightweight mock that behaves like a Contract document."""
    c = MagicMock()
    c.uid = uid
    c.contract_code = contract_code
    return c


# ---------------------------------------------------------------------------
# ModuleRegistry tests
# ---------------------------------------------------------------------------


class TestModuleRegistry:
    def test_list_modules_contains_core_three(self):
        """Registry must expose the three core modules."""
        modules = ModuleRegistry.list_modules()
        assert "employee" in modules
        assert "inventory" in modules
        assert "vehicle" in modules
        assert len(modules) >= 3

    def test_get_module_returns_instance(self):
        """get_module returns a ContractModule instance for each known name."""
        from backend.modules.base_module import ContractModule

        for name in ("employee", "inventory", "vehicle"):
            module = ModuleRegistry.get_module(name)
            assert module is not None
            assert isinstance(module, ContractModule)

    def test_get_module_unknown_returns_none(self):
        assert ModuleRegistry.get_module("nonexistent") is None

    def test_get_module_info_structure(self):
        info = ModuleRegistry.get_module_info("employee")
        assert info is not None
        assert info["name"] == "employee"
        assert "required_models" in info
        assert isinstance(info["required_models"], list)
        assert "description" in info

    def test_get_module_info_unknown_returns_none(self):
        assert ModuleRegistry.get_module_info("nonexistent") is None

    def test_list_all_modules_info(self):
        all_info = ModuleRegistry.list_all_modules_info()
        assert len(all_info) >= 3
        names = [i["name"] for i in all_info]
        assert "employee" in names

    def test_register_and_unregister_dynamic_module(self):
        """Modules can be registered and unregistered at runtime."""
        from backend.modules.base_module import ContractModule

        class DummyModule(ContractModule):
            module_name = "dummy_test"
            required_models = []

            async def initialize(self, contract):
                return {}

            async def calculate_cost(self, contract, month, year):
                return {"module": self.module_name, "total_cost": 0.0}

            async def validate(self, contract, date):
                return {"module": self.module_name, "is_valid": True, "issues": [], "warnings": []}

        ModuleRegistry.register_module(DummyModule())
        assert "dummy_test" in ModuleRegistry.list_modules()

        ModuleRegistry.unregister_module("dummy_test")
        assert "dummy_test" not in ModuleRegistry.list_modules()


# ---------------------------------------------------------------------------
# EmployeeModule tests
# ---------------------------------------------------------------------------


class TestEmployeeModule:
    @pytest.mark.asyncio
    async def test_calculate_cost_returns_correct_structure_no_employees(self):
        """With no assignments the module returns zero cost and correct keys."""
        module = ModuleRegistry.get_module("employee")
        contract = _make_contract()

        with patch(
            "backend.models.assignments.EmployeeAssignment"
        ) as mock_ea:
            mock_ea.find.return_value.to_list = AsyncMock(return_value=[])
            result = await module.calculate_cost(contract, month=4, year=2026)

        assert result["module"] == "employee"
        assert result["total_cost"] == 0.0
        assert isinstance(result["total_cost"], float)
        assert result["employee_count"] == 0

    @pytest.mark.asyncio
    async def test_calculate_cost_sums_salary_and_allowance(self):
        """Cost = basic_salary + allowance per assigned employee."""
        module = ModuleRegistry.get_module("employee")
        contract = _make_contract()

        mock_assignment = MagicMock()
        mock_assignment.employee_id = 10

        mock_employee = MagicMock()
        mock_employee.uid = 10
        mock_employee.name = "Ali"
        mock_employee.designation = "Driver"
        mock_employee.basic_salary = 800.0
        mock_employee.allowance = 200.0

        with patch(
            "backend.models.assignments.EmployeeAssignment"
        ) as mock_ea, patch(
            "backend.models.hr.Employee"
        ) as mock_emp_cls:
            mock_ea.find.return_value.to_list = AsyncMock(
                return_value=[mock_assignment]
            )
            mock_emp_cls.find.return_value.to_list = AsyncMock(
                return_value=[mock_employee]
            )
            mock_emp_cls.uid = MagicMock()

            result = await module.calculate_cost(contract, month=4, year=2026)

        assert result["module"] == "employee"
        assert result["total_cost"] == pytest.approx(1000.0)
        assert result["employee_count"] == 1

    @pytest.mark.asyncio
    async def test_validate_returns_valid_with_no_employees(self):
        """Validation passes when no employees are assigned."""
        module = ModuleRegistry.get_module("employee")
        contract = _make_contract()

        with patch(
            "backend.models.assignments.EmployeeAssignment"
        ) as mock_ea:
            mock_ea.find.return_value.to_list = AsyncMock(return_value=[])
            result = await module.validate(contract, date.today())

        assert result["module"] == "employee"
        assert result["is_valid"] is True
        assert isinstance(result["issues"], list)
        assert isinstance(result["warnings"], list)


# ---------------------------------------------------------------------------
# InventoryModule tests
# ---------------------------------------------------------------------------


class TestInventoryModule:
    @pytest.mark.asyncio
    async def test_calculate_cost_returns_correct_structure_no_movements(self):
        """With no movements the module returns zero cost and correct keys."""
        module = ModuleRegistry.get_module("inventory")
        contract = _make_contract()

        with patch(
            "backend.models.materials.MaterialMovement"
        ) as mock_mm:
            mock_mm.find.return_value.to_list = AsyncMock(return_value=[])
            result = await module.calculate_cost(contract, month=4, year=2026)

        assert result["module"] == "inventory"
        assert result["total_cost"] == 0.0
        assert isinstance(result["total_cost"], float)
        assert result["movement_count"] == 0

    @pytest.mark.asyncio
    async def test_validate_returns_correct_structure(self):
        module = ModuleRegistry.get_module("inventory")
        contract = _make_contract()

        with patch(
            "backend.models.materials.MaterialMovement"
        ) as mock_mm:
            mock_mm.find.return_value.to_list = AsyncMock(return_value=[])
            result = await module.validate(contract, date.today())

        assert result["module"] == "inventory"
        assert result["is_valid"] is True
        assert "date" in result
        assert isinstance(result["issues"], list)
        assert isinstance(result["warnings"], list)


# ---------------------------------------------------------------------------
# VehicleModule tests
# ---------------------------------------------------------------------------


class TestVehicleModule:
    @pytest.mark.asyncio
    async def test_calculate_cost_returns_correct_structure_no_data(self):
        """With no vehicle data the module returns zero cost and correct keys."""
        module = ModuleRegistry.get_module("vehicle")
        contract = _make_contract()

        with patch(
            "backend.models.vehicles.VehicleExpense"
        ) as mock_ve, patch(
            "backend.models.vehicles.TripLog"
        ) as mock_tl:
            mock_ve.find.return_value.to_list = AsyncMock(return_value=[])
            mock_tl.find.return_value.to_list = AsyncMock(return_value=[])
            result = await module.calculate_cost(contract, month=4, year=2026)

        assert result["module"] == "vehicle"
        assert result["total_cost"] == 0.0
        assert isinstance(result["total_cost"], float)
        assert result["total_trips"] == 0
        assert result["total_kilometers"] == 0.0
        assert result["cost_per_km"] == 0.0

    @pytest.mark.asyncio
    async def test_validate_returns_correct_structure(self):
        module = ModuleRegistry.get_module("vehicle")
        contract = _make_contract()

        with patch("backend.models.vehicles.TripLog") as mock_tl:
            mock_tl.find.return_value.to_list = AsyncMock(return_value=[])
            result = await module.validate(contract, date.today())

        assert result["module"] == "vehicle"
        assert result["is_valid"] is True
        assert "date" in result
        assert isinstance(result["issues"], list)
        assert isinstance(result["warnings"], list)


# ---------------------------------------------------------------------------
# Contract model module fields test
# ---------------------------------------------------------------------------


class TestContractModuleFields:
    def test_contract_has_enabled_modules_field(self):
        """Contract model must expose enabled_modules and module_config fields."""
        from backend.models.projects import Contract

        fields = Contract.model_fields
        assert "enabled_modules" in fields
        assert "module_config" in fields

    def test_enabled_modules_defaults_to_empty_list(self):
        """enabled_modules defaults to []."""
        from backend.models.projects import Contract

        field = Contract.model_fields["enabled_modules"]
        # Pydantic v2: default_factory or default
        default = (
            field.default_factory()
            if field.default_factory is not None
            else field.default
        )
        assert default == []

    def test_module_config_defaults_to_empty_dict(self):
        """module_config defaults to {}."""
        from backend.models.projects import Contract

        field = Contract.model_fields["module_config"]
        default = (
            field.default_factory()
            if field.default_factory is not None
            else field.default
        )
        assert default == {}
