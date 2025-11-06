from ..interfaces.base_metric import IMetric
from ..registry import MetricRegistry

class ConversionRateMetric(IMetric):
    @property
    def name(self): return "conversion_rate"

    def compute(self, binder, **kwargs):
        clients = binder.adapter.list_children(binder.current_user, "clients")
        converted = [c for c in clients if c.get("status") == "converted"]
        return {"conversion_rate": len(converted) / max(len(clients), 1)}

MetricRegistry.register(ConversionRateMetric)
