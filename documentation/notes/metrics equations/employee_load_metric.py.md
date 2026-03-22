**employee_load**

---

### Primary (using employee metadata):

For each employee:

`employee_load = hours_per_week`

Then:

`avg_load = Σ(hours_per_week of all employees) ÷ number_of_employees`

---

### So overall:

* **employee_loads** = mapping of `employee_id → hours_per_week`
* **avg_load** = average of those values

---

### Fallback (using events):

For each employee:

`employee_load = number of assigned events in date window`

Then:

`avg_load = Σ(assigned event counts per employee) ÷ number_of_employees_with_assignments`

---

### Final equations:

**Primary:**

`avg_load = Σ(hours_per_week) ÷ total_employees`

**Fallback:**

`avg_load = Σ(assigned_events_per_employee) ÷ total_active_employees`
