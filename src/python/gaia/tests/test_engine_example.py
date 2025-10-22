from gaia.adapters.dummy_adapter import DummyAdapter
from gaia.engine import GaiaEngine

def test_roi_basic():
    dummy_data = {
        "u": {
            "time_logs": [{"user":"u","timestamp":"2025-10-01T09:00:00Z","seconds":3600}],
            "analytics": [],
            "user_doc": {"plan":"starter", "patients":[]}
        }
    }
    adapter = DummyAdapter(dummy_data)
    eng = GaiaEngine(adapter, config={"default_avg_hourly": 50, "plan_price_map":{"starter": 10}})
    res = eng.compute("roi", "u", {"from":"2025-10-01","to":"2025-10-02"})
    assert "hours_saved" in res
    assert res["hours_saved"] == 1.0
