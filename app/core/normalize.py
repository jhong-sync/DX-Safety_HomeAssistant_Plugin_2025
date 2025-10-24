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
    
    # 기본값 설정
    headline = raw.get("headline")
    description = raw.get("description")
    raw_severity = raw.get("severity", "moderate")
    areas = []
    
    # info 배열에서 지진 데이터 추출 (새로운 구조)
    info_array = raw.get("info", [])
    if isinstance(info_array, list) and len(info_array) > 0:
        info = info_array[0]  # 첫 번째 info 객체 사용
        
        # 심각도 추출 (info 배열에서 우선)
        if "severity" in info:
            raw_severity = info.get("severity", raw_severity)
        
        # 헤드라인과 설명 추출 (info 배열에서 우선)
        headline = info.get("headline") or headline
        description = info.get("description") or description
        
        # 좌표 정보 추출 (Latitude, Longitude 필드)
        lat_str = info.get("Latitude")
        lon_str = info.get("Longitude")
        
        if lat_str is not None and lon_str is not None:
            try:
                # 좌표를 float로 변환
                lat = float(lat_str)
                lon = float(lon_str)
                # Point 지오메트리 생성 (경도, 위도 순서)
                geometry = Geometry(type="Point", coordinates=[lon, lat])
                
                # 위치 정보 추출 (다국어 지원)
                location_info = (info.get("Location") or 
                               info.get("Location.en") or 
                               info.get("Location.zh") or 
                               info.get("Location.ja"))
                
                area_name = location_info if location_info else f"지진 발생지 ({lat}, {lon})"
                area = Area(name=area_name, geometry=geometry)
                areas.append(area)
                log.info(f"지진 좌표 추출됨: lat={lat}, lon={lon}, area_name={area_name}")
            except (ValueError, TypeError) as e:
                # 좌표 변환 실패 시 로그 기록
                log.error(f"지진 좌표 변환 실패: Latitude={lat_str}, Longitude={lon_str}, error={e}")
        
        # area 배열에서 추가 영역 정보 추출
        raw_areas = info.get("area", [])
        if isinstance(raw_areas, list):
            for area_data in raw_areas:
                if isinstance(area_data, dict):
                    area_desc = area_data.get("areaDesc")
                    if area_desc and not areas:  # 좌표가 없는 경우에만 사용
                        geometry = Geometry(type="Point", coordinates=[0, 0])  # 기본값
                        area = Area(name=area_desc, geometry=geometry)
                        areas.append(area)
    
    # 기존 영역 정보 추출 (하위 호환성)
    raw_areas = raw.get("areas", [])
    if isinstance(raw_areas, list) and not areas:  # info에서 추출한 영역이 없는 경우에만
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
    
    # parameters 필드에서 추가 정보 추출 시도 (하위 호환성)
    parameters = raw.get("parameters", {})
    if isinstance(parameters, dict) and not areas:
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
        elif location_info:
            # 기존 로직: 위치 정보만 있고 좌표가 없는 경우
            geometry = Geometry(type="Point", coordinates=[0, 0])  # 기본값
            area = Area(name=location_info, geometry=geometry)
            areas.append(area)
    
    # 숫자인 경우 직접 매핑, 문자열인 경우 소문자 변환 후 매핑
    if isinstance(raw_severity, int):
        severity = severity_map.get(raw_severity, "moderate")
    else:
        severity = severity_map.get(str(raw_severity).lower(), "moderate")
    
    return CAE(
        event_id=event_id,
        sent_at=sent_at,
        headline=headline,
        severity=severity,  # type: ignore[arg-type]
        description=description,
        areas=areas,
    )
