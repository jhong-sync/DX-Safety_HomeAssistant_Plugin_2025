"""
DX-Safety 전반적인 기능 통합 테스트

이 모듈은 DX-Safety 프로젝트의 모든 주요 기능을 테스트하는 포괄적인 테스트 스위트입니다.
각 테스트는 독립적으로 실행 가능하며, 실제 환경과 유사한 조건에서 동작을 검증합니다.
"""

import pytest
import asyncio
import json
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# 프로젝트 모듈들
from app.core.models import CAE, Decision, Area, Geometry, Severity
from app.core import normalize, policy
from app.settings import Settings
from app.adapters.mqtt_remote.client_async import RemoteMqttIngestor
from app.adapters.mqtt_local.publisher_async import LocalMqttPublisher
from app.adapters.storage.sqlite_outbox import SQLiteOutbox
from app.adapters.storage.sqlite_idem import SQLiteIdemStore
from app.adapters.homeassistant.client import HAClient
from app.adapters.tts.engine import TTSEngine
from app.orchestrators.orchestrator import Orchestrator
from app.observability.logging_setup import setup_logging_dev, get_logger


class TestComprehensiveFunctionality:
    """전반적인 기능 통합 테스트 클래스"""
    
    @pytest.fixture(autouse=True)
    def setup_logging(self):
        """테스트용 로깅 설정"""
        setup_logging_dev(level="DEBUG")
        self.logger = get_logger("test_comprehensive")
    
    @pytest.fixture
    def sample_cap_message(self) -> Dict[str, Any]:
        """테스트용 CAP 메시지 샘플"""
        return {
            "id": "test-alert-001",
            "sentAt": "2025-01-15T10:30:00Z",
            "headline": "강풍 주의보 발표",
            "severity": "moderate",
            "description": "서울 지역에 강풍 주의보가 발표되었습니다.",
            "areas": [
                {
                    "name": "서울특별시",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [126.8, 37.4],
                            [127.2, 37.4],
                            [127.2, 37.8],
                            [126.8, 37.8],
                            [126.8, 37.4]
                        ]]
                    }
                }
            ],
            "effective": "2025-01-15T10:30:00Z",
            "expires": "2025-01-16T10:30:00Z"
        }
    
    @pytest.fixture
    def test_settings(self) -> Settings:
        """테스트용 설정"""
        settings = Settings()
        # 테스트 환경에 맞게 설정 조정
        settings.remote_mqtt.host = "localhost"
        settings.remote_mqtt.port = 1883
        settings.local_mqtt.host = "localhost"
        settings.local_mqtt.port = 1883
        settings.geopolicy.lat = 37.5665  # 서울시청
        settings.geopolicy.lon = 126.9780
        settings.geopolicy.severity_threshold = "minor"
        settings.geopolicy.distance_km_threshold = 50.0
        return settings

    # ===== 1. 핵심 모델 및 정규화 테스트 =====
    
    def test_cae_model_creation(self, sample_cap_message):
        """CAE 모델 생성 및 검증"""
        cae = normalize.to_cae(sample_cap_message)
        
        assert cae.event_id == "test-alert-001"
        assert cae.headline == "강풍 주의보 발표"
        assert cae.severity == "moderate"
        assert cae.description == "서울 지역에 강풍 주의보가 발표되었습니다."
        assert len(cae.areas) == 1
        assert cae.areas[0].name == "서울특별시"
    
    def test_severity_hierarchy(self):
        """심각도 계층 구조 테스트"""
        # 심각도 순서: minor < moderate < severe < critical
        assert Severity.minor < Severity.moderate
        assert Severity.moderate < Severity.severe
        assert Severity.severe < Severity.critical
        
        # 정책 평가 테스트
        cae = CAE(
            event_id="test",
            sent_at="2025-01-01T00:00:00Z",
            severity="severe"
        )
        
        # severe >= moderate (통과)
        decision = policy.evaluate(cae, threshold="moderate")
        assert decision.trigger == True
        
        # severe < critical (거부)
        decision = policy.evaluate(cae, threshold="critical")
        assert decision.trigger == False
    
    def test_geometry_validation(self):
        """지리 정보 검증 테스트"""
        # 유효한 Point 형상
        point_geom = Geometry(
            type="Point",
            coordinates=[127.0, 37.5]
        )
        assert point_geom.type == "Point"
        assert len(point_geom.coordinates) == 2
        
        # 유효한 Polygon 형상
        polygon_geom = Geometry(
            type="Polygon",
            coordinates=[[
                [126.8, 37.4],
                [127.2, 37.4],
                [127.2, 37.8],
                [126.8, 37.8],
                [126.8, 37.4]
            ]]
        )
        assert polygon_geom.type == "Polygon"
        assert len(polygon_geom.coordinates[0]) >= 4  # 최소 4개 점

    # ===== 2. 정책 평가 테스트 =====
    
    def test_geographic_policy(self, test_settings):
        """지리적 정책 평가 테스트"""
        # 서울시청 근처 경보 (통과)
        nearby_cae = CAE(
            event_id="nearby",
            sent_at="2025-01-01T00:00:00Z",
            severity="moderate",
            areas=[
                Area(
                    name="서울시청 근처",
                    geometry=Geometry(
                        type="Point",
                        coordinates=[126.9780, 37.5665]  # 서울시청
                    )
                )
            ]
        )
        
        decision = policy.evaluate_geographic(
            nearby_cae, 
            lat=test_settings.geopolicy.lat,
            lon=test_settings.geopolicy.lon,
            radius_km=test_settings.geopolicy.distance_km_threshold
        )
        assert decision.trigger == True
        
        # 부산 경보 (거부)
        far_cae = CAE(
            event_id="far",
            sent_at="2025-01-01T00:00:00Z",
            severity="moderate",
            areas=[
                Area(
                    name="부산",
                    geometry=Geometry(
                        type="Point",
                        coordinates=[129.0756, 35.1796]  # 부산
                    )
                )
            ]
        )
        
        decision = policy.evaluate_geographic(
            far_cae,
            lat=test_settings.geopolicy.lat,
            lon=test_settings.geopolicy.lon,
            radius_km=test_settings.geopolicy.distance_km_threshold
        )
        assert decision.trigger == False
    
    def test_time_based_policy(self):
        """시간 기반 정책 테스트"""
        # 야간 모드 테스트
        night_time = datetime(2025, 1, 15, 23, 0, 0, tzinfo=timezone.utc)
        day_time = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        
        cae = CAE(
            event_id="test",
            sent_at="2025-01-01T00:00:00Z",
            severity="moderate"
        )
        
        # 야간 모드 활성화 시
        decision = policy.evaluate_time(cae, night_mode=True, current_time=night_time)
        assert decision.trigger == False  # 야간에는 알림 거부
        
        # 주간 모드
        decision = policy.evaluate_time(cae, night_mode=False, current_time=night_time)
        assert decision.trigger == True  # 야간 모드 비활성화 시 통과

    # ===== 3. 저장소 및 지속성 테스트 =====
    
    @pytest.mark.asyncio
    async def test_sqlite_outbox(self):
        """SQLite Outbox 테스트"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        
        try:
            outbox = SQLiteOutbox(db_path)
            await outbox.initialize()
            
            # 메시지 저장
            message = {"test": "data", "id": "msg-001"}
            await outbox.store("test-topic", message)
            
            # 메시지 조회
            messages = await outbox.get_pending()
            assert len(messages) == 1
            assert messages[0]["topic"] == "test-topic"
            assert messages[0]["payload"]["id"] == "msg-001"
            
            # 메시지 삭제
            await outbox.delete(messages[0]["id"])
            messages = await outbox.get_pending()
            assert len(messages) == 0
            
        finally:
            os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_sqlite_idempotency(self):
        """SQLite 중복 제거 테스트"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        
        try:
            idem_store = SQLiteIdemStore(db_path)
            await idem_store.initialize()
            
            # 첫 번째 메시지 (성공)
            result = await idem_store.is_duplicate("test-msg-001")
            assert result == False
            
            # 중복 메시지 (실패)
            await idem_store.mark_processed("test-msg-001")
            result = await idem_store.is_duplicate("test-msg-001")
            assert result == True
            
        finally:
            os.unlink(db_path)

    # ===== 4. MQTT 통신 테스트 =====
    
    @pytest.mark.asyncio
    async def test_mqtt_publisher_mock(self):
        """MQTT 발행자 모의 테스트"""
        mock_client = AsyncMock()
        publisher = LocalMqttPublisher(
            host="localhost",
            port=1883,
            topic_prefix="test"
        )
        publisher._client = mock_client
        
        # 메시지 발행 테스트
        await publisher.publish("alert", {"test": "message"})
        
        # 발행 호출 확인
        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args
        assert "test/alert" in call_args[0][0]  # 토픽 확인
    
    @pytest.mark.asyncio
    async def test_mqtt_ingestor_mock(self):
        """MQTT 수신자 모의 테스트"""
        mock_client = AsyncMock()
        ingestor = RemoteMqttIngestor(
            host="localhost",
            port=1883,
            topic="test/#"
        )
        ingestor._client = mock_client
        
        # 연결 테스트
        await ingestor.connect()
        mock_client.connect.assert_called_once()
        
        # 구독 테스트
        await ingestor.subscribe()
        mock_client.subscribe.assert_called_once_with("test/#")

    # ===== 5. Home Assistant 통합 테스트 =====
    
    @pytest.mark.asyncio
    async def test_ha_client_mock(self):
        """Home Assistant 클라이언트 모의 테스트"""
        mock_session = AsyncMock()
        ha_client = HAClient(
            base_url="http://localhost:8123",
            token="test-token"
        )
        ha_client._session = mock_session
        
        # 센서 상태 업데이트 테스트
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"state": "success"})
        mock_session.post.return_value = mock_response
        
        await ha_client.update_sensor("sensor.test", "test_value")
        
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "api/states/sensor.test" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_ha_event_publishing(self):
        """Home Assistant 이벤트 발행 테스트"""
        mock_session = AsyncMock()
        ha_client = HAClient(
            base_url="http://localhost:8123",
            token="test-token"
        )
        ha_client._session = mock_session
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"message": "Event fired"})
        mock_session.post.return_value = mock_response
        
        # 이벤트 발행
        await ha_client.fire_event("dxsafety_alert", {
            "event_id": "test-001",
            "severity": "moderate"
        })
        
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "api/events/dxsafety_alert" in call_args[0][0]

    # ===== 6. TTS 엔진 테스트 =====
    
    @pytest.mark.asyncio
    async def test_tts_engine(self):
        """TTS 엔진 테스트"""
        mock_publisher = AsyncMock()
        tts_engine = TTSEngine(
            topic="test/tts",
            template="{headline} - {description}",
            voice_language="ko-KR"
        )
        tts_engine._publisher = mock_publisher
        
        # TTS 메시지 생성 및 발행
        cae = CAE(
            event_id="test",
            sent_at="2025-01-01T00:00:00Z",
            headline="테스트 경보",
            description="테스트 설명입니다."
        )
        
        await tts_engine.announce(cae)
        
        mock_publisher.publish.assert_called_once()
        call_args = mock_publisher.publish.call_args
        assert "test/tts" in call_args[0][0]
        
        # 템플릿 적용 확인
        payload = json.loads(call_args[0][1])
        assert "테스트 경보 - 테스트 설명입니다." in payload["message"]

    # ===== 7. 오케스트레이터 통합 테스트 =====
    
    @pytest.mark.asyncio
    async def test_orchestrator_flow(self, sample_cap_message, test_settings):
        """오케스트레이터 전체 플로우 테스트"""
        # 모의 컴포넌트들
        mock_ingestor = AsyncMock()
        mock_publisher = AsyncMock()
        mock_outbox = AsyncMock()
        mock_idem_store = AsyncMock()
        mock_ha_client = AsyncMock()
        mock_tts_engine = AsyncMock()
        
        # 오케스트레이터 생성
        orchestrator = Orchestrator(
            settings=test_settings,
            ingestor=mock_ingestor,
            publisher=mock_publisher,
            outbox=mock_outbox,
            idem_store=mock_idem_store,
            ha_client=mock_ha_client,
            tts_engine=mock_tts_engine
        )
        
        # 중복 제거 모의 (중복 아님)
        mock_idem_store.is_duplicate.return_value = False
        
        # 정책 평가 모의 (통과)
        with patch('app.orchestrators.orchestrator.policy.evaluate') as mock_policy:
            mock_policy.return_value = Decision(trigger=True, level="moderate", reason="Passed")
            
            # 메시지 처리
            await orchestrator.process_message(sample_cap_message)
            
            # 각 단계 호출 확인
            mock_idem_store.is_duplicate.assert_called_once()
            mock_policy.assert_called_once()
            mock_ha_client.update_sensor.assert_called()
            mock_tts_engine.announce.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_orchestrator_duplicate_handling(self, sample_cap_message, test_settings):
        """중복 메시지 처리 테스트"""
        mock_ingestor = AsyncMock()
        mock_publisher = AsyncMock()
        mock_outbox = AsyncMock()
        mock_idem_store = AsyncMock()
        mock_ha_client = AsyncMock()
        mock_tts_engine = AsyncMock()
        
        orchestrator = Orchestrator(
            settings=test_settings,
            ingestor=mock_ingestor,
            publisher=mock_publisher,
            outbox=mock_outbox,
            idem_store=mock_idem_store,
            ha_client=mock_ha_client,
            tts_engine=mock_tts_engine
        )
        
        # 중복 메시지로 설정
        mock_idem_store.is_duplicate.return_value = True
        
        # 메시지 처리
        await orchestrator.process_message(sample_cap_message)
        
        # 중복 처리 확인
        mock_idem_store.is_duplicate.assert_called_once()
        mock_ha_client.update_sensor.assert_not_called()  # 중복이므로 처리 안됨
        mock_tts_engine.announce.assert_not_called()

    # ===== 8. 설정 및 환경변수 테스트 =====
    
    def test_settings_validation(self):
        """설정 검증 테스트"""
        settings = Settings()
        
        # 필수 필드 검증
        assert settings.remote_mqtt.host is not None
        assert settings.remote_mqtt.port > 0
        assert settings.local_mqtt.host is not None
        assert settings.local_mqtt.port > 0
        
        # 정책 설정 검증
        assert settings.geopolicy.severity_threshold in ["minor", "moderate", "severe", "critical"]
        assert settings.geopolicy.distance_km_threshold > 0
    
    def test_environment_variable_override(self):
        """환경변수 오버라이드 테스트"""
        with patch.dict(os.environ, {
            'REMOTE_MQTT_HOST': 'test-host',
            'REMOTE_MQTT_PORT': '1884',
            'SEVERITY_THRESHOLD': 'severe',
            'LOG_LEVEL': 'DEBUG'
        }):
            from app.main import build_settings
            settings = build_settings()
            
            assert settings.remote_mqtt.host == 'test-host'
            assert settings.remote_mqtt.port == 1884
            assert settings.geopolicy.severity_threshold == 'severe'

    # ===== 9. 오류 처리 및 복구 테스트 =====
    
    @pytest.mark.asyncio
    async def test_mqtt_connection_failure(self):
        """MQTT 연결 실패 처리 테스트"""
        mock_client = AsyncMock()
        mock_client.connect.side_effect = Exception("Connection failed")
        
        ingestor = RemoteMqttIngestor(
            host="invalid-host",
            port=1883,
            topic="test/#"
        )
        ingestor._client = mock_client
        
        # 연결 실패 시 예외 발생 확인
        with pytest.raises(Exception):
            await ingestor.connect()
    
    @pytest.mark.asyncio
    async def test_ha_api_failure(self):
        """Home Assistant API 실패 처리 테스트"""
        mock_session = AsyncMock()
        mock_response = Mock()
        mock_response.status = 500
        mock_session.post.return_value = mock_response
        
        ha_client = HAClient(
            base_url="http://localhost:8123",
            token="test-token"
        )
        ha_client._session = mock_session
        
        # API 실패 시 예외 발생 확인
        with pytest.raises(Exception):
            await ha_client.update_sensor("sensor.test", "value")

    # ===== 10. 성능 및 부하 테스트 =====
    
    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self, test_settings):
        """동시 메시지 처리 테스트"""
        mock_ingestor = AsyncMock()
        mock_publisher = AsyncMock()
        mock_outbox = AsyncMock()
        mock_idem_store = AsyncMock()
        mock_ha_client = AsyncMock()
        mock_tts_engine = AsyncMock()
        
        orchestrator = Orchestrator(
            settings=test_settings,
            ingestor=mock_ingestor,
            publisher=mock_publisher,
            outbox=mock_outbox,
            idem_store=mock_idem_store,
            ha_client=mock_ha_client,
            tts_engine=mock_tts_engine
        )
        
        # 중복 제거 모의
        mock_idem_store.is_duplicate.return_value = False
        
        # 정책 평가 모의
        with patch('app.orchestrators.orchestrator.policy.evaluate') as mock_policy:
            mock_policy.return_value = Decision(trigger=True, level="moderate", reason="Passed")
            
            # 동시에 여러 메시지 처리
            messages = [
                {"id": f"msg-{i}", "headline": f"Alert {i}", "severity": "moderate"}
                for i in range(10)
            ]
            
            tasks = [
                orchestrator.process_message(msg) 
                for msg in messages
            ]
            
            await asyncio.gather(*tasks)
            
            # 모든 메시지가 처리되었는지 확인
            assert mock_idem_store.is_duplicate.call_count == 10
            assert mock_ha_client.update_sensor.call_count == 10
            assert mock_tts_engine.announce.call_count == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
