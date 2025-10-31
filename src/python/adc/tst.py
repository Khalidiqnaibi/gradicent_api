# simple wiring example (dev)
from ..binder.adapters.inmemory_adapter import InMemoryAdapter
from ..binder.binder_business import BinderBusiness
from ..binder.gaia.gaia_engine import GaiaEngine

adapter = InMemoryAdapter()
binder = BinderBusiness(adapter)
binder.create_user({"id": "company_1", "name": "Acme", "email": "a@acme.com"})
binder.current_user = "company_1"

# create client
c = binder.create_client({"id": "client_1", "name": "John Doe"})
# add transaction
t = binder.create_transaction("client_1", {"id": "txn_1", "amount": 300.0, "method": "card"})
# add interaction with time_saved metadata (for ROI)
binder.create_interaction("client_1", {"id": "i1", "type": "onboarding", "metadata": {"time_saved_hours": 2}})

# analytics
gaia = GaiaEngine(binder, config={"default_avg_hourly": 60, "plan_price_map":{"default": 100}})
print(gaia.finance())
print(gaia.roi())
