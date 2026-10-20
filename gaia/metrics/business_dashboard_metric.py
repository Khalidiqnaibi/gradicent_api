"""
business_dashboard_metric.py
----------------------------
One-call summary for the business dashboard and analytics pages
(GET /api/gaia/compute?metric=business_dashboard&domain=business&user_id=...).

Built from the current binder records (clients, their transactions, employees) rather than the
legacy analytics blob, so it works for accounts created on the Supabase data model.

Values the data cannot support (ROI, previous-period comparisons) are returned as None instead
of invented numbers; the frontend hides or dashes them.
"""

from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

from ..interfaces.base_metric import IMetric
from ..registry import MetricRegistry

MAX_CLIENTS = 500          # cap the per-client transaction scan for very large accounts
TXN_LIMIT = 500          # transactions read per client
NON_REVENUE_STATUSES = {"failed", "cancelled", "canceled", "refund", "refunded", "pending", "void"}
CHURNED_STATUSES = {"churned", "inactive", "cancelled", "canceled", "lost"}
DATE_KEYS = ("date", "paid_at", "paidAt", "created_at", "createdAt", "timestamp")
CLIENT_DATE_KEYS = ("joinDate", "join_date", "created_at", "createdAt", "registered", "date")
AMOUNT_KEYS = ("amount", "total", "payed", "paid", "value")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _to_float(value: Any) -> Optional[float]:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if n == n else None  # drop NaN


def _parse_day(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            # epoch seconds or milliseconds
            return datetime.fromtimestamp(value / 1000 if value > 1e11 else value).date()
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:19] if "T" in text else text[:10], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _first(record: Dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if record.get(key) not in (None, ""):
            return record[key]
    return None


def _list_all(fetch) -> List[Dict[str, Any]]:
    """Fetch up to MAX_CLIENTS rows from a binder list_* method in one query."""
    return list(fetch(limit=MAX_CLIENTS) or [])[:MAX_CLIENTS]


def _pct(part: float, whole: float) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


class BusinessDashboardMetric(IMetric):
    """Aggregate KPIs, revenue trend and breakdowns for the business dashboard."""

    @property
    def name(self) -> str:
        return "business_dashboard"

    def compute(self, binder, **kwargs) -> Dict[str, Any]:
        today = date.today()
        this_month = (today.year, today.month)
        last_month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)

        clients = _list_all(binder.list_clients)

        # ---- clients ----
        statuses = [str(c.get("status") or "").strip().lower() for c in clients]
        churned = sum(1 for s in statuses if s in CHURNED_STATUSES)
        active = sum(1 for s in statuses if s not in CHURNED_STATUSES and s != "lead")

        joined = [_parse_day(_first(c, CLIENT_DATE_KEYS)) for c in clients]
        new_this_month = (
            sum(1 for d in joined if d and (d.year, d.month) == this_month)
            if any(joined) else None
        )

        plan_counts = Counter(str(c.get("plan")).strip() for c in clients if c.get("plan"))
        plans_total = sum(plan_counts.values())
        clients_by_plan = [
            {"plan": plan, "count": count, "percentage": _pct(count, plans_total)}
            for plan, count in plan_counts.most_common()
        ]

        # ---- transactions (revenue) ----
        revenue_by_month: Dict[tuple, float] = defaultdict(float)
        revenue_by_service: Dict[str, float] = defaultdict(float)
        for client in clients:
            client_id = client.get("id")
            if client_id is None:
                continue
            try:
                transactions = binder.list_transactions(str(client_id), limit=TXN_LIMIT) or []
            except Exception:
                continue  # one unreadable client shouldn't sink the whole dashboard
            for txn in transactions:
                if str(txn.get("status") or "").strip().lower() in NON_REVENUE_STATUSES:
                    continue
                amount = _to_float(_first(txn, AMOUNT_KEYS))
                day = _parse_day(_first(txn, DATE_KEYS))
                if amount is None or day is None:
                    continue
                revenue_by_month[(day.year, day.month)] += amount
                service = _first(txn, ("service", "serviceName", "description", "type"))
                if service:
                    revenue_by_service[str(service)] += amount

        ytd = sum(v for (y, _m), v in revenue_by_month.items() if y == today.year)

        trend = []
        for offset in range(11, -1, -1):
            month_index = today.month - 1 - offset
            year = today.year + month_index // 12
            month = month_index % 12 + 1
            trend.append({
                "month": MONTHS[month - 1],
                "revenue": round(revenue_by_month.get((year, month), 0.0), 2),
                "prevYear": round(revenue_by_month.get((year - 1, month), 0.0), 2),
            })

        services_total = sum(revenue_by_service.values())
        top_services = [
            {"service": name, "revenue": round(value, 2), "percentage": _pct(value, services_total)}
            for name, value in sorted(revenue_by_service.items(), key=lambda kv: kv[1], reverse=True)[:6]
        ]

        # ---- team ----
        try:
            employee_count = len(_list_all(binder.list_employees))
        except Exception:
            employee_count = None

        return {
            "totalRevenueYTD": round(ytd, 2),
            "revenueThisMonth": round(revenue_by_month.get(this_month, 0.0), 2),
            "lastMonthRevenue": round(revenue_by_month.get(last_month, 0.0), 2),
            "activeClients": active,
            "totalClients": len(clients),
            "newClientsThisMonth": new_this_month,
            "churnRate": _pct(churned, len(clients)),
            "previousChurnRate": None,
            "roi": None,
            "previousRoi": None,
            "employeeCount": employee_count,
            "topServices": top_services,
            "revenueByMonth": trend,
            "clientsByPlan": clients_by_plan,
            "employeeProductivity": [],
        }


MetricRegistry.register(BusinessDashboardMetric)
