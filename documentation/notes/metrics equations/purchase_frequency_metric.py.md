**purchase_frequency (avg_purchases_per_customer)**

---

### 1. Count Purchases per Customer

* Using **payment events** (types 600, 601, 602, 604) in the date window:

`purchases_per_customer[customer_id] = count(payment events with amount > 0 for that customer)`

* **Fallback:** use client transaction records:

`purchases_per_customer[customer_id] = count(transactions with amount > 0 in date window)`

---

### 2. Average Purchases per Customer

`avg_purchases_per_customer = Σ(purchases_per_customer.values()) ÷ number_of_customers_with_purchases`

---

### Final Equation:

```id="m4w07b"
avg_purchases_per_customer = total number of purchases ÷ number of paying customers
```
