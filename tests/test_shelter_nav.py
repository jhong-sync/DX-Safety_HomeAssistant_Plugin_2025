"""
대피소 네비게이션 기능 테스트

이 테스트는 다음 기능들을 검증합니다:
1. 대피소 데이터 로드 (Excel/CSV)
2. 최근접 대피소 계산
3. 네이버 지도 URL 생성
4. Home Assistant API 연동
5. 푸시 알림 발송
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from app.features.shelter_nav import (
    load_shelters, 
    build_naver_url, 
    find_nearest, 
    ShelterNavigator
)
from app.adapters.homeassistant.client import HAClient

class TestShelterNavigation:
    """대피소 네비게이션 테스트 클래스"""
    
    @pytest.fixture
    def sample_shelters(self):
        """테스트용 대피소 데이터"""
        return [
            {"name": "서울시민대피소", "address": "서울특별시 중구 세종대로 110", "lat": 37.5665, "lon": 126.9780},
            {"name": "강남구대피소", "address": "서울특별시 강남구 테헤란로 152", "lat": 37.5172, "lon": 127.0473},
            {"name": "마포구대피소", "address": "서울특별시 마포구 와우산로 94", "lat": 37.5572, "lon": 126.9236},
            {"name": "용산구대피소", "address": "서울특별시 용산구 한강대로 257", "lat": 37.5320, "lon": 126.9903},
            {"name": "성동구대피소", "address": "서울특별시 성동구 왕십리로 83", "lat": 37.5507, "lon": 127.0409},
        ]
    
    @pytest.fixture
    def sample_devices(self):
        """테스트용 디바이스 데이터"""
        return [
            {
                "entity_id": "device_tracker.iphone_12",
                "name": "iPhone 12",
                "lat": 37.5665,
                "lon": 126.9780
            },
            {
                "entity_id": "device_tracker.samsung_galaxy",
                "name": "Samsung Galaxy",
                "lat": 37.5172,
                "lon": 127.0473
            }
        ]
    
    def test_build_naver_url(self):
        """네이버 지도 URL 생성 테스트"""
        url = build_naver_url(37.5665, 126.9780, "서울시민대피소", "com.synctechno.dxsafety")
        expected = "nmap://navigation?dlat=37.566500&dlng=126.978000&dname=%EC%84%9C%EC%9A%B8%EC%8B%9C%EB%AF%BC%EB%8C%80%ED%94%BC%EC%86%8C&appname=com.synctechno.dxsafety"
        assert url == expected
    
    def test_find_nearest(self, sample_shelters):
        """최근접 대피소 찾기 테스트"""
        # 강남역 근처에서 테스트
        lat, lon = 37.5172, 127.0473
        nearest, distance = find_nearest(lat, lon, sample_shelters)
        
        assert nearest["name"] == "강남구대피소"
        assert distance < 1.0  # 1km 이내
        
        # 마포역 근처에서 테스트
        lat, lon = 37.5572, 126.9236
        nearest, distance = find_nearest(lat, lon, sample_shelters)
        
        assert nearest["name"] == "마포구대피소"
        assert distance < 1.0  # 1km 이내
    
    def test_find_nearest_empty_list(self):
        """빈 대피소 목록에서 최근접 찾기 테스트"""
        with pytest.raises(ValueError, match="대피소 데이터가 없습니다"):
            find_nearest(37.5665, 126.9780, [])
    
    @pytest.mark.asyncio
    async def test_shelter_navigator_init(self):
        """ShelterNavigator 초기화 테스트"""
        mock_ha = MagicMock()
        nav = ShelterNavigator(mock_ha, "/test/path.xlsx", "com.test.app")
        
        assert nav.ha == mock_ha
        assert nav.path == "/test/path.xlsx"
        assert nav.appname == "com.test.app"
        assert nav._shelters == []
    
    @pytest.mark.asyncio
    async def test_shelter_navigator_load(self, sample_shelters):
        """대피소 데이터 로드 테스트"""
        mock_ha = MagicMock()
        nav = ShelterNavigator(mock_ha, "/test/path.xlsx", "com.test.app")
        
        # load_shelters 함수를 모킹
        with patch('app.features.shelter_nav.load_shelters', return_value=sample_shelters):
            nav.load()
            assert nav._shelters == sample_shelters
    
    @pytest.mark.asyncio
    async def test_shelter_navigator_notify_all_devices(self, sample_shelters, sample_devices):
        """모든 디바이스에 알림 발송 테스트"""
        mock_ha = MagicMock()
        mock_ha.list_notify_mobile_services = AsyncMock(return_value=["mobile_app_iphone_12", "mobile_app_samsung_galaxy"])
        mock_ha.get_device_trackers = AsyncMock(return_value=sample_devices)
        mock_ha.notify = AsyncMock()
        
        nav = ShelterNavigator(mock_ha, "/test/path.xlsx", "com.test.app")
        nav._shelters = sample_shelters
        
        await nav.notify_all_devices()
        
        # 각 디바이스에 대해 notify가 호출되었는지 확인
        assert mock_ha.notify.call_count == 2
        
        # 첫 번째 호출 확인 (iPhone 12)
        first_call = mock_ha.notify.call_args_list[0]
        assert first_call[0][0] == "mobile_app_iphone_12"  # service
        assert first_call[0][1] == "가까운 대피소 안내"  # title
        assert "서울시민대피소" in first_call[0][2]  # message
        assert "nmap://navigation" in first_call[0][3]  # url
        
        # 두 번째 호출 확인 (Samsung Galaxy)
        second_call = mock_ha.notify.call_args_list[1]
        assert second_call[0][0] == "mobile_app_samsung_galaxy"  # service
        assert second_call[0][1] == "가까운 대피소 안내"  # title
        assert "강남구대피소" in second_call[0][2]  # message
        assert "nmap://navigation" in second_call[0][3]  # url
    
    @pytest.mark.asyncio
    async def test_shelter_navigator_notify_with_group(self, sample_shelters, sample_devices):
        """notify_group을 사용한 알림 발송 테스트"""
        mock_ha = MagicMock()
        mock_ha.list_notify_mobile_services = AsyncMock(return_value=[])
        mock_ha.get_device_trackers = AsyncMock(return_value=sample_devices)
        mock_ha.notify = AsyncMock()
        
        nav = ShelterNavigator(mock_ha, "/test/path.xlsx", "com.test.app")
        nav._shelters = sample_shelters
        
        await nav.notify_all_devices(notify_group="notify_all")
        
        # notify_group이 사용되었는지 확인
        assert mock_ha.notify.call_count == 2
        for call in mock_ha.notify.call_args_list:
            assert call[0][0] == "notify_all"  # service
    
    @pytest.mark.asyncio
    async def test_shelter_navigator_no_services(self, sample_shelters, sample_devices):
        """알림 서비스가 없을 때 테스트"""
        mock_ha = MagicMock()
        mock_ha.list_notify_mobile_services = AsyncMock(return_value=[])
        mock_ha.get_device_trackers = AsyncMock(return_value=sample_devices)
        mock_ha.notify = AsyncMock()
        
        nav = ShelterNavigator(mock_ha, "/test/path.xlsx", "com.test.app")
        nav._shelters = sample_shelters
        
        await nav.notify_all_devices()
        
        # notify가 호출되지 않았는지 확인
        mock_ha.notify.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_shelter_navigator_no_devices(self, sample_shelters):
        """디바이스가 없을 때 테스트"""
        mock_ha = MagicMock()
        mock_ha.list_notify_mobile_services = AsyncMock(return_value=["mobile_app_test"])
        mock_ha.get_device_trackers = AsyncMock(return_value=[])
        mock_ha.notify = AsyncMock()
        
        nav = ShelterNavigator(mock_ha, "/test/path.xlsx", "com.test.app")
        nav._shelters = sample_shelters
        
        await nav.notify_all_devices()
        
        # notify가 호출되지 않았는지 확인
        mock_ha.notify.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_shelter_navigator_notify_error_handling(self, sample_shelters, sample_devices):
        """알림 발송 오류 처리 테스트"""
        mock_ha = MagicMock()
        mock_ha.list_notify_mobile_services = AsyncMock(return_value=["mobile_app_iphone_12", "mobile_app_samsung_galaxy"])
        mock_ha.get_device_trackers = AsyncMock(return_value=sample_devices)
        mock_ha.notify = AsyncMock(side_effect=Exception("Network error"))
        
        nav = ShelterNavigator(mock_ha, "/test/path.xlsx", "com.test.app")
        nav._shelters = sample_shelters
        
        # 오류가 발생해도 계속 진행되는지 확인
        await nav.notify_all_devices()
        
        # notify가 호출되었는지 확인 (오류가 발생했지만 계속 진행)
        assert mock_ha.notify.call_count == 2

class TestShelterDataLoading:
    """대피소 데이터 로드 테스트"""
    
    def test_load_shelters_csv(self):
        """CSV 파일 로드 테스트"""
        csv_content = """name,address,lat,lon
서울시민대피소,서울특별시 중구 세종대로 110,37.5665,126.9780
강남구대피소,서울특별시 강남구 테헤란로 152,37.5172,127.0473"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            shelters = load_shelters(temp_path)
            assert len(shelters) == 2
            assert shelters[0]["name"] == "서울시민대피소"
            assert shelters[0]["lat"] == 37.5665
            assert shelters[0]["lon"] == 126.9780
            assert shelters[1]["name"] == "강남구대피소"
        finally:
            os.unlink(temp_path)
    
    def test_load_shelters_invalid_format(self):
        """지원하지 않는 파일 형식 테스트"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"test")
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="지원하지 않는 파일 형식"):
                load_shelters(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_load_shelters_missing_file(self):
        """존재하지 않는 파일 테스트"""
        with pytest.raises(FileNotFoundError):
            load_shelters("/nonexistent/file.xlsx")

class TestIntegration:
    """통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_full_shelter_navigation_flow(self):
        """전체 대피소 네비게이션 플로우 테스트"""
        # 테스트 데이터
        shelters = [
            {"name": "서울시민대피소", "address": "서울특별시 중구 세종대로 110", "lat": 37.5665, "lon": 126.9780},
            {"name": "강남구대피소", "address": "서울특별시 강남구 테헤란로 152", "lat": 37.5172, "lon": 127.0473},
        ]
        
        devices = [
            {
                "entity_id": "device_tracker.iphone_12",
                "name": "iPhone 12",
                "lat": 37.5665,
                "lon": 126.9780
            }
        ]
        
        # Mock 설정
        mock_ha = MagicMock()
        mock_ha.list_notify_mobile_services = AsyncMock(return_value=["mobile_app_iphone_12"])
        mock_ha.get_device_trackers = AsyncMock(return_value=devices)
        mock_ha.notify = AsyncMock()
        
        # ShelterNavigator 생성 및 테스트
        nav = ShelterNavigator(mock_ha, "/test/path.xlsx", "com.synctechno.dxsafety")
        nav._shelters = shelters
        
        await nav.notify_all_devices()
        
        # 검증
        mock_ha.notify.assert_called_once()
        call_args = mock_ha.notify.call_args[0]
        
        assert call_args[0] == "mobile_app_iphone_12"  # service
        assert call_args[1] == "가까운 대피소 안내"  # title
        assert "서울시민대피소" in call_args[2]  # message
        assert "nmap://navigation" in call_args[3]  # url
        assert "com.synctechno.dxsafety" in call_args[3]  # appname
