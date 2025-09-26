"""
Common 모듈 단위 테스트

이 모듈은 지리 유틸리티와 재시도 로직의 기능을 테스트합니다.
"""

import pytest
import asyncio
import math
import random
from unittest.mock import AsyncMock, Mock, patch
from app.common.geo import (
    haversine_distance, point_in_polygon, calculate_bounding_box,
    is_point_near_polygon, validate_coordinates
)
from app.common.retry import exponential_backoff, retry_with_backoff


class TestHaversineDistance:
    """Haversine 거리 계산 테스트"""
    
    def test_haversine_distance_same_point(self):
        """같은 지점 간 거리 테스트"""
        distance = haversine_distance(37.5665, 126.9780, 37.5665, 126.9780)
        assert distance == 0.0
    
    def test_haversine_distance_seoul_to_busan(self):
        """서울에서 부산까지 거리 테스트"""
        # 서울: 37.5665, 126.9780
        # 부산: 35.1796, 129.0756
        distance = haversine_distance(37.5665, 126.9780, 35.1796, 129.0756)
        
        # 실제 거리는 약 325km
        assert 320 <= distance <= 330
    
    def test_haversine_distance_seoul_to_incheon(self):
        """서울에서 인천까지 거리 테스트"""
        # 서울: 37.5665, 126.9780
        # 인천: 37.4563, 126.7052
        distance = haversine_distance(37.5665, 126.9780, 37.4563, 126.7052)
        
        # 실제 거리는 약 28km
        assert 25 <= distance <= 30
    
    def test_haversine_distance_equator(self):
        """적도상의 거리 테스트"""
        # 적도상의 두 지점 (경도만 다름)
        distance = haversine_distance(0, 0, 0, 1)
        
        # 1도는 약 111km
        assert 110 <= distance <= 112
    
    def test_haversine_distance_meridian(self):
        """자오선상의 거리 테스트"""
        # 자오선상의 두 지점 (위도만 다름)
        distance = haversine_distance(0, 0, 1, 0)
        
        # 1도는 약 111km
        assert 110 <= distance <= 112
    
    def test_haversine_distance_negative_coordinates(self):
        """음수 좌표 거리 테스트"""
        # 남반구의 두 지점
        distance = haversine_distance(-37.5665, -126.9780, -35.1796, -129.0756)
        
        # 거리가 양수여야 함
        assert distance > 0
    
    def test_haversine_distance_large_distance(self):
        """큰 거리 테스트"""
        # 지구 반대편의 두 지점
        distance = haversine_distance(0, 0, 0, 180)
        
        # 지구 둘레의 절반은 약 20,000km
        assert 19000 <= distance <= 21000
    
    def test_haversine_distance_precision(self):
        """정밀도 테스트"""
        # 매우 가까운 두 지점
        distance = haversine_distance(37.5665, 126.9780, 37.5666, 126.9781)
        
        # 거리가 매우 작아야 함
        assert 0 < distance < 0.1


class TestPointInPolygon:
    """점이 폴리곤 내부에 있는지 테스트"""
    
    @pytest.fixture
    def square_polygon(self):
        """정사각형 폴리곤"""
        return [
            (126.0, 37.0),  # 좌하
            (127.0, 37.0),  # 우하
            (127.0, 38.0),  # 우상
            (126.0, 38.0)   # 좌상
        ]
    
    def test_point_in_polygon_inside(self, square_polygon):
        """폴리곤 내부의 점 테스트"""
        point = (126.5, 37.5)  # 정사각형 중앙
        result = point_in_polygon(point, square_polygon)
        assert result is True
    
    def test_point_in_polygon_outside(self, square_polygon):
        """폴리곤 외부의 점 테스트"""
        point = (125.0, 37.5)  # 정사각형 왼쪽
        result = point_in_polygon(point, square_polygon)
        assert result is False
    
    def test_point_in_polygon_on_edge(self, square_polygon):
        """폴리곤 경계선상의 점 테스트"""
        point = (126.0, 37.5)  # 왼쪽 경계선
        result = point_in_polygon(point, square_polygon)
        assert result is True
    
    def test_point_in_polygon_on_vertex(self, square_polygon):
        """폴리곤 꼭짓점의 점 테스트"""
        point = (126.0, 37.0)  # 좌하 꼭짓점
        result = point_in_polygon(point, square_polygon)
        assert result is True
    
    def test_point_in_polygon_empty_polygon(self):
        """빈 폴리곤 테스트"""
        point = (126.5, 37.5)
        result = point_in_polygon(point, [])
        assert result is False
    
    def test_point_in_polygon_insufficient_points(self):
        """점이 부족한 폴리곤 테스트"""
        point = (126.5, 37.5)
        polygon = [(126.0, 37.0), (127.0, 37.0)]  # 2개 점만
        result = point_in_polygon(point, polygon)
        assert result is False
    
    def test_point_in_polygon_complex_polygon(self):
        """복잡한 폴리곤 테스트"""
        # L자 모양 폴리곤
        polygon = [
            (126.0, 37.0),  # 좌하
            (127.0, 37.0),  # 우하
            (127.0, 37.5),  # 우중
            (126.5, 37.5),  # 중중
            (126.5, 38.0),  # 중상
            (126.0, 38.0)   # 좌상
        ]
        
        # L자 내부
        point_inside = (126.2, 37.2)
        result_inside = point_in_polygon(point_inside, polygon)
        assert result_inside is True
        
        # L자 외부
        point_outside = (126.7, 37.7)
        result_outside = point_in_polygon(point_outside, polygon)
        assert result_outside is False


class TestCalculateBoundingBox:
    """경계 상자 계산 테스트"""
    
    def test_calculate_bounding_box_square(self):
        """정사각형 폴리곤의 경계 상자 테스트"""
        polygon = [
            (126.0, 37.0),  # 좌하
            (127.0, 37.0),  # 우하
            (127.0, 38.0),  # 우상
            (126.0, 38.0)   # 좌상
        ]
        
        min_lon, min_lat, max_lon, max_lat = calculate_bounding_box(polygon)
        
        assert min_lon == 126.0
        assert min_lat == 37.0
        assert max_lon == 127.0
        assert max_lat == 38.0
    
    def test_calculate_bounding_box_triangle(self):
        """삼각형 폴리곤의 경계 상자 테스트"""
        polygon = [
            (126.0, 37.0),  # 좌하
            (127.0, 37.0),  # 우하
            (126.5, 38.0)   # 상단
        ]
        
        min_lon, min_lat, max_lon, max_lat = calculate_bounding_box(polygon)
        
        assert min_lon == 126.0
        assert min_lat == 37.0
        assert max_lon == 127.0
        assert max_lat == 38.0
    
    def test_calculate_bounding_box_empty_polygon(self):
        """빈 폴리곤의 경계 상자 테스트"""
        min_lon, min_lat, max_lon, max_lat = calculate_bounding_box([])
        
        assert min_lon == 0
        assert min_lat == 0
        assert max_lon == 0
        assert max_lat == 0
    
    def test_calculate_bounding_box_single_point(self):
        """단일 점의 경계 상자 테스트"""
        polygon = [(126.5, 37.5)]
        
        min_lon, min_lat, max_lon, max_lat = calculate_bounding_box(polygon)
        
        assert min_lon == 126.5
        assert min_lat == 37.5
        assert max_lon == 126.5
        assert max_lat == 37.5
    
    def test_calculate_bounding_box_negative_coordinates(self):
        """음수 좌표의 경계 상자 테스트"""
        polygon = [
            (-127.0, -38.0),  # 좌하
            (-126.0, -38.0),  # 우하
            (-126.0, -37.0),  # 우상
            (-127.0, -37.0)   # 좌상
        ]
        
        min_lon, min_lat, max_lon, max_lat = calculate_bounding_box(polygon)
        
        assert min_lon == -127.0
        assert min_lat == -38.0
        assert max_lon == -126.0
        assert max_lat == -37.0


class TestIsPointNearPolygon:
    """점이 폴리곤 근처에 있는지 테스트"""
    
    @pytest.fixture
    def square_polygon(self):
        """정사각형 폴리곤"""
        return [
            (126.0, 37.0),  # 좌하
            (127.0, 37.0),  # 우하
            (127.0, 38.0),  # 우상
            (126.0, 38.0)   # 좌상
        ]
    
    def test_is_point_near_polygon_inside(self, square_polygon):
        """폴리곤 내부의 점 테스트"""
        point = (126.5, 37.5)  # 정사각형 중앙
        result = is_point_near_polygon(point, square_polygon, 1.0)
        assert result is True
    
    def test_is_point_near_polygon_outside_close(self, square_polygon):
        """폴리곤 외부이지만 가까운 점 테스트"""
        point = (125.9, 37.5)  # 정사각형 왼쪽 근처
        result = is_point_near_polygon(point, square_polygon, 10.0)  # 10km 버퍼
        assert result is True
    
    def test_is_point_near_polygon_outside_far(self, square_polygon):
        """폴리곤 외부이고 먼 점 테스트"""
        point = (125.0, 37.5)  # 정사각형 왼쪽 멀리
        result = is_point_near_polygon(point, square_polygon, 1.0)  # 1km 버퍼
        assert result is False
    
    def test_is_point_near_polygon_zero_buffer(self, square_polygon):
        """버퍼가 0인 경우 테스트"""
        point = (126.5, 37.5)  # 정사각형 중앙
        result = is_point_near_polygon(point, square_polygon, 0.0)
        assert result is True
        
        point = (125.0, 37.5)  # 정사각형 외부
        result = is_point_near_polygon(point, square_polygon, 0.0)
        assert result is False
    
    def test_is_point_near_polygon_large_buffer(self, square_polygon):
        """큰 버퍼 테스트"""
        point = (120.0, 30.0)  # 매우 먼 지점
        result = is_point_near_polygon(point, square_polygon, 1000.0)  # 1000km 버퍼
        assert result is True


class TestValidateCoordinates:
    """좌표 검증 테스트"""
    
    def test_validate_coordinates_valid(self):
        """유효한 좌표 테스트"""
        result = validate_coordinates(37.5665, 126.9780)
        assert result is True
    
    def test_validate_coordinates_invalid_latitude_high(self):
        """위도가 너무 높은 경우 테스트"""
        result = validate_coordinates(90.1, 126.9780)
        assert result is False
    
    def test_validate_coordinates_invalid_latitude_low(self):
        """위도가 너무 낮은 경우 테스트"""
        result = validate_coordinates(-90.1, 126.9780)
        assert result is False
    
    def test_validate_coordinates_invalid_longitude_high(self):
        """경도가 너무 높은 경우 테스트"""
        result = validate_coordinates(37.5665, 180.1)
        assert result is False
    
    def test_validate_coordinates_invalid_longitude_low(self):
        """경도가 너무 낮은 경우 테스트"""
        result = validate_coordinates(37.5665, -180.1)
        assert result is False
    
    def test_validate_coordinates_boundary_values(self):
        """경계값 테스트"""
        # 유효한 경계값
        assert validate_coordinates(90.0, 180.0) is True
        assert validate_coordinates(-90.0, -180.0) is True
        assert validate_coordinates(0.0, 0.0) is True
        
        # 무효한 경계값
        assert validate_coordinates(90.1, 180.0) is False
        assert validate_coordinates(90.0, 180.1) is False
        assert validate_coordinates(-90.1, -180.0) is False
        assert validate_coordinates(-90.0, -180.1) is False


class TestExponentialBackoff:
    """지수 백오프 테스트"""
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_first_attempt(self):
        """첫 번째 시도의 백오프 테스트"""
        start_time = asyncio.get_event_loop().time()
        
        await exponential_backoff(1, 1.0, 10.0)
        
        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time
        
        # 첫 번째 시도는 기본 지연 시간
        assert 0.9 <= elapsed <= 1.1
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_second_attempt(self):
        """두 번째 시도의 백오프 테스트"""
        start_time = asyncio.get_event_loop().time()
        
        await exponential_backoff(2, 1.0, 10.0)
        
        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time
        
        # 두 번째 시도는 2배 지연 시간
        assert 1.9 <= elapsed <= 2.1
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_third_attempt(self):
        """세 번째 시도의 백오프 테스트"""
        start_time = asyncio.get_event_loop().time()
        
        await exponential_backoff(3, 1.0, 10.0)
        
        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time
        
        # 세 번째 시도는 4배 지연 시간
        assert 3.9 <= elapsed <= 4.1
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_max_delay(self):
        """최대 지연 시간 테스트"""
        start_time = asyncio.get_event_loop().time()
        
        await exponential_backoff(10, 1.0, 5.0)  # 최대 지연 시간 5초
        
        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time
        
        # 최대 지연 시간을 초과하지 않아야 함
        assert 4.9 <= elapsed <= 5.1
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_zero_attempt(self):
        """0번째 시도의 백오프 테스트"""
        start_time = asyncio.get_event_loop().time()
        
        await exponential_backoff(0, 1.0, 10.0)
        
        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time
        
        # 0번째 시도는 기본 지연 시간
        assert 0.9 <= elapsed <= 1.1


class TestRetryWithBackoff:
    """백오프와 함께 재시도 테스트"""
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_first_attempt(self):
        """첫 번째 시도에서 성공 테스트"""
        call_count = 0
        
        async def mock_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await retry_with_backoff(mock_func, max_retries=3)
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_after_retries(self):
        """재시도 후 성공 테스트"""
        call_count = 0
        
        async def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return "success"
        
        result = await retry_with_backoff(mock_func, max_retries=3)
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_max_retries_exceeded(self):
        """최대 재시도 횟수 초과 테스트"""
        call_count = 0
        
        async def mock_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Permanent error")
        
        with pytest.raises(Exception, match="Permanent error"):
            await retry_with_backoff(mock_func, max_retries=2)
        
        assert call_count == 3  # 1번 시도 + 2번 재시도
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_custom_delays(self):
        """사용자 정의 지연 시간 테스트"""
        call_count = 0
        delays = []
        
        async def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return "success"
        
        # 지연 시간 모니터링을 위한 패치
        original_sleep = asyncio.sleep
        
        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0.01)  # 실제로는 짧게 대기
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            result = await retry_with_backoff(
                mock_func, 
                max_retries=3, 
                base_delay=0.5, 
                max_delay=5.0
            )
        
        assert result == "success"
        assert call_count == 3
        assert len(delays) == 2  # 2번의 재시도
        
        # 지연 시간이 지수적으로 증가하는지 확인
        assert delays[0] <= delays[1]
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_jitter(self):
        """지터 적용 테스트"""
        call_count = 0
        delays = []
        
        async def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary error")
            return "success"
        
        # 지연 시간 모니터링을 위한 패치
        original_sleep = asyncio.sleep
        
        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0.01)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            result = await retry_with_backoff(
                mock_func, 
                max_retries=3, 
                base_delay=1.0, 
                jitter=True
            )
        
        assert result == "success"
        assert len(delays) == 1
        
        # 지터가 적용되어 지연 시간이 변동되었는지 확인
        # 지터는 0.5 ~ 1.0 배 사이에서 랜덤하게 적용됨
        assert 0.5 <= delays[0] <= 1.0
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_no_jitter(self):
        """지터 미적용 테스트"""
        call_count = 0
        delays = []
        
        async def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary error")
            return "success"
        
        # 지연 시간 모니터링을 위한 패치
        original_sleep = asyncio.sleep
        
        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0.01)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            result = await retry_with_backoff(
                mock_func, 
                max_retries=3, 
                base_delay=1.0, 
                jitter=False
            )
        
        assert result == "success"
        assert len(delays) == 1
        
        # 지터가 적용되지 않아 정확한 지연 시간이 적용되었는지 확인
        assert delays[0] == 1.0
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_zero_max_retries(self):
        """최대 재시도 횟수가 0인 경우 테스트"""
        call_count = 0
        
        async def mock_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Error")
        
        with pytest.raises(Exception, match="Error"):
            await retry_with_backoff(mock_func, max_retries=0)
        
        assert call_count == 1  # 1번만 시도


class TestCommonIntegration:
    """Common 모듈 통합 테스트"""
    
    def test_geo_functions_integration(self):
        """지리 함수 통합 테스트"""
        # 서울 시청 좌표
        seoul_lat, seoul_lon = 37.5665, 126.9780
        
        # 부산 좌표
        busan_lat, busan_lon = 35.1796, 129.0756
        
        # 거리 계산
        distance = haversine_distance(seoul_lat, seoul_lon, busan_lat, busan_lon)
        assert distance > 0
        
        # 좌표 검증
        assert validate_coordinates(seoul_lat, seoul_lon) is True
        assert validate_coordinates(busan_lat, busan_lon) is True
        
        # 폴리곤 생성 (서울 근처)
        polygon = [
            (126.5, 37.5),
            (127.5, 37.5),
            (127.5, 38.5),
            (126.5, 38.5)
        ]
        
        # 점이 폴리곤 내부에 있는지 확인
        assert point_in_polygon((seoul_lon, seoul_lat), polygon) is True
        assert point_in_polygon((busan_lon, busan_lat), polygon) is False
        
        # 경계 상자 계산
        min_lon, min_lat, max_lon, max_lat = calculate_bounding_box(polygon)
        assert min_lon == 126.5
        assert min_lat == 37.5
        assert max_lon == 127.5
        assert max_lat == 38.5
        
        # 점이 폴리곤 근처에 있는지 확인
        assert is_point_near_polygon((seoul_lon, seoul_lat), polygon, 1.0) is True
        assert is_point_near_polygon((busan_lon, busan_lat), polygon, 1000.0) is True
    
    @pytest.mark.asyncio
    async def test_retry_functions_integration(self):
        """재시도 함수 통합 테스트"""
        call_count = 0
        
        async def unreliable_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "Success after retries"
        
        # 재시도 로직 테스트
        result = await retry_with_backoff(
            unreliable_func,
            max_retries=5,
            base_delay=0.1,
            max_delay=1.0,
            jitter=True
        )
        
        assert result == "Success after retries"
        assert call_count == 3
    
    def test_common_functions_error_handling(self):
        """Common 함수 에러 처리 테스트"""
        # 잘못된 좌표로 거리 계산
        with pytest.raises((ValueError, TypeError)):
            haversine_distance("invalid", "invalid", 37.5665, 126.9780)
        
        # 잘못된 폴리곤으로 점 검사
        result = point_in_polygon((126.5, 37.5), None)
        assert result is False
        
        # 잘못된 좌표 검증
        assert validate_coordinates("invalid", "invalid") is False
    
    def test_common_functions_performance(self):
        """Common 함수 성능 테스트"""
        import time
        
        # 대량의 거리 계산 성능 테스트
        start_time = time.time()
        
        for i in range(1000):
            haversine_distance(37.5665, 126.9780, 37.5665 + i * 0.001, 126.9780 + i * 0.001)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 성능 확인
        assert processing_time < 1.0  # 1초 이내에 완료되어야 함
        
        # 대량의 점-폴리곤 검사 성능 테스트
        polygon = [(126.0, 37.0), (127.0, 37.0), (127.0, 38.0), (126.0, 38.0)]
        
        start_time = time.time()
        
        for i in range(1000):
            point_in_polygon((126.5 + i * 0.001, 37.5 + i * 0.001), polygon)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 성능 확인
        assert processing_time < 1.0  # 1초 이내에 완료되어야 함
