import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from pathlib import Path
from app.observability.logger import get_logger
from typing import Union

log = get_logger()

SCHEMA = json.loads((Path(__file__).parent / "cae_schema.json").read_text(encoding="utf-8"))

class Normalizer:
    def to_cae(self, raw: Union[bytes, str]) -> dict:
        # 공급자 포맷 → CAE로 매핑
        # raw가 bytes인지 str인지 확인하여 적절히 처리
        if isinstance(raw, bytes):
            obj = json.loads(raw.decode("utf-8"))
        elif isinstance(raw, str):
            obj = json.loads(raw)
        else:
            raise ValueError(f"Unsupported raw type: {type(raw)}. Expected bytes or str")
        
        # parameters 추출
        params = obj.get("parameters", {})
        
        # severity 매핑 (urgency + severity 조합)
        severity = self._map_severity(obj.get("urgency"), obj.get("severity"))
        
        # areas 생성 (위치 정보 기반)
        areas = self._create_areas(params)
        
        cae = {
            "eventId": obj.get("identifier"),  # 원본의 identifier 사용
            "sentAt": obj.get("sent"),  # 원본의 sent 사용
            "headline": self._get_headline(params),  # 다국어 지원
            "description": self._get_description(params),  # 다국어 지원
            "severity": severity,
            "expiresAt": self._calculate_expires_at(obj.get("sent")),  # 만료 시간 계산
            "areas": areas,
        }
        
        try:
            validate(instance=cae, schema=SCHEMA)
        except ValidationError as e:
            log.error(f"CAE schema validation failed: {e.message}")
            log.error(f"Generated CAE data: {cae}")
            raise ValueError(f"CAE schema validation failed: {e.message}")
        
        return cae
    
    def _map_severity(self, urgency: int, severity: int) -> str:
        """urgency와 severity를 조합하여 CAE severity로 매핑"""
        # urgency: 1=Immediate, 2=Expected, 3=Future, 4=Past
        # severity: 1=Minor, 2=Moderate, 3=Severe, 4=Extreme, 5=Unknown
        
        if severity == 5:  # Unknown
            return "moderate"
        elif severity == 4:  # Extreme
            return "critical"
        elif severity == 3:  # Severe
            return "severe"
        elif severity == 2:  # Moderate
            return "moderate"
        else:  # severity == 1 (Minor)
            return "minor"
    
    def _get_headline(self, params: dict) -> str:
        """다국어 헤드라인 추출 (한국어 우선)"""
        # 한국어 헤드라인이 있으면 사용
        if "headline" in params:
            return params["headline"]
        
        # 영어 헤드라인 사용
        if "headline.en" in params:
            return params["headline.en"]
        
        # 기본값
        return "지진 현장경보"
    
    def _get_description(self, params: dict) -> str:
        """다국어 설명 추출 (한국어 우선)"""
        # 한국어 설명이 있으면 사용
        if "description" in params:
            return params["description"]
        
        # 영어 설명 사용
        if "description.en" in params:
            return params["description.en"]
        
        # 기본값
        return "지진 현장경보가 발령되었습니다."
    
    def _create_areas(self, params: dict) -> list:
        """위치 정보를 기반으로 areas 생성"""
        areas = []
        
        # 관측소 위치 정보가 있으면 Point geometry 생성
        if "STALatitude" in params and "STALongitude" in params:
            try:
                lat = float(params["STALatitude"])
                lon = float(params["STALongitude"])
                
                area = {
                    "name": params.get("ObservationLocation", "관측소 위치"),
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]  # GeoJSON 형식: [경도, 위도]
                    }
                }
                areas.append(area)
            except (ValueError, TypeError):
                log.warning(f"Invalid coordinates: {params.get('STALatitude')}, {params.get('STALongitude')}")
        
        # circle 정보가 있으면 Circle geometry 생성
        if "circle" in params and params["circle"] != "undefined, undefined 1000":
            try:
                # circle 형식: "lat, lon radius" 파싱
                circle_parts = params["circle"].split()
                if len(circle_parts) >= 3:
                    lat = float(circle_parts[0])
                    lon = float(circle_parts[1])
                    radius = float(circle_parts[2])
                    
                    area = {
                        "name": "영향 반경",
                        "geometry": {
                            "type": "Circle",
                            "coordinates": [lon, lat],
                            "radius_km": radius
                        }
                    }
                    areas.append(area)
            except (ValueError, IndexError):
                log.warning(f"Invalid circle format: {params.get('circle')}")
        
        # areas가 비어있으면 기본 위치 생성
        if not areas:
            area = {
                "name": "전북 부안군 일대",
                "geometry": {
                    "type": "Point",
                    "coordinates": [126.72, 35.73]  # 기본 좌표
                }
            }
            areas.append(area)
        
        return areas
    
    def _calculate_expires_at(self, sent_time: str) -> str:
        """발송 시간으로부터 만료 시간 계산 (24시간 후)"""
        if not sent_time:
            return None
        
        try:
            from datetime import datetime, timedelta
            from dateutil import parser
            
            # ISO 8601 형식 파싱
            sent_dt = parser.parse(sent_time)
            expires_dt = sent_dt + timedelta(hours=24)
            
            return expires_dt.isoformat()
        except Exception as e:
            log.warning(f"Failed to calculate expires_at: {e}")
            return None