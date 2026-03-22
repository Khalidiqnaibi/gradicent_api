**productivity metrics**

---

### 1. Total Time

`total_time_minutes = Σ(seconds from all time_tracking events in date window) ÷ 60`

---

### 2. Average Time per Session

`avg_time_per_session_minutes = total_time_minutes ÷ number_of_unique_session_dates`

* A **session** is counted as a unique date with any tracked time

---

### 3. Percent Productive

`percent_productive = (Σ(seconds where timestamp.hour ∈ [8,18)) ÷ total_seconds) × 100`

* Measures proportion of work done during productive hours (8:00–18:00)

---

### 4. Visits per Active Hour

`visits_per_active_hour = total_interaction_events ÷ (total_seconds ÷ 3600)`

* Only counts **interaction added events** (type 202) in window
* Active hours = total_time_minutes ÷ 60

---

### 5. Time vs Clients (per day)

For each day:

* `minutes[day] = Σ(seconds for that day) ÷ 60`
* `clients[day] = count of client-added events (type 201) on that day`

Labels are the sorted dates for the window.

---

### Summary Equations

```
total_time_minutes = Σ(time_tracking_seconds) ÷ 60
avg_time_per_session_minutes = total_time_minutes ÷ count(unique session dates)
percent_productive = (Σ(seconds between 8:00–18:00) ÷ total_seconds) × 100
visits_per_active_hour = total_interactions ÷ (total_seconds ÷ 3600)
time_vs_clients = { labels: dates, minutes: daily_minutes, clients: daily_clients_added }
```
