"""
SQLite-based idempotency store for DX-Safety.

This module implements a SQLite-based idempotency store
for deduplication of alert messages.
"""

import aiosqlite
import time
from typing import Optional
from app.observability.logger import get_logger

log = get_logger("dxsafety.idem")

# SQLite 스키마
SCHEMA = """
CREATE TABLE IF NOT EXISTS idem (
    k TEXT PRIMARY KEY,
    exp INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_idem_exp ON idem(exp);
"""

class SQLiteIdemStore:
    """SQLite 기반 Idempotency 저장소"""
    
    def __init__(self, path: str, ttl_sec: int):
        """
        초기화합니다.
        
        Args:
            path: SQLite 데이터베이스 파일 경로
            ttl_sec: TTL 만료 시간 (초)
        """
        self.path = path
        self.ttl = ttl_sec
        log.info(f"SQLiteIdemStore 초기화: {path}, TTL: {ttl_sec}초")
    
    async def init(self) -> None:
        """데이터베이스를 초기화합니다."""
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            await db.commit()
        log.info(f"SQLiteIdemStore 스키마 초기화 완료")
    
    async def add_if_absent(self, key: str) -> bool:
        """
        키가 없으면 추가하고 True를 반환, 있으면 False를 반환합니다.
        
        Args:
            key: 추가할 키
            
        Returns:
            추가 성공 여부
        """
        now = int(time.time())
        exp = now + self.ttl
        
        try:
            async with aiosqlite.connect(self.path) as db:
                await db.execute(
                    "INSERT INTO idem (k, exp) VALUES (?, ?)",
                    (key, exp)
                )
                await db.commit()
                return True
        except aiosqlite.IntegrityError:
            # 키가 이미 존재함
            return False
        except Exception as e:
            log.error(f"SQLiteIdemStore add_if_absent 오류: {e}")
            return False
    
    async def gc(self, now: Optional[int] = None) -> int:
        """
        만료된 항목들을 정리합니다.
        
        Args:
            now: 현재 시간 (Unix timestamp), None이면 현재 시간 사용
            
        Returns:
            삭제된 항목 수
        """
        if now is None:
            now = int(time.time())
        
        try:
            async with aiosqlite.connect(self.path) as db:
                cursor = await db.execute(
                    "DELETE FROM idem WHERE exp < ?",
                    (now,)
                )
                await db.commit()
                deleted = cursor.rowcount
                if deleted > 0:
                    log.info(f"만료된 항목 {deleted}개 정리됨")
                return deleted
        except Exception as e:
            log.error(f"SQLiteIdemStore gc 오류: {e}")
            return 0
    
    async def get_count(self) -> int:
        """
        현재 저장된 항목 수를 반환합니다.
        
        Returns:
            항목 수
        """
        try:
            async with aiosqlite.connect(self.path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM idem")
                result = await cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            log.error(f"SQLiteIdemStore get_count 오류: {e}")
            return 0
