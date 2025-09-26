"""
테스트 설정 및 픽스처

이 모듈은 pytest 설정과 공통 픽스처를 제공합니다.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import AsyncMock, Mock
from app.settings import Settings


@pytest.fixture(scope="session")
def event_loop():
    """세션 스코프의 이벤트 루프"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path():
    """임시 데이터베이스 파일 경로"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name
    yield temp_path
    # 테스트 후 파일 정리
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_file_path():
    """임시 파일 경로"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = f.name
    yield temp_path
    # 테스트 후 파일 정리
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def sample_settings():
    """테스트용 설정"""
    settings = Settings()
    settings.observability.service_name = "test-service"
    settings.observability.build_version = "1.0.0"
    settings.observability.log_level = "INFO"
    settings.observability.http_port = 8080
    return settings


@pytest.fixture
def mock_ha_client():
    """테스트용 Home Assistant 클라이언트"""
    return AsyncMock()


@pytest.fixture
def mock_mqtt_client():
    """테스트용 MQTT 클라이언트"""
    return AsyncMock()


@pytest.fixture
def mock_tts_engine():
    """테스트용 TTS 엔진"""
    return AsyncMock()


@pytest.fixture
def sample_cae():
    """테스트용 CAE 객체"""
    from app.core.models import CAE, Area, Geometry, Severity
    return CAE(
        event_id="test_event",
        sent_at="2024-01-01T00:00:00Z",
        severity=Severity.MODERATE,
        areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
    )


@pytest.fixture
def sample_decision():
    """테스트용 Decision 객체"""
    from app.core.models import Decision
    return Decision(trigger=True, reason="test", level="test")


@pytest.fixture
def sample_shelters():
    """테스트용 대피소 데이터"""
    return [
        {"name": "대피소1", "address": "서울시 강남구", "lat": 37.5665, "lon": 126.9780},
        {"name": "대피소2", "address": "서울시 서초구", "lat": 37.4947, "lon": 127.0276},
        {"name": "대피소3", "address": "서울시 송파구", "lat": 37.5145, "lon": 127.1050},
    ]


@pytest.fixture
def sample_polygon():
    """테스트용 폴리곤"""
    return [
        (126.0, 37.0),  # 좌하
        (127.0, 37.0),  # 우하
        (127.0, 38.0),  # 우상
        (126.0, 38.0)   # 좌상
    ]


@pytest.fixture
def mock_dependencies():
    """테스트용 의존성 목업"""
    return {
        'ingest': AsyncMock(),
        'publisher': AsyncMock(),
        'idem': AsyncMock(),
        'ha_client': AsyncMock(),
        'tts_engine': AsyncMock()
    }


# pytest 설정
def pytest_configure(config):
    """pytest 설정"""
    config.addinivalue_line(
        "markers", "asyncio: 비동기 테스트 마커"
    )
    config.addinivalue_line(
        "markers", "slow: 느린 테스트 마커"
    )
    config.addinivalue_line(
        "markers", "integration: 통합 테스트 마커"
    )


def pytest_collection_modifyitems(config, items):
    """테스트 아이템 수정"""
    for item in items:
        # 비동기 테스트에 asyncio 마커 추가
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
        
        # 느린 테스트 마커 추가
        if "performance" in item.name or "stress" in item.name:
            item.add_marker(pytest.mark.slow)
        
        # 통합 테스트 마커 추가
        if "integration" in item.name:
            item.add_marker(pytest.mark.integration)
