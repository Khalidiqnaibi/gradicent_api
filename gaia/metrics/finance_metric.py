"""
finance_metric.py
-----------------
Computes financial KPIs for Binder:
- Total revenue
- Total unpaid balance
- Average revenue per client
- Daily revenue/unpaid trends

Optimized to:
- Avoid unnecessary intermediate lists
- Minimize nested loops
- Parse dates only once
- Aggregate data in a single pass
"""

from typing import Dict, Any
from ..interfaces.base_metric import IMetric
from ..registry import MetricRegistry
from ..utils import parse_date


class FinanceMetric(IMetric):
    """
    Finance metric implementation.

    Relies on:
    - analytics events stored in user metadata
    - interaction data stored per client
    """

    @property
    def name(self) -> str:
        """Unique metric identifier."""
        return "finance"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        """
        Compute finance metrics for a given date range.

        Keyword Args:
            From / from: start date
            To / to: end date

        Returns:
            Dict[str, Any]: Aggregated finance statistics
        """

        # Parse date range once
        start = parse_date(kwargs.get("From", kwargs.get("from")))
        end = parse_date(kwargs.get("To", kwargs.get("to")))

        # Fetch required data
        patients = binder.adapter.list_children(
            binder.domain,
            binder.current_user,
            "clients"
        ) or []

        meta = binder.adapter.get_child(
            binder.domain,
            binder.current_user,
            "metadata"
        ) or {}

        analytics = meta.get("analytics", {})

        total_revenue = 0.0
        total_unpaid = 0.0

        # Trends accumulator
        trends_map: Dict[str, Dict[str, float]] = {}
        total_ids =[]

        # Single pass over analytics
        for date_str, day_data in analytics.items():
            date = parse_date(date_str)
            if not (start <= date <= end):
                continue

            events = day_data.get("events", [])
            if not events:
                continue

            day_bucket = trends_map.setdefault(
                date_str,
                {"revenue": 0.0, "unpaid": 0.0}
            )

            for event in events:
                if event.get("type") not in (202, 402):
                    continue

                meta_info = event.get("meta", {})
                client_id = meta_info.get("id")
                interaction_no = meta_info.get("interaction_no")

                if client_id is None or interaction_no is None:
                    continue

                try:
                    client = patients[int(client_id)]
                except (IndexError, ValueError, TypeError):
                    continue
                
                if client_id not in total_ids:
                    total_ids.append(client_id)
                interactions = client.get("interactions")
                if not interactions:
                    continue

                if isinstance(interactions, list):
                    try:
                        interaction = interactions[interaction_no]
                    except (IndexError, TypeError):
                        continue
                else:
                    interaction = interactions

                payed = float(interaction.get("payed", 0))
                debit = float(interaction.get("debit", 0))

                # Aggregate totals
                total_revenue += payed
                total_unpaid += debit

                # Aggregate daily trends
                day_bucket["revenue"] += payed
                day_bucket["unpaid"] += debit

        # Build trends output (ordered by date insertion)
        trends = {
            "date": list(trends_map.keys()),
            "revenue": [v["revenue"] for v in trends_map.values()],
            "unpaid": [v["unpaid"] for v in trends_map.values()],
        }

        avg_revenue = total_revenue / max(len(patients), 1)

        return {
            "total_revenue": round(total_revenue, 2),
            "total_unpaid": round(total_unpaid, 2),
            "clients":total_ids,
            "avg_revenue_per_client": round(avg_revenue, 2),
            "trends": trends,
        }


MetricRegistry.register(FinanceMetric)
