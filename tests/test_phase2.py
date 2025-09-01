"""
Tests for Phase 2 components.

This module contains tests for the reliability features
including idempotency, outbox, and retry mechanisms.
"""

import pytest
import asyncio
import tempfile
import time
from app.adapters.storage.sqlite_idem import SQLiteIdemStore
from app.adapters.storage.sqlite_outbox import SQLiteOutbox
from app.common.retry import exponential_backoff, retry_with_backoff

@pytest.mark.asyncio
async def test_sqlite_idem_store_basic():
    """SQLiteIdemStore 기본 기능 테스트"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        store = SQLiteIdemStore(db_path, ttl_sec=3600)
        await store.init()
        
        # 키 추가 테스트
        assert await store.add_if_absent("test_key_1") is True
        assert await store.add_if_absent("test_key_1") is False  # 중복
        
        # 다른 키 추가
        assert await store.add_if_absent("test_key_2") is True
        
        # 개수 확인
        assert await store.get_count() == 2
        
    finally:
        import os
        os.unlink(db_path)

@pytest.mark.asyncio
async def test_sqlite_outbox_basic():
    """SQLiteOutbox 기본 기능 테스트"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        outbox = SQLiteOutbox(db_path)
        await outbox.init()
        
        # 메시지 추가
        oid1 = await outbox.enqueue("test/topic", b"test_payload", qos=1, retain=False)
        oid2 = await outbox.enqueue("test/topic2", b"test_payload2", qos=2, retain=True)
        
        assert oid1 == 1
        assert oid2 == 2
        
        # 가장 오래된 항목 조회
        item = await outbox.peek_oldest()
        assert item is not None
        assert item.id == 1
        assert item.topic == "test/topic"
        assert item.payload == b"test_payload"
        assert item.qos == 1
        assert item.retain is False
        assert item.attempts == 0
        
        # 시도 횟수 증가
        await outbox.mark_attempt(1)
        item = await outbox.peek_oldest()
        assert item.attempts == 1
        
        # 항목 삭제
        await outbox.delete(1)
        assert await outbox.get_count() == 1
        
    finally:
        import os
        os.unlink(db_path)

@pytest.mark.asyncio
async def test_exponential_backoff():
    """지수 백오프 테스트"""
    start_time = time.time()
    
    await exponential_backoff(1, 0.1, 1.0)
    
    elapsed = time.time() - start_time
    assert 0.09 <= elapsed <= 0.11  # 약 0.1초 지연
    
    start_time = time.time()
    await exponential_backoff(2, 0.1, 1.0)
    
    elapsed = time.time() - start_time
    assert 0.19 <= elapsed <= 0.22  # 약 0.2초 지연 (여유 시간 추가)

@pytest.mark.asyncio
async def test_retry_with_backoff():
    """재시도 백오프 테스트"""
    attempt_count = 0
    
    async def failing_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ValueError("임시 오류")
        return "성공"
    
    # 재시도 성공 테스트
    result = await retry_with_backoff(failing_function, max_retries=3, base_delay=0.01)
    assert result == "성공"
    assert attempt_count == 3
    
    # 재시도 실패 테스트
    attempt_count = 0
    
    async def always_failing_function():
        nonlocal attempt_count
        attempt_count += 1
        raise ValueError("영구 오류")
    
    with pytest.raises(ValueError, match="영구 오류"):
        await retry_with_backoff(always_failing_function, max_retries=2, base_delay=0.01)
    
    assert attempt_count == 3  # 1번 시도 + 2번 재시도
