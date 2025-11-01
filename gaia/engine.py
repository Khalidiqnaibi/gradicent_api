"""
engine.py
---------
Main interface to the Gaia analytics system.
Applies the Facade pattern to expose a simple API for complex analytics logic.
"""

from typing import Dict, Any
from .registry import MetricRegistry


class GaiaEngine:
    """
    Coordinates metric computation for any Binder domain.
    """

    def compute(self, binder, metric_name: str, **kwargs) -> Dict[str, Any]:
        """
        Compute any registered metric dynamically.

        Example:
            engine.compute(binder, "roi", from="2025-01-01", to="2025-02-01")

        Args:
            binder: The Binder instance (Business or Medical).
            metric_name (str): The name of the metric plugin.
            **kwargs: Parameters for computation.

        Returns:
            dict: Computed result.
        """
        metric = MetricRegistry.get_metric(metric_name)
        return metric.compute(binder, **kwargs)

    def list_available_metrics(self):
        """Return list of available metrics."""
        return MetricRegistry.list_metrics()
