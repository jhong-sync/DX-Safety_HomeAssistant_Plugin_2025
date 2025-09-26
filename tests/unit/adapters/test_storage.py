"""
Storage Adapter 모듈 단위 테스트

이 모듈은 SQLite 기반 저장소 어댑터들의 기능을 테스트합니다.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import AsyncMock, Mock, patch
from app.adapters.storage.sqlite_outbox import SQLiteOutbox, OutboxItem
from app.adapters.storage.sqlite_idem import SQLiteIdemStore


class TestSQLiteOutbox:
    """SQLite Outbox 테스트"""
    
    @pytest.fixture
    def temp_db_path(self):
        """임시 데이터베이스 파일 경로"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # 테스트 후 파일 정리
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def outbox(self, temp_db_path):
        """테스트용 SQLite Outbox"""
        return SQLiteOutbox(temp_db_path)
    
    @pytest.mark.asyncio
    async def test_outbox_initialization(self, outbox, temp_db_path):
        """Outbox 초기화 테스트"""
        assert outbox.path == temp_db_path
    
    @pytest.mark.asyncio
    async def test_outbox_init_schema(self, outbox):
        """Outbox 스키마 초기화 테스트"""
        await outbox.init()
        
        # 스키마가 생성되었는지 확인
        assert os.path.exists(outbox.path)
    
    @pytest.mark.asyncio
    async def test_outbox_enqueue_message(self, outbox):
        """Outbox 메시지 추가 테스트"""
        await outbox.init()
        
        topic = "test/topic"
        payload = b'{"test": "message"}'
        qos = 1
        retain = False
        
        # 메시지 추가
        message_id = await outbox.enqueue(topic, payload, qos, retain)
        
        assert message_id is not None
        assert message_id > 0
    
    @pytest.mark.asyncio
    async def test_outbox_enqueue_message_with_retain(self, outbox):
        """retain 플래그가 있는 메시지 추가 테스트"""
        await outbox.init()
        
        topic = "test/topic"
        payload = b'{"test": "message"}'
        qos = 2
        retain = True
        
        # 메시지 추가
        message_id = await outbox.enqueue(topic, payload, qos, retain)
        
        assert message_id is not None
        
        # 메시지 조회하여 retain 플래그 확인
        item = await outbox.peek_oldest()
        assert item is not None
        assert item.retain is True
        assert item.qos == 2
    
    @pytest.mark.asyncio
    async def test_outbox_peek_oldest(self, outbox):
        """가장 오래된 메시지 조회 테스트"""
        await outbox.init()
        
        # 여러 메시지 추가
        await outbox.enqueue("topic1", b"message1", 1, False)
        await outbox.enqueue("topic2", b"message2", 1, False)
        await outbox.enqueue("topic3", b"message3", 1, False)
        
        # 가장 오래된 메시지 조회
        item = await outbox.peek_oldest()
        
        assert item is not None
        assert item.topic == "topic1"
        assert item.payload == b"message1"
        assert item.qos == 1
        assert item.retain is False
    
    @pytest.mark.asyncio
    async def test_outbox_peek_oldest_empty(self, outbox):
        """빈 Outbox에서 조회 테스트"""
        await outbox.init()
        
        # 빈 상태에서 조회
        item = await outbox.peek_oldest()
        
        assert item is None
    
    @pytest.mark.asyncio
    async def test_outbox_mark_sent(self, outbox):
        """메시지 발송 완료 표시 테스트"""
        await outbox.init()
        
        # 메시지 추가
        message_id = await outbox.enqueue("test/topic", b"test message", 1, False)
        
        # 발송 완료 표시
        await outbox.mark_sent(message_id)
        
        # 메시지가 삭제되었는지 확인
        item = await outbox.peek_oldest()
        assert item is None
    
    @pytest.mark.asyncio
    async def test_outbox_mark_failed(self, outbox):
        """메시지 발송 실패 표시 테스트"""
        await outbox.init()
        
        # 메시지 추가
        message_id = await outbox.enqueue("test/topic", b"test message", 1, False)
        
        # 발송 실패 표시
        await outbox.mark_failed(message_id)
        
        # 메시지가 여전히 존재하는지 확인
        item = await outbox.peek_oldest()
        assert item is not None
        assert item.id == message_id
        assert item.attempts == 1
    
    @pytest.mark.asyncio
    async def test_outbox_get_pending(self, outbox):
        """대기 중인 메시지 조회 테스트"""
        await outbox.init()
        
        # 여러 메시지 추가
        await outbox.enqueue("topic1", b"message1", 1, False)
        await outbox.enqueue("topic2", b"message2", 1, False)
        await outbox.enqueue("topic3", b"message3", 1, False)
        
        # 대기 중인 메시지 조회
        pending_items = await outbox.get_pending()
        
        assert len(pending_items) == 3
        assert all(isinstance(item, OutboxItem) for item in pending_items)
    
    @pytest.mark.asyncio
    async def test_outbox_concurrent_access(self, outbox):
        """동시 접근 테스트"""
        await outbox.init()
        
        # 동시에 여러 메시지 추가
        tasks = []
        for i in range(10):
            task = asyncio.create_task(
                outbox.enqueue(f"topic{i}", f"message{i}".encode(), 1, False)
            )
            tasks.append(task)
        
        # 모든 작업 완료 대기
        message_ids = await asyncio.gather(*tasks)
        
        # 모든 메시지가 추가되었는지 확인
        assert len(message_ids) == 10
        assert all(msg_id is not None for msg_id in message_ids)
        
        # 모든 메시지가 조회되는지 확인
        pending_items = await outbox.get_pending()
        assert len(pending_items) == 10
    
    @pytest.mark.asyncio
    async def test_outbox_transaction_handling(self, outbox):
        """트랜잭션 처리 테스트"""
        await outbox.init()
        
        # 메시지 추가
        message_id = await outbox.enqueue("test/topic", b"test message", 1, False)
        
        # 메시지 조회
        item = await outbox.peek_oldest()
        assert item is not None
        
        # 발송 완료 표시
        await outbox.mark_sent(message_id)
        
        # 메시지가 삭제되었는지 확인
        item = await outbox.peek_oldest()
        assert item is None
    
    @pytest.mark.asyncio
    async def test_outbox_error_recovery(self, outbox):
        """에러 복구 테스트"""
        await outbox.init()
        
        # 잘못된 메시지 ID로 발송 완료 표시 시도
        await outbox.mark_sent(99999)  # 존재하지 않는 ID
        
        # 에러가 발생하지 않는지 확인
        assert True  # 예외가 발생하지 않으면 성공
    
    @pytest.mark.asyncio
    async def test_outbox_large_payload(self, outbox):
        """큰 페이로드 처리 테스트"""
        await outbox.init()
        
        # 큰 페이로드 생성
        large_payload = b"x" * 10000
        
        # 큰 메시지 추가
        message_id = await outbox.enqueue("test/topic", large_payload, 1, False)
        
        assert message_id is not None
        
        # 메시지 조회하여 페이로드 확인
        item = await outbox.peek_oldest()
        assert item is not None
        assert item.payload == large_payload
        assert len(item.payload) == 10000


class TestSQLiteIdemStore:
    """SQLite Idempotency Store 테스트"""
    
    @pytest.fixture
    def temp_db_path(self):
        """임시 데이터베이스 파일 경로"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # 테스트 후 파일 정리
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def idem_store(self, temp_db_path):
        """테스트용 SQLite Idempotency Store"""
        return SQLiteIdemStore(temp_db_path, ttl_sec=3600)
    
    @pytest.mark.asyncio
    async def test_idem_store_initialization(self, idem_store, temp_db_path):
        """Idempotency Store 초기화 테스트"""
        assert idem_store.path == temp_db_path
        assert idem_store.ttl == 3600
    
    @pytest.mark.asyncio
    async def test_idem_store_init_schema(self, idem_store):
        """Idempotency Store 스키마 초기화 테스트"""
        await idem_store.init()
        
        # 스키마가 생성되었는지 확인
        assert os.path.exists(idem_store.path)
    
    @pytest.mark.asyncio
    async def test_idem_store_add_if_absent_new_key(self, idem_store):
        """새로운 키 추가 테스트"""
        await idem_store.init()
        
        key = "test_key_1"
        
        # 새로운 키 추가
        result = await idem_store.add_if_absent(key)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_idem_store_add_if_absent_existing_key(self, idem_store):
        """기존 키 추가 시도 테스트"""
        await idem_store.init()
        
        key = "test_key_2"
        
        # 첫 번째 추가
        result1 = await idem_store.add_if_absent(key)
        assert result1 is True
        
        # 두 번째 추가 시도 (중복)
        result2 = await idem_store.add_if_absent(key)
        assert result2 is False
    
    @pytest.mark.asyncio
    async def test_idem_store_add_if_absent_multiple_keys(self, idem_store):
        """여러 키 추가 테스트"""
        await idem_store.init()
        
        keys = [f"test_key_{i}" for i in range(10)]
        
        # 모든 키 추가
        results = []
        for key in keys:
            result = await idem_store.add_if_absent(key)
            results.append(result)
        
        # 모든 키가 성공적으로 추가되었는지 확인
        assert all(results)
        assert len(results) == 10
    
    @pytest.mark.asyncio
    async def test_idem_store_gc_expired_items(self, idem_store):
        """만료된 항목 정리 테스트"""
        await idem_store.init()
        
        # 만료된 키 추가 (과거 시간으로 설정)
        with patch('time.time', return_value=1000):
            await idem_store.add_if_absent("expired_key")
        
        # 현재 시간으로 정리 실행
        with patch('time.time', return_value=2000):
            deleted_count = await idem_store.gc()
        
        assert deleted_count == 1
    
    @pytest.mark.asyncio
    async def test_idem_store_gc_no_expired_items(self, idem_store):
        """만료된 항목이 없는 경우 정리 테스트"""
        await idem_store.init()
        
        # 현재 시간으로 키 추가
        await idem_store.add_if_absent("current_key")
        
        # 정리 실행
        deleted_count = await idem_store.gc()
        
        assert deleted_count == 0
    
    @pytest.mark.asyncio
    async def test_idem_store_ttl_handling(self, idem_store):
        """TTL 처리 테스트"""
        await idem_store.init()
        
        key = "ttl_test_key"
        
        # 키 추가
        result = await idem_store.add_if_absent(key)
        assert result is True
        
        # TTL이 지나기 전에는 중복으로 간주되어야 함
        result = await idem_store.add_if_absent(key)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_idem_store_concurrent_access(self, idem_store):
        """동시 접근 테스트"""
        await idem_store.init()
        
        # 동시에 여러 키 추가
        tasks = []
        for i in range(10):
            task = asyncio.create_task(
                idem_store.add_if_absent(f"concurrent_key_{i}")
            )
            tasks.append(task)
        
        # 모든 작업 완료 대기
        results = await asyncio.gather(*tasks)
        
        # 모든 키가 성공적으로 추가되었는지 확인
        assert all(results)
        assert len(results) == 10
    
    @pytest.mark.asyncio
    async def test_idem_store_error_handling(self, idem_store):
        """에러 처리 테스트"""
        await idem_store.init()
        
        # 잘못된 데이터베이스 경로로 에러 시뮬레이션
        invalid_store = SQLiteIdemStore("/invalid/path/database.db", ttl_sec=3600)
        
        # 에러가 발생해도 시스템이 중단되지 않는지 확인
        result = await invalid_store.add_if_absent("test_key")
        assert result is False  # 에러 발생 시 False 반환
    
    @pytest.mark.asyncio
    async def test_idem_store_custom_ttl(self):
        """사용자 정의 TTL 테스트"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        
        try:
            # 짧은 TTL로 설정
            idem_store = SQLiteIdemStore(temp_path, ttl_sec=1)
            await idem_store.init()
            
            key = "short_ttl_key"
            
            # 키 추가
            result = await idem_store.add_if_absent(key)
            assert result is True
            
            # 1초 후에는 중복으로 간주되어야 함
            await asyncio.sleep(1.1)
            result = await idem_store.add_if_absent(key)
            assert result is False
            
            # 정리 실행
            deleted_count = await idem_store.gc()
            assert deleted_count == 1
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestStorageIntegration:
    """Storage 통합 테스트"""
    
    @pytest.fixture
    def temp_db_path(self):
        """임시 데이터베이스 파일 경로"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # 테스트 후 파일 정리
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def outbox(self, temp_db_path):
        """테스트용 SQLite Outbox"""
        return SQLiteOutbox(temp_db_path)
    
    @pytest.fixture
    def idem_store(self, temp_db_path):
        """테스트용 SQLite Idempotency Store"""
        return SQLiteIdemStore(temp_db_path, ttl_sec=3600)
    
    @pytest.mark.asyncio
    async def test_storage_integration_outbox_and_idem(self, outbox, idem_store):
        """Outbox와 Idempotency Store 통합 테스트"""
        # 두 저장소 모두 초기화
        await outbox.init()
        await idem_store.init()
        
        # 메시지 키 생성
        message_key = "test_message_key"
        
        # 중복 체크
        is_new = await idem_store.add_if_absent(message_key)
        assert is_new is True
        
        # 메시지를 Outbox에 추가
        message_id = await outbox.enqueue("test/topic", b"test message", 1, False)
        assert message_id is not None
        
        # 동일한 키로 중복 체크
        is_new = await idem_store.add_if_absent(message_key)
        assert is_new is False
        
        # 메시지 발송 완료 표시
        await outbox.mark_sent(message_id)
        
        # 메시지가 삭제되었는지 확인
        item = await outbox.peek_oldest()
        assert item is None
    
    @pytest.mark.asyncio
    async def test_storage_integration_concurrent_access(self, outbox, idem_store):
        """동시 접근 통합 테스트"""
        await outbox.init()
        await idem_store.init()
        
        # 동시에 여러 작업 수행
        tasks = []
        
        # Outbox 작업
        for i in range(5):
            task = asyncio.create_task(
                outbox.enqueue(f"topic{i}", f"message{i}".encode(), 1, False)
            )
            tasks.append(task)
        
        # Idempotency Store 작업
        for i in range(5):
            task = asyncio.create_task(
                idem_store.add_if_absent(f"key{i}")
            )
            tasks.append(task)
        
        # 모든 작업 완료 대기
        results = await asyncio.gather(*tasks)
        
        # 모든 작업이 성공했는지 확인
        assert len(results) == 10
        assert all(result is not None for result in results)
        
        # Outbox에 메시지가 추가되었는지 확인
        pending_items = await outbox.get_pending()
        assert len(pending_items) == 5
    
    @pytest.mark.asyncio
    async def test_storage_integration_error_recovery(self, outbox, idem_store):
        """에러 복구 통합 테스트"""
        await outbox.init()
        await idem_store.init()
        
        # 정상적인 작업
        message_key = "error_test_key"
        is_new = await idem_store.add_if_absent(message_key)
        assert is_new is True
        
        message_id = await outbox.enqueue("test/topic", b"test message", 1, False)
        assert message_id is not None
        
        # 에러 시뮬레이션 후 복구
        # 잘못된 메시지 ID로 발송 완료 표시 시도
        await outbox.mark_sent(99999)  # 존재하지 않는 ID
        
        # 원래 메시지는 여전히 존재해야 함
        item = await outbox.peek_oldest()
        assert item is not None
        assert item.id == message_id
        
        # 정상적인 발송 완료 표시
        await outbox.mark_sent(message_id)
        
        # 메시지가 삭제되었는지 확인
        item = await outbox.peek_oldest()
        assert item is None
    
    @pytest.mark.asyncio
    async def test_storage_integration_performance(self, outbox, idem_store):
        """성능 통합 테스트"""
        await outbox.init()
        await idem_store.init()
        
        # 대량의 데이터 처리
        start_time = asyncio.get_event_loop().time()
        
        # 100개의 메시지와 키 처리
        tasks = []
        for i in range(100):
            # Outbox 작업
            task1 = asyncio.create_task(
                outbox.enqueue(f"topic{i}", f"message{i}".encode(), 1, False)
            )
            tasks.append(task1)
            
            # Idempotency Store 작업
            task2 = asyncio.create_task(
                idem_store.add_if_absent(f"key{i}")
            )
            tasks.append(task2)
        
        # 모든 작업 완료 대기
        results = await asyncio.gather(*tasks)
        
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        # 성능 확인
        assert len(results) == 200
        assert all(result is not None for result in results)
        assert processing_time < 5.0  # 5초 이내에 완료되어야 함
        
        # 데이터 확인
        pending_items = await outbox.get_pending()
        assert len(pending_items) == 100
