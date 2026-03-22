**total_customers**

---

### 1. Total Customers

`total_customers = count(unique entity IDs seen in the date window)`

Where an entity ID is taken from event metadata and can come from:

* `entity_id`
* `patient`
* `client`
* `id`

---

### 2. Returning Customers

`returning_customers = count(unique entities that satisfy the returning rule)`

#### Returning rule:

* If an entity has a **NEW** event (`201`) inside the period, it is **new**.
* It becomes **returning** only if it also has an **interaction** event (`402`) **after** the NEW event date.
* Interaction on the **same date** as the NEW event does **not** count as returning.
* If the entity was created before the period and has interaction(s) in the period, it is **returning**.

So:

`returning_customers = |{ entity : (new_in_period AND interaction_date > new_date) OR (no_new_in_period AND has_interaction_in_period) }|`

---

### 3. Average Visits per Customer

`avg_visits_per_customer = total_interaction_events ÷ total_customers`

Where:

`total_interaction_events = count(events where type = 402 in date window)`

---

### 4. Weekly New Customers

For each week:

`weekly_new_count[week] = count(unique entities with NEW events (201) in that week)`

---

### 5. Weekly Returning Customers

For each week:

`weekly_returning_count[week] = count(unique entities with INTERACTION events (402) in that week that also satisfy the returning rule)`

---

### Final summary equations

```text
total_customers = count(unique entity IDs in window)
returning_customers = count(unique entities that are new-after-interaction eligible or pre-existing with interactions)
avg_visits_per_customer = total_interaction_events / total_customers
weekly_counts = unique new entities per week
weekly_returning_counts = unique returning entities per week
```
