**unpaid_customers**

---

An entity counts as unpaid if it has **at least one transaction** with:

* `paid = false`
* `amount > 0`

So:

`unpaid_customers = count(clients with at least one unpaid transaction)`

---

### Final equation summary

```text
business unpaid_customers = count(clients where any transaction has paid = false and amount > 0)
```
