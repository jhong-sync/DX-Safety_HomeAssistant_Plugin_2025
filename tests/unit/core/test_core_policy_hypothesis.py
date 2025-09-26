"""
hypothesis를 활용한 policy 모듈 테스트

이 모듈은 hypothesis 패키지를 사용하여 
정책 평가 함수들의 속성 기반 테스트를 수행합니다.
"""

import pytest
from hypothesis import given, strategies as st, settings, example
from hypothesis.strategies import composite, lists, text, integers, floats, booleans
from typing import List, Dict, Any, Optional, Tuple
from pydantic import ValidationError

from app.core.policy import evaluate, SEVERITY_ORDER
from app.core.models import CAE, Area, Geometry, Decision, Severity


class TestPolicyEvaluation:
    """정책 평가 함수 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        threshold=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_evaluate_severity_comparison(self, event_id: str, sent_at: str, 
                                         severity: Severity, threshold: Severity):
        """심각도 비교 평가 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        decision = evaluate(cae, threshold=threshold)
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        
        # 심각도 순서에 따른 트리거 확인
        expected_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER[threshold]
        assert decision.trigger == expected_trigger
        
        # 이유 문자열 확인
        if expected_trigger:
            assert f"severity({severity}) >= threshold({threshold})" in decision.reason
        else:
            assert "below threshold" in decision.reason
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_evaluate_default_threshold(self, event_id: str, sent_at: str, severity: Severity):
        """기본 임계값으로 평가 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        decision = evaluate(cae)  # 기본 임계값 "moderate" 사용
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        
        # 기본 임계값 "moderate"와 비교
        expected_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER["moderate"]
        assert decision.trigger == expected_trigger
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        threshold=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_evaluate_trigger_logic(self, event_id: str, sent_at: str, 
                                  severity: Severity, threshold: Severity):
        """트리거 로직 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        decision = evaluate(cae, threshold=threshold)
        
        # 심각도 순서 확인
        severity_order = SEVERITY_ORDER[severity]
        threshold_order = SEVERITY_ORDER[threshold]
        
        if severity_order >= threshold_order:
            assert decision.trigger is True
            assert ">=" in decision.reason
        else:
            assert decision.trigger is False
            assert "below threshold" in decision.reason
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        threshold=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_evaluate_reason_field(self, event_id: str, sent_at: str, 
                                 severity: Severity, threshold: Severity):
        """이유 필드 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        decision = evaluate(cae, threshold=threshold)
        
        assert isinstance(decision.reason, str)
        assert len(decision.reason) > 0
        
        # 이유에 심각도와 임계값이 포함되어야 함 (트리거된 경우에만)
        if decision.trigger:
            assert severity in decision.reason
            assert threshold in decision.reason
        else:
            # 트리거되지 않은 경우 "below threshold" 메시지 확인
            assert "below threshold" in decision.reason
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        threshold=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_evaluate_level_field(self, event_id: str, sent_at: str, 
                                severity: Severity, threshold: Severity):
        """레벨 필드 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        decision = evaluate(cae, threshold=threshold)
        
        assert decision.level == severity
        assert decision.level in ["minor", "moderate", "severe", "critical"]


class TestPolicyEdgeCases:
    """정책 평가 엣지 케이스 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50)
    )
    def test_evaluate_minor_severity(self, event_id: str, sent_at: str):
        """최소 심각도 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity="minor")
        
        # 모든 임계값에 대해 테스트
        for threshold in ["minor", "moderate", "severe", "critical"]:
            decision = evaluate(cae, threshold=threshold)
            
            if threshold == "minor":
                assert decision.trigger is True
            else:
                assert decision.trigger is False
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50)
    )
    def test_evaluate_critical_severity(self, event_id: str, sent_at: str):
        """최대 심각도 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity="critical")
        
        # 모든 임계값에 대해 테스트
        for threshold in ["minor", "moderate", "severe", "critical"]:
            decision = evaluate(cae, threshold=threshold)
            assert decision.trigger is True  # critical은 항상 트리거
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_evaluate_same_severity_threshold(self, event_id: str, sent_at: str, severity: Severity):
        """동일한 심각도와 임계값 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        decision = evaluate(cae, threshold=severity)
        
        assert decision.trigger is True  # 동일하면 트리거
        assert f"severity({severity}) >= threshold({severity})" in decision.reason
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        threshold=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_evaluate_boundary_conditions(self, event_id: str, sent_at: str, 
                                       severity: Severity, threshold: Severity):
        """경계 조건 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        decision = evaluate(cae, threshold=threshold)
        
        # 경계 조건 확인
        severity_order = SEVERITY_ORDER[severity]
        threshold_order = SEVERITY_ORDER[threshold]
        
        if severity_order == threshold_order:
            assert decision.trigger is True
        elif severity_order > threshold_order:
            assert decision.trigger is True
        else:
            assert decision.trigger is False


class TestPolicyWithAreas:
    """영역이 있는 CAE로 정책 평가 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        threshold=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        areas=st.lists(
            st.builds(
                Area,
                name=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
                geometry=st.builds(
                    Geometry,
                    type=st.sampled_from(["Point", "Polygon"]),
                    coordinates=st.lists(st.floats(min_value=-180, max_value=180), min_size=2, max_size=10)
                )
            ),
            max_size=5
        )
    )
    def test_evaluate_with_areas(self, event_id: str, sent_at: str, severity: Severity,
                                threshold: Severity, areas: List[Area]):
        """영역이 있는 CAE로 평가 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity, areas=areas)
        
        decision = evaluate(cae, threshold=threshold)
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        assert len(cae.areas) == len(areas)
        
        # 영역 정보는 평가에 영향을 주지 않아야 함 (심각도만 고려)
        expected_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER[threshold]
        assert decision.trigger == expected_trigger
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        threshold=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_evaluate_empty_areas(self, event_id: str, sent_at: str, severity: Severity,
                                threshold: Severity):
        """빈 영역 리스트로 평가 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity, areas=[])
        
        decision = evaluate(cae, threshold=threshold)
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        assert cae.areas == []
        
        # 빈 영역 리스트는 평가에 영향을 주지 않아야 함
        expected_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER[threshold]
        assert decision.trigger == expected_trigger


class TestPolicyConsistency:
    """정책 평가 일관성 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_evaluate_consistency(self, event_id: str, sent_at: str, severity: Severity):
        """평가 일관성 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        # 여러 번 평가해도 결과가 동일해야 함
        decision1 = evaluate(cae, threshold="moderate")
        decision2 = evaluate(cae, threshold="moderate")
        
        assert decision1.trigger == decision2.trigger
        assert decision1.reason == decision2.reason
        assert decision1.level == decision2.level
    
    def test_evaluate_threshold_order(self):
        """임계값 순서 테스트"""
        # minor 심각도로 테스트
        cae = CAE(event_id="test", sent_at="2024-01-01T00:00:00Z", severity="minor")
        
        # minor 임계값에서는 트리거됨
        decision_minor = evaluate(cae, threshold="minor")
        assert decision_minor.trigger is True
        
        # moderate 임계값에서는 트리거되지 않음
        decision_moderate = evaluate(cae, threshold="moderate")
        assert decision_moderate.trigger is False
        
        # severe 임계값에서는 트리거되지 않음
        decision_severe = evaluate(cae, threshold="severe")
        assert decision_severe.trigger is False
        
        # critical 임계값에서는 트리거되지 않음
        decision_critical = evaluate(cae, threshold="critical")
        assert decision_critical.trigger is False
        
        # moderate 심각도로 테스트
        cae_moderate = CAE(event_id="test", sent_at="2024-01-01T00:00:00Z", severity="moderate")
        
        # minor, moderate 임계값에서는 트리거됨
        assert evaluate(cae_moderate, threshold="minor").trigger is True
        assert evaluate(cae_moderate, threshold="moderate").trigger is True
        
        # severe, critical 임계값에서는 트리거되지 않음
        assert evaluate(cae_moderate, threshold="severe").trigger is False
        assert evaluate(cae_moderate, threshold="critical").trigger is False


class TestPolicyProperties:
    """정책 평가 속성 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        threshold=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_evaluate_monotonicity(self, event_id: str, sent_at: str, 
                                 severity: Severity, threshold: Severity):
        """단조성 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        decision = evaluate(cae, threshold=threshold)
        
        # 심각도가 높을수록 트리거 확률이 높아야 함
        severity_order = SEVERITY_ORDER[severity]
        threshold_order = SEVERITY_ORDER[threshold]
        
        if severity_order >= threshold_order:
            assert decision.trigger is True
        else:
            assert decision.trigger is False
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_evaluate_reflexivity(self, event_id: str, sent_at: str, severity: Severity):
        """반사성 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        # 동일한 심각도와 임계값으로 평가
        decision = evaluate(cae, threshold=severity)
        
        assert decision.trigger is True  # 반사성: severity >= severity는 항상 True
        assert decision.level == severity
