"""Inventory / material tracking module for contracts."""

from calendar import monthrange
from datetime import datetime
from typing import Any, Dict, List

from backend.modules.base_module import ContractModule


class InventoryModule(ContractModule):
    """
    Module for tracking material/inventory costs for contracts.
    Handles material movements, stock levels, and cost calculations.
    """

    module_name = "inventory"
    required_models = ["Material", "MaterialMovement"]

    async def initialize(self, contract: Any) -> Dict[str, Any]:
        """Initialize inventory module for contract."""
        from backend.models.materials import MaterialMovement

        # MaterialMovement links to a contract via reference_id + reference_type
        movements = await MaterialMovement.find(
            MaterialMovement.reference_id == contract.uid,
            MaterialMovement.reference_type == "contract_usage",
        ).to_list()

        return {
            "module": self.module_name,
            "status": "initialized",
            "total_movements": len(movements),
        }

    async def calculate_cost(
        self,
        contract: Any,
        month: int,
        year: int,
    ) -> Dict[str, Any]:
        """
        Calculate total inventory costs for this contract for the given month.

        Cost = Sum of material movements OUT linked to this contract for the month.
        Movements are linked via reference_id == contract.uid and
        reference_type == "contract_usage".  Date filtering uses created_at.
        """
        from backend.models.materials import Material, MaterialMovement

        _, last_day = monthrange(year, month)
        start_dt = datetime(year, month, 1)
        end_dt = datetime(year, month, last_day, 23, 59, 59)

        movements = await MaterialMovement.find(
            {
                "reference_id": contract.uid,
                "reference_type": "contract_usage",
                "movement_type": "OUT",
                "created_at": {"$gte": start_dt, "$lte": end_dt},
            }
        ).to_list()

        if not movements:
            return {
                "module": self.module_name,
                "total_cost": 0.0,
                "movement_count": 0,
                "breakdown_by_material": {},
                "movements": [],
            }

        total_cost = 0.0
        breakdown_by_material: Dict[str, Dict[str, Any]] = {}
        movement_details: List[Dict[str, Any]] = []

        for movement in movements:
            material = await Material.find_one(
                Material.uid == movement.material_id
            )
            material_name = (
                material.name
                if material
                else f"Material {movement.material_id}"
            )

            movement_cost = movement.total_cost or 0.0
            total_cost += movement_cost

            if material_name not in breakdown_by_material:
                breakdown_by_material[material_name] = {
                    "quantity": 0.0,
                    "total_cost": 0.0,
                }
            breakdown_by_material[material_name]["quantity"] += movement.quantity
            breakdown_by_material[material_name]["total_cost"] += movement_cost

            movement_details.append(
                {
                    "date": movement.created_at.isoformat() if movement.created_at else None,
                    "material": material_name,
                    "quantity": movement.quantity,
                    "cost": movement_cost,
                }
            )

        return {
            "module": self.module_name,
            "total_cost": total_cost,
            "movement_count": len(movements),
            "breakdown_by_material": breakdown_by_material,
            "movements": movement_details,
        }

    async def validate(
        self,
        contract: Any,
        date: Any,
    ) -> Dict[str, Any]:
        """
        Validate inventory levels for scheduled deliveries.
        """
        from backend.models.materials import MaterialMovement

        if isinstance(date, datetime):
            target_date = date.date()
        elif isinstance(date, str):
            from datetime import datetime as _dt
            target_date = _dt.fromisoformat(date).date()
        else:
            target_date = date  # already a datetime.date

        start_dt = datetime(target_date.year, target_date.month, target_date.day)
        end_dt = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)

        movements_today = await MaterialMovement.find(
            {
                "reference_id": contract.uid,
                "reference_type": "contract_usage",
                "created_at": {"$gte": start_dt, "$lte": end_dt},
            }
        ).to_list()

        return {
            "module": self.module_name,
            "is_valid": True,
            "date": target_date.isoformat(),
            "movements_today": len(movements_today),
            "issues": [],
            "warnings": [],
        }

    async def get_resource_requirements(self, contract: Any) -> Dict[str, Any]:
        """Get material requirements for this contract."""
        from backend.models.materials import Material, MaterialMovement

        movements = await MaterialMovement.find(
            MaterialMovement.reference_id == contract.uid,
            MaterialMovement.reference_type == "contract_usage",
        ).to_list()

        material_ids = list({m.material_id for m in movements})
        materials = await Material.find(
            Material.uid.in_(material_ids)
        ).to_list()

        return {
            "module": self.module_name,
            "total_materials": len(materials),
            "materials": [
                {
                    "id": m.uid,
                    "name": m.name,
                    "unit": m.unit_of_measure,
                }
                for m in materials
            ],
        }
