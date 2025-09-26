"""
hypothesis를 활용한 geo_policy 모듈 테스트

이 모듈은 hypothesis 패키지를 사용하여 
지리적 정책 평가 함수들의 속성 기반 테스트를 수행합니다.
"""

import pytest
from hypothesis import given, strategies as st, settings, example
from hypothesis.strategies import composite, lists, text, integers, floats, booleans, tuples
from typing import List, Dict, Any, Optional, Tuple
from pydantic import ValidationError

from app.core.geo_policy import evaluate_geographic_policy, evaluate_simple_policy, SEVERITY_ORDER
from app.core.models import CAE, Area, Geometry, Decision, Severity


class TestGeographicPolicyEvaluation:
    """지리적 정책 평가 함수 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        severity_threshold=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        distance_threshold=st.floats(min_value=0.1, max_value=100.0),
        polygon_buffer=st.floats(min_value=0.0, max_value=10.0),
        mode=st.sampled_from(["AND", "OR"])
    )
    def test_evaluate_geographic_policy_basic(self, event_id: str, sent_at: str, 
                                            severity: Severity, severity_threshold: str,
                                            distance_threshold: float, polygon_buffer: float,
                                            mode: str):
        """기본 지리적 정책 평가 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        decision = evaluate_geographic_policy(
            cae,
            severity_threshold=severity_threshold,
            distance_threshold_km=distance_threshold,
            polygon_buffer_km=polygon_buffer,
            mode=mode
        )
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        assert isinstance(decision.trigger, bool)
        assert isinstance(decision.reason, str)
        assert len(decision.reason) > 0
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        home_lat=st.floats(min_value=-90, max_value=90),
        home_lon=st.floats(min_value=-180, max_value=180),
        alert_lat=st.floats(min_value=-90, max_value=90),
        alert_lon=st.floats(min_value=-180, max_value=180),
        distance_threshold=st.floats(min_value=0.1, max_value=100.0)
    )
    def test_evaluate_geographic_policy_with_point(self, event_id: str, sent_at: str,
                                                  severity: Severity, home_lat: float, home_lon: float,
                                                  alert_lat: float, alert_lon: float,
                                                  distance_threshold: float):
        """Point 형상으로 지리적 정책 평가 테스트"""
        # Point 형상 영역 생성
        geometry = Geometry(type="Point", coordinates=[alert_lon, alert_lat])
        area = Area(name="Test Area", geometry=geometry)
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity, areas=[area])
        
        decision = evaluate_geographic_policy(
            cae,
            home_coordinates=(home_lat, home_lon),
            distance_threshold_km=distance_threshold,
            mode="AND"
        )
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        
        # 심각도 평가 결과 확인
        severity_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER["moderate"]
        
        # 지리적 평가는 거리에 따라 결정됨
        # 실제 거리 계산은 haversine_distance 함수에 의존
        if severity_trigger:
            assert "severity" in decision.reason
        else:
            assert "below threshold" in decision.reason or "no_geographic_match" in decision.reason
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        home_lat=st.floats(min_value=-90, max_value=90),
        home_lon=st.floats(min_value=-180, max_value=180),
        polygon_coords=st.lists(
            st.tuples(
                st.floats(min_value=-180, max_value=180),
                st.floats(min_value=-90, max_value=90)
            ),
            min_size=3,
            max_size=10
        ),
        polygon_buffer=st.floats(min_value=0.0, max_value=10.0)
    )
    def test_evaluate_geographic_policy_with_polygon(self, event_id: str, sent_at: str,
                                                   severity: Severity, home_lat: float, home_lon: float,
                                                   polygon_coords: List[Tuple[float, float]],
                                                   polygon_buffer: float):
        """Polygon 형상으로 지리적 정책 평가 테스트"""
        # Polygon 형상 영역 생성
        geometry = Geometry(type="Polygon", coordinates=[polygon_coords])
        area = Area(name="Test Polygon Area", geometry=geometry)
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity, areas=[area])
        
        decision = evaluate_geographic_policy(
            cae,
            home_coordinates=(home_lat, home_lon),
            polygon_buffer_km=polygon_buffer,
            mode="AND"
        )
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        
        # 심각도 평가 결과 확인
        severity_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER["moderate"]
        
        if severity_trigger:
            assert "severity" in decision.reason
        else:
            assert "below threshold" in decision.reason or "no_geographic_match" in decision.reason
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        mode=st.sampled_from(["AND", "OR"])
    )
    def test_evaluate_geographic_policy_no_home_coordinates(self, event_id: str, sent_at: str,
                                                           severity: Severity, mode: str):
        """홈 좌표가 없는 지리적 정책 평가 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        decision = evaluate_geographic_policy(cae, mode=mode)
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        
        # 홈 좌표가 없으면 심각도만 평가됨
        severity_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER["moderate"]
        
        if mode == "AND":
            assert decision.trigger is False  # 지리적 평가가 False이므로 AND는 False
        else:  # OR
            assert decision.trigger == severity_trigger  # 심각도만 평가됨
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        home_lat=st.floats(min_value=-90, max_value=90),
        home_lon=st.floats(min_value=-180, max_value=180)
    )
    def test_evaluate_geographic_policy_invalid_home_coordinates(self, event_id: str, sent_at: str,
                                                               severity: Severity, home_lat: float, home_lon: float):
        """잘못된 홈 좌표로 지리적 정책 평가 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        # 잘못된 좌표 (범위를 벗어난 값)
        invalid_coords = (home_lat + 200, home_lon + 200)  # 범위를 벗어나도록 조정
        
        decision = evaluate_geographic_policy(cae, home_coordinates=invalid_coords)
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        
        # 잘못된 좌표는 무시되고 심각도만 평가됨
        severity_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER["moderate"]
        assert decision.trigger == severity_trigger


class TestSimplePolicyEvaluation:
    """단순 정책 평가 함수 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        severity_threshold=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_evaluate_simple_policy(self, event_id: str, sent_at: str, 
                                  severity: Severity, severity_threshold: str):
        """단순 정책 평가 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        decision = evaluate_simple_policy(cae, severity_threshold=severity_threshold)
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        
        # 심각도 비교 결과 확인
        expected_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER[severity_threshold]
        assert decision.trigger == expected_trigger
        
        # 이유 확인
        if expected_trigger:
            assert f"severity({severity}) >= threshold({severity_threshold})" in decision.reason
        else:
            assert "below threshold" in decision.reason
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_evaluate_simple_policy_default_threshold(self, event_id: str, sent_at: str, severity: Severity):
        """기본 임계값으로 단순 정책 평가 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        decision = evaluate_simple_policy(cae)  # 기본 임계값 "moderate" 사용
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        
        # 기본 임계값 "moderate"와 비교
        expected_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER["moderate"]
        assert decision.trigger == expected_trigger


class TestGeographicPolicyMode:
    """지리적 정책 모드 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        home_lat=st.floats(min_value=-90, max_value=90),
        home_lon=st.floats(min_value=-180, max_value=180),
        alert_lat=st.floats(min_value=-90, max_value=90),
        alert_lon=st.floats(min_value=-180, max_value=180),
        distance_threshold=st.floats(min_value=0.1, max_value=100.0)
    )
    def test_evaluate_geographic_policy_and_mode(self, event_id: str, sent_at: str,
                                               severity: Severity, home_lat: float, home_lon: float,
                                               alert_lat: float, alert_lon: float,
                                               distance_threshold: float):
        """AND 모드로 지리적 정책 평가 테스트"""
        geometry = Geometry(type="Point", coordinates=[alert_lon, alert_lat])
        area = Area(name="Test Area", geometry=geometry)
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity, areas=[area])
        
        decision = evaluate_geographic_policy(
            cae,
            home_coordinates=(home_lat, home_lon),
            distance_threshold_km=distance_threshold,
            mode="AND"
        )
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        
        # AND 모드에서는 심각도와 지리적 조건 모두 만족해야 함
        severity_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER["moderate"]
        
        if decision.trigger:
            assert "AND" in decision.reason
        else:
            assert "below threshold" in decision.reason or "no_geographic_match" in decision.reason
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        home_lat=st.floats(min_value=-90, max_value=90),
        home_lon=st.floats(min_value=-180, max_value=180),
        alert_lat=st.floats(min_value=-90, max_value=90),
        alert_lon=st.floats(min_value=-180, max_value=180),
        distance_threshold=st.floats(min_value=0.1, max_value=100.0)
    )
    def test_evaluate_geographic_policy_or_mode(self, event_id: str, sent_at: str,
                                              severity: Severity, home_lat: float, home_lon: float,
                                              alert_lat: float, alert_lon: float,
                                              distance_threshold: float):
        """OR 모드로 지리적 정책 평가 테스트"""
        geometry = Geometry(type="Point", coordinates=[alert_lon, alert_lat])
        area = Area(name="Test Area", geometry=geometry)
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity, areas=[area])
        
        decision = evaluate_geographic_policy(
            cae,
            home_coordinates=(home_lat, home_lon),
            distance_threshold_km=distance_threshold,
            mode="OR"
        )
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        
        # OR 모드에서는 심각도 또는 지리적 조건 중 하나만 만족하면 됨
        severity_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER["moderate"]
        
        if decision.trigger:
            assert "OR" in decision.reason or "severity" in decision.reason
        else:
            assert "below threshold" in decision.reason and "no_geographic_match" in decision.reason


class TestGeographicPolicyEdgeCases:
    """지리적 정책 엣지 케이스 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_evaluate_geographic_policy_empty_areas(self, event_id: str, sent_at: str, severity: Severity):
        """빈 영역 리스트로 지리적 정책 평가 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity, areas=[])
        
        decision = evaluate_geographic_policy(cae)
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        
        # 빈 영역 리스트는 지리적 평가에 영향을 주지 않아야 함
        severity_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER["moderate"]
        assert decision.trigger == severity_trigger
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        home_lat=st.floats(min_value=-90, max_value=90),
        home_lon=st.floats(min_value=-180, max_value=180)
    )
    def test_evaluate_geographic_policy_zero_distance_threshold(self, event_id: str, sent_at: str,
                                                             severity: Severity, home_lat: float, home_lon: float):
        """거리 임계값이 0인 지리적 정책 평가 테스트"""
        # 홈 좌표와 동일한 위치의 Point 영역 생성
        geometry = Geometry(type="Point", coordinates=[home_lon, home_lat])
        area = Area(name="Same Location", geometry=geometry)
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity, areas=[area])
        
        decision = evaluate_geographic_policy(
            cae,
            home_coordinates=(home_lat, home_lon),
            distance_threshold_km=0.0,
            mode="AND"
        )
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        
        # 거리 임계값이 0이면 정확히 같은 위치에서만 트리거됨
        severity_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER["moderate"]
        
        if decision.trigger:
            assert "distance(0.00km)" in decision.reason or "severity" in decision.reason
        else:
            assert "below threshold" in decision.reason or "no_geographic_match" in decision.reason
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        home_lat=st.floats(min_value=-90, max_value=90),
        home_lon=st.floats(min_value=-180, max_value=180)
    )
    def test_evaluate_geographic_policy_large_distance_threshold(self, event_id: str, sent_at: str,
                                                               severity: Severity, home_lat: float, home_lon: float):
        """큰 거리 임계값으로 지리적 정책 평가 테스트"""
        # 홈 좌표와 다른 위치의 Point 영역 생성
        geometry = Geometry(type="Point", coordinates=[home_lon + 1, home_lat + 1])
        area = Area(name="Different Location", geometry=geometry)
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity, areas=[area])
        
        decision = evaluate_geographic_policy(
            cae,
            home_coordinates=(home_lat, home_lon),
            distance_threshold_km=1000.0,  # 매우 큰 거리 임계값
            mode="AND"
        )
        
        assert isinstance(decision, Decision)
        assert decision.level == severity
        
        # 큰 거리 임계값이면 대부분의 위치에서 트리거됨
        severity_trigger = SEVERITY_ORDER[severity] >= SEVERITY_ORDER["moderate"]
        
        if decision.trigger:
            assert "distance" in decision.reason or "severity" in decision.reason
        else:
            assert "below threshold" in decision.reason


class TestGeographicPolicyConsistency:
    """지리적 정책 일관성 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        home_lat=st.floats(min_value=-90, max_value=90),
        home_lon=st.floats(min_value=-180, max_value=180)
    )
    def test_evaluate_geographic_policy_consistency(self, event_id: str, sent_at: str,
                                                  severity: Severity, home_lat: float, home_lon: float):
        """지리적 정책 평가 일관성 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        # 여러 번 평가해도 결과가 동일해야 함
        decision1 = evaluate_geographic_policy(cae, home_coordinates=(home_lat, home_lon))
        decision2 = evaluate_geographic_policy(cae, home_coordinates=(home_lat, home_lon))
        
        assert decision1.trigger == decision2.trigger
        assert decision1.level == decision2.level
        # 이유는 동일할 수 있지만 항상 같지는 않을 수 있음 (거리 계산 정밀도 등)
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_simple_vs_geographic_policy_consistency(self, event_id: str, sent_at: str, severity: Severity):
        """단순 정책과 지리적 정책 일관성 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        simple_decision = evaluate_simple_policy(cae)
        geographic_decision = evaluate_geographic_policy(cae)  # 홈 좌표 없음
        
        # 홈 좌표가 없으면 지리적 정책은 단순 정책과 동일해야 함
        assert simple_decision.trigger == geographic_decision.trigger
        assert simple_decision.level == geographic_decision.level
