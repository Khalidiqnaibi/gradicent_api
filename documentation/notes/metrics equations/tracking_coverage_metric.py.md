Here’s the formula for the **Tracking Coverage Metric**:

---

**Sections tracked:**

1. Clients added (`201`) → `has_clients`
2. Interactions added (`202`) → `has_interactions`
3. Payments / product purchases (`204` or `207`) → `has_payments`
4. Analytics viewed (`301`) → `has_analytics_shown`
5. User has products configured → `has_products`
6. User has services configured → `has_services`

---

**Equations:**

```
covered_sections = sum(has_clients, has_interactions, has_payments, has_analytics_shown, has_products, has_services)
total_sections = 6
coverage_percent = (covered_sections / total_sections) * 100
```

* `covered_sections` counts how many of the 6 sections are “true” (tracked).
* `coverage_percent` is the percentage of sections that are tracked.
