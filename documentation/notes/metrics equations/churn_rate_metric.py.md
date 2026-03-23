**churn_rate_percent**

`result = (number of churned customers ÷ total customers) × 100`

---

### Using heartbeat events (primary):

* **total customers** = number of unique clients with heartbeat activity in the date window
* **churned customers** = clients whose **last activity timestamp** is older than the cutoff

Where:

* `cutoff = now − inactive_days`

So the equation becomes:

`churn_rate_percent = (count(clients with last_seen < cutoff) ÷ count(unique active clients in window)) × 100`

---

### Fallback (client interactions):

* **total customers** = total number of clients
* **churned customers** = clients whose **last interaction timestamp** is missing OR older than cutoff

So:

`churn_rate_percent = (count(clients with no interactions OR last_interaction < cutoff) ÷ total clients) × 100`
