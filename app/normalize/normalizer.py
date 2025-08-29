import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from pathlib import Path

SCHEMA = json.loads((Path(__file__).parent / "cae_schema.json").read_text(encoding="utf-8"))

class Normalizer:
    def to_cae(self, raw: bytes) -> dict:
        # 공급자 포맷 → CAE로 매핑 (여기서는 이미 유사 구조라고 가정; 필요시 매핑 로직 추가)
        obj = json.loads(raw.decode("utf-8"))
        logging.info({"msg": "raw_input", "data": obj})
        cae = {
            "eventId": obj.get("id") or obj.get("eventId"),
            "sentAt": obj.get("sent") or obj.get("sentAt"),
            "headline": obj.get("headline", ""),
            "description": obj.get("description", ""),
            "severity": obj.get("severity", "moderate"),
            "expiresAt": obj.get("expiresAt"),
            "areas": obj.get("areas", []),
        }
        try:
            validate(instance=cae, schema=SCHEMA)
        except ValidationError as e:
            raise ValueError(f"CAE schema validation failed: {e.message}")
        return cae