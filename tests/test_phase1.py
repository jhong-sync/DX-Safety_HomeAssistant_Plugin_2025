"""
Basic tests for Phase 1 components.

This module contains basic tests for the core domain models,
normalization functions, and policy evaluation.
"""

import pytest
from app.core.models import CAE, Decision, Area, Geometry, Severity
from app.core import normalize, policy

def test_cae_model():
    """CAE 모델 테스트"""
    # 기본 CAE 생성
    cae = CAE(
        event_id="test-123",
        sent_at="2025-01-01T00:00:00Z",
        headline="Test Alert",
        severity="moderate",
        description="Test description"
    )
    
    assert cae.event_id == "test-123"
    assert cae.severity == "moderate"
    assert cae.headline == "Test Alert"

def test_normalize_to_cae():
    """정규화 함수 테스트"""
    # 원시 데이터
    raw = {
        "id": "test-123",
        "sentAt": "2025-01-01T00:00:00Z",
        "headline": "Test Alert",
        "severity": "severe",
        "description": "Test description"
    }
    
    # 정규화
    cae = normalize.to_cae(raw)
    
    assert cae.event_id == "test-123"
    assert cae.sent_at == "2025-01-01T00:00:00Z"
    assert cae.severity == "severe"
    assert cae.headline == "Test Alert"

def test_policy_evaluate():
    """정책 평가 함수 테스트"""
    # 테스트 CAE
    cae = CAE(
        event_id="test-123",
        sent_at="2025-01-01T00:00:00Z",
        severity="severe"
    )
    
    # moderate 임계값으로 평가
    decision = policy.evaluate(cae, threshold="moderate")
    
    assert decision.trigger == True  # severe >= moderate
    assert decision.level == "severe"
    assert "severity(severe) >= threshold(moderate)" in decision.reason
    
    # critical 임계값으로 평가
    decision = policy.evaluate(cae, threshold="critical")
    
    assert decision.trigger == False  # severe < critical
    assert decision.level == "severe"
    assert "below threshold" in decision.reason

def test_geometry_and_area():
    """지리 정보 모델 테스트"""
    # Point 형상
    point_geom = Geometry(
        type="Point",
        coordinates=[127.0, 37.5]
    )
    
    area = Area(
        name="Seoul",
        geometry=point_geom
    )
    
    assert area.geometry.type == "Point"
    assert area.geometry.coordinates == [127.0, 37.5]
    assert area.name == "Seoul"
