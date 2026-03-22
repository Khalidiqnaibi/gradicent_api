**interaction_to_sale_rate (conversion_percent)**

---

### 1. Interactions

`interactions = count(events where type = 202 in date window)`

---

### 2. Paid Interactions

`paid_interactions = count(events where type = 202 AND payed > 0)`

---

### 3. Conversion Rate

`conversion_percent = (paid_interactions ÷ interactions) × 100`

---

### Final equation:

`interaction_to_sale_rate = (count(paid interactions) ÷ count(all interactions)) × 100`
