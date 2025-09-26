"""
Features 모듈 단위 테스트

이 모듈은 대피소 네비게이션 기능을 테스트합니다.
"""

import pytest
import tempfile
import os
import csv
from unittest.mock import AsyncMock, Mock, patch, mock_open
from app.features.shelter_nav import (
    ShelterNavigator, load_shelters, find_nearest,
    build_naver_url, Shelter
)


class TestLoadShelters:
    """대피소 데이터 로드 테스트"""
    
    def test_load_shelters_csv(self):
        """CSV 파일에서 대피소 데이터 로드 테스트"""
        # 임시 CSV 파일 생성
        csv_content = """name,address,lat,lon
대피소1,서울시 강남구,37.5665,126.9780
대피소2,서울시 서초구,37.4947,127.0276
대피소3,서울시 송파구,37.5145,127.1050"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            # 대피소 데이터 로드
            shelters = load_shelters(temp_path)
            
            # 결과 확인
            assert len(shelters) == 3
            assert shelters[0]['name'] == '대피소1'
            assert shelters[0]['address'] == '서울시 강남구'
            assert shelters[0]['lat'] == 37.5665
            assert shelters[0]['lon'] == 126.9780
            
            assert shelters[1]['name'] == '대피소2'
            assert shelters[1]['lat'] == 37.4947
            assert shelters[1]['lon'] == 127.0276
            
            assert shelters[2]['name'] == '대피소3'
            assert shelters[2]['lat'] == 37.5145
            assert shelters[2]['lon'] == 127.1050
            
        finally:
            os.unlink(temp_path)
    
    def test_load_shelters_csv_without_address(self):
        """주소가 없는 CSV 파일에서 대피소 데이터 로드 테스트"""
        # 임시 CSV 파일 생성
        csv_content = """name,lat,lon
대피소1,37.5665,126.9780
대피소2,37.4947,127.0276"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            # 대피소 데이터 로드
            shelters = load_shelters(temp_path)
            
            # 결과 확인
            assert len(shelters) == 2
            assert shelters[0]['name'] == '대피소1'
            assert shelters[0]['address'] == ''  # 주소가 없으면 빈 문자열
            assert shelters[0]['lat'] == 37.5665
            assert shelters[0]['lon'] == 126.9780
            
        finally:
            os.unlink(temp_path)
    
    def test_load_shelters_xlsx(self):
        """Excel 파일에서 대피소 데이터 로드 테스트"""
        # Excel 파일 모킹
        mock_workbook = Mock()
        mock_worksheet = Mock()
        
        # 헤더 설정
        mock_headers = [
            "Facility Name",
            "Latitude (EPSG4326)",
            "Longitude (EPSG4326)",
            "Lot-based Full Address"
        ]
        mock_worksheet[1] = [Mock(value=header) for header in mock_headers]
        
        # 데이터 행 설정
        mock_rows = [
            ("대피소1", 37.5665, 126.9780, "서울시 강남구"),
            ("대피소2", 37.4947, 127.0276, "서울시 서초구"),
            ("대피소3", 37.5145, 127.1050, "서울시 송파구")
        ]
        
        def mock_iter_rows(min_row=2, values_only=True):
            for row_data in mock_rows:
                yield row_data
        
        mock_worksheet.iter_rows = mock_iter_rows
        mock_workbook.active = mock_worksheet
        
        with patch('openpyxl.load_workbook', return_value=mock_workbook):
            # 임시 파일 경로 생성
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
                temp_path = f.name
            
            try:
                # 대피소 데이터 로드
                shelters = load_shelters(temp_path)
                
                # 결과 확인
                assert len(shelters) == 3
                assert shelters[0]['name'] == '대피소1'
                assert shelters[0]['address'] == '서울시 강남구'
                assert shelters[0]['lat'] == 37.5665
                assert shelters[0]['lon'] == 126.9780
                
            finally:
                os.unlink(temp_path)
    
    def test_load_shelters_xlsx_missing_columns(self):
        """필수 컬럼이 없는 Excel 파일 테스트"""
        mock_workbook = Mock()
        mock_worksheet = Mock()
        
        # 필수 컬럼이 없는 헤더
        mock_headers = ["Name", "Lat", "Lon"]
        mock_worksheet[1] = [Mock(value=header) for header in mock_headers]
        
        mock_workbook.active = mock_worksheet
        
        with patch('openpyxl.load_workbook', return_value=mock_workbook):
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
                temp_path = f.name
            
            try:
                # 에러 발생 확인
                with pytest.raises(ValueError, match="시설명 컬럼을 찾을 수 없습니다"):
                    load_shelters(temp_path)
                    
            finally:
                os.unlink(temp_path)
    
    def test_load_shelters_xlsx_invalid_coordinates(self):
        """유효하지 않은 좌표가 있는 Excel 파일 테스트"""
        mock_workbook = Mock()
        mock_worksheet = Mock()
        
        # 헤더 설정
        mock_headers = [
            "Facility Name",
            "Latitude (EPSG4326)",
            "Longitude (EPSG4326)",
            "Lot-based Full Address"
        ]
        mock_worksheet[1] = [Mock(value=header) for header in mock_headers]
        
        # 유효하지 않은 좌표가 포함된 데이터
        mock_rows = [
            ("대피소1", 37.5665, 126.9780, "서울시 강남구"),  # 유효한 좌표
            ("대피소2", "", 127.0276, "서울시 서초구"),        # 빈 위도
            ("대피소3", 37.5145, "", "서울시 송파구"),        # 빈 경도
            ("대피소4", "invalid", 127.1050, "서울시 송파구"), # 잘못된 위도
            ("대피소5", 37.5145, "invalid", "서울시 송파구"),  # 잘못된 경도
            ("대피소6", 40.0, 140.0, "한국 밖"),              # 한국 지역 밖
            ("", 37.5145, 127.1050, "이름 없음"),             # 빈 이름
        ]
        
        def mock_iter_rows(min_row=2, values_only=True):
            for row_data in mock_rows:
                yield row_data
        
        mock_worksheet.iter_rows = mock_iter_rows
        mock_workbook.active = mock_worksheet
        
        with patch('openpyxl.load_workbook', return_value=mock_workbook):
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
                temp_path = f.name
            
            try:
                # 대피소 데이터 로드 (유효하지 않은 데이터는 건너뛰어야 함)
                shelters = load_shelters(temp_path)
                
                # 유효한 데이터만 로드되었는지 확인
                assert len(shelters) == 1
                assert shelters[0]['name'] == '대피소1'
                assert shelters[0]['lat'] == 37.5665
                assert shelters[0]['lon'] == 126.9780
                
            finally:
                os.unlink(temp_path)
    
    def test_load_shelters_unsupported_format(self):
        """지원하지 않는 파일 형식 테스트"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            # 에러 발생 확인
            with pytest.raises(ValueError, match="지원하지 않는 파일 형식"):
                load_shelters(temp_path)
                
        finally:
            os.unlink(temp_path)
    
    def test_load_shelters_file_not_found(self):
        """존재하지 않는 파일 테스트"""
        with pytest.raises(FileNotFoundError):
            load_shelters("nonexistent_file.csv")


class TestFindNearestShelter:
    """가장 가까운 대피소 찾기 테스트"""
    
    @pytest.fixture
    def sample_shelters(self):
        """테스트용 대피소 데이터"""
        return [
            {"name": "대피소1", "address": "서울시 강남구", "lat": 37.5665, "lon": 126.9780},
            {"name": "대피소2", "address": "서울시 서초구", "lat": 37.4947, "lon": 127.0276},
            {"name": "대피소3", "address": "서울시 송파구", "lat": 37.5145, "lon": 127.1050},
            {"name": "대피소4", "address": "서울시 마포구", "lat": 37.5663, "lon": 126.9779},
        ]
    
    def test_find_nearest_shelter(self, sample_shelters):
        """가장 가까운 대피소 찾기 테스트"""
        # 테스트 위치 (서울시청 근처)
        test_lat, test_lon = 37.5665, 126.9780
        
        # 가장 가까운 대피소 찾기
        nearest, distance = find_nearest(sample_shelters, test_lat, test_lon)
        
        # 결과 확인
        assert nearest is not None
        assert nearest['name'] == '대피소1'  # 가장 가까운 대피소
        assert nearest['lat'] == 37.5665
        assert nearest['lon'] == 126.9780
        assert distance >= 0  # 거리는 0 이상이어야 함
    
    def test_find_nearest_shelter_empty_list(self):
        """빈 대피소 목록에서 가장 가까운 대피소 찾기 테스트"""
        with pytest.raises(ValueError, match="대피소 데이터가 없습니다"):
            find_nearest([], 37.5665, 126.9780)
    
    def test_find_nearest_shelter_single_shelter(self):
        """대피소가 하나만 있을 때 테스트"""
        shelters = [{"name": "대피소1", "address": "서울시 강남구", "lat": 37.5665, "lon": 126.9780}]
        
        nearest, distance = find_nearest(shelters, 37.4947, 127.0276)
        
        # 결과 확인
        assert nearest is not None
        assert nearest['name'] == '대피소1'
        assert distance >= 0
    
    def test_find_nearest_shelter_distance_calculation(self, sample_shelters):
        """거리 계산 정확성 테스트"""
        # 테스트 위치
        test_lat, test_lon = 37.5000, 127.0000
        
        # 가장 가까운 대피소 찾기
        nearest, distance = find_nearest(sample_shelters, test_lat, test_lon)
        
        # 결과 확인
        assert nearest is not None
        # 테스트 위치에서 가장 가까운 대피소는 대피소2일 것으로 예상
        assert nearest['name'] == '대피소2'
        assert distance >= 0


class TestBuildNaverUrl:
    """네이버 지도 URL 생성 테스트"""
    
    def test_build_naver_url_basic(self):
        """기본 네이버 지도 URL 생성 테스트"""
        url = build_naver_url(37.5665, 126.9780, "대피소1", "test_app")
        
        # URL 확인
        assert "nmap://navigation" in url
        assert "dlat=37.566500" in url
        assert "dlng=126.978000" in url
        assert "dname=%EB%8C%80%ED%94%BC%EC%86%8C1" in url  # URL 인코딩된 "대피소1"
        assert "appname=test_app" in url
    
    def test_build_naver_url_with_special_characters(self):
        """특수문자가 포함된 이름으로 URL 생성 테스트"""
        url = build_naver_url(37.5665, 126.9780, "대피소 (특수)", "test_app")
        
        # URL 확인
        assert "nmap://navigation" in url
        assert "dlat=37.566500" in url
        assert "dlng=126.978000" in url
        assert "appname=test_app" in url
    
    def test_build_naver_url_coordinate_precision(self):
        """좌표 정밀도 테스트"""
        url = build_naver_url(37.123456789, 126.987654321, "정밀도테스트", "test_app")
        
        # URL 확인 - 소수점 6자리까지 표시
        assert "dlat=37.123457" in url
        assert "dlng=126.987654" in url


class TestShelterNavigator:
    """대피소 네비게이터 테스트"""
    
    @pytest.fixture
    def mock_ha_client(self):
        """테스트용 Home Assistant 클라이언트"""
        return AsyncMock()
    
    @pytest.fixture
    def sample_shelters(self):
        """테스트용 대피소 데이터"""
        return [
            {"name": "대피소1", "address": "서울시 강남구", "lat": 37.5665, "lon": 126.9780},
            {"name": "대피소2", "address": "서울시 서초구", "lat": 37.4947, "lon": 127.0276},
            {"name": "대피소3", "address": "서울시 송파구", "lat": 37.5145, "lon": 127.1050},
        ]
    
    def test_shelter_navigator_initialization(self, mock_ha_client):
        """대피소 네비게이터 초기화 테스트"""
        navigator = ShelterNavigator(
            ha=mock_ha_client,
            path="test_shelters.xlsx",
            appname="test_app"
        )
        
        assert navigator.ha == mock_ha_client
        assert navigator.path == "test_shelters.xlsx"
        assert navigator.appname == "test_app"
        assert navigator._shelters == []
    
    def test_shelter_navigator_load_data(self, mock_ha_client, sample_shelters):
        """대피소 데이터 로드 테스트"""
        navigator = ShelterNavigator(
            ha=mock_ha_client,
            path="test_shelters.xlsx",
            appname="test_app"
        )
        
        with patch('app.features.shelter_nav.load_shelters', return_value=sample_shelters) as mock_load:
            navigator.load()
            
            # 데이터가 로드되었는지 확인
            assert navigator._shelters == sample_shelters
            mock_load.assert_called_once_with("test_shelters.xlsx")
    
    def test_shelter_navigator_load_data_error(self, mock_ha_client):
        """대피소 데이터 로드 에러 테스트"""
        navigator = ShelterNavigator(
            ha=mock_ha_client,
            path="nonexistent_file.xlsx",
            appname="test_app"
        )
        
        with patch('app.features.shelter_nav.load_shelters', side_effect=FileNotFoundError("File not found")):
            with pytest.raises(FileNotFoundError):
                navigator.load_data()
    
    def test_shelter_navigator_find_nearest(self, mock_ha_client, sample_shelters):
        """가장 가까운 대피소 찾기 테스트"""
        navigator = ShelterNavigator(
            ha=mock_ha_client,
            path="test_shelters.xlsx",
            appname="test_app"
        )
        
        # 데이터 로드
        navigator.shelters = sample_shelters
        
        # 가장 가까운 대피소 찾기
        nearest = navigator.find_nearest(37.5665, 126.9780)
        
        # 결과 확인
        assert nearest is not None
        assert nearest['name'] == '대피소1'
    
    def test_shelter_navigator_find_nearest_empty_data(self, mock_ha_client):
        """데이터가 없을 때 가장 가까운 대피소 찾기 테스트"""
        navigator = ShelterNavigator(
            ha=mock_ha_client,
            path="test_shelters.xlsx",
            appname="test_app"
        )
        
        # 빈 데이터
        navigator.shelters = []
        
        # 가장 가까운 대피소 찾기
        nearest = navigator.find_nearest(37.5665, 126.9780)
        
        # 결과 확인
        assert nearest is None
    
    @pytest.mark.asyncio
    async def test_shelter_navigator_notify_all_devices(self, mock_ha_client, sample_shelters):
        """모든 디바이스에 알림 전송 테스트"""
        navigator = ShelterNavigator(
            ha=mock_ha_client,
            path="test_shelters.xlsx",
            appname="test_app"
        )
        
        # 데이터 로드
        navigator.shelters = sample_shelters
        
        # Home Assistant 클라이언트 모킹
        mock_ha_client.call_service = AsyncMock()
        
        # 알림 전송
        await navigator.notify_all_devices("test_group")
        
        # 서비스 호출 확인
        mock_ha_client.call_service.assert_called_once()
        
        # 호출된 매개변수 확인
        call_args = mock_ha_client.call_service.call_args
        assert call_args[0][0] == "notify"  # domain
        assert call_args[0][1] == "test_group"  # service
        
        service_data = call_args[0][2]
        assert "message" in service_data
        assert "title" in service_data
    
    @pytest.mark.asyncio
    async def test_shelter_navigator_notify_all_devices_no_group(self, mock_ha_client, sample_shelters):
        """그룹 없이 모든 디바이스에 알림 전송 테스트"""
        navigator = ShelterNavigator(
            ha=mock_ha_client,
            path="test_shelters.xlsx",
            appname="test_app"
        )
        
        # 데이터 로드
        navigator.shelters = sample_shelters
        
        # Home Assistant 클라이언트 모킹
        mock_ha_client.call_service = AsyncMock()
        
        # 알림 전송 (그룹 없음)
        await navigator.notify_all_devices()
        
        # 서비스 호출 확인
        mock_ha_client.call_service.assert_called_once()
        
        # 호출된 매개변수 확인
        call_args = mock_ha_client.call_service.call_args
        assert call_args[0][0] == "notify"  # domain
        assert call_args[0][1] == "mobile_app_test_app"  # 기본 서비스명
    
    @pytest.mark.asyncio
    async def test_shelter_navigator_notify_all_devices_error(self, mock_ha_client, sample_shelters):
        """알림 전송 에러 테스트"""
        navigator = ShelterNavigator(
            ha=mock_ha_client,
            path="test_shelters.xlsx",
            appname="test_app"
        )
        
        # 데이터 로드
        navigator.shelters = sample_shelters
        
        # Home Assistant 클라이언트 에러 모킹
        mock_ha_client.call_service.side_effect = Exception("Notification error")
        
        # 에러 발생 확인
        with pytest.raises(Exception, match="Notification error"):
            await navigator.notify_all_devices("test_group")
    
    def test_shelter_navigator_distance_calculation(self, mock_ha_client, sample_shelters):
        """거리 계산 테스트"""
        navigator = ShelterNavigator(
            ha=mock_ha_client,
            path="test_shelters.xlsx",
            appname="test_app"
        )
        
        # 데이터 로드
        navigator.shelters = sample_shelters
        
        # 거리 계산
        distance = navigator._calculate_distance(37.5665, 126.9780, 37.4947, 127.0276)
        
        # 거리가 계산되었는지 확인
        assert distance > 0
        assert isinstance(distance, float)
    
    def test_shelter_navigator_error_handling(self, mock_ha_client):
        """에러 처리 테스트"""
        navigator = ShelterNavigator(
            ha=mock_ha_client,
            path="test_shelters.xlsx",
            appname="test_app"
        )
        
        # 잘못된 경로로 데이터 로드 시도
        with patch('app.features.shelter_nav.load_shelters', side_effect=Exception("Load error")):
            with pytest.raises(Exception, match="Load error"):
                navigator.load_data()


class TestShelterNavigationIntegration:
    """대피소 네비게이션 통합 테스트"""
    
    @pytest.fixture
    def mock_ha_client(self):
        """테스트용 Home Assistant 클라이언트"""
        return AsyncMock()
    
    @pytest.fixture
    def sample_shelters(self):
        """테스트용 대피소 데이터"""
        return [
            {"name": "대피소1", "address": "서울시 강남구", "lat": 37.5665, "lon": 126.9780},
            {"name": "대피소2", "address": "서울시 서초구", "lat": 37.4947, "lon": 127.0276},
            {"name": "대피소3", "address": "서울시 송파구", "lat": 37.5145, "lon": 127.1050},
        ]
    
    @pytest.mark.asyncio
    async def test_shelter_navigation_integration(self, mock_ha_client, sample_shelters):
        """대피소 네비게이션 통합 테스트"""
        navigator = ShelterNavigator(
            ha=mock_ha_client,
            path="test_shelters.xlsx",
            appname="test_app"
        )
        
        # 데이터 로드
        with patch('app.features.shelter_nav.load_shelters', return_value=sample_shelters):
            navigator.load_data()
        
        # 가장 가까운 대피소 찾기
        nearest = navigator.find_nearest(37.5665, 126.9780)
        assert nearest is not None
        assert nearest['name'] == '대피소1'
        
        # 알림 전송
        mock_ha_client.call_service = AsyncMock()
        await navigator.notify_all_devices("test_group")
        
        # 서비스 호출 확인
        mock_ha_client.call_service.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shelter_navigation_integration_error_handling(self, mock_ha_client):
        """대피소 네비게이션 에러 처리 통합 테스트"""
        navigator = ShelterNavigator(
            ha=mock_ha_client,
            path="test_shelters.xlsx",
            appname="test_app"
        )
        
        # 데이터 로드 에러
        with patch('app.features.shelter_nav.load_shelters', side_effect=FileNotFoundError("File not found")):
            with pytest.raises(FileNotFoundError):
                navigator.load_data()
        
        # 빈 데이터로 초기화
        navigator.shelters = []
        
        # 가장 가까운 대피소 찾기 (데이터 없음)
        nearest = navigator.find_nearest(37.5665, 126.9780)
        assert nearest is None
        
        # 알림 전송 (데이터 없음)
        mock_ha_client.call_service = AsyncMock()
        await navigator.notify_all_devices("test_group")
        
        # 서비스가 호출되었는지 확인 (데이터가 없어도 알림은 전송됨)
        mock_ha_client.call_service.assert_called_once()
    
    def test_shelter_navigation_integration_performance(self, mock_ha_client):
        """대피소 네비게이션 성능 통합 테스트"""
        # 대량의 대피소 데이터 생성
        large_shelters = []
        for i in range(1000):
            large_shelters.append({
                "name": f"대피소{i}",
                "address": f"서울시 {i}구",
                "lat": 37.5 + (i % 100) * 0.001,
                "lon": 126.9 + (i % 100) * 0.001
            })
        
        navigator = ShelterNavigator(
            ha=mock_ha_client,
            path="test_shelters.xlsx",
            appname="test_app"
        )
        
        # 데이터 로드
        with patch('app.features.shelter_nav.load_shelters', return_value=large_shelters):
            navigator.load_data()
        
        # 성능 테스트
        import time
        start_time = time.time()
        
        # 여러 번 가장 가까운 대피소 찾기
        for i in range(100):
            nearest = navigator.find_nearest(37.5 + i * 0.001, 126.9 + i * 0.001)
            assert nearest is not None
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 성능 확인
        assert processing_time < 5.0  # 5초 이내에 완료되어야 함
