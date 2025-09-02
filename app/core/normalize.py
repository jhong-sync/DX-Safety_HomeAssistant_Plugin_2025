"""
Normalization functions for DX-Safety.

This module contains pure functions for converting raw provider payloads
into internal domain models.
"""

from typing import Any, Dict
from .models import CAE, Area, Geometry, Severity
from app.observability.logging_setup import get_logger

log = get_logger("dxsafety.normalize")

def to_cae(raw: Dict[str, Any]) -> CAE:
    """
    원시 제공자 페이로드를 CAE 모델로 변환합니다.
    
    Args:
        raw: 원시 딕셔너리 데이터
        
    Returns:
        정규화된 CAE 모델
    """
    # 이벤트 ID 추출 (identifier 필드도 확인)
    event_id = str(raw.get("id") or raw.get("eventId") or raw.get("identifier") or "")
    
    # 전송 시간 추출 (sent 필드도 확인)
    sent_at = str(raw.get("sentAt") or raw.get("sent_at") or raw.get("sent") or "")
    
    # 심각도 매핑 (숫자와 문자열 모두 처리)
    severity_map = {
        "minor": "minor",
        "moderate": "moderate", 
        "severe": "severe",
        "critical": "critical",
        # 숫자 심각도 매핑
        1: "minor",
        2: "minor", 
        3: "moderate",
        4: "severe",
        5: "critical"
    }
    raw_severity = raw.get("severity", "moderate")
    
    # 숫자인 경우 직접 매핑, 문자열인 경우 소문자 변환 후 매핑
    if isinstance(raw_severity, int):
        severity = severity_map.get(raw_severity, "moderate")
    else:
        severity = severity_map.get(str(raw_severity).lower(), "moderate")
    
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
    
    # parameters 필드에서 추가 정보 추출 시도
    parameters = raw.get("parameters", {})
    if isinstance(parameters, dict):
        # parameters에서 위치 정보 추출
        location_info = parameters.get("Location.en") or parameters.get("Location.zh") or parameters.get("Location.ja")
        
        # STALatitude, STALongitude 값 추출
        sta_lat = parameters.get("STALatitude")
        sta_lon = parameters.get("STALongitude")
        
        if sta_lat is not None and sta_lon is not None:
            try:
                # 좌표를 float로 변환
                lat = float(sta_lat)
                lon = float(sta_lon)
                # Point 지오메트리 생성 (경도, 위도 순서)
                geometry = Geometry(type="Point", coordinates=[lon, lat])
                area_name = location_info if location_info else f"Alert Area ({lat}, {lon})"
                area = Area(name=area_name, geometry=geometry)
                areas.append(area)
                log.info(f"CAP 좌표 추출됨: lat={lat}, lon={lon}, area_name={area_name}")
            except (ValueError, TypeError) as e:
                # 좌표 변환 실패 시 로그 기록
                log.error(f"좌표 변환 실패: STALatitude={sta_lat}, STALongitude={sta_lon}, error={e}")
        elif location_info and not areas:
            # 기존 로직: 위치 정보만 있고 좌표가 없는 경우
            geometry = Geometry(type="Point", coordinates=[0, 0])  # 기본값
            area = Area(name=location_info, geometry=geometry)
            areas.append(area)
    
    return CAE(
        event_id=event_id,
        sent_at=sent_at,
        headline=raw.get("headline"),
        severity=severity,  # type: ignore[arg-type]
        description=raw.get("description"),
        areas=areas,
    )
