from app.normalize.normalizer import Normalizer
import json

def test_cae_validation_ok():
    n = Normalizer()
    raw = json.dumps({
        "id": "E123",
        "sent": "2025-08-26T12:00:00Z",
        "headline": "지진 속보",
        "severity": "severe",
        "areas": [{"geometry": {"type": "Point", "coordinates": [126.9780, 37.5665]}}]
    }).encode("utf-8")
    cae = n.to_cae(raw)
    assert cae["eventId"] == "E123"