**revenue_per_employee**

---

### 1. Total Revenue

`total_revenue = sum(amount of all payment events in date window)`

* Prefer metadata.finance if available
* Fallback: sum payments by assignee from events (types 600, 601, 602, 604)

---

### 2. Revenue per Employee

`revenue_per_employee = total_revenue ÷ number_of_employees`

* Number of employees can come from:

  * metadata list of employees, or
  * assignees detected in payment events

---

### Final Equation:

```id="rk4q6l"
revenue_per_employee = total revenue ÷ employee count
```
