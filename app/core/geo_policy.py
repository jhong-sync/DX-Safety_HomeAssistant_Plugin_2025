"""
Geographic policy evaluation for DX-Safety.

This module implements geographic policy evaluation
combining severity thresholds with geographic proximity.
"""

from typing import List, Tuple, Optional
from app.core.models import CAE, Decision, Area
from app.common.geo import (
    haversine_distance, 
    point_in_polygon, 
    is_point_near_polygon,
    validate_coordinates
)
from app.observability.logging_setup import get_logger

log = get_logger()

# 심각도 순서 정의 (낮음 -> 높음)
SEVERITY_ORDER = {
    "minor": 0,
    "moderate": 1,
    "severe": 2,
    "critical": 3
}

def evaluate_geographic_policy(
    cae: CAE,
    home_coordinates: Optional[Tuple[float, float]] = None,
    *,
    severity_threshold: str = "moderate",
    distance_threshold_km: float = 5.0,
    polygon_buffer_km: float = 0.0,
    mode: str = "AND"
) -> Decision:
    """
    지리적 정책을 평가합니다.
    
    Args:
        cae: 평가할 CAE 모델
        home_coordinates: 홈 좌표 (위도, 경도)
        severity_threshold: 심각도 임계값
        distance_threshold_km: 거리 임계값 (킬로미터)
        polygon_buffer_km: 폴리곤 버퍼 (킬로미터)
        mode: 평가 모드 ("AND" 또는 "OR")
        
    Returns:
        정책 평가 결과
    """
    # 심각도 평가
    severity_trigger = SEVERITY_ORDER[cae.severity] >= SEVERITY_ORDER[severity_threshold]
    
    # 지리적 평가
    geographic_trigger = False
    geographic_reason = "no_geographic_check"
    
    if home_coordinates and validate_coordinates(*home_coordinates):
        home_lat, home_lon = home_coordinates
        
        # 각 영역에 대해 지리적 평가
        for area in cae.areas:
            if area.geometry.type == "Point":
                # Point 형상: 거리 기반 평가
                if len(area.geometry.coordinates) >= 2:
                    alert_lon, alert_lat = area.geometry.coordinates[0], area.geometry.coordinates[1]
                    
                    if validate_coordinates(alert_lat, alert_lon):
                        distance = haversine_distance(home_lat, home_lon, alert_lat, alert_lon)
                        if distance <= distance_threshold_km:
                            geographic_trigger = True
                            geographic_reason = f"distance({distance:.2f}km) <= threshold({distance_threshold_km}km)"
                            break
                            
            elif area.geometry.type == "Polygon":
                # Polygon 형상: 점-폴리곤 테스트
                if len(area.geometry.coordinates) > 0:
                    polygon = area.geometry.coordinates[0]  # 첫 번째 링
                    if len(polygon) >= 3:
                        # 홈 좌표를 (경도, 위도) 형식으로 변환
                        home_point = (home_lon, home_lat)
                        
                        if is_point_near_polygon(home_point, polygon, polygon_buffer_km):
                            geographic_trigger = True
                            geographic_reason = f"home_in_polygon_with_buffer({polygon_buffer_km}km)"
                            break
    
    # 모드에 따른 최종 평가
    if mode == "AND":
        final_trigger = severity_trigger and geographic_trigger
    else:  # "OR"
        final_trigger = severity_trigger or geographic_trigger
    
    # 이유 생성
    if final_trigger:
        if mode == "AND":
            reason = f"severity({cae.severity}) >= threshold({severity_threshold}) AND {geographic_reason}"
        else:
            reason = f"severity({cae.severity}) >= threshold({severity_threshold}) OR {geographic_reason}"
    else:
        if not severity_trigger and not geographic_trigger:
            reason = f"severity({cae.severity}) < threshold({severity_threshold}) AND no_geographic_match"
        elif not severity_trigger:
            reason = f"severity({cae.severity}) < threshold({severity_threshold})"
        else:
            reason = f"no_geographic_match: {geographic_reason}"
    
    # 레벨 설정
    level = cae.severity
    
    log.debug("지리적 정책 평가 완료",
              event_id=cae.event_id,
              severity=cae.severity,
              severity_trigger=severity_trigger,
              geographic_trigger=geographic_trigger,
              final_trigger=final_trigger,
              mode=mode)
    
    return Decision(
        trigger=final_trigger,
        reason=reason,
        level=level
    )

def evaluate_simple_policy(
    cae: CAE,
    *,
    severity_threshold: str = "moderate"
) -> Decision:
    """
    단순 심각도 기반 정책을 평가합니다 (지리적 고려 없음).
    
    Args:
        cae: 평가할 CAE 모델
        severity_threshold: 심각도 임계값
        
    Returns:
        정책 평가 결과
    """
    # 심각도 비교
    trigger = SEVERITY_ORDER[cae.severity] >= SEVERITY_ORDER[severity_threshold]
    
    # 이유 생성
    reason = f"severity({cae.severity}) >= threshold({severity_threshold})" if trigger else "below threshold"
    
    # 레벨 설정
    level = cae.severity
    
    return Decision(
        trigger=trigger,
        reason=reason,
        level=level
    )
