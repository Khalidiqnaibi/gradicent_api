**LTV (Customer Lifetime Value)**

---

### 1. Average Transaction Value

`avg_transaction_value = total_paid_amount ÷ total_number_of_transactions`

Where:

* **total_paid_amount** = sum of all payment amounts in the date window
* **total_number_of_transactions** = sum of all purchases across all customers

---

### 2. Average Purchases per Customer

`avg_purchases_per_customer = total_number_of_transactions ÷ number_of_customers_with_purchases`

---

### 3. LTV Estimate

`ltv = avg_transaction_value × avg_purchases_per_customer`

---

### Notes:

* Primary calculation uses **payment events** (types 204, 207) in the date window
* Fallback: uses **client transaction records** if no payment events exist

**Final Equation:**

```
ltv = (Σ(amount of all payments) ÷ total transactions) × (total transactions ÷ number of customers with transactions)
```
