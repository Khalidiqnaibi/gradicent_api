from ..binder import *

adapter = FirebaseCrudAdapter("drs")
binder = BinderMedical(adapter)
GAIA= GaiaEngine(binder)

binder.current_user = "google_id_123"

# Create a doctor account
binder.create({"google_id": "google_id_123", "name": "Dr. Aisha"})

# Add a patient
patient = binder.create_client({"name": "John Doe", "age": 45})

# Add a visit
binder.create_interaction(patient["id"], {"diagnosis": "Flu", "treatment": "Rest + fluids"})

# Update patient info
binder.update_client(patient["id"], {"location": "New York"})

# List visits
visits = binder.list(patient["id"])
