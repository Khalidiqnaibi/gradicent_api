**days_since_last_event (data_freshness)**

`result = current_date − latest_event_timestamp (in days)`

---

### Equation:

`days_since_last_event = (now − max(event_timestamp in window)).days`

---

### Where:

* **latest_event_timestamp** = most recent event timestamp within the selected date window
* If no window is provided → use all available data

---

### Edge case:

* If no events exist:

`days_since_last_event = null`
`has_events = false`
