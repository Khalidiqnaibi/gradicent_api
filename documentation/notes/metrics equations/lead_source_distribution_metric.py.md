**lead_source_distribution**

---

### 1. Count of Leads per Source

For each lead-added event (type `201`) in the date window:

`lead_count[source] = count(events where lead.source = source)`

If source is missing → count under `"unknown"`.

---

### 2. Total Leads

`total_leads = Σ(lead_count[source] for all sources)`

---

### Final Equations

* **Distribution:** `distribution[source] = number of leads from that source`
* **Total Leads:** `total_leads = sum of all distribution counts`
