"""
base_metric.py
--------------
Defines the abstract base class for all Gaia metrics.
Follows SOLID — each metric is a single responsibility component.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class IMetric(ABC):
    """
    Interface for analytics metric plugins.
    Each metric must define how it computes and describes itself.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique metric name identifier."""
        pass

    @abstractmethod
    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        """
        Compute this metric given a binder (data source).

        Args:
            binder: Any binder implementing the CRUD interfaces.
            **kwargs: Context parameters (e.g., date range).

        Returns:
            dict: Resulting analytics data for dashboards.
        """
        pass
