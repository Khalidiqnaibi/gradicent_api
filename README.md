# Gradicent Developer Handbook

**Gradicent API** – *Data-Driven. Not Data-Distraction.*
Core backend API powering **Binder**, **Gaia**, and **GDE** — a unified platform for making businesses data-driven through structured data, analytics, and automated decision systems.

---

# 1. Overview

Gradicent API is the **central backend system** for all Gradicent LLC products.

It provides three foundational layers:

1. **Binder Engine** – Business data layer (entities + CRUD + events)
2. **Gaia Engine** – Analytics layer (metrics + dashboards + insights)
3. **GDE (Gradicent Decision Engine)** – Decision layer (constraints + actions + plans)

Together they form:

```
DATA  →  METRICS  →  DECISIONS  →  ACTIONS
Binder   Gaia        GDE         Business Growth
```

The system is built using:

* SOLID principles
* Plugin-based extensibility
* Strict company code standards
* Explicit state (no hidden magic)
* Measurable, testable logic

---

# 2. Full Project Structure

```
BINDERSOFTWARE_API/
│
├── app.py
├── config.py
├── README.md
├── requirements.txt
│
├── auth/                      # Authentication system
├── binder/                    # Data + CRUD engine
├── gaia/                      # Analytics engine
├── gde/                       # Decision engine
├── routes/                    # API blueprints
├── services/                  # Service layer
├── payments/                  # Payment providers
├── decorators/                # Auth guards
├── utils/                     # Utilities + event logging
├── documentation/             # Standards + known issues
├── tests/                     # System tests
├── static/                    # Frontend assets
└── templates/                 # HTML templates
```

---

# 3. Binder Engine (Data Layer)

## Purpose

Binder is the **source of truth**.

It manages:

* Users
* Clients
* Employees
* Interactions
* Transactions
* Products
* Services
* Appointments
* Files
* Events

Binder does:

* CRUD
* Data validation
* Event logging
* Domain separation (business / medical)

Binder does NOT:

* Compute analytics
* Make decisions

---

## Core Binder Structure

```
binder/
├── binder_business.py
├── binder_medical.py
├── adapters/
├── repositories/
├── models/
├── interfaces/
```

Binder uses a **StorageAdapter abstraction**:

| Adapter               | Purpose                   |
| --------------------- | ------------------------- |
| FirebaseCrudAdapter   | Production storage        |
| UnitedFirebaseAdapter | Unified Firebase handling |
| InMemoryAdapter       | Testing                   |

---

## Example Usage

```python
from binder import BinderBusiness
from binder.adapters.firebase_crud_adapter import FirebaseCrudAdapter

adapter = FirebaseCrudAdapter()
binder = BinderBusiness(adapter)

binder.current_user = "u123"

client = binder.create_client({"name": "Acme"})
binder.create_transaction(client["id"], {"amount": 200})
```

---

## Events System

Binder logs **events** for dated analytics.

Example event:

```json
{
  "meta": {
    "id": "2",
    "interaction_no": 0
  },
  "timestamp": "2025-12-23T11:39:21.542468",
  "type": 202,
  "user": "102978595279148299747"
}
```

Events are:

* Date-bound
* Lightweight
* Used only for time-window analytics
* Not used for full data reconstruction

---

# 4. Gaia Engine (Analytics Layer)

## Purpose

Gaia converts Binder data into **measurable business metrics**.

Gaia:

* Computes metrics inside time windows
* Uses plugin-based metric system
* Never mutates Binder data
* Returns aggregated summaries only

Gaia does NOT:

* Make business decisions
* Modify state

---

## Structure

```
gaia/
├── engine.py
├── registry.py
├── utils.py
├── metrics/
├── interfaces/base_metric.py
```

---

## How Metrics Work

Each metric:

* Implements `IMetric`
* Has a unique `name`
* Implements `compute(binder, **kwargs)`
* Is registered in `MetricRegistry`

---

### Example Metric

```python
class LeadVolumeMetric(IMetric):
    @property
    def name(self):
        return "lead_volume"

    def compute(self, binder, **kwargs):
        # date-bound computation
        return {"lead_count": 54}
```

---

## Example API Call

```
GET /api/gaia/compute?metric=finance&domain=business&user_id=u1
```

Response:

```json
{
  "status": "success",
  "data": {
    "total_revenue": 2500.0,
    "total_unpaid": 300.0
  },
  "message": "Metric 'finance' computed successfully."
}
```

---

# 5. GDE – Gradicent Decision Engine

## Purpose

GDE transforms metrics into:

* Business constraints
* Ranked urgency
* Concrete actions
* Execution plans

It answers:

> “What is the main constraint blocking growth right now?”

---

## Mental Model

```
Binder → Gaia → GDE

Raw Data → Metrics → Constraint Detection → Action Plan
```

---

# 6. GDE Architecture

```
gde/
├── gde_engine.py
├── gde_registry.py
├── constraints/
├── actions/
├── interfaces/
└── test/
```

---

## Constraint System

Each constraint:

* Defines `required_metrics`
* Implements `score_constraint(metrics)`
* Returns urgency score (0–10)
* Optionally implements `explain()`

Examples:

* low_leads
* low_conversion
* low_revenue
* high_churn
* low_ltv
* operational_overload
* data_visibility

---

## Actions System

Each constraint maps to actions:

```
constraints/low_leads_constraint.py
actions/low_leads_actions.py
```

Actions are:

* Concrete
* Prioritized
* Executable
* Clear

---

# 7. GDE Workflow (Full Flow)

### Step 1 – API Route

`routes/gde_routes.py`

```python
@gde_blueprint.route("/analyze", methods=["GET"])
```

Receives:

* user_id
* domain

---

### Step 2 – Service Layer

`services/gde_service.py`

```python
def analyze_business_decisions(binder):
    engine = GDEngine()
    return engine.analyze_business(binder)
```

Service layer:

* Keeps routes thin
* Handles orchestration

---

### Step 3 – Engine Execution

`gde_engine.py`

Inside `analyze_business(binder)`:

1. Collect all registered constraints
2. Aggregate required metrics
3. Ask Gaia to compute needed metrics
4. Score each constraint
5. Rank constraints
6. Select top constraint
7. Fetch mapped actions
8. Return structured output

---

### Step 4 – Final Output

```json
{
  "top_constraint": "low_conversion",
  "urgency_score": 8.4,
  "diagnostic": {...},
  "recommended_actions": [...],
  "supporting_metrics": {...}
}
```

---

# 8. GDE Principles

1. Fully deterministic
2. Date-bound metrics only
3. No raw data exposure
4. Constraint-first thinking (Hormozi-inspired)
5. One main constraint at a time

---

# 9. Example End-to-End Flow

User calls:

```
GET /api/gde/analyze?user_id=u1&domain=business
```

System:

1. Binder loads user data
2. GDE collects needed metrics
3. Gaia computes:

   * lead_volume
   * conversion_rate
   * churn_rate
   * revenue
4. GDE scores constraints
5. Detects: `low_conversion`
6. Returns actions:

   * Improve offer
   * Optimize follow-up
   * Improve sales scripts

---

# 10. Service Layer Overview

All API routes call services.

```
routes → services → engines → repositories/adapters
```

Example:

* `binder_routes.py` → `binder_service.py`
* `gaia_routes.py` → `gaia engine`
* `gde_routes.py` → `gde_service.py`

This keeps:

* Routes clean
* Business logic centralized
* Testability high

---

# 11. Authentication Layer

```
auth/
├── auth_service.py
├── providers/google_provider.py
```

Supports:

* Google OAuth
* Extensible provider system

---

# 12. Payments Layer

```
payments/
├── stripe_provider.py
├── payment_provider.py
```

Implements provider abstraction.

---

# 13. Testing

Run:

```bash
pytest -v
```

Includes:

* Auth flow tests
* Binder route tests
* GDE engine tests
* Firebase tests

Test naming:

```
test_<feature>_<expected_behavior>()
```

---

# 14. Developer Setup

1. Clone repository
2. Create Python 3.10 venv
3. Install:

```bash
pip install -r requirements.txt
```

4. Add `.env`
5. Run:

```bash
python app.py
```

API available at:

```
http://localhost:5000/api/
```

---

# 15. Design Principles

| Principle             | Implementation               |
| --------------------- | ---------------------------- |
| Single Responsibility | Separate engines             |
| Open/Closed           | Plugin metrics & constraints |
| Dependency Inversion  | Adapter abstractions         |
| No Hidden State       | Explicit binder.current_user |
| Date-Bound Analytics  | All Gaia metrics             |

---

# 16. How Everything Fits Together

```
User → Binder (data entry)
Binder → Events (tracking)
Gaia → Metrics (numbers)
GDE → Decisions (plan)
Actions → Business growth
```

This is the Gradicent System.

---

# 17. Mission

Gradicent LLC builds systems that help companies:

* Identify constraints
* Remove bottlenecks
* Increase revenue
* Improve operational efficiency
* Become truly data-driven

---

# 18. Motto

**Be Data Driven. Not Data Distracted.**

---

# 19. License

© 2025-2026 Gradicent LLC
Internal company software.
Not for public distribution.
