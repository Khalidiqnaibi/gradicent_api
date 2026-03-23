**manual_work_ratio (manual_ratio_percent)**

---

### 1. Total Events

`total_events = count(all events in the date window)`

---

### 2. Manual Events

`manual_events = count(events where type ∈ MANUAL_TYPES in date window)`

Where:

`MANUAL_TYPES = {400, 401, 402, 203, 204, 205, 206, 403, 404, 405, 406}`

---

### 3. Manual Work Ratio

`manual_ratio_percent = (manual_events ÷ total_events) × 100`

---

### Final Equation:

```
manual_ratio_percent = (number of manual events ÷ total number of events) × 100
```
