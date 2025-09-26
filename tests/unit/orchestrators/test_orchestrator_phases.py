"""
Orchestrator Phase 모듈 단위 테스트

이 모듈은 Phase 1-5 오케스트레이터들의 기능을 테스트합니다.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from app.orchestrators.orchestrator_phase1 import OrchestratorP1
from app.orchestrators.orchestrator_phase2 import OrchestratorP2
from app.orchestrators.orchestrator_phase3 import OrchestratorP3
from app.orchestrators.orchestrator_phase4 import OrchestratorP4
from app.orchestrators.orchestrator_phase5 import OrchestratorP5
from app.core.models import CAE, Decision, Area, Geometry


class TestOrchestratorPhase1:
    """Phase 1 오케스트레이터 테스트"""
    
    @pytest.fixture
    def orchestrator_p1(self):
        """테스트용 Phase 1 오케스트레이터"""
        mock_deps = {
            'ingest': AsyncMock(),
            'dispatch': AsyncMock()
        }
        return OrchestratorP1(**mock_deps, severity_threshold="moderate")
    
    def test_orchestrator_p1_initialization(self, orchestrator_p1):
        """Phase 1 오케스트레이터 초기화 테스트"""
        assert orchestrator_p1.threshold == "moderate"
        assert orchestrator_p1.ingest is not None
        assert orchestrator_p1.dispatch is not None
    
    def test_orchestrator_p1_initialization_with_custom_threshold(self):
        """사용자 정의 임계값으로 Phase 1 오케스트레이터 초기화 테스트"""
        mock_deps = {
            'ingest': AsyncMock(),
            'dispatch': AsyncMock()
        }
        orchestrator = OrchestratorP1(**mock_deps, severity_threshold="severe")
        assert orchestrator.threshold == "severe"
    
    @pytest.mark.asyncio
    async def test_orchestrator_p1_start(self, orchestrator_p1):
        """Phase 1 오케스트레이터 시작 테스트"""
        # 스트림 모킹
        mock_message = {"test": "message"}
        orchestrator_p1._stream = AsyncMock(return_value=[mock_message].__aiter__())
        
        # 의존성 모킹
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity="moderate",
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        mock_decision = Decision(trigger=True, reason="test", level="test")
        
        with patch('app.core.normalize.to_cae', return_value=mock_cae) as mock_to_cae:
            with patch('app.core.policy.evaluate', return_value=mock_decision) as mock_evaluate:
                orchestrator_p1.dispatch.publish_alert = AsyncMock()
                
                # 시작 실행
                await orchestrator_p1.start()
                
                # 정규화와 정책 평가가 호출되었는지 확인
                mock_to_cae.assert_called_with(mock_message)
                mock_evaluate.assert_called_with(mock_cae, threshold="moderate")
                orchestrator_p1.dispatch.publish_alert.assert_called_with(mock_cae, mock_decision)
    
    @pytest.mark.asyncio
    async def test_orchestrator_p1_start_with_no_trigger(self, orchestrator_p1):
        """트리거되지 않은 경우 Phase 1 오케스트레이터 테스트"""
        mock_message = {"test": "message"}
        orchestrator_p1._stream = AsyncMock(return_value=[mock_message].__aiter__())
        
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity="moderate",
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        mock_decision = Decision(trigger=False, reason="test", level="test")
        
        with patch('app.core.normalize.to_cae', return_value=mock_cae):
            with patch('app.core.policy.evaluate', return_value=mock_decision):
                orchestrator_p1.dispatch.publish_alert = AsyncMock()
                
                # 시작 실행
                await orchestrator_p1.start()
                
                # 트리거되지 않았으므로 발송되지 않아야 함
                orchestrator_p1.dispatch.publish_alert.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_orchestrator_p1_stream(self, orchestrator_p1):
        """Phase 1 오케스트레이터 스트림 테스트"""
        mock_message = {"test": "message"}
        orchestrator_p1.ingest.recv.return_value = [mock_message].__aiter__()
        
        # 스트림 실행
        messages = []
        async for msg in orchestrator_p1._stream():
            messages.append(msg)
        
        # 메시지가 스트림되었는지 확인
        assert len(messages) == 1
        assert messages[0] == mock_message


class TestOrchestratorPhase2:
    """Phase 2 오케스트레이터 테스트"""
    
    @pytest.fixture
    def orchestrator_p2(self):
        """테스트용 Phase 2 오케스트레이터"""
        mock_deps = {
            'ingest': AsyncMock(),
            'dispatch': AsyncMock(),
            'kvstore': AsyncMock()
        }
        return OrchestratorP2(**mock_deps, severity_threshold="moderate")
    
    def test_orchestrator_p2_initialization(self, orchestrator_p2):
        """Phase 2 오케스트레이터 초기화 테스트"""
        assert orchestrator_p2.threshold == "moderate"
        assert orchestrator_p2.ingest is not None
        assert orchestrator_p2.dispatch is not None
        assert orchestrator_p2.kvstore is not None
    
    @pytest.mark.asyncio
    async def test_orchestrator_p2_start(self, orchestrator_p2):
        """Phase 2 오케스트레이터 시작 테스트"""
        mock_message = {"test": "message"}
        orchestrator_p2._stream = AsyncMock(return_value=[mock_message].__aiter__())
        
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity="moderate",
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        mock_decision = Decision(trigger=True, reason="test", level="test")
        
        with patch('app.core.normalize.to_cae', return_value=mock_cae):
            with patch('app.core.policy.evaluate', return_value=mock_decision):
                orchestrator_p2.kvstore.get = AsyncMock(return_value=None)
                orchestrator_p2.kvstore.set = AsyncMock()
                orchestrator_p2.dispatch.publish_alert = AsyncMock()
                
                # 시작 실행
                await orchestrator_p2.start()
                
                # KVStore 작업이 호출되었는지 확인
                orchestrator_p2.kvstore.get.assert_called()
                orchestrator_p2.kvstore.set.assert_called()
                orchestrator_p2.dispatch.publish_alert.assert_called()


class TestOrchestratorPhase3:
    """Phase 3 오케스트레이터 테스트"""
    
    @pytest.fixture
    def orchestrator_p3(self):
        """테스트용 Phase 3 오케스트레이터"""
        mock_deps = {
            'ingest': AsyncMock(),
            'dispatch': AsyncMock(),
            'kvstore': AsyncMock()
        }
        return OrchestratorP3(**mock_deps, severity_threshold="moderate")
    
    def test_orchestrator_p3_initialization(self, orchestrator_p3):
        """Phase 3 오케스트레이터 초기화 테스트"""
        assert orchestrator_p3.threshold == "moderate"
        assert orchestrator_p3.ingest is not None
        assert orchestrator_p3.dispatch is not None
        assert orchestrator_p3.kvstore is not None
    
    @pytest.mark.asyncio
    async def test_orchestrator_p3_start(self, orchestrator_p3):
        """Phase 3 오케스트레이터 시작 테스트"""
        mock_message = {"test": "message"}
        orchestrator_p3._stream = AsyncMock(return_value=[mock_message].__aiter__())
        
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity="moderate",
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        mock_decision = Decision(trigger=True, reason="test", level="test")
        
        with patch('app.core.normalize.to_cae', return_value=mock_cae):
            with patch('app.core.policy.evaluate', return_value=mock_decision):
                orchestrator_p3.kvstore.get = AsyncMock(return_value=None)
                orchestrator_p3.kvstore.set = AsyncMock()
                orchestrator_p3.dispatch.publish_alert = AsyncMock()
                
                # 시작 실행
                await orchestrator_p3.start()
                
                # KVStore 작업이 호출되었는지 확인
                orchestrator_p3.kvstore.get.assert_called()
                orchestrator_p3.kvstore.set.assert_called()
                orchestrator_p3.dispatch.publish_alert.assert_called()


class TestOrchestratorPhase4:
    """Phase 4 오케스트레이터 테스트"""
    
    @pytest.fixture
    def orchestrator_p4(self):
        """테스트용 Phase 4 오케스트레이터"""
        mock_deps = {
            'ingest': AsyncMock(),
            'dispatch': AsyncMock(),
            'kvstore': AsyncMock()
        }
        return OrchestratorP4(**mock_deps, severity_threshold="moderate")
    
    def test_orchestrator_p4_initialization(self, orchestrator_p4):
        """Phase 4 오케스트레이터 초기화 테스트"""
        assert orchestrator_p4.threshold == "moderate"
        assert orchestrator_p4.ingest is not None
        assert orchestrator_p4.dispatch is not None
        assert orchestrator_p4.kvstore is not None
    
    @pytest.mark.asyncio
    async def test_orchestrator_p4_start(self, orchestrator_p4):
        """Phase 4 오케스트레이터 시작 테스트"""
        mock_message = {"test": "message"}
        orchestrator_p4._stream = AsyncMock(return_value=[mock_message].__aiter__())
        
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity="moderate",
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        mock_decision = Decision(trigger=True, reason="test", level="test")
        
        with patch('app.core.normalize.to_cae', return_value=mock_cae):
            with patch('app.core.policy.evaluate', return_value=mock_decision):
                orchestrator_p4.kvstore.get = AsyncMock(return_value=None)
                orchestrator_p4.kvstore.set = AsyncMock()
                orchestrator_p4.dispatch.publish_alert = AsyncMock()
                
                # 시작 실행
                await orchestrator_p4.start()
                
                # KVStore 작업이 호출되었는지 확인
                orchestrator_p4.kvstore.get.assert_called()
                orchestrator_p4.kvstore.set.assert_called()
                orchestrator_p4.dispatch.publish_alert.assert_called()


class TestOrchestratorPhase5:
    """Phase 5 오케스트레이터 테스트"""
    
    @pytest.fixture
    def orchestrator_p5(self):
        """테스트용 Phase 5 오케스트레이터"""
        mock_deps = {
            'ingest': AsyncMock(),
            'dispatch': AsyncMock(),
            'kvstore': AsyncMock()
        }
        return OrchestratorP5(**mock_deps, severity_threshold="moderate")
    
    def test_orchestrator_p5_initialization(self, orchestrator_p5):
        """Phase 5 오케스트레이터 초기화 테스트"""
        assert orchestrator_p5.threshold == "moderate"
        assert orchestrator_p5.ingest is not None
        assert orchestrator_p5.dispatch is not None
        assert orchestrator_p5.kvstore is not None
    
    @pytest.mark.asyncio
    async def test_orchestrator_p5_start(self, orchestrator_p5):
        """Phase 5 오케스트레이터 시작 테스트"""
        mock_message = {"test": "message"}
        orchestrator_p5._stream = AsyncMock(return_value=[mock_message].__aiter__())
        
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity="moderate",
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        mock_decision = Decision(trigger=True, reason="test", level="test")
        
        with patch('app.core.normalize.to_cae', return_value=mock_cae):
            with patch('app.core.policy.evaluate', return_value=mock_decision):
                orchestrator_p5.kvstore.get = AsyncMock(return_value=None)
                orchestrator_p5.kvstore.set = AsyncMock()
                orchestrator_p5.dispatch.publish_alert = AsyncMock()
                
                # 시작 실행
                await orchestrator_p5.start()
                
                # KVStore 작업이 호출되었는지 확인
                orchestrator_p5.kvstore.get.assert_called()
                orchestrator_p5.kvstore.set.assert_called()
                orchestrator_p5.dispatch.publish_alert.assert_called()


class TestOrchestratorPhaseErrorHandling:
    """Phase 오케스트레이터 에러 처리 테스트"""
    
    @pytest.fixture
    def orchestrator_p1(self):
        """테스트용 Phase 1 오케스트레이터"""
        mock_deps = {
            'ingest': AsyncMock(),
            'dispatch': AsyncMock()
        }
        return OrchestratorP1(**mock_deps, severity_threshold="moderate")
    
    @pytest.mark.asyncio
    async def test_orchestrator_phase_error_handling(self, orchestrator_p1):
        """Phase 오케스트레이터 에러 처리 테스트"""
        # 에러를 발생시키는 모킹
        orchestrator_p1._stream.side_effect = Exception("Stream error")
        
        with pytest.raises(Exception, match="Stream error"):
            await orchestrator_p1.start()
    
    @pytest.mark.asyncio
    async def test_orchestrator_phase_normalize_error_handling(self, orchestrator_p1):
        """정규화 에러 처리 테스트"""
        mock_message = {"test": "message"}
        orchestrator_p1._stream = AsyncMock(return_value=[mock_message].__aiter__())
        
        with patch('app.core.normalize.to_cae', side_effect=Exception("Normalize error")):
            with pytest.raises(Exception, match="Normalize error"):
                await orchestrator_p1.start()
    
    @pytest.mark.asyncio
    async def test_orchestrator_phase_policy_error_handling(self, orchestrator_p1):
        """정책 평가 에러 처리 테스트"""
        mock_message = {"test": "message"}
        orchestrator_p1._stream = AsyncMock(return_value=[mock_message].__aiter__())
        
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity="moderate",
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        
        with patch('app.core.normalize.to_cae', return_value=mock_cae):
            with patch('app.core.policy.evaluate', side_effect=Exception("Policy error")):
                with pytest.raises(Exception, match="Policy error"):
                    await orchestrator_p1.start()
    
    @pytest.mark.asyncio
    async def test_orchestrator_phase_dispatch_error_handling(self, orchestrator_p1):
        """발송 에러 처리 테스트"""
        mock_message = {"test": "message"}
        orchestrator_p1._stream = AsyncMock(return_value=[mock_message].__aiter__())
        
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity="moderate",
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        mock_decision = Decision(trigger=True, reason="test", level="test")
        
        with patch('app.core.normalize.to_cae', return_value=mock_cae):
            with patch('app.core.policy.evaluate', return_value=mock_decision):
                orchestrator_p1.dispatch.publish_alert.side_effect = Exception("Dispatch error")
                
                with pytest.raises(Exception, match="Dispatch error"):
                    await orchestrator_p1.start()


class TestOrchestratorPhasePerformance:
    """Phase 오케스트레이터 성능 테스트"""
    
    @pytest.fixture
    def orchestrator_p1(self):
        """테스트용 Phase 1 오케스트레이터"""
        mock_deps = {
            'ingest': AsyncMock(),
            'dispatch': AsyncMock()
        }
        return OrchestratorP1(**mock_deps, severity_threshold="moderate")
    
    @pytest.mark.asyncio
    async def test_orchestrator_phase_performance(self, orchestrator_p1):
        """Phase 오케스트레이터 성능 테스트"""
        # 여러 메시지로 성능 테스트
        mock_messages = [{"test": f"message_{i}"} for i in range(10)]
        orchestrator_p1._stream = AsyncMock(return_value=mock_messages.__aiter__())
        
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity="moderate",
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        mock_decision = Decision(trigger=True, reason="test", level="test")
        
        with patch('app.core.normalize.to_cae', return_value=mock_cae):
            with patch('app.core.policy.evaluate', return_value=mock_decision):
                orchestrator_p1.dispatch.publish_alert = AsyncMock()
                
                # 시작 실행
                await orchestrator_p1.start()
                
                # 모든 메시지가 처리되었는지 확인
                assert orchestrator_p1.dispatch.publish_alert.call_count == 10
    
    @pytest.mark.asyncio
    async def test_orchestrator_phase_concurrent_processing(self, orchestrator_p1):
        """Phase 오케스트레이터 동시 처리 테스트"""
        # 동시 처리 테스트
        mock_message = {"test": "message"}
        orchestrator_p1._stream = AsyncMock(return_value=[mock_message].__aiter__())
        
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity="moderate",
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        mock_decision = Decision(trigger=True, reason="test", level="test")
        
        with patch('app.core.normalize.to_cae', return_value=mock_cae):
            with patch('app.core.policy.evaluate', return_value=mock_decision):
                orchestrator_p1.dispatch.publish_alert = AsyncMock()
                
                # 여러 태스크로 동시 실행
                tasks = [asyncio.create_task(orchestrator_p1.start()) for _ in range(3)]
                
                # 모든 태스크가 완료되도록 짧은 시간 후 취소
                await asyncio.sleep(0.1)
                for task in tasks:
                    task.cancel()
                
                # 모든 태스크가 정상적으로 취소되었는지 확인
                for task in tasks:
                    assert task.cancelled()
