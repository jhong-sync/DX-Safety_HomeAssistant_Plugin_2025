"""
SQLite-based outbox for DX-Safety.

This module implements a SQLite-based outbox pattern
for durable message queuing and delivery.
"""

import aiosqlite
import json
import time
from dataclasses import dataclass
from typing import Optional, List
from app.observability.logger import get_logger

log = get_logger("dxsafety.outbox")

# SQLite 스키마
SCHEMA = """
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    payload BLOB NOT NULL,
    qos INTEGER NOT NULL DEFAULT 1,
    retain INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_outbox_created ON outbox(created_at);
"""

@dataclass
class OutboxItem:
    """Outbox 항목"""
    id: int
    topic: str
    payload: bytes
    qos: int
    retain: bool
    attempts: int

class SQLiteOutbox:
    """SQLite 기반 Outbox"""
    
    def __init__(self, path: str):
        """
        초기화합니다.
        
        Args:
            path: SQLite 데이터베이스 파일 경로
        """
        self.path = path
        log.info(f"SQLiteOutbox 초기화: {path}")
    
    async def init(self) -> None:
        """데이터베이스를 초기화합니다."""
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            await db.commit()
        log.info(f"SQLiteOutbox 스키마 초기화 완료: {self.path}")
    
    async def enqueue(self, topic: str, payload: bytes, qos: int = 1, retain: bool = False) -> int:
        """
        메시지를 Outbox에 추가합니다.
        
        Args:
            topic: MQTT 토픽
            payload: 메시지 페이로드
            qos: QoS 레벨
            retain: retain 플래그
            
        Returns:
            생성된 항목의 ID
        """
        now = int(time.time())
        
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "INSERT INTO outbox (topic, payload, qos, retain, created_at) VALUES (?, ?, ?, ?, ?)",
                (topic, payload, qos, 1 if retain else 0, now)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def peek_oldest(self) -> Optional[OutboxItem]:
        """
        가장 오래된 항목을 조회합니다 (삭제하지 않음).
        
        Returns:
            가장 오래된 OutboxItem 또는 None
        """
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT id, topic, payload, qos, retain, attempts FROM outbox ORDER BY created_at ASC LIMIT 1"
            )
            row = await cursor.fetchone()
            
            if row:
                return OutboxItem(
                    id=row[0],
                    topic=row[1],
                    payload=row[2],
                    qos=row[3],
                    retain=bool(row[4]),
                    attempts=row[5]
                )
            return None
    
    async def mark_attempt(self, oid: int) -> None:
        """
        발송 시도 횟수를 증가시킵니다.
        
        Args:
            oid: Outbox 항목 ID
        """
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE outbox SET attempts = attempts + 1 WHERE id = ?",
                (oid,)
            )
            await db.commit()
    
    async def delete(self, oid: int) -> None:
        """
        항목을 삭제합니다 (성공적으로 발송된 경우).
        
        Args:
            oid: 삭제할 Outbox 항목 ID
        """
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM outbox WHERE id = ?", (oid,))
            await db.commit()
    
    async def get_count(self) -> int:
        """
        현재 저장된 항목 수를 반환합니다.
        
        Returns:
            항목 수
        """
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM outbox")
            result = await cursor.fetchone()
            return result[0] if result else 0
