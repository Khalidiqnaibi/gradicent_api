"""
Gaia Engine 
--------------------------
Analytics engine that consumes uniform model dicts from Binder.
No adapter between Gaia and Binder required — just call Binder methods.
"""

from typing import Dict, Any, List
from statistics import mean


class GaiaEngine:
    def __init__(self, binder: Any, config: Dict[str, Any] = None):
        """
        binder: instance of BusinessBinder (or any binder exposing uniform methods)
        """
        self.binder = binder
        self.config = config or {"default_avg_hourly": 50, "plan_price_map": {}}

    def finance(self) -> Dict[str, Any]:
        """Aggregate revenue and unpaid across all clients for current user."""
        user_id = self.binder.current_user
        if not user_id:
            raise RuntimeError("binder.current_user not set")
        clients = self.binder.adapter.list_children(user_id, "clients")
        total_revenue = 0.0
        total_unpaid = 0.0
        per_client = {}
        for c in clients:
            txns = c.get("transactions", []) or []
            rev = sum(float(t.get("amount", 0) or 0) for t in txns)
            unpaid = sum(float(t.get("metadata", {}).get("debit", 0) or 0) for t in txns)
            total_revenue += rev
            total_unpaid += unpaid
            per_client[c["id"]] = rev
        avg_per_client = mean(per_client.values()) if per_client else 0.0
        return {
            "total_revenue": round(total_revenue, 2),
            "total_unpaid": round(total_unpaid, 2),
            "avg_revenue_per_client": round(avg_per_client, 2),
            "per_client": per_client
        }

    def roi(self) -> Dict[str, Any]:
        """Simple ROI: hours_saved * avg_hourly - subscription (example)."""
        # example: hours saved = sum of interaction metadata 'time_saved' if set
        user_id = self.binder.current_user
        if not user_id:
            raise RuntimeError("binder.current_user not set")
        clients = self.binder.adapter.list_children(user_id, "clients")
        hours = 0.0
        for c in clients:
            for it in c.get("interactions", []) or []:
                hours += float(it.get("metadata", {}).get("time_saved_hours", 0) or 0)
        avg_hourly = float(self.config.get("default_avg_hourly", 50))
        subscription = float(self.config.get("plan_price_map", {}).get("default", 0))
        binder_roi = round(hours * avg_hourly - subscription, 2)
        return {"hours_saved": round(hours, 2), "binder_roi": binder_roi}
