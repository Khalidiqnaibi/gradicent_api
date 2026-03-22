**revenue_per_product**

---

### 1. Aggregate Revenue by Product

* Using **product purchase events** (type 602 / 207) in the date window:

```
revenue_per_product[product_id] = sum(amount of all purchases of that product)
```

* **Fallback:** sum amounts from client transactions tagged with `product_id` in the date window.

---

### Final Equation:

```id="rpp8qk"
revenue_per_product[product_id] = Σ(amount of purchases for product_id in date window)
```
