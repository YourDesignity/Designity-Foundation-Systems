"""Abstract base class for all contract modules."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List


class ContractModule(ABC):
    """
    Abstract base class for all contract modules.
    Each module provides cost calculation and validation for a specific aspect of contracts.
    """

    module_name: str = "base"
    required_models: List[str] = []

    @abstractmethod
    async def initialize(self, contract: Any) -> Dict[str, Any]:
        """
        Called when module is enabled for a contract.
        Returns initialization status and any setup data.
        """
        pass

    @abstractmethod
    async def calculate_cost(
        self,
        contract: Any,
        month: int,
        year: int,
    ) -> Dict[str, Any]:
        """
        Calculate this module's cost contribution for a given month.

        Returns:
        {
            "module": "employee",
            "total_cost": 5000.0,
            "breakdown": {...},
            "details": [...]
        }
        """
        pass

    @abstractmethod
    async def validate(
        self,
        contract: Any,
        date: datetime,
    ) -> Dict[str, Any]:
        """
        Validate this module's requirements for a specific date.

        Returns:
        {
            "module": "employee",
            "is_valid": True,
            "issues": [],
            "warnings": []
        }
        """
        pass

    async def get_resource_requirements(self, contract: Any) -> Dict[str, Any]:
        """
        Get resource requirements for this module.
        Optional override for modules that need to declare resources.
        """
        return {}

    async def cleanup(self, contract: Any) -> bool:
        """
        Cleanup when module is disabled for a contract.
        Optional override for modules that need cleanup.
        """
        return True
