**financial_summary**

---

### 1. Total Paid

#### Medical domain:

`total_payed = Σ(payed amounts from finance events)`

If scaling factor exists:

`payed = payed × div_factor (e.g., 10)`

---

#### Business domain:

`total_payed = Σ(amounts where paid = true)`

---

### 2. Total Debit

#### Medical domain:

`total_debit = Σ(debit amounts from finance events)`

If scaling factor exists:

`debit = debit × div_factor`

---

#### Business domain:

`total_debit = Σ(amounts where paid = false)`

---

### Final equations:

**Medical:**

* `total_payed = Σ(payed × scaling_factor_if_any)`
* `total_debit = Σ(debit × scaling_factor_if_any)`

**Business:**

* `total_payed = Σ(amount where paid = true)`
* `total_debit = Σ(amount where paid = false)`

---

### Scope condition:

* Only include events within the date range
* Only include events with types: `202, 402, 401`
