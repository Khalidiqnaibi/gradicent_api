**avg_customer_lifetime_days**

`result = average(customer lifetime in days)`

---

### Using events (primary):

For each customer:

* **lifetime** = `last_activity_date − first_purchase_date`

Where:

* **first_purchase_date** = earliest first purchase event (type `600`) in window
* **last_activity_date** = latest heartbeat event (types `[402, 202]`) or fallback interaction

So:

`avg_customer_lifetime_days = mean( (last_activity − first_purchase) in days for all valid customers )`

---

### Expanded equation:

`avg_customer_lifetime_days = Σ(lifetime_days_per_customer) ÷ number_of_customers_with_valid_lifetime`

---

### Fallback (per client):

For each customer:

* **lifetime** = `last_interaction_date − created_at`

So:

`avg_customer_lifetime_days = Σ(last_interaction − created_at in days) ÷ count(valid customers)`
