from gaia.engine import GaiaEngine
from binder import BinderBusiness, FirebaseCrudAdapter

adapter = FirebaseCrudAdapter()
binder = BinderBusiness(adapter)
binder.set_current_user("user_123")

engine = GaiaEngine()

# Compute ROI metric
roi = engine.compute(binder, "roi", From="2025-01-01", To="2025-02-01", avg_hourly=60)
print(roi)

# Compute finance metric
finance = engine.compute(binder, "finance")
print(finance)

# List all available metrics
print(engine.list_available_metrics())
