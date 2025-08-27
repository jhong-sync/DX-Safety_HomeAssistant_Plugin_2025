from app.policy.engine import PolicyEngine
from types import SimpleNamespace

def cfg():
    return SimpleNamespace(policy=SimpleNamespace(lat=37.5665, lon=126.9780, radius_km_buffer=2.0, severity_threshold="moderate"))

def test_policy_in_area():
    p = PolicyEngine(SimpleNamespace(policy=cfg().policy))
    cae = {"severity": "severe", "areas": [{"geometry": {"type": "Point", "coordinates": [126.9780, 37.5665]}}]}
    d = p.evaluate(cae)
    assert d.trigger