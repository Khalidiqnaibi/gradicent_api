**matched_entities**

---

### 1. New Entities

`new_entities = set of entities with creation events (type 201) in date window)`

---

### 2. Returning Entities

`returning_entities = set of entities with interaction/update events (type 202) in date window)`

---

### 3. Total Matched Entities

`touched_entities = new_entities ∪ returning_entities`

* Only entities linked to events in the date window are considered
* The final matched entities list can be further filtered by date of visit/interaction (`visit_date` for medical, `interaction_date` for other domains)

---

### Classification:

* **New** → entities with creation events (201)
* **Returning** → entities with interaction events (202)

---

### Summary Equation:

```
matched_entities = all entities in touched_entities
new_entities = entities with type 201 events
returning_entities = entities with type 202 events
```
