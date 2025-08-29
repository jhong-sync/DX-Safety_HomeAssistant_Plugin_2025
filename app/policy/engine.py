from dataclasses import dataclass
from typing import Optional
from app.utils.geo import point_in_polygon, distance_km
from app.observability.logger import get_logger
log = get_logger()

@dataclass
class Decision:
    trigger: bool
    reason: str
    target_topic: str = ""

class PolicyEngine:
    def __init__(self, cfg):
        self.cfg = cfg
        self.severity_rank = {"minor":1, "moderate":2, "severe":3, "critical":4}

    def evaluate(self, cae: dict) -> Decision:
        sev_ok = self.severity_rank.get(cae["severity"], 2) >= self.severity_rank.get(self.cfg.policy.severity_threshold, 2)
        if not sev_ok:
            return Decision(False, "severity_below_threshold")
        lat, lon = self._resolve_location()
        in_area = False
        for area in cae.get("areas", []):
            g = area.get("geometry", {})
            t = g.get("type")
            coords = g.get("coordinates", [])
            if t == "Point":
                log.info({"msg": "point", "buffer": self.cfg.policy.radius_km_buffer, "home_lat": lat, "home_lon": lon, "eq_lat": coords[1], "eq_lon": coords[0], "distance": distance_km((lat, lon), (coords[1], coords[0]))})
                in_area = distance_km((lat, lon), (coords[1], coords[0])) <= self.cfg.policy.radius_km_buffer
            elif t == "Circle":
                in_area = distance_km((lat, lon), (coords[1], coords[0])) <= g.get("radius_km", 0) + self.cfg.policy.radius_km_buffer
            elif t == "Polygon":
                in_area = point_in_polygon(lon, lat, coords[0])  # coords[0] = outer ring [ [lon,lat], ... ]
            if in_area:
                break
        if not in_area:
            log.info({"msg": "outside_area", "cae": cae})
            return Decision(False, "outside_area")
        log.info({"msg": "policy_triggered", "cae": cae})
        return Decision(True, "ok", target_topic="alerts")

    def _resolve_location(self):
        # TODO: Supervisor API 통해 zone.home 좌표 조회 (백업: 옵션 lat/lon)
        # if self.cfg.policy.lat is not None and self.cfg.policy.lon is not None:
        #     return self.cfg.policy.lat, self.cfg.policy.lon
        # fallback 임시 좌표 (필히 실제 구현 교체)
        return 35.7234, 126.72134