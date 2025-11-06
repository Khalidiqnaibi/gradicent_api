"""
registry.py
-----------
Manages registration and lookup of available metrics.
This enables dynamic discovery — plug-and-play metric expansion.
"""

from typing import Dict, Type
from .interfaces.base_metric import IMetric


class MetricRegistry:
    """Registry to hold all metric classes."""

    _registry: Dict[str, Type[IMetric]] = {}

    @classmethod
    def register(cls, metric_cls: Type[IMetric]) -> None:
        """Register a metric plugin."""
        name = metric_cls().name
        cls._registry[name] = metric_cls

    @classmethod
    def get_metric(cls, name: str) -> IMetric:
        """Instantiate a registered metric by name."""
        if name not in cls._registry:
            raise ValueError(f"Metric '{name}' not registered.")
        return cls._registry[name]()

    @classmethod
    def list_metrics(cls):
        """List available metric names."""
        return list(cls._registry.keys())
