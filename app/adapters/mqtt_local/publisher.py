"""
Local MQTT publisher adapter stub.

This module provides a stub implementation of AlertDispatchPort
for local MQTT publishing (dry-run capable).
"""

from typing import Optional
from app.core.models import CAE, Decision

class LocalMqttPublisher:
    """로컬 MQTT 발송 어댑터 (스텁)"""
    
    def __init__(self, topic_prefix: str, dry_run: bool = True):
        """
        초기화합니다.
        
        Args:
            topic_prefix: MQTT 토픽 접두사
            dry_run: 드라이 런 모드 여부
        """
        self.topic_prefix = topic_prefix.rstrip("/")
        self.dry_run = dry_run
    
    async def publish_alert(self, cae: CAE, decision: Decision) -> None:
        """
        경보를 발송합니다.
        
        Args:
            cae: 경보 데이터
            decision: 정책 평가 결과
        """
        if self.dry_run:
            # 드라이 런 모드에서는 로그만 출력
            print(f"[DRY_RUN] Would publish to {self.topic_prefix}/alerts/{decision.level}")
            print(f"  Event ID: {cae.event_id}")
            print(f"  Severity: {decision.level}")
            print(f"  Reason: {decision.reason}")
            return
        
        # 실제 구현 시 MQTT 발송 로직 추가
        pass
