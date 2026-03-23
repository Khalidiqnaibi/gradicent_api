**finance metrics**

---

### 1. Total Revenue

`total_revenue = Σ(payed amount for all qualifying interactions in date window)`

---

### 2. Total Unpaid

`total_unpaid = Σ(debit amount for all qualifying interactions in date window)`

Where:

* `debit = debit` if exists
* otherwise `debit = -balance`

---

### 3. Average Revenue per Client

`avg_revenue_per_client = total_revenue ÷ total_number_of_clients`

---

### 4. Daily Revenue Trend

For each day:

`daily_revenue[day] = Σ(payed amounts for that day)`

---

### 5. Daily Unpaid Trend

For each day:

`daily_unpaid[day] = Σ(debit amounts for that day)`

---

### 6. Clients involved

`clients = unique set of client_ids involved in qualifying interactions`

---

### Notes (implicit in equations):

* Only interactions linked to valid events (types `202`, `402`) inside the date window are counted
* Each interaction contributes:

  * **revenue → payed**
  * **unpaid → debit**
