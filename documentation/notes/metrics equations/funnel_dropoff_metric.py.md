**funnel_dropoff**

---

### 1. Clients Added

`clients_added = count(events where type = 201 in date window)`

---

### 2. Interactions

`interactions = count(events where type = 202 in date window)`

---

### 3. Payments

`payments = count(payment events in window)`

Where a payment counts if:

`payment_amount > 0`

So:

`payments = count(events where type = 202 and payed > 0) + count(events where type ∈ [600,601,602,604] and amount > 0)`

---

### 4. Clients → Interactions conversion

`clients_to_interactions_pct = (interactions ÷ clients_added) × 100`

---

### 5. Interactions → Payments conversion

`interactions_to_payments_pct = (payments ÷ interactions) × 100`

---

### Funnel logic summary

```
clients_added → interactions → payments
```

And the dropoff is simply the conversion rate between each stage.
