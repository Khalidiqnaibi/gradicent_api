#  **Gradicent API**

> **Data-Driven. Not Data-Distraction.**
> Core backend API powering Binder and Gaia — a unified platform for making any business data-driven through structured data, analytics, and automation.

---

##  **Overview**

The **Gradicent API** is the unified backend for all Gradicent LLC software products.
It provides two foundational layers:

1. **Binder Engine** → Handles business logic, entities, and CRUD operations (users, clients, visits, employees, etc.)
2. **Gaia Engine** → Handles analytics, dashboards, and metric computation for ROI, finance, productivity, and any future insight.

These layers are designed using **SOLID principles** and **Gradicent’s company code standards** to ensure maximum clarity, reusability, and scalability.

---

##  **Architecture**

```
gradicent-api/
│
├── app.py                      # Flask app entry point
│
├── binder/                     # Business logic and data management
│   ├── binder_business.py      # Business domain binder
│   ├── binder_medical.py       # Medical domain binder
│   ├── adapters/               # Data storage adapters
│   │   ├── firebase_crud_adapter.py
│   │   └── inmemory_adapter.py
│   ├── gaia/                   # Domain-specific extensions for analytics
│   │   └── gaia_engine.py
│   ├── interfaces/             # Abstract interfaces and contracts
│   │   ├── binder.py
│   │   ├── binder_interface.py
│   │   └── storage_adapter.py
│   ├── models/                 # Uniform data schemas
│   │   └── models.py
│   └── services/               # Domain service logic (optional)
│       └── medical_service.py
│
├── gaia/                       # Global analytics engine
│   ├── engine.py               # Facade for metric computation
│   ├── registry.py             # Plugin registry for metrics
│   ├── utils.py                # Time parsing, helpers
│   ├── interfaces/
│   │   └── base_metric.py      # Abstract metric interface
│   ├── metrics/                # Pluggable metric modules
│   │   ├── conversion_rate_metric.py
│   │   ├── finance_metric.py
│   │   └── roi_metric.py
│   └── test/
│       └── api_test.py
│
└── routes/                     # Flask routes (controllers)
    ├── binder_routes.py
    ├── gaia_routes.py
    └── __init__.py
```

---

##  **Core Components**

### 1. Binder Engine

**Purpose:** Manage entities (users, clients, visits, products, services) through consistent CRUD interfaces.

**Principles:**

* Every Binder domain (e.g., `BinderBusiness`, `BinderMedical`) extends from the same abstract interfaces.
* Each uses a `StorageAdapter` (Firebase, SQL, or in-memory) for persistence.
* Uniform data models ensure Gaia can analyze any domain seamlessly.

**Example:**

```python
from binder.adapters.firebase_crud_adapter import FirebaseCrudAdapter
from binder.binder_business import BinderBusiness

adapter = FirebaseCrudAdapter()
binder = BinderBusiness(adapter)
binder.set_current_user("u123")

client = binder.create_client({"name": "Acme Corp"})
binder.create_transaction(client["id"], {"amount": 200.0, "status": "paid"})
```

---

### 2. Gaia Engine

**Purpose:** Perform any kind of data analysis or metric computation with a plugin-based system.

**Structure:**

* `engine.py` → Facade that executes metrics by name.
* `registry.py` → Keeps track of all metric plugins.
* `metrics/` → Individual metric definitions (e.g., ROI, Finance, Conversion Rate).
* `base_metric.py` → Defines the `IMetric` interface for all analytics modules.

**Example:**

```python
from gaia import GaiaEngine

engine = GaiaEngine()
results = engine.compute(binder, "roi", From="2025-01-01", To="2025-02-01")
print(results)
```

**Add a new metric:**

```python
# gaia/metrics/customer_growth_metric.py
from gaia.interfaces.base_metric import IMetric
from gaia.registry import MetricRegistry

class CustomerGrowthMetric(IMetric):
    @property
    def name(self):
        return "customer_growth"

    def compute(self, binder, **kwargs):
        clients = binder.adapter.list_children(binder.current_user, "clients")
        return {"client_count": len(clients)}

MetricRegistry.register(CustomerGrowthMetric)
```

No engine changes required - instantly available at:

```
GET /api/gaia/compute?metric=customer_growth&domain=business&user_id=u1
```

---

##  **API Overview**

###  Binder Routes (`/api/binder`)

| Route            | Method | Description                                  |
| ---------------- | ------ | -------------------------------------------- |
| `/create_user`   | POST   | Create a user (doctor, business owner, etc.) |
| `/add_client`    | POST   | Add a client or patient                      |
| `/update_client` | PATCH  | Update existing client data                  |

---

###  Gaia Routes (`/api/gaia`)

| Route      | Method | Description                               |
| ---------- | ------ | ----------------------------------------- |
| `/metrics` | GET    | List all available metric plugins         |
| `/compute` | GET    | Compute any registered metric dynamically |

**Example:**

```
GET /api/gaia/compute?metric=finance&domain=medical&user_id=u1
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "total_revenue": 2500.0,
    "total_unpaid": 300.0,
    "avg_revenue_per_client": 833.3
  },
  "message": "Metric 'finance' computed successfully."
}
```

---

##  **Adapters**

Adapters abstract how data is stored or retrieved.
Any backend (Firebase, SQL, local memory) can be used by implementing the `StorageAdapter` interface.

| Adapter               | Description                            |
| --------------------- | -------------------------------------- |
| `FirebaseCrudAdapter` | Uses Firebase Realtime Database        |
| `InMemoryAdapter`     | Local testing adapter (no external DB) |

---

##  **Design Principles**

| Principle                     | Applied Through                                                |
| ----------------------------- | -------------------------------------------------------------- |
| **S — Single Responsibility** | Each class has one purpose (metric, adapter, binder, route).   |
| **O — Open/Closed**           | Add metrics or domains without touching core logic.            |
| **L — Liskov Substitution**   | Any Binder or Adapter can replace another seamlessly.          |
| **I — Interface Segregation** | Small, focused interfaces (`ICrudService`, `IMetric`).         |
| **D — Dependency Inversion**  | Business logic depends on abstractions, not concrete adapters. |

---

##  **Developer Setup**

### 1. Install dependencies

```bash
pip install flask firebase-admin pytest black isort flake8
```

### 2. Firebase setup

Create a service account key and place it at the root:

```
serviceAccountKey.json
```

### 3. Run the API

```bash
python app.py
```

Access the API at:

```
http://localhost:5000/api/
```

---

##  **Testing**

Each module has its own test directory (e.g., `gaia/test/api_test.py`).

Example:

```bash
pytest -v
```

**Test naming convention:**

```
test_<function_or_class_name>_returns_expected_result()
```

---

##  **Extending the System**

| Extension                           | How to Add                                                                   |
| ----------------------------------- | ---------------------------------------------------------------------------- |
| **New Domain (e.g., BinderRetail)** | Create `binder_retail.py` implementing the same interfaces.                  |
| **New Storage Adapter**             | Add file under `binder/adapters/` and implement `StorageAdapter`.            |
| **New Metric**                      | Add file under `gaia/metrics/` and register via `MetricRegistry.register()`. |
| **New Route**                       | Create a file in `/routes/`, following company standards.                    |

---

##  **About Gradicent LLC**

**Gradicent LLC** helps organizations become **data-driven, not data-distracted**.
Our goal is to empower teams to make fast, informed decisions through intelligent software systems like **Binder** and **Gaia**.

**Motto:**

> “Be Data Driven. Not Data Distracted.”

**Website:** [gradicent.com](https://gradicent.com)

---

## **License**

© 2025 Gradicent LLC — All rights reserved.
Internal company software. Not for public distribution.

