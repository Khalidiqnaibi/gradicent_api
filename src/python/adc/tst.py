from gaia.adapters.firebase_crud_adapter import FirebaseCrudAdapter
from gaia.engine import GaiaEngine
from ..binder.binder_business import BinderBusiness

firebase = FirebaseCrudAdapter()
engine = GaiaEngine(adapter=firebase, config={})
binder = BinderBusiness(adapter=firebase, gaia_engine=engine)

binder.current_user = "google_id_123"

# Add client
client = binder.create_client({"name": "Acme Inc."})

# Update client info
binder.update_client(client["id"], {"location": "New York"})

# Add product and service
binder.create_product({"name": "Widget", "price": 150.0})
binder.create_service({"name": "Consultation", "hourly_rate": 75.0})

# Add employee
employee = binder.create_employee({"name": "Aisha", "role": "Manager"})

# Create interaction and transaction
binder.create_interaction(client["id"], {"type": "meeting", "note": "Quarterly review"})
binder.create_transaction(client["id"], {"amount": 300.0, "method": "credit"})

# Read, update, delete examples
binder.read_client(client["id"])
binder.update_employee(employee["id"], {"role": "Director"})
binder.delete_transaction(client["id"], "txn_123")
