"""
Geographic utilities for DX-Safety.

This module provides geographic calculations including
distance calculation, point-in-polygon testing, and
coordinate transformations.
"""

import math
from typing import List, Tuple, Optional
from app.observability.logging_setup import get_logger

log = get_logger()

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    두 지점 간의 Haversine 거리를 계산합니다 (킬로미터).
    
    Args:
        lat1: 첫 번째 지점의 위도
        lon1: 첫 번째 지점의 경도
        lat2: 두 번째 지점의 위도
        lon2: 두 번째 지점의 경도
        
    Returns:
        두 지점 간의 거리 (킬로미터)
    """
    # 도를 라디안으로 변환
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # 위도와 경도의 차이
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine 공식
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    
    # 지구 반지름 (킬로미터)
    r = 6371
    
    return c * r

def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """
    점이 폴리곤 내부에 있는지 Ray casting 알고리즘으로 확인합니다.
    
    Args:
        point: 확인할 점 (경도, 위도)
        polygon: 폴리곤의 꼭짓점들 [(경도, 위도), ...]
        
    Returns:
        점이 폴리곤 내부에 있으면 True, 외부에 있으면 False
    """
    if len(polygon) < 3:
        return False
    
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside

def calculate_bounding_box(polygon: List[Tuple[float, float]]) -> Tuple[float, float, float, float]:
    """
    폴리곤의 경계 상자를 계산합니다.
    
    Args:
        polygon: 폴리곤의 꼭짓점들 [(경도, 위도), ...]
        
    Returns:
        (min_lon, min_lat, max_lon, max_lat)
    """
    if not polygon:
        return (0, 0, 0, 0)
    
    lons = [p[0] for p in polygon]
    lats = [p[1] for p in polygon]
    
    return (min(lons), min(lats), max(lons), max(lats))

def is_point_near_polygon(point: Tuple[float, float], 
                         polygon: List[Tuple[float, float]], 
                         buffer_km: float) -> bool:
    """
    점이 폴리곤 근처에 있는지 확인합니다 (버퍼 포함).
    
    Args:
        point: 확인할 점 (경도, 위도)
        polygon: 폴리곤의 꼭짓점들 [(경도, 위도), ...]
        buffer_km: 버퍼 거리 (킬로미터)
        
    Returns:
        점이 폴리곤 또는 버퍼 내부에 있으면 True
    """
    # 먼저 폴리곤 내부인지 확인
    if point_in_polygon(point, polygon):
        return True
    
    # 버퍼가 0이면 폴리곤 내부만 확인
    if buffer_km <= 0:
        return False
    
    # 각 꼭짓점까지의 거리 확인
    for vertex in polygon:
        distance = haversine_distance(point[1], point[0], vertex[1], vertex[0])
        if distance <= buffer_km:
            return True
    
    return False

def validate_coordinates(lat: float, lon: float) -> bool:
    """
    좌표가 유효한지 확인합니다.
    
    Args:
        lat: 위도
        lon: 경도
        
    Returns:
        좌표가 유효하면 True
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180
