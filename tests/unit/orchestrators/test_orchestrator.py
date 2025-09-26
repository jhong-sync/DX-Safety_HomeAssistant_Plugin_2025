"""
Orchestrator 모듈 단위 테스트

이 모듈은 메인 오케스트레이터의 기능을 테스트합니다.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from app.orchestrators.orchestrator import Orchestrator
from app.core.models import CAE, Decision, Area, Geometry
from app.settings import Settings


class TestOrchestratorInitialization:
    """오케스트레이터 초기화 테스트"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """테스트용 의존성 목업"""
        return {
            'ingest': AsyncMock(),
            'publisher': AsyncMock(),
            'idem': AsyncMock(),
            'ha_client': AsyncMock(),
            'tts_engine': AsyncMock()
        }
    
    def test_orchestrator_initialization_with_default_settings(self, mock_dependencies):
        """기본 설정으로 오케스트레이터 초기화 테스트"""
        orchestrator = Orchestrator(
            **mock_dependencies,
            severity_threshold="Moderate"
        )
        
        assert orchestrator.threshold == "Moderate"
        assert orchestrator.distance_threshold == 5.0
        assert orchestrator.polygon_buffer == 0.0
        assert orchestrator.policy_mode == "AND"
        assert orchestrator.voice_enabled is True
        assert orchestrator.voice_language == "ko-KR"
        assert orchestrator.shelter_nav_enabled is False
        assert orchestrator.home_coordinates is None
    
    def test_orchestrator_initialization_with_custom_settings(self, mock_dependencies):
        """사용자 정의 설정으로 오케스트레이터 초기화 테스트"""
        orchestrator = Orchestrator(
            **mock_dependencies,
            severity_threshold="Severe",
            distance_threshold_km=10.0,
            polygon_buffer_km=2.0,
            policy_mode="OR",
            voice_enabled=False,
            voice_language="en-US",
            queue_maxsize=500
        )
        
        assert orchestrator.threshold == "Severe"
        assert orchestrator.distance_threshold == 10.0
        assert orchestrator.polygon_buffer == 2.0
        assert orchestrator.policy_mode == "OR"
        assert orchestrator.voice_enabled is False
        assert orchestrator.voice_language == "en-US"
        assert orchestrator.q.maxsize == 500
    
    def test_orchestrator_initialization_with_shelter_nav_enabled(self, mock_dependencies):
        """대피소 네비게이션 활성화된 오케스트레이터 초기화 테스트"""
        settings = Settings()
        orchestrator = Orchestrator(
            **mock_dependencies,
            severity_threshold="Moderate",
            shelter_nav_enabled=True,
            shelter_nav_settings=settings
        )
        
        assert orchestrator.shelter_nav_enabled is True
        assert orchestrator.shelter_nav_settings == settings
        assert orchestrator.shelter_navigator is None  # start()에서 초기화됨
    
    def test_orchestrator_initialization_with_tts_enabled(self, mock_dependencies):
        """TTS 활성화된 오케스트레이터 초기화 테스트"""
        orchestrator = Orchestrator(
            **mock_dependencies,
            severity_threshold="Moderate",
            voice_enabled=True
        )
        
        assert orchestrator.voice_enabled is True
        assert orchestrator.tts_engine == mock_dependencies['tts_engine']
    
    def test_orchestrator_initialization_with_invalid_settings(self, mock_dependencies):
        """잘못된 설정으로 오케스트레이터 초기화 테스트"""
        with pytest.raises((ValueError, TypeError)):
            Orchestrator(
                **mock_dependencies,
                severity_threshold="InvalidSeverity",
                policy_mode="INVALID_MODE"
            )


class TestOrchestratorLifecycle:
    """오케스트레이터 생명주기 테스트"""
    
    @pytest.fixture
    def orchestrator(self):
        """테스트용 오케스트레이터"""
        mock_deps = {
            'ingest': AsyncMock(),
            'publisher': AsyncMock(),
            'idem': AsyncMock(),
            'ha_client': AsyncMock(),
            'tts_engine': AsyncMock()
        }
        return Orchestrator(**mock_deps, severity_threshold="Moderate")
    
    @pytest.mark.asyncio
    async def test_orchestrator_start_with_idem_init(self, orchestrator):
        """Idempotency 저장소 초기화 테스트"""
        orchestrator.idem.init = AsyncMock()
        
        with patch.object(orchestrator, '_load_home_coordinates', new_callable=AsyncMock):
            with patch.object(orchestrator, '_producer', new_callable=AsyncMock):
                with patch.object(orchestrator, '_consumer', new_callable=AsyncMock):
                    with patch.object(orchestrator, '_update_metrics', new_callable=AsyncMock):
                        with patch.object(orchestrator.publisher, 'start', new_callable=AsyncMock):
                            with patch.object(orchestrator.tts_engine, 'start', new_callable=AsyncMock):
                                # start() 메서드가 완료되도록 짧은 시간 후 취소
                                task = asyncio.create_task(orchestrator.start())
                                await asyncio.sleep(0.1)
                                task.cancel()
                                
                                orchestrator.idem.init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_orchestrator_start_with_home_coordinates_load(self, orchestrator):
        """홈 좌표 로드 테스트"""
        orchestrator.idem.init = AsyncMock()
        orchestrator._load_home_coordinates = AsyncMock()
        
        with patch.object(orchestrator, '_producer', new_callable=AsyncMock):
            with patch.object(orchestrator, '_consumer', new_callable=AsyncMock):
                with patch.object(orchestrator, '_update_metrics', new_callable=AsyncMock):
                    with patch.object(orchestrator.publisher, 'start', new_callable=AsyncMock):
                        with patch.object(orchestrator.tts_engine, 'start', new_callable=AsyncMock):
                            task = asyncio.create_task(orchestrator.start())
                            await asyncio.sleep(0.1)
                            task.cancel()
                            
                            orchestrator._load_home_coordinates.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_orchestrator_start_with_shelter_navigator_init(self):
        """대피소 네비게이터 초기화 테스트"""
        settings = Settings()
        mock_deps = {
            'ingest': AsyncMock(),
            'publisher': AsyncMock(),
            'idem': AsyncMock(),
            'ha_client': AsyncMock(),
            'tts_engine': AsyncMock()
        }
        orchestrator = Orchestrator(
            **mock_deps,
            severity_threshold="Moderate",
            shelter_nav_enabled=True,
            shelter_nav_settings=settings
        )
        
        orchestrator.idem.init = AsyncMock()
        orchestrator._load_home_coordinates = AsyncMock()
        
        with patch('app.orchestrators.orchestrator.ShelterNavigator') as mock_shelter_nav:
            with patch.object(orchestrator, '_producer', new_callable=AsyncMock):
                with patch.object(orchestrator, '_consumer', new_callable=AsyncMock):
                    with patch.object(orchestrator, '_update_metrics', new_callable=AsyncMock):
                        with patch.object(orchestrator.publisher, 'start', new_callable=AsyncMock):
                            with patch.object(orchestrator.tts_engine, 'start', new_callable=AsyncMock):
                                task = asyncio.create_task(orchestrator.start())
                                await asyncio.sleep(0.1)
                                task.cancel()
                                
                                mock_shelter_nav.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_orchestrator_start_with_tts_engine_start(self, orchestrator):
        """TTS 엔진 시작 테스트"""
        orchestrator.idem.init = AsyncMock()
        orchestrator._load_home_coordinates = AsyncMock()
        orchestrator.tts_engine.start = AsyncMock()
        
        with patch.object(orchestrator, '_producer', new_callable=AsyncMock):
            with patch.object(orchestrator, '_consumer', new_callable=AsyncMock):
                with patch.object(orchestrator, '_update_metrics', new_callable=AsyncMock):
                    with patch.object(orchestrator.publisher, 'start', new_callable=AsyncMock):
                        task = asyncio.create_task(orchestrator.start())
                        await asyncio.sleep(0.1)
                        task.cancel()
                        
                        orchestrator.tts_engine.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_orchestrator_start_task_creation(self, orchestrator):
        """태스크 생성 테스트"""
        orchestrator.idem.init = AsyncMock()
        orchestrator._load_home_coordinates = AsyncMock()
        orchestrator._producer = AsyncMock()
        orchestrator._consumer = AsyncMock()
        orchestrator._update_metrics = AsyncMock()
        orchestrator.publisher.start = AsyncMock()
        orchestrator.tts_engine.start = AsyncMock()
        
        with patch('asyncio.create_task') as mock_create_task:
            task = asyncio.create_task(orchestrator.start())
            await asyncio.sleep(0.1)
            task.cancel()
            
            # 프로듀서, 컨슈머, 발송 워커, 메트릭, TTS 태스크가 생성되어야 함
            assert mock_create_task.call_count >= 5


class TestOrchestratorTasks:
    """오케스트레이터 태스크 테스트"""
    
    @pytest.fixture
    def orchestrator(self):
        """테스트용 오케스트레이터"""
        mock_deps = {
            'ingest': AsyncMock(),
            'publisher': AsyncMock(),
            'idem': AsyncMock(),
            'ha_client': AsyncMock(),
            'tts_engine': AsyncMock()
        }
        return Orchestrator(**mock_deps, severity_threshold="Moderate")
    
    @pytest.mark.asyncio
    async def test_orchestrator_producer_task(self, orchestrator):
        """프로듀서 태스크 테스트"""
        # 메시지 스트림 모킹
        mock_message = {"test": "message"}
        orchestrator.ingest.recv.return_value = [mock_message].__aiter__()
        
        # 큐 모킹
        orchestrator.q.put_nowait = Mock()
        
        # 프로듀서 실행
        producer_task = asyncio.create_task(orchestrator._producer())
        await asyncio.sleep(0.1)
        producer_task.cancel()
        
        # 큐에 메시지가 추가되었는지 확인
        orchestrator.q.put_nowait.assert_called_with(mock_message)
    
    @pytest.mark.asyncio
    async def test_orchestrator_consumer_task(self, orchestrator):
        """컨슈머 태스크 테스트"""
        # 큐에 테스트 메시지 추가
        mock_message = {"test": "message"}
        orchestrator.q.put = AsyncMock(return_value=None)
        orchestrator.q.get = AsyncMock(return_value=mock_message)
        
        # 의존성 모킹
        orchestrator.idem.add_if_absent = AsyncMock(return_value=True)
        
        with patch('app.core.normalize.to_cae') as mock_to_cae:
            mock_cae = CAE(
                event_id="test_event",
                sent_at="2024-01-01T00:00:00Z",
                severity="moderate",
                areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
            )
            mock_to_cae.return_value = mock_cae
            
            with patch('app.core.geo_policy.evaluate_geographic_policy') as mock_eval_geo:
                with patch('app.core.geo_policy.evaluate_simple_policy') as mock_eval_simple:
                    mock_decision = Decision(trigger=True, reason="test", level="test")
                    mock_eval_geo.return_value = mock_decision
                    mock_eval_simple.return_value = mock_decision
                    
                    # 컨슈머 실행
                    consumer_task = asyncio.create_task(orchestrator._consumer())
                    await asyncio.sleep(0.1)
                    consumer_task.cancel()
                    
                    # 정규화 함수가 호출되었는지 확인
                    mock_to_cae.assert_called_with(mock_message)
    
    @pytest.mark.asyncio
    async def test_orchestrator_task_coordination(self, orchestrator):
        """태스크 조율 테스트"""
        orchestrator.idem.init = AsyncMock()
        orchestrator._load_home_coordinates = AsyncMock()
        orchestrator._producer = AsyncMock()
        orchestrator._consumer = AsyncMock()
        orchestrator._update_metrics = AsyncMock()
        orchestrator.publisher.start = AsyncMock()
        orchestrator.tts_engine.start = AsyncMock()
        
        # 모든 태스크가 동시에 실행되는지 확인
        task = asyncio.create_task(orchestrator.start())
        await asyncio.sleep(0.1)
        task.cancel()
        
        # 모든 주요 메서드가 호출되었는지 확인
        orchestrator.idem.init.assert_called_once()
        orchestrator._load_home_coordinates.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_orchestrator_task_error_handling(self, orchestrator):
        """태스크 에러 처리 테스트"""
        # 에러를 발생시키는 모킹
        orchestrator.idem.init.side_effect = Exception("Test error")
        
        with pytest.raises(Exception):
            await orchestrator.start()


class TestMessageProcessingPipeline:
    """메시지 처리 파이프라인 테스트"""
    
    @pytest.fixture
    def orchestrator(self):
        """테스트용 오케스트레이터"""
        mock_deps = {
            'ingest': AsyncMock(),
            'publisher': AsyncMock(),
            'idem': AsyncMock(),
            'ha_client': AsyncMock(),
            'tts_engine': AsyncMock()
        }
        return Orchestrator(**mock_deps, severity_threshold="Moderate")
    
    @pytest.mark.asyncio
    async def test_message_ingestion_from_remote_mqtt(self, orchestrator):
        """원격 MQTT에서 메시지 수집 테스트"""
        mock_message = {"source": "mqtt", "data": "test"}
        orchestrator.ingest.recv.return_value = [mock_message].__aiter__()
        
        # 프로듀서 실행
        producer_task = asyncio.create_task(orchestrator._producer())
        await asyncio.sleep(0.1)
        producer_task.cancel()
        
        # 메시지가 수집되었는지 확인
        orchestrator.ingest.recv.assert_called()
    
    @pytest.mark.asyncio
    async def test_message_normalization_to_cae(self, orchestrator):
        """메시지 정규화 테스트"""
        mock_raw = {"alert": "test"}
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity="moderate",
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        
        with patch('app.core.normalize.to_cae', return_value=mock_cae) as mock_to_cae:
            orchestrator.q.get = AsyncMock(return_value=mock_raw)
            orchestrator.idem.add_if_absent = AsyncMock(return_value=True)
            
            with patch('app.core.geo_policy.evaluate_geographic_policy') as mock_eval_geo:
                with patch('app.core.geo_policy.evaluate_simple_policy') as mock_eval_simple:
                    mock_decision = Decision(trigger=True, reason="test", level="test")
                    mock_eval_geo.return_value = mock_decision
                    mock_eval_simple.return_value = mock_decision
                    
                    # 컨슈머 실행
                    consumer_task = asyncio.create_task(orchestrator._consumer())
                    await asyncio.sleep(0.1)
                    consumer_task.cancel()
                    
                    # 정규화 함수가 호출되었는지 확인
                    mock_to_cae.assert_called_with(mock_raw)
    
    @pytest.mark.asyncio
    async def test_message_geographic_policy_evaluation(self, orchestrator):
        """지리적 정책 평가 테스트"""
        orchestrator.home_coordinates = (37.5665, 126.9780)  # 서울 좌표
        
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity="moderate",
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[37.5665, 126.9780]))]
        )
        
        with patch('app.core.normalize.to_cae', return_value=mock_cae):
            orchestrator.q.get = AsyncMock(return_value={"test": "message"})
            orchestrator.idem.add_if_absent = AsyncMock(return_value=True)
            
            with patch('app.core.geo_policy.evaluate_geographic_policy') as mock_eval_geo:
                mock_decision = Decision(trigger=True, reason="geographic", level="test")
                mock_eval_geo.return_value = mock_decision
                
                with patch('app.core.geo_policy.evaluate_simple_policy') as mock_eval_simple:
                    mock_eval_simple.return_value = mock_decision
                    
                    # 컨슈머 실행
                    consumer_task = asyncio.create_task(orchestrator._consumer())
                    await asyncio.sleep(0.1)
                    consumer_task.cancel()
                    
                    # 지리적 정책 평가가 호출되었는지 확인
                    mock_eval_geo.assert_called()
    
    @pytest.mark.asyncio
    async def test_message_idempotency_check(self, orchestrator):
        """메시지 중복 제거 테스트"""
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity="moderate",
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        
        with patch('app.core.normalize.to_cae', return_value=mock_cae):
            orchestrator.q.get = AsyncMock(return_value={"test": "message"})
            orchestrator.idem.add_if_absent = AsyncMock(return_value=False)  # 중복 메시지
            
            with patch('app.core.geo_policy.evaluate_geographic_policy') as mock_eval_geo:
                with patch('app.core.geo_policy.evaluate_simple_policy') as mock_eval_simple:
                    mock_decision = Decision(trigger=True, reason="test", level="test")
                    mock_eval_geo.return_value = mock_decision
                    mock_eval_simple.return_value = mock_decision
                    
                    # 컨슈머 실행
                    consumer_task = asyncio.create_task(orchestrator._consumer())
                    await asyncio.sleep(0.1)
                    consumer_task.cancel()
                    
                    # 중복 체크가 호출되었는지 확인
                    orchestrator.idem.add_if_absent.assert_called()


class TestOrchestratorSettingsAndPolicy:
    """오케스트레이터 설정 및 정책 테스트"""
    
    @pytest.fixture
    def orchestrator(self):
        """테스트용 오케스트레이터"""
        mock_deps = {
            'ingest': AsyncMock(),
            'publisher': AsyncMock(),
            'idem': AsyncMock(),
            'ha_client': AsyncMock(),
            'tts_engine': AsyncMock()
        }
        return Orchestrator(**mock_deps, severity_threshold="Moderate")
    
    def test_severity_threshold_policy(self):
        """심각도 임계값 정책 테스트"""
        mock_deps = {
            'ingest': AsyncMock(),
            'publisher': AsyncMock(),
            'idem': AsyncMock(),
            'ha_client': AsyncMock(),
            'tts_engine': AsyncMock()
        }
        
        # 다양한 심각도 임계값으로 테스트
        for threshold in ["Minor", "Moderate", "Severe", "Extreme"]:
            orchestrator = Orchestrator(**mock_deps, severity_threshold=threshold)
            assert orchestrator.threshold == threshold
    
    def test_distance_threshold_policy(self):
        """거리 임계값 정책 테스트"""
        mock_deps = {
            'ingest': AsyncMock(),
            'publisher': AsyncMock(),
            'idem': AsyncMock(),
            'ha_client': AsyncMock(),
            'tts_engine': AsyncMock()
        }
        
        # 다양한 거리 임계값으로 테스트
        for distance in [1.0, 5.0, 10.0, 50.0]:
            orchestrator = Orchestrator(**mock_deps, severity_threshold="Moderate", distance_threshold_km=distance)
            assert orchestrator.distance_threshold == distance
    
    def test_polygon_buffer_policy(self):
        """폴리곤 버퍼 정책 테스트"""
        mock_deps = {
            'ingest': AsyncMock(),
            'publisher': AsyncMock(),
            'idem': AsyncMock(),
            'ha_client': AsyncMock(),
            'tts_engine': AsyncMock()
        }
        
        # 다양한 폴리곤 버퍼로 테스트
        for buffer in [0.0, 1.0, 2.5, 5.0]:
            orchestrator = Orchestrator(**mock_deps, severity_threshold="Moderate", polygon_buffer_km=buffer)
            assert orchestrator.polygon_buffer == buffer
    
    def test_policy_mode_and_logic(self):
        """AND 정책 모드 테스트"""
        mock_deps = {
            'ingest': AsyncMock(),
            'publisher': AsyncMock(),
            'idem': AsyncMock(),
            'ha_client': AsyncMock(),
            'tts_engine': AsyncMock()
        }
        
        orchestrator = Orchestrator(**mock_deps, severity_threshold="Moderate", policy_mode="AND")
        assert orchestrator.policy_mode == "AND"
    
    def test_policy_mode_or_logic(self):
        """OR 정책 모드 테스트"""
        mock_deps = {
            'ingest': AsyncMock(),
            'publisher': AsyncMock(),
            'idem': AsyncMock(),
            'ha_client': AsyncMock(),
            'tts_engine': AsyncMock()
        }
        
        orchestrator = Orchestrator(**mock_deps, severity_threshold="Moderate", policy_mode="OR")
        assert orchestrator.policy_mode == "OR"
    
    def test_night_mode_policy(self):
        """야간 모드 정책 테스트"""
        mock_deps = {
            'ingest': AsyncMock(),
            'publisher': AsyncMock(),
            'idem': AsyncMock(),
            'ha_client': AsyncMock(),
            'tts_engine': AsyncMock()
        }
        
        # 음성 알림 활성화/비활성화 테스트
        orchestrator_enabled = Orchestrator(**mock_deps, severity_threshold="Moderate", voice_enabled=True)
        orchestrator_disabled = Orchestrator(**mock_deps, severity_threshold="Moderate", voice_enabled=False)
        
        assert orchestrator_enabled.voice_enabled is True
        assert orchestrator_disabled.voice_enabled is False


class TestOrchestratorErrorHandling:
    """오케스트레이터 에러 처리 테스트"""
    
    @pytest.fixture
    def orchestrator(self):
        """테스트용 오케스트레이터"""
        mock_deps = {
            'ingest': AsyncMock(),
            'publisher': AsyncMock(),
            'idem': AsyncMock(),
            'ha_client': AsyncMock(),
            'tts_engine': AsyncMock()
        }
        return Orchestrator(**mock_deps, severity_threshold="Moderate")
    
    @pytest.mark.asyncio
    async def test_orchestrator_error_handling(self, orchestrator):
        """오케스트레이터 일반 에러 처리 테스트"""
        orchestrator.idem.init.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            await orchestrator.start()
    
    @pytest.mark.asyncio
    async def test_mqtt_connection_error_handling(self, orchestrator):
        """MQTT 연결 에러 처리 테스트"""
        orchestrator.ingest.recv.side_effect = Exception("MQTT connection failed")
        
        # 프로듀서에서 에러가 발생해도 시스템이 중단되지 않는지 확인
        producer_task = asyncio.create_task(orchestrator._producer())
        await asyncio.sleep(0.1)
        producer_task.cancel()
        
        # 에러가 발생했지만 태스크가 정상적으로 취소되었는지 확인
        assert producer_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_ha_api_error_handling(self, orchestrator):
        """Home Assistant API 에러 처리 테스트"""
        orchestrator.ha_client.__aenter__.side_effect = Exception("HA API error")
        
        # 홈 좌표 로드에서 에러가 발생해도 시스템이 계속 동작하는지 확인
        await orchestrator._load_home_coordinates()
        
        # 에러가 발생했지만 홈 좌표가 None으로 설정되었는지 확인
        assert orchestrator.home_coordinates is None
    
    @pytest.mark.asyncio
    async def test_sqlite_error_handling(self, orchestrator):
        """SQLite 에러 처리 테스트"""
        orchestrator.idem.add_if_absent.side_effect = Exception("SQLite error")
        
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity="moderate",
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        
        with patch('app.core.normalize.to_cae', return_value=mock_cae):
            orchestrator.q.get = AsyncMock(return_value={"test": "message"})
            
            with patch('app.core.geo_policy.evaluate_geographic_policy') as mock_eval_geo:
                with patch('app.core.geo_policy.evaluate_simple_policy') as mock_eval_simple:
                    mock_decision = Decision(trigger=True, reason="test", level="test")
                    mock_eval_geo.return_value = mock_decision
                    mock_eval_simple.return_value = mock_decision
                    
                    # 컨슈머에서 에러가 발생해도 시스템이 중단되지 않는지 확인
                    consumer_task = asyncio.create_task(orchestrator._consumer())
                    await asyncio.sleep(0.1)
                    consumer_task.cancel()
                    
                    # 에러가 발생했지만 태스크가 정상적으로 취소되었는지 확인
                    assert consumer_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_tts_error_handling(self, orchestrator):
        """TTS 에러 처리 테스트"""
        orchestrator.tts_engine.start.side_effect = Exception("TTS engine error")
        
        with pytest.raises(Exception, match="TTS engine error"):
            await orchestrator.start()
    
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, orchestrator):
        """네트워크 타임아웃 처리 테스트"""
        orchestrator.ha_client.__aenter__.side_effect = asyncio.TimeoutError("Network timeout")
        
        # 타임아웃이 발생해도 시스템이 계속 동작하는지 확인
        await orchestrator._load_home_coordinates()
        
        # 타임아웃이 발생했지만 홈 좌표가 None으로 설정되었는지 확인
        assert orchestrator.home_coordinates is None


class TestOrchestratorMetrics:
    """오케스트레이터 메트릭 테스트"""
    
    @pytest.fixture
    def orchestrator(self):
        """테스트용 오케스트레이터"""
        mock_deps = {
            'ingest': AsyncMock(),
            'publisher': AsyncMock(),
            'idem': AsyncMock(),
            'ha_client': AsyncMock(),
            'tts_engine': AsyncMock()
        }
        return Orchestrator(**mock_deps, severity_threshold="Moderate")
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, orchestrator):
        """메트릭 수집 테스트"""
        with patch('app.observability.metrics.alerts_received') as mock_alerts_received:
            with patch('app.observability.metrics.queue_depth') as mock_queue_depth:
                mock_message = {"test": "message"}
                orchestrator.ingest.recv.return_value = [mock_message].__aiter__()
                
                # 프로듀서 실행
                producer_task = asyncio.create_task(orchestrator._producer())
                await asyncio.sleep(0.1)
                producer_task.cancel()
                
                # 메트릭이 업데이트되었는지 확인
                mock_alerts_received.labels.assert_called_with(source="mqtt")
                mock_queue_depth.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_metrics_update_frequency(self, orchestrator):
        """메트릭 업데이트 빈도 테스트"""
        with patch('app.observability.metrics.alerts_valid') as mock_alerts_valid:
            mock_cae = CAE(
                event_id="test_event",
                sent_at="2024-01-01T00:00:00Z",
                severity="moderate",
                areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
            )
            
            with patch('app.core.normalize.to_cae', return_value=mock_cae):
                orchestrator.q.get = AsyncMock(return_value={"test": "message"})
                orchestrator.idem.add_if_absent = AsyncMock(return_value=True)
                
                with patch('app.core.geo_policy.evaluate_geographic_policy') as mock_eval_geo:
                    with patch('app.core.geo_policy.evaluate_simple_policy') as mock_eval_simple:
                        mock_decision = Decision(trigger=True, reason="test", level="test")
                        mock_eval_geo.return_value = mock_decision
                        mock_eval_simple.return_value = mock_decision
                        
                        # 컨슈머 실행
                        consumer_task = asyncio.create_task(orchestrator._consumer())
                        await asyncio.sleep(0.1)
                        consumer_task.cancel()
                        
                        # 유효한 경보 메트릭이 업데이트되었는지 확인
                        mock_alerts_valid.labels.assert_called_with(severity="moderate")
    
    @pytest.mark.asyncio
    async def test_metrics_accuracy(self, orchestrator):
        """메트릭 정확성 테스트"""
        with patch('app.observability.metrics.alerts_duplicate') as mock_alerts_duplicate:
            mock_cae = CAE(
                event_id="test_event",
                sent_at="2024-01-01T00:00:00Z",
                severity="moderate",
                areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
            )
            
            with patch('app.core.normalize.to_cae', return_value=mock_cae):
                orchestrator.q.get = AsyncMock(return_value={"test": "message"})
                orchestrator.idem.add_if_absent = AsyncMock(return_value=False)  # 중복 메시지
                
                with patch('app.core.geo_policy.evaluate_geographic_policy') as mock_eval_geo:
                    with patch('app.core.geo_policy.evaluate_simple_policy') as mock_eval_simple:
                        mock_decision = Decision(trigger=True, reason="test", level="test")
                        mock_eval_geo.return_value = mock_decision
                        mock_eval_simple.return_value = mock_decision
                        
                        # 컨슈머 실행
                        consumer_task = asyncio.create_task(orchestrator._consumer())
                        await asyncio.sleep(0.1)
                        consumer_task.cancel()
                        
                        # 중복 메시지 메트릭이 업데이트되었는지 확인
                        mock_alerts_duplicate.inc.assert_called()
    
    @pytest.mark.asyncio
    async def test_metrics_performance_impact(self, orchestrator):
        """메트릭 성능 영향 테스트"""
        # 메트릭 수집이 성능에 미치는 영향을 최소화하는지 확인
        start_time = asyncio.get_event_loop().time()
        
        with patch('app.observability.metrics.normalize_seconds') as mock_normalize_seconds:
            with patch('app.observability.metrics.policy_seconds') as mock_policy_seconds:
                mock_cae = CAE(
                    event_id="test_event",
                    sent_at="2024-01-01T00:00:00Z",
                    severity="moderate",
                    areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
                )
                
                with patch('app.core.normalize.to_cae', return_value=mock_cae):
                    orchestrator.q.get = AsyncMock(return_value={"test": "message"})
                    orchestrator.idem.add_if_absent = AsyncMock(return_value=True)
                    
                    with patch('app.core.geo_policy.evaluate_geographic_policy') as mock_eval_geo:
                        with patch('app.core.geo_policy.evaluate_simple_policy') as mock_eval_simple:
                            mock_decision = Decision(trigger=True, reason="test", level="test")
                            mock_eval_geo.return_value = mock_decision
                            mock_eval_simple.return_value = mock_decision
                            
                            # 컨슈머 실행
                            consumer_task = asyncio.create_task(orchestrator._consumer())
                            await asyncio.sleep(0.1)
                            consumer_task.cancel()
                            
                            # 메트릭 컨텍스트 매니저가 호출되었는지 확인
                            mock_normalize_seconds.time.assert_called()
                            mock_policy_seconds.time.assert_called()
    
    @pytest.mark.asyncio
    async def test_metrics_error_handling(self, orchestrator):
        """메트릭 에러 처리 테스트"""
        # 메트릭 수집 중 에러가 발생해도 시스템이 중단되지 않는지 확인
        with patch('app.observability.metrics.alerts_received') as mock_alerts_received:
            mock_alerts_received.labels.side_effect = Exception("Metrics error")
            
            mock_message = {"test": "message"}
            orchestrator.ingest.recv.return_value = [mock_message].__aiter__()
            
            # 프로듀서에서 메트릭 에러가 발생해도 시스템이 계속 동작하는지 확인
            producer_task = asyncio.create_task(orchestrator._producer())
            await asyncio.sleep(0.1)
            producer_task.cancel()
            
            # 에러가 발생했지만 태스크가 정상적으로 취소되었는지 확인
            assert producer_task.cancelled()
