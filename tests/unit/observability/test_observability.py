"""
Observability 모듈 단위 테스트

이 모듈은 헬스 체크, 메트릭, 로깅, 서버 등의 관찰 가능성 기능을 테스트합니다.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from fastapi.testclient import TestClient
from app.observability.health import create_app
from app.observability.metrics import (
    alerts_received, alerts_valid, alerts_triggered, alerts_duplicate,
    publish_retries, reconnects, normalize_seconds, policy_seconds,
    end_to_end_seconds, queue_depth, outbox_size, idem_store_size, uptime_seconds
)
from app.observability.logging_setup import setup_logging_dev, get_logger, InterceptHandler
from app.settings import Settings


class TestHealthEndpoints:
    """헬스 체크 엔드포인트 테스트"""
    
    @pytest.fixture
    def settings(self):
        """테스트용 설정"""
        settings = Settings()
        settings.observability.service_name = "test-service"
        settings.observability.build_version = "1.0.0"
        settings.observability.log_level = "INFO"
        return settings
    
    @pytest.fixture
    def app(self, settings):
        """테스트용 FastAPI 앱"""
        return create_app(settings)
    
    @pytest.fixture
    def client(self, app):
        """테스트용 클라이언트"""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """헬스 체크 엔드포인트 테스트"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "test-service"
        assert "timestamp" in data
    
    def test_ready_endpoint(self, client):
        """레디니스 체크 엔드포인트 테스트"""
        response = client.get("/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["service"] == "test-service"
        assert "timestamp" in data
    
    def test_metrics_endpoint(self, client):
        """메트릭 엔드포인트 테스트"""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
        
        # Prometheus 메트릭 형식 확인
        content = response.text
        assert "# HELP" in content
        assert "# TYPE" in content
    
    def test_info_endpoint(self, client):
        """정보 엔드포인트 테스트"""
        response = client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "test-service"
        assert data["version"] == "1.0.0"
        assert data["log_level"] == "INFO"
        assert "uptime" in data
    
    def test_root_endpoint(self, client):
        """루트 엔드포인트 테스트"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "test-service"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "health" in data["endpoints"]
        assert "ready" in data["endpoints"]
        assert "metrics" in data["endpoints"]
        assert "info" in data["endpoints"]
    
    def test_shelter_notify_endpoint_disabled(self, client):
        """대피소 알림 엔드포인트 비활성화 테스트"""
        response = client.post("/shelter/notify", json={})
        
        assert response.status_code == 400
        data = response.json()
        assert "shelter_nav disabled" in data["detail"]
    
    def test_shelter_notify_endpoint_enabled(self, client, settings):
        """대피소 알림 엔드포인트 활성화 테스트"""
        # 대피소 네비게이션 활성화
        settings.shelter_nav.enabled = True
        settings.shelter_nav.file_path = "test.xlsx"
        settings.shelter_nav.appname = "test_app"
        settings.shelter_nav.notify_group = "test_group"
        
        with patch('app.observability.health.HAClient') as mock_ha_client:
            with patch('app.observability.health.ShelterNavigator') as mock_shelter_nav:
                mock_ha_instance = AsyncMock()
                mock_ha_client.return_value = mock_ha_instance
                
                mock_nav_instance = AsyncMock()
                mock_shelter_nav.return_value = mock_nav_instance
                
                # 새로운 앱과 클라이언트 생성
                app = create_app(settings)
                client = TestClient(app)
                
                response = client.post("/shelter/notify", json={"notify_group": "custom_group"})
                
                assert response.status_code == 200
                data = response.json()
                assert data["ok"] is True
                assert "대피소 알림 발송 완료" in data["message"]
    
    def test_shelter_notify_endpoint_error(self, client, settings):
        """대피소 알림 엔드포인트 에러 테스트"""
        # 대피소 네비게이션 활성화
        settings.shelter_nav.enabled = True
        settings.shelter_nav.file_path = "test.xlsx"
        settings.shelter_nav.appname = "test_app"
        
        with patch('app.observability.health.HAClient') as mock_ha_client:
            with patch('app.observability.health.ShelterNavigator') as mock_shelter_nav:
                mock_ha_instance = AsyncMock()
                mock_ha_client.return_value = mock_ha_instance
                
                mock_nav_instance = AsyncMock()
                mock_nav_instance.notify_all_devices.side_effect = Exception("Test error")
                mock_shelter_nav.return_value = mock_nav_instance
                
                # 새로운 앱과 클라이언트 생성
                app = create_app(settings)
                client = TestClient(app)
                
                response = client.post("/shelter/notify", json={})
                
                assert response.status_code == 500
                data = response.json()
                assert "Notification failed" in data["detail"]


class TestMetricsCollection:
    """메트릭 수집 테스트"""
    
    def test_alerts_received_counter(self):
        """경보 수신 카운터 테스트"""
        # 카운터 초기화
        alerts_received.clear()
        
        # 카운터 증가
        alerts_received.labels(source="mqtt").inc()
        alerts_received.labels(source="mqtt").inc(5)
        alerts_received.labels(source="api").inc()
        
        # 값 확인
        assert alerts_received.labels(source="mqtt")._value._value == 6
        assert alerts_received.labels(source="api")._value._value == 1
    
    def test_alerts_valid_counter(self):
        """유효한 경보 카운터 테스트"""
        # 카운터 초기화
        alerts_valid.clear()
        
        # 카운터 증가
        alerts_valid.labels(severity="moderate").inc()
        alerts_valid.labels(severity="severe").inc(3)
        alerts_valid.labels(severity="moderate").inc(2)
        
        # 값 확인
        assert alerts_valid.labels(severity="moderate")._value._value == 3
        assert alerts_valid.labels(severity="severe")._value._value == 3
    
    def test_alerts_triggered_counter(self):
        """트리거된 경보 카운터 테스트"""
        # 카운터 초기화
        alerts_triggered.clear()
        
        # 카운터 증가
        alerts_triggered.labels(severity="moderate", level="warning").inc()
        alerts_triggered.labels(severity="severe", level="critical").inc(2)
        
        # 값 확인
        assert alerts_triggered.labels(severity="moderate", level="warning")._value._value == 1
        assert alerts_triggered.labels(severity="severe", level="critical")._value._value == 2
    
    def test_alerts_duplicate_counter(self):
        """중복 경보 카운터 테스트"""
        # 카운터 초기화
        alerts_duplicate.clear()
        
        # 카운터 증가
        alerts_duplicate.inc()
        alerts_duplicate.inc(5)
        
        # 값 확인
        assert alerts_duplicate._value._value == 6
    
    def test_publish_retries_counter(self):
        """발송 재시도 카운터 테스트"""
        # 카운터 초기화
        publish_retries.clear()
        
        # 카운터 증가
        publish_retries.labels(topic="alerts").inc()
        publish_retries.labels(topic="alerts").inc(3)
        publish_retries.labels(topic="events").inc()
        
        # 값 확인
        assert publish_retries.labels(topic="alerts")._value._value == 4
        assert publish_retries.labels(topic="events")._value._value == 1
    
    def test_reconnects_counter(self):
        """재연결 카운터 테스트"""
        # 카운터 초기화
        reconnects.clear()
        
        # 카운터 증가
        reconnects.labels(client="remote").inc()
        reconnects.labels(client="local").inc(2)
        
        # 값 확인
        assert reconnects.labels(client="remote")._value._value == 1
        assert reconnects.labels(client="local")._value._value == 2
    
    def test_normalize_seconds_histogram(self):
        """정규화 시간 히스토그램 테스트"""
        # 히스토그램 초기화
        normalize_seconds.clear()
        
        # 히스토그램 기록
        normalize_seconds.observe(0.001)
        normalize_seconds.observe(0.01)
        normalize_seconds.observe(0.1)
        
        # 값 확인
        assert normalize_seconds._sum._value == 0.111
        assert normalize_seconds._count._value == 3
    
    def test_policy_seconds_histogram(self):
        """정책 평가 시간 히스토그램 테스트"""
        # 히스토그램 초기화
        policy_seconds.clear()
        
        # 히스토그램 기록
        policy_seconds.observe(0.005)
        policy_seconds.observe(0.05)
        policy_seconds.observe(0.5)
        
        # 값 확인
        assert policy_seconds._sum._value == 0.555
        assert policy_seconds._count._value == 3
    
    def test_end_to_end_seconds_histogram(self):
        """전체 처리 시간 히스토그램 테스트"""
        # 히스토그램 초기화
        end_to_end_seconds.clear()
        
        # 히스토그램 기록
        end_to_end_seconds.observe(0.1)
        end_to_end_seconds.observe(1.0)
        end_to_end_seconds.observe(5.0)
        
        # 값 확인
        assert end_to_end_seconds._sum._value == 6.1
        assert end_to_end_seconds._count._value == 3
    
    def test_queue_depth_gauge(self):
        """큐 깊이 게이지 테스트"""
        # 게이지 초기화
        queue_depth.set(0)
        
        # 게이지 설정
        queue_depth.set(10)
        queue_depth.set(5)
        queue_depth.inc(2)
        queue_depth.dec(1)
        
        # 값 확인
        assert queue_depth._value._value == 6
    
    def test_outbox_size_gauge(self):
        """Outbox 크기 게이지 테스트"""
        # 게이지 초기화
        outbox_size.set(0)
        
        # 게이지 설정
        outbox_size.set(100)
        outbox_size.inc(50)
        outbox_size.dec(25)
        
        # 값 확인
        assert outbox_size._value._value == 125
    
    def test_idem_store_size_gauge(self):
        """Idempotency 저장소 크기 게이지 테스트"""
        # 게이지 초기화
        idem_store_size.set(0)
        
        # 게이지 설정
        idem_store_size.set(1000)
        idem_store_size.inc(500)
        idem_store_size.dec(200)
        
        # 값 확인
        assert idem_store_size._value._value == 1300
    
    def test_uptime_seconds_gauge(self):
        """업타임 게이지 테스트"""
        # 게이지 초기화
        uptime_seconds.set(0)
        
        # 업타임 설정
        uptime_seconds.set(3600)  # 1시간
        uptime_seconds.inc(1800)  # 30분 추가
        
        # 값 확인
        assert uptime_seconds._value._value == 5400
    
    def test_metrics_context_manager(self):
        """메트릭 컨텍스트 매니저 테스트"""
        # 히스토그램 초기화
        normalize_seconds.clear()
        
        # 컨텍스트 매니저 사용
        with normalize_seconds.time():
            time.sleep(0.01)  # 10ms 대기
        
        # 값 확인
        assert normalize_seconds._count._value == 1
        assert normalize_seconds._sum._value >= 0.01


class TestLoggingSetup:
    """로깅 설정 테스트"""
    
    def test_intercept_handler_emit(self):
        """InterceptHandler emit 테스트"""
        handler = InterceptHandler()
        
        # 로그 레코드 생성
        record = Mock()
        record.levelname = "INFO"
        record.levelno = 20
        record.getMessage.return_value = "Test message"
        record.exc_info = None
        
        # emit 호출
        with patch('app.observability.logging_setup.logger') as mock_logger:
            handler.emit(record)
            
            # loguru 로거가 호출되었는지 확인
            mock_logger.opt.assert_called_once()
            mock_logger.log.assert_called_once()
    
    def test_intercept_handler_emit_with_exception(self):
        """예외가 있는 InterceptHandler emit 테스트"""
        handler = InterceptHandler()
        
        # 로그 레코드 생성
        record = Mock()
        record.levelname = "ERROR"
        record.levelno = 40
        record.getMessage.return_value = "Error message"
        record.exc_info = (Exception, Exception("Test error"), None)
        
        # emit 호출
        with patch('app.observability.logging_setup.logger') as mock_logger:
            handler.emit(record)
            
            # loguru 로거가 호출되었는지 확인
            mock_logger.opt.assert_called_once()
            mock_logger.log.assert_called_once()
    
    def test_intercept_handler_emit_invalid_level(self):
        """잘못된 레벨의 InterceptHandler emit 테스트"""
        handler = InterceptHandler()
        
        # 로그 레코드 생성
        record = Mock()
        record.levelname = "INVALID"
        record.levelno = 99
        record.getMessage.return_value = "Test message"
        record.exc_info = None
        
        # emit 호출
        with patch('app.observability.logging_setup.logger') as mock_logger:
            handler.emit(record)
            
            # loguru 로거가 호출되었는지 확인
            mock_logger.opt.assert_called_once()
            mock_logger.log.assert_called_once()
    
    def test_setup_logging_dev(self):
        """개발 환경 로깅 설정 테스트"""
        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging_dev(level="DEBUG")
            
            # basicConfig가 호출되었는지 확인
            mock_basic_config.assert_called_once()
    
    def test_get_logger(self):
        """로거 가져오기 테스트"""
        logger = get_logger("test.module")
        
        # 로거가 반환되었는지 확인
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'debug')


class TestServer:
    """서버 테스트"""
    
    @pytest.fixture
    def settings(self):
        """테스트용 설정"""
        settings = Settings()
        settings.observability.log_level = "INFO"
        settings.observability.http_port = 8080
        return settings
    
    def test_run_http_server(self, settings):
        """HTTP 서버 실행 테스트"""
        with patch('app.observability.server.setup_logging_dev') as mock_setup_logging:
            with patch('app.observability.server.get_logger') as mock_get_logger:
                with patch('app.observability.server.create_app') as mock_create_app:
                    with patch('app.observability.server.uvicorn.run') as mock_uvicorn_run:
                        mock_logger = Mock()
                        mock_get_logger.return_value = mock_logger
                        
                        mock_app = Mock()
                        mock_create_app.return_value = mock_app
                        
                        from app.observability.server import run_http_server
                        
                        # 서버 실행
                        run_http_server(settings, host="127.0.0.1", port=9090)
                        
                        # 설정이 올바르게 호출되었는지 확인
                        mock_setup_logging.assert_called_once_with(level="INFO")
                        mock_get_logger.assert_called_once_with("dxsafety.observability")
                        mock_create_app.assert_called_once_with(settings)
                        mock_uvicorn_run.assert_called_once()
                        
                        # uvicorn.run 호출 인수 확인
                        call_args = mock_uvicorn_run.call_args
                        assert call_args[0][0] == mock_app
                        assert call_args[1]['host'] == "127.0.0.1"
                        assert call_args[1]['port'] == 9090
                        assert call_args[1]['log_level'] == "info"
                        assert call_args[1]['access_log'] is True
    
    def test_run_http_server_default_port(self, settings):
        """기본 포트로 HTTP 서버 실행 테스트"""
        with patch('app.observability.server.setup_logging_dev'):
            with patch('app.observability.server.get_logger'):
                with patch('app.observability.server.create_app'):
                    with patch('app.observability.server.uvicorn.run') as mock_uvicorn_run:
                        from app.observability.server import run_http_server
                        
                        # 서버 실행 (포트 지정 안함)
                        run_http_server(settings)
                        
                        # 기본 포트가 사용되었는지 확인
                        call_args = mock_uvicorn_run.call_args
                        assert call_args[1]['port'] == 8080
    
    def test_run_http_server_error_handling(self, settings):
        """HTTP 서버 에러 처리 테스트"""
        with patch('app.observability.server.setup_logging_dev') as mock_setup_logging:
            mock_setup_logging.side_effect = Exception("Logging setup error")
            
            with pytest.raises(Exception, match="Logging setup error"):
                from app.observability.server import run_http_server
                run_http_server(settings)


class TestObservabilityIntegration:
    """관찰 가능성 통합 테스트"""
    
    @pytest.fixture
    def settings(self):
        """테스트용 설정"""
        settings = Settings()
        settings.observability.service_name = "test-service"
        settings.observability.build_version = "1.0.0"
        settings.observability.log_level = "INFO"
        settings.observability.http_port = 8080
        return settings
    
    def test_observability_integration(self, settings):
        """관찰 가능성 통합 테스트"""
        # FastAPI 앱 생성
        app = create_app(settings)
        client = TestClient(app)
        
        # 모든 엔드포인트 테스트
        endpoints = ["/health", "/ready", "/metrics", "/info", "/"]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            
            if endpoint == "/metrics":
                assert "text/plain" in response.headers["content-type"]
            else:
                data = response.json()
                assert "service" in data or "status" in data
    
    def test_observability_metrics_integration(self, settings):
        """메트릭 통합 테스트"""
        # 메트릭 초기화
        alerts_received.clear()
        alerts_valid.clear()
        queue_depth.set(0)
        
        # 메트릭 업데이트
        alerts_received.labels(source="mqtt").inc(10)
        alerts_valid.labels(severity="moderate").inc(8)
        queue_depth.set(5)
        
        # FastAPI 앱 생성
        app = create_app(settings)
        client = TestClient(app)
        
        # 메트릭 엔드포인트 호출
        response = client.get("/metrics")
        assert response.status_code == 200
        
        # 메트릭 내용 확인
        content = response.text
        assert "alerts_received_total" in content
        assert "alerts_valid_total" in content
        assert "internal_queue_depth" in content
    
    def test_observability_logging_integration(self, settings):
        """로깅 통합 테스트"""
        with patch('app.observability.logging_setup.logger') as mock_logger:
            # 로거 가져오기
            logger = get_logger("test.module")
            
            # 로그 메시지 출력
            logger.info("Test info message")
            logger.error("Test error message")
            
            # loguru 로거가 호출되었는지 확인
            assert mock_logger.info.called or mock_logger.log.called
            assert mock_logger.error.called or mock_logger.log.called
    
    def test_observability_server_integration(self, settings):
        """서버 통합 테스트"""
        with patch('app.observability.server.setup_logging_dev'):
            with patch('app.observability.server.get_logger'):
                with patch('app.observability.server.create_app') as mock_create_app:
                    with patch('app.observability.server.uvicorn.run'):
                        from app.observability.server import run_http_server
                        
                        # 서버 실행
                        run_http_server(settings)
                        
                        # 앱이 생성되었는지 확인
                        mock_create_app.assert_called_once_with(settings)
    
    def test_observability_error_handling(self, settings):
        """관찰 가능성 에러 처리 테스트"""
        # FastAPI 앱 생성
        app = create_app(settings)
        client = TestClient(app)
        
        # 존재하지 않는 엔드포인트 테스트
        response = client.get("/nonexistent")
        assert response.status_code == 404
        
        # 잘못된 HTTP 메서드 테스트
        response = client.post("/health")
        assert response.status_code == 405
    
    def test_observability_performance(self, settings):
        """관찰 가능성 성능 테스트"""
        # FastAPI 앱 생성
        app = create_app(settings)
        client = TestClient(app)
        
        # 성능 테스트
        start_time = time.time()
        
        # 여러 엔드포인트 동시 호출
        endpoints = ["/health", "/ready", "/info"]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 성능 확인
        assert processing_time < 1.0  # 1초 이내에 완료되어야 함
