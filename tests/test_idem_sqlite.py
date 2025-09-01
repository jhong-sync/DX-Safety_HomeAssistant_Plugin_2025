"""
SQLite Idempotency 저장소 테스트.
"""

import asyncio
import time
import pytest
import tempfile
import os
from app.adapters.storage.sqlite_idem import SQLiteIdemStore


@pytest.mark.asyncio
async def test_sqlite_idem_store_init():
    """SQLiteIdemStore 초기화 테스트."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        store = SQLiteIdemStore(db_path, ttl_sec=3600)
        await store.init()
        
        # 초기화 후 항목 수가 0인지 확인
        count = await store.get_count()
        assert count == 0
    finally:
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_add_if_absent_basic():
    """기본적인 add_if_absent 기능 테스트."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        store = SQLiteIdemStore(db_path, ttl_sec=3600)
        await store.init()
        
        # 첫 번째 추가는 성공해야 함
        result1 = await store.add_if_absent("test_key_1")
        assert result1 is True
        
        # 같은 키로 다시 추가하면 실패해야 함
        result2 = await store.add_if_absent("test_key_1")
        assert result2 is False
        
        # 다른 키는 성공해야 함
        result3 = await store.add_if_absent("test_key_2")
        assert result3 is True
        
        # 총 항목 수가 2개여야 함
        count = await store.get_count()
        assert count == 2
    finally:
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_add_if_absent_and_gc():
    """add_if_absent와 GC 기능 테스트."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        store = SQLiteIdemStore(db_path, ttl_sec=1)  # 1초 TTL
        await store.init()
        
        # 키 추가
        assert await store.add_if_absent("k1") is True
        assert await store.add_if_absent("k1") is False  # 중복
        
        # TTL보다 긴 시간 대기 후 GC 실행
        await asyncio.sleep(1.2)
        
        # GC를 명시적으로 미래 시간으로 실행하여 확실히 삭제
        future_time = int(time.time()) + 10
        deleted = await store.gc(now=future_time)
        assert deleted >= 1
        
        # GC 후 항목 수가 0이어야 함
        count = await store.get_count()
        assert count == 0
    finally:
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_gc_with_custom_time():
    """사용자 정의 시간으로 GC 테스트."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        store = SQLiteIdemStore(db_path, ttl_sec=3600)
        await store.init()
        
        # 키 추가
        await store.add_if_absent("k1")
        
        # 과거 시간으로 GC 실행 (삭제되지 않아야 함)
        past_time = int(time.time()) - 7200  # 2시간 전
        deleted = await store.gc(now=past_time)
        assert deleted == 0
        
        # 미래 시간으로 GC 실행 (삭제되어야 함)
        future_time = int(time.time()) + 7200  # 2시간 후
        deleted = await store.gc(now=future_time)
        assert deleted >= 1
    finally:
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_concurrent_add_if_absent():
    """동시 add_if_absent 테스트."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        store = SQLiteIdemStore(db_path, ttl_sec=3600)
        await store.init()
        
        # 동시에 같은 키를 여러 번 추가
        async def add_key(key):
            return await store.add_if_absent(key)
        
        # 같은 키를 동시에 여러 번 추가
        tasks = [add_key("concurrent_key") for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # 하나만 True이고 나머지는 False여야 함
        true_count = sum(1 for r in results if r)
        assert true_count == 1
        
        # 총 항목 수가 1개여야 함
        count = await store.get_count()
        assert count == 1
    finally:
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_error_handling():
    """에러 처리 테스트."""
    # 존재하지 않는 경로로 초기화 시도
    store = SQLiteIdemStore("/nonexistent/path/test.db", ttl_sec=3600)
    
    # 초기화 실패 시 예외 발생
    with pytest.raises(Exception):
        await store.init()
    
    # 에러 상황에서 add_if_absent는 False 반환
    result = await store.add_if_absent("test_key")
    assert result is False
