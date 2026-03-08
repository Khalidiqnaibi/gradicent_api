# Gradicent Developer Handbook

**Gradicent API** – *Data-Driven. Not Data-Distraction.*
Core backend API powering Binder and Gaia — a unified platform for making businesses data-driven through structured data, analytics, and automation.

---

## 1. Overview

Gradicent API is the **unified backend** for all Gradicent LLC software products. It provides three foundational layers:

1. **Binder Engine** – Handles business logic, entities, and CRUD operations (users, clients, visits, employees, etc.).
2. **Gaia Engine** – Handles analytics, dashboards, and metric computation for ROI, finance, productivity, and other insights.
3. **GDE (Gradicent Decision Engine)** – Generates **data-driven plans** from Binder and Gaia data for actionable insights.

The system is designed following **SOLID principles** and Gradicent’s **company code standards** to ensure clarity, scalability, and maintainability.

---

## 2. Architecture

```
gradicent-api/
│
├── app.py                      # Flask app entry point
├── config.py                   # DefaultConfig class with env settings
├── binder/                     # Business logic and data management
│   ├── binder_business.py      # Business domain binder
│   ├── binder_medical.py       # Medical domain binder
│   ├── adapters/               # Storage adapters
│   │   ├── firebase_crud_adapter.py
│   │   ├── firebase_file_storage_adapter.py
│   │   └── inmemory_adapter.py
│   ├── interfaces/             # Abstract interfaces
│   │   ├── binder.py
│   │   ├── binder_mixins.py
│   │   └── storage_adapter.py
│   ├── models/                 # Data models
│   │   ├── models.py
│   │   └── legacy_user.py
│   └── repositories/           # CRUD repositories
│
├── gaia/                       # Analytics engine
│   ├── engine.py               # Metric computation facade
│   ├── registry.py             # Metric plugin registry
│   ├── utils.py                # Helpers and time parsing
│   ├── interfaces/
│   │   └── base_metric.py      # Metric interface
│   ├── metrics/                # Metric implementations
│   │   ├── conversion_rate_metric.py
│   │   ├── finance_metric.py
│   │   ├── roi_metric.py
│   │   └── productivity_metric.py
│   └── test/
│       └── api_test.py
│
├── payments/                   # Payment providers
│   ├── stripe_provider.py
│   └── payment_provider.py
│
├── routes/                     # Flask blueprints
│   ├── auth_routes.py
│   ├── binder_routes.py
│   ├── gaia_routes.py
│   ├── payments_routes.py
│   ├── frontend_routes.py
│   └── file_routes.py
│
├── services/                   # Business services
│   ├── subscription_service.py
│   ├── user_service.py
│   └── binder_service.py
│
├── utils/                      # Utility functions
│   ├── log_events.py
│   ├── provision_user.py
│   └── get_plan_status.py
│
├── decorators/                 # Authorization decorators
│   ├── req_login.py
│   └── req_admin.py
│
├── static/                     # Frontend assets (images, CSS, JS)
└── templates/                  # HTML templates
```

---

## 3. Core Components

### Binder Engine

* **Purpose:** Manage entities (users, clients, visits, products, services) via uniform CRUD interfaces.
* **Principles:**

  * Every Binder domain (e.g., `BinderBusiness`, `BinderMedical`) implements the same abstract interfaces.
  * Uses a `StorageAdapter` (Firebase, SQL, or in-memory) for persistence.
  * Uniform data models ensure compatibility with Gaia analytics.

**Example:**

```python
from binder import FirebaseCrudAdapter, BinderBusiness

adapter = FirebaseCrudAdapter()
binder = BinderBusiness(adapter)
binder.set_current_user("u123")

client = binder.create_client({"name": "Acme Corp"})
binder.create_transaction(client["id"], {"amount": 200.0, "status": "paid"})
```

---

### Gaia Engine

* **Purpose:** Perform analytics and metric computation using a plugin-based system.
* **Structure:**

  * `engine.py` → Executes metrics by name
  * `registry.py` → Maintains all metric plugins
  * `metrics/` → Metric implementations (ROI, Finance, Conversion Rate, Productivity)
  * `base_metric.py` → Defines the `IMetric` interface

**Add a new metric:**

```python
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

**Example API call:**

```
GET /api/gaia/compute?metric=customer_growth&domain=business&user_id=u1
```

---

### Adapters

Abstract how data is stored or retrieved. Implement the `StorageAdapter` interface to add a new backend.

| Adapter             | Description                    |
| ------------------- | ------------------------------ |
| FirebaseCrudAdapter | Firebase Realtime Database     |
| InMemoryAdapter     | Local memory storage (testing) |

---

### Payments

* Supports multiple providers: Stripe, Paddle, PayPal
* Implement `IPaymentProvider` to add a new provider

---

## 4. API Overview

### Binder Routes (`/api/binder`)

| Route            | Method | Description                                |
| ---------------- | ------ | ------------------------------------------ |
| `/create_user`   | POST   | Create a new user (doctor, business owner) |
| `/add_client`    | POST   | Add a new client or patient                |
| `/update_client` | PATCH  | Update client or patient data              |

### Gaia Routes (`/api/gaia`)

| Route      | Method | Description                             |
| ---------- | ------ | --------------------------------------- |
| `/metrics` | GET    | List all available metric plugins       |
| `/compute` | GET    | Compute a registered metric dynamically |

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

## 5. Developer Setup

1. Clone repository
2. Create virtual environment (Python 3.10)
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set `.env` with dev credentials (Firebase, OAuth, Stripe)
5. Run locally:

```bash
python app.py
```

Access API at:

```
http://localhost:5000/api/
```

---

## 6. Testing

* Tests located in `tests/` and `gaia/test/`
* Run all tests:

```bash
pytest -v
```

* Follow **test naming conventions**: `test_<function_or_class_name>_returns_expected_result()`

---

## 7. Extending the System

| Extension               | How to Add                                                              |
| ----------------------- | ----------------------------------------------------------------------- |
| **New Binder Domain**   | Create a new file implementing existing interfaces                      |
| **New Storage Adapter** | Implement `StorageAdapter` in `binder/adapters/`                        |
| **New Metric**          | Implement `IMetric` in `gaia/metrics/` and register in `MetricRegistry` |
| **New Route**           | Create a new blueprint in `routes/` following company code standards    |

---

## 8. Onboarding

1. Manager provides task list for first week
2. Read **this documentation fully** before touching code
3. Setup environment and credentials
4. Pair with a mentor for first 2–3 tasks
5. Follow code standards provided in onboarding package

---

## 9. Known Issues

* All known errors and troubleshooting guides are in:

```
documentation/errors/not yet/1 → 5
```

* Folder numbering = priority (5 = highest)

---

## 10. Design Principles

| Principle                 | Applied Through                                               |
| ------------------------- | ------------------------------------------------------------- |
| S – Single Responsibility | Each class has one purpose (metric, adapter, binder, route)   |
| O – Open/Closed           | Add metrics or domains without touching core logic            |
| L – Liskov Substitution   | Any Binder or Adapter can replace another seamlessly          |
| I – Interface Segregation | Small, focused interfaces (`ICrudService`, `IMetric`)         |
| D – Dependency Inversion  | Business logic depends on abstractions, not concrete adapters |

---

## 11. About Gradicent LLC

Gradicent LLC helps organizations **be data-driven, not data-distracted**, empowering teams to make fast, informed decisions through intelligent software systems like **Binder** and **Gaia**.

**Motto:**
*“Be Data Driven. Not Data Distracted.”*

**Website:** [gradicent.com](https://gradicent.com)

---

## 12. License

© 2025 Gradicent LLC — All rights reserved.
Internal company software. Not for public distribution.

