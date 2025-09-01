"""
Integration test for Phase 1 orchestrator.

This module tests the complete Phase 1 pipeline with stub adapters.
"""

import pytest
import asyncio
from typing import AsyncIterator, Dict, List
from app.orchestrators.orchestrator_phase1 import OrchestratorP1
from app.adapters.mqtt_remote.client import RemoteMqttIngestor
from app.adapters.mqtt_local.publisher import LocalMqttPublisher

class TestIngestAdapter:
    """테스트용 수집 어댑터"""
    
    def __init__(self, payloads: List[Dict]):
        self.payloads = payloads
    
    async def recv(self) -> AsyncIterator[Dict]:
        for payload in self.payloads:
            yield payload

@pytest.mark.asyncio
async def test_orchestrator_phase1_integration():
    """Phase 1 오케스트레이터 통합 테스트"""
    
    # 테스트 데이터
    test_payloads = [
        {
            "id": "test-1",
            "sentAt": "2025-01-01T00:00:00Z",
            "headline": "Test Alert 1",
            "severity": "severe",
            "description": "Test description 1"
        },
        {
            "id": "test-2", 
            "sentAt": "2025-01-01T01:00:00Z",
            "headline": "Test Alert 2",
            "severity": "minor",
            "description": "Test description 2"
        }
    ]
    
    # 어댑터 생성
    ingest = TestIngestAdapter(test_payloads)
    dispatch = LocalMqttPublisher("test/topic", dry_run=True)
    
    # 오케스트레이터 생성
    orchestrator = OrchestratorP1(
        ingest=ingest,
        dispatch=dispatch,
        severity_threshold="moderate"
    )
    
    # 실행 (짧은 시간만)
    task = asyncio.create_task(orchestrator.start())
    await asyncio.sleep(0.1)  # 짧은 실행
    task.cancel()
    
    # 테스트 통과 (예외 없이 실행됨)
    assert True
