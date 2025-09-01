"""
Normalization functions for DX-Safety.

This module contains pure functions for converting raw provider payloads
into internal domain models.
"""

from typing import Any, Dict
from .models import CAE, Area, Geometry, Severity

def to_cae(raw: Dict[str, Any]) -> CAE:
    """
    원시 제공자 페이로드를 CAE 모델로 변환합니다.
    
    Args:
        raw: 원시 딕셔너리 데이터
        
    Returns:
        정규화된 CAE 모델
    """
    # 이벤트 ID 추출
    event_id = str(raw.get("id") or raw.get("eventId") or "")
    
    # 전송 시간 추출
    sent_at = str(raw.get("sentAt") or raw.get("sent_at") or "")
    
    # 심각도 매핑
    severity_map = {
        "minor": "minor",
        "moderate": "moderate", 
        "severe": "severe",
        "critical": "critical"
    }
    raw_severity = raw.get("severity", "moderate")
    severity = severity_map.get(raw_severity.lower(), "moderate")
    
    # 영역 정보 추출
    areas = []
    raw_areas = raw.get("areas", [])
    if isinstance(raw_areas, list):
        for area_data in raw_areas:
            if isinstance(area_data, dict):
                geom_data = area_data.get("geometry", {})
                if geom_data and isinstance(geom_data, dict):
                    geom_type = geom_data.get("type", "Point")
                    coords = geom_data.get("coordinates", [])
                    if coords:
                        geometry = Geometry(type=geom_type, coordinates=coords)
                        area = Area(
                            name=area_data.get("name"),
                            geometry=geometry
                        )
                        areas.append(area)
    
    return CAE(
        event_id=event_id,
        sent_at=sent_at,
        headline=raw.get("headline"),
        severity=severity,  # type: ignore[arg-type]
        description=raw.get("description"),
        areas=areas,
    )
