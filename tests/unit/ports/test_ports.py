"""
Port 모듈 단위 테스트

이 모듈은 포트 인터페이스들의 기능을 테스트합니다.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from app.ports.ingest import AlertIngestPort
from app.ports.dispatch import AlertDispatchPort
from app.ports.kvstore import KVStorePort
from app.ports.metrics import MetricsPort
from app.core.models import CAE, Decision, Area, Geometry, Severity


class TestAlertIngestPort:
    """경보 수집 포트 인터페이스 테스트"""
    
    @pytest.fixture
    def mock_ingest_port(self):
        """테스트용 경보 수집 포트"""
        class MockIngestPort:
            async def recv(self):
                """모킹된 수집 메서드"""
                messages = [
                    {"test": "message1"},
                    {"test": "message2"},
                    {"test": "message3"}
                ]
                for message in messages:
                    yield message
        
        return MockIngestPort()
    
    @pytest.mark.asyncio
    async def test_ingest_port_interface(self, mock_ingest_port):
        """경보 수집 포트 인터페이스 테스트"""
        # 인터페이스가 올바르게 구현되었는지 확인
        assert hasattr(mock_ingest_port, 'recv')
        assert callable(mock_ingest_port.recv)
    
    @pytest.mark.asyncio
    async def test_ingest_port_implementation(self, mock_ingest_port):
        """경보 수집 포트 구현 테스트"""
        messages = []
        async for message in mock_ingest_port.recv():
            messages.append(message)
        
        assert len(messages) == 3
        assert messages[0] == {"test": "message1"}
        assert messages[1] == {"test": "message2"}
        assert messages[2] == {"test": "message3"}
    
    @pytest.mark.asyncio
    async def test_ingest_port_error_handling(self):
        """경보 수집 포트 에러 처리 테스트"""
        class ErrorIngestPort:
            async def recv(self):
                """에러를 발생시키는 수집 메서드"""
                raise Exception("Ingest error")
        
        error_port = ErrorIngestPort()
        
        with pytest.raises(Exception, match="Ingest error"):
            async for message in error_port.recv():
                pass
    
    @pytest.mark.asyncio
    async def test_ingest_port_empty_stream(self):
        """빈 스트림 경보 수집 포트 테스트"""
        class EmptyIngestPort:
            async def recv(self):
                """빈 스트림을 반환하는 수집 메서드"""
                return
                yield  # 이 줄은 실행되지 않음
        
        empty_port = EmptyIngestPort()
        
        messages = []
        async for message in empty_port.recv():
            messages.append(message)
        
        assert len(messages) == 0
    
    @pytest.mark.asyncio
    async def test_ingest_port_concurrent_access(self, mock_ingest_port):
        """동시 접근 경보 수집 포트 테스트"""
        # 여러 태스크에서 동시에 수집
        tasks = []
        for i in range(3):
            task = asyncio.create_task(self._collect_messages(mock_ingest_port))
            tasks.append(task)
        
        # 모든 작업 완료 대기
        results = await asyncio.gather(*tasks)
        
        # 모든 태스크가 메시지를 수집했는지 확인
        assert len(results) == 3
        for result in results:
            assert len(result) == 3
    
    async def _collect_messages(self, ingest_port):
        """메시지 수집 헬퍼 메서드"""
        messages = []
        async for message in ingest_port.recv():
            messages.append(message)
        return messages


class TestAlertDispatchPort:
    """경보 발송 포트 인터페이스 테스트"""
    
    @pytest.fixture
    def mock_dispatch_port(self):
        """테스트용 경보 발송 포트"""
        class MockDispatchPort:
            def __init__(self):
                self.published_alerts = []
            
            async def publish_alert(self, cae: CAE, decision: Decision):
                """모킹된 발송 메서드"""
                self.published_alerts.append((cae, decision))
        
        return MockDispatchPort()
    
    @pytest.fixture
    def sample_cae(self):
        """테스트용 CAE 객체"""
        return CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity=Severity.MODERATE,
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
    
    @pytest.fixture
    def sample_decision(self):
        """테스트용 Decision 객체"""
        return Decision(trigger=True, reason="test", level="test")
    
    @pytest.mark.asyncio
    async def test_dispatch_port_interface(self, mock_dispatch_port):
        """경보 발송 포트 인터페이스 테스트"""
        # 인터페이스가 올바르게 구현되었는지 확인
        assert hasattr(mock_dispatch_port, 'publish_alert')
        assert callable(mock_dispatch_port.publish_alert)
    
    @pytest.mark.asyncio
    async def test_dispatch_port_implementation(self, mock_dispatch_port, sample_cae, sample_decision):
        """경보 발송 포트 구현 테스트"""
        # 경보 발송
        await mock_dispatch_port.publish_alert(sample_cae, sample_decision)
        
        # 발송된 경보 확인
        assert len(mock_dispatch_port.published_alerts) == 1
        published_cae, published_decision = mock_dispatch_port.published_alerts[0]
        assert published_cae == sample_cae
        assert published_decision == sample_decision
    
    @pytest.mark.asyncio
    async def test_dispatch_port_multiple_alerts(self, mock_dispatch_port, sample_cae, sample_decision):
        """여러 경보 발송 테스트"""
        # 여러 경보 발송
        for i in range(5):
            cae = CAE(
                event_id=f"test_event_{i}",
                sent_at="2024-01-01T00:00:00Z",
                severity=Severity.MODERATE,
                areas=[Area(name=f"Test Area {i}", geometry=Geometry(type="Point", coordinates=[0, 0]))]
            )
            decision = Decision(trigger=True, reason=f"test_{i}", level="test")
            await mock_dispatch_port.publish_alert(cae, decision)
        
        # 모든 경보가 발송되었는지 확인
        assert len(mock_dispatch_port.published_alerts) == 5
    
    @pytest.mark.asyncio
    async def test_dispatch_port_error_handling(self, sample_cae, sample_decision):
        """경보 발송 포트 에러 처리 테스트"""
        class ErrorDispatchPort:
            async def publish_alert(self, cae: CAE, decision: Decision):
                """에러를 발생시키는 발송 메서드"""
                raise Exception("Dispatch error")
        
        error_port = ErrorDispatchPort()
        
        with pytest.raises(Exception, match="Dispatch error"):
            await error_port.publish_alert(sample_cae, sample_decision)
    
    @pytest.mark.asyncio
    async def test_dispatch_port_concurrent_access(self, sample_cae, sample_decision):
        """동시 접근 경보 발송 포트 테스트"""
        class ConcurrentDispatchPort:
            def __init__(self):
                self.published_alerts = []
                self.lock = asyncio.Lock()
            
            async def publish_alert(self, cae: CAE, decision: Decision):
                """동시 접근을 고려한 발송 메서드"""
                async with self.lock:
                    self.published_alerts.append((cae, decision))
        
        concurrent_port = ConcurrentDispatchPort()
        
        # 여러 태스크에서 동시에 발송
        tasks = []
        for i in range(10):
            cae = CAE(
                event_id=f"test_event_{i}",
                sent_at="2024-01-01T00:00:00Z",
                severity=Severity.MODERATE,
                areas=[Area(name=f"Test Area {i}", geometry=Geometry(type="Point", coordinates=[0, 0]))]
            )
            decision = Decision(trigger=True, reason=f"test_{i}", level="test")
            task = asyncio.create_task(concurrent_port.publish_alert(cae, decision))
            tasks.append(task)
        
        # 모든 작업 완료 대기
        await asyncio.gather(*tasks)
        
        # 모든 경보가 발송되었는지 확인
        assert len(concurrent_port.published_alerts) == 10


class TestKVStorePort:
    """키-값 저장소 포트 인터페이스 테스트"""
    
    @pytest.fixture
    def mock_kvstore_port(self):
        """테스트용 키-값 저장소 포트"""
        class MockKVStorePort:
            def __init__(self):
                self.store = {}
            
            async def get(self, key: str):
                """모킹된 조회 메서드"""
                return self.store.get(key)
            
            async def set(self, key: str, value: str, ttl_sec=None):
                """모킹된 저장 메서드"""
                self.store[key] = value
            
            async def delete(self, key: str):
                """모킹된 삭제 메서드"""
                if key in self.store:
                    del self.store[key]
        
        return MockKVStorePort()
    
    @pytest.mark.asyncio
    async def test_kvstore_port_interface(self, mock_kvstore_port):
        """키-값 저장소 포트 인터페이스 테스트"""
        # 인터페이스가 올바르게 구현되었는지 확인
        assert hasattr(mock_kvstore_port, 'get')
        assert hasattr(mock_kvstore_port, 'set')
        assert hasattr(mock_kvstore_port, 'delete')
        assert callable(mock_kvstore_port.get)
        assert callable(mock_kvstore_port.set)
        assert callable(mock_kvstore_port.delete)
    
    @pytest.mark.asyncio
    async def test_kvstore_port_implementation(self, mock_kvstore_port):
        """키-값 저장소 포트 구현 테스트"""
        # 값 저장
        await mock_kvstore_port.set("test_key", "test_value")
        
        # 값 조회
        value = await mock_kvstore_port.get("test_key")
        assert value == "test_value"
        
        # 값 삭제
        await mock_kvstore_port.delete("test_key")
        
        # 삭제 확인
        value = await mock_kvstore_port.get("test_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_kvstore_port_get_nonexistent_key(self, mock_kvstore_port):
        """존재하지 않는 키 조회 테스트"""
        value = await mock_kvstore_port.get("nonexistent_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_kvstore_port_set_with_ttl(self, mock_kvstore_port):
        """TTL과 함께 값 저장 테스트"""
        # TTL과 함께 저장 (실제 구현에서는 TTL 처리가 필요)
        await mock_kvstore_port.set("test_key", "test_value", ttl_sec=3600)
        
        # 값이 저장되었는지 확인
        value = await mock_kvstore_port.get("test_key")
        assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_kvstore_port_multiple_operations(self, mock_kvstore_port):
        """여러 작업 테스트"""
        # 여러 키-값 저장
        for i in range(10):
            await mock_kvstore_port.set(f"key_{i}", f"value_{i}")
        
        # 모든 값 조회
        for i in range(10):
            value = await mock_kvstore_port.get(f"key_{i}")
            assert value == f"value_{i}"
        
        # 모든 키 삭제
        for i in range(10):
            await mock_kvstore_port.delete(f"key_{i}")
        
        # 모든 값이 삭제되었는지 확인
        for i in range(10):
            value = await mock_kvstore_port.get(f"key_{i}")
            assert value is None
    
    @pytest.mark.asyncio
    async def test_kvstore_port_error_handling(self):
        """키-값 저장소 포트 에러 처리 테스트"""
        class ErrorKVStorePort:
            async def get(self, key: str):
                raise Exception("Get error")
            
            async def set(self, key: str, value: str, ttl_sec=None):
                raise Exception("Set error")
            
            async def delete(self, key: str):
                raise Exception("Delete error")
        
        error_port = ErrorKVStorePort()
        
        # 각 메서드에서 에러 발생 확인
        with pytest.raises(Exception, match="Get error"):
            await error_port.get("test_key")
        
        with pytest.raises(Exception, match="Set error"):
            await error_port.set("test_key", "test_value")
        
        with pytest.raises(Exception, match="Delete error"):
            await error_port.delete("test_key")
    
    @pytest.mark.asyncio
    async def test_kvstore_port_concurrent_access(self):
        """동시 접근 키-값 저장소 포트 테스트"""
        class ConcurrentKVStorePort:
            def __init__(self):
                self.store = {}
                self.lock = asyncio.Lock()
            
            async def get(self, key: str):
                async with self.lock:
                    return self.store.get(key)
            
            async def set(self, key: str, value: str, ttl_sec=None):
                async with self.lock:
                    self.store[key] = value
            
            async def delete(self, key: str):
                async with self.lock:
                    if key in self.store:
                        del self.store[key]
        
        concurrent_port = ConcurrentKVStorePort()
        
        # 동시에 여러 작업 수행
        tasks = []
        
        # 저장 작업
        for i in range(10):
            task = asyncio.create_task(concurrent_port.set(f"key_{i}", f"value_{i}"))
            tasks.append(task)
        
        # 모든 작업 완료 대기
        await asyncio.gather(*tasks)
        
        # 모든 값이 저장되었는지 확인
        for i in range(10):
            value = await concurrent_port.get(f"key_{i}")
            assert value == f"value_{i}"


class TestMetricsPort:
    """메트릭 포트 인터페이스 테스트"""
    
    @pytest.fixture
    def mock_metrics_port(self):
        """테스트용 메트릭 포트"""
        class MockMetricsPort:
            def __init__(self):
                self.counters = {}
                self.histograms = {}
                self.gauges = {}
            
            def increment_counter(self, name: str, value: int = 1, labels: dict = None):
                """모킹된 카운터 증가 메서드"""
                key = f"{name}:{labels or {}}"
                self.counters[key] = self.counters.get(key, 0) + value
            
            def record_histogram(self, name: str, value: float, labels: dict = None):
                """모킹된 히스토그램 기록 메서드"""
                key = f"{name}:{labels or {}}"
                if key not in self.histograms:
                    self.histograms[key] = []
                self.histograms[key].append(value)
            
            def set_gauge(self, name: str, value: float, labels: dict = None):
                """모킹된 게이지 설정 메서드"""
                key = f"{name}:{labels or {}}"
                self.gauges[key] = value
        
        return MockMetricsPort()
    
    def test_metrics_port_interface(self, mock_metrics_port):
        """메트릭 포트 인터페이스 테스트"""
        # 인터페이스가 올바르게 구현되었는지 확인
        assert hasattr(mock_metrics_port, 'increment_counter')
        assert hasattr(mock_metrics_port, 'record_histogram')
        assert hasattr(mock_metrics_port, 'set_gauge')
        assert callable(mock_metrics_port.increment_counter)
        assert callable(mock_metrics_port.record_histogram)
        assert callable(mock_metrics_port.set_gauge)
    
    def test_metrics_port_increment_counter(self, mock_metrics_port):
        """카운터 증가 테스트"""
        # 카운터 증가
        mock_metrics_port.increment_counter("test_counter")
        mock_metrics_port.increment_counter("test_counter", value=5)
        
        # 카운터 값 확인
        assert mock_metrics_port.counters["test_counter:{}"] == 6
    
    def test_metrics_port_increment_counter_with_labels(self, mock_metrics_port):
        """라벨과 함께 카운터 증가 테스트"""
        labels = {"service": "test", "method": "GET"}
        
        # 라벨과 함께 카운터 증가
        mock_metrics_port.increment_counter("test_counter", labels=labels)
        
        # 카운터 값 확인
        key = f"test_counter:{labels}"
        assert mock_metrics_port.counters[key] == 1
    
    def test_metrics_port_record_histogram(self, mock_metrics_port):
        """히스토그램 기록 테스트"""
        # 히스토그램 기록
        mock_metrics_port.record_histogram("test_histogram", 1.5)
        mock_metrics_port.record_histogram("test_histogram", 2.5)
        mock_metrics_port.record_histogram("test_histogram", 3.5)
        
        # 히스토그램 값 확인
        values = mock_metrics_port.histograms["test_histogram:{}"]
        assert len(values) == 3
        assert 1.5 in values
        assert 2.5 in values
        assert 3.5 in values
    
    def test_metrics_port_record_histogram_with_labels(self, mock_metrics_port):
        """라벨과 함께 히스토그램 기록 테스트"""
        labels = {"service": "test", "method": "POST"}
        
        # 라벨과 함께 히스토그램 기록
        mock_metrics_port.record_histogram("test_histogram", 1.0, labels=labels)
        
        # 히스토그램 값 확인
        key = f"test_histogram:{labels}"
        assert len(mock_metrics_port.histograms[key]) == 1
        assert mock_metrics_port.histograms[key][0] == 1.0
    
    def test_metrics_port_set_gauge(self, mock_metrics_port):
        """게이지 설정 테스트"""
        # 게이지 설정
        mock_metrics_port.set_gauge("test_gauge", 10.5)
        
        # 게이지 값 확인
        assert mock_metrics_port.gauges["test_gauge:{}"] == 10.5
        
        # 게이지 업데이트
        mock_metrics_port.set_gauge("test_gauge", 20.5)
        
        # 업데이트된 값 확인
        assert mock_metrics_port.gauges["test_gauge:{}"] == 20.5
    
    def test_metrics_port_set_gauge_with_labels(self, mock_metrics_port):
        """라벨과 함께 게이지 설정 테스트"""
        labels = {"service": "test", "instance": "1"}
        
        # 라벨과 함께 게이지 설정
        mock_metrics_port.set_gauge("test_gauge", 15.0, labels=labels)
        
        # 게이지 값 확인
        key = f"test_gauge:{labels}"
        assert mock_metrics_port.gauges[key] == 15.0
    
    def test_metrics_port_multiple_metrics(self, mock_metrics_port):
        """여러 메트릭 테스트"""
        # 다양한 메트릭 기록
        mock_metrics_port.increment_counter("requests_total", labels={"method": "GET"})
        mock_metrics_port.increment_counter("requests_total", labels={"method": "POST"})
        mock_metrics_port.record_histogram("request_duration", 0.1, labels={"method": "GET"})
        mock_metrics_port.record_histogram("request_duration", 0.2, labels={"method": "POST"})
        mock_metrics_port.set_gauge("active_connections", 5)
        mock_metrics_port.set_gauge("memory_usage", 0.8)
        
        # 모든 메트릭이 기록되었는지 확인
        assert len(mock_metrics_port.counters) == 2
        assert len(mock_metrics_port.histograms) == 2
        assert len(mock_metrics_port.gauges) == 2
    
    def test_metrics_port_error_handling(self):
        """메트릭 포트 에러 처리 테스트"""
        class ErrorMetricsPort:
            def increment_counter(self, name: str, value: int = 1, labels: dict = None):
                raise Exception("Counter error")
            
            def record_histogram(self, name: str, value: float, labels: dict = None):
                raise Exception("Histogram error")
            
            def set_gauge(self, name: str, value: float, labels: dict = None):
                raise Exception("Gauge error")
        
        error_port = ErrorMetricsPort()
        
        # 각 메서드에서 에러 발생 확인
        with pytest.raises(Exception, match="Counter error"):
            error_port.increment_counter("test_counter")
        
        with pytest.raises(Exception, match="Histogram error"):
            error_port.record_histogram("test_histogram", 1.0)
        
        with pytest.raises(Exception, match="Gauge error"):
            error_port.set_gauge("test_gauge", 1.0)


class TestPortIntegration:
    """포트 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_port_integration_workflow(self):
        """포트 통합 워크플로우 테스트"""
        # 모든 포트를 모킹
        class MockIngestPort:
            async def recv(self):
                yield {"test": "message"}
        
        class MockDispatchPort:
            def __init__(self):
                self.published_alerts = []
            
            async def publish_alert(self, cae: CAE, decision: Decision):
                self.published_alerts.append((cae, decision))
        
        class MockKVStorePort:
            def __init__(self):
                self.store = {}
            
            async def get(self, key: str):
                return self.store.get(key)
            
            async def set(self, key: str, value: str, ttl_sec=None):
                self.store[key] = value
            
            async def delete(self, key: str):
                if key in self.store:
                    del self.store[key]
        
        class MockMetricsPort:
            def __init__(self):
                self.counters = {}
            
            def increment_counter(self, name: str, value: int = 1, labels: dict = None):
                key = f"{name}:{labels or {}}"
                self.counters[key] = self.counters.get(key, 0) + value
        
        # 포트 인스턴스 생성
        ingest_port = MockIngestPort()
        dispatch_port = MockDispatchPort()
        kvstore_port = MockKVStorePort()
        metrics_port = MockMetricsPort()
        
        # 통합 워크플로우 실행
        async for message in ingest_port.recv():
            # 메시지 처리
            await kvstore_port.set("last_message", str(message))
            metrics_port.increment_counter("messages_processed")
            
            # 경보 발송 (모킹)
            cae = CAE(
                event_id="test_event",
                sent_at="2024-01-01T00:00:00Z",
                severity=Severity.MODERATE,
                areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
            )
            decision = Decision(trigger=True, reason="test", level="test")
            await dispatch_port.publish_alert(cae, decision)
        
        # 결과 확인
        assert len(dispatch_port.published_alerts) == 1
        assert metrics_port.counters["messages_processed:{}"] == 1
        assert await kvstore_port.get("last_message") == "{'test': 'message'}"
    
    @pytest.mark.asyncio
    async def test_port_integration_error_handling(self):
        """포트 통합 에러 처리 테스트"""
        class ErrorIngestPort:
            async def recv(self):
                raise Exception("Ingest error")
        
        class ErrorDispatchPort:
            async def publish_alert(self, cae: CAE, decision: Decision):
                raise Exception("Dispatch error")
        
        class ErrorKVStorePort:
            async def get(self, key: str):
                raise Exception("KVStore error")
            
            async def set(self, key: str, value: str, ttl_sec=None):
                raise Exception("KVStore error")
        
        class ErrorMetricsPort:
            def increment_counter(self, name: str, value: int = 1, labels: dict = None):
                raise Exception("Metrics error")
        
        # 에러 포트 인스턴스 생성
        error_ingest = ErrorIngestPort()
        error_dispatch = ErrorDispatchPort()
        error_kvstore = ErrorKVStorePort()
        error_metrics = ErrorMetricsPort()
        
        # 각 포트에서 에러 발생 확인
        with pytest.raises(Exception, match="Ingest error"):
            async for message in error_ingest.recv():
                pass
        
        cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity=Severity.MODERATE,
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        decision = Decision(trigger=True, reason="test", level="test")
        
        with pytest.raises(Exception, match="Dispatch error"):
            await error_dispatch.publish_alert(cae, decision)
        
        with pytest.raises(Exception, match="KVStore error"):
            await error_kvstore.get("test_key")
        
        with pytest.raises(Exception, match="KVStore error"):
            await error_kvstore.set("test_key", "test_value")
        
        with pytest.raises(Exception, match="Metrics error"):
            error_metrics.increment_counter("test_counter")
    
    @pytest.mark.asyncio
    async def test_port_integration_performance(self):
        """포트 통합 성능 테스트"""
        class PerformanceIngestPort:
            async def recv(self):
                for i in range(100):
                    yield {"test": f"message_{i}"}
        
        class PerformanceDispatchPort:
            def __init__(self):
                self.published_alerts = []
            
            async def publish_alert(self, cae: CAE, decision: Decision):
                self.published_alerts.append((cae, decision))
        
        class PerformanceKVStorePort:
            def __init__(self):
                self.store = {}
            
            async def get(self, key: str):
                return self.store.get(key)
            
            async def set(self, key: str, value: str, ttl_sec=None):
                self.store[key] = value
        
        class PerformanceMetricsPort:
            def __init__(self):
                self.counters = {}
            
            def increment_counter(self, name: str, value: int = 1, labels: dict = None):
                key = f"{name}:{labels or {}}"
                self.counters[key] = self.counters.get(key, 0) + value
        
        # 성능 포트 인스턴스 생성
        ingest_port = PerformanceIngestPort()
        dispatch_port = PerformanceDispatchPort()
        kvstore_port = PerformanceKVStorePort()
        metrics_port = PerformanceMetricsPort()
        
        # 성능 테스트 실행
        start_time = asyncio.get_event_loop().time()
        
        message_count = 0
        async for message in ingest_port.recv():
            message_count += 1
            
            # 메시지 처리
            await kvstore_port.set(f"message_{message_count}", str(message))
            metrics_port.increment_counter("messages_processed")
            
            # 경보 발송 (모킹)
            cae = CAE(
                event_id=f"test_event_{message_count}",
                sent_at="2024-01-01T00:00:00Z",
                severity=Severity.MODERATE,
                areas=[Area(name=f"Test Area {message_count}", geometry=Geometry(type="Point", coordinates=[0, 0]))]
            )
            decision = Decision(trigger=True, reason=f"test_{message_count}", level="test")
            await dispatch_port.publish_alert(cae, decision)
        
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        # 성능 확인
        assert message_count == 100
        assert len(dispatch_port.published_alerts) == 100
        assert metrics_port.counters["messages_processed:{}"] == 100
        assert processing_time < 5.0  # 5초 이내에 완료되어야 함
