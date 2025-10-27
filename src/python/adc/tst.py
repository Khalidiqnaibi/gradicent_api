from gaia.adapters.firebase_crud_adapter import FirebaseCrudAdapter
from binders.medical_binder import MedicalBinder
from binders.business_binder import BusinessBinder

firebase_adapter = FirebaseCrudAdapter()
medical_binder = MedicalBinder(adapter=firebase_adapter)
business_binder = BusinessBinder(adapter=firebase_adapter)

# Set active user (from session)
medical_binder.current_user = session.get("google_id")

# Add new patient
new_patient = medical_binder.add_client({"name": "John Doe", "age": 32})

# Add new visit
visit = medical_binder.add_interaction(new_patient["id"], {
    "diagnosis": "Flu",
    "visit_date": "2025-10-27"
})

# Update patient info
medical_binder.update_client(new_patient["id"], {"location": "New York"})
