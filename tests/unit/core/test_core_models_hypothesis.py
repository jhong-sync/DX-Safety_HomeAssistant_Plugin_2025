"""
hypothesis를 활용한 코어 모델 테스트

이 모듈은 hypothesis 패키지를 사용하여 
코어 모델들의 속성 기반 테스트를 수행합니다.
"""

import pytest
from hypothesis import given, strategies as st, settings, example
from hypothesis.strategies import composite, lists, text, integers, floats, booleans
from typing import List, Dict, Any, Optional
from pydantic import ValidationError

from app.core.models import CAE, Area, Geometry, Decision, Severity


class TestGeometryModel:
    """Geometry 모델 테스트"""
    
    @given(
        geom_type=st.sampled_from(["Point", "Polygon"]),
        coordinates=st.lists(st.floats(min_value=-180, max_value=180), min_size=2, max_size=10)
    )
    def test_geometry_creation(self, geom_type: str, coordinates: List[float]):
        """Geometry 모델 생성 테스트"""
        geometry = Geometry(type=geom_type, coordinates=coordinates)
        
        assert geometry.type == geom_type
        assert geometry.coordinates == coordinates
        assert isinstance(geometry.coordinates, list)
    
    @given(
        geom_type=st.text(min_size=1, max_size=20).filter(lambda x: x not in ["Point", "Polygon"]),
        coordinates=st.lists(st.floats(), min_size=1)
    )
    def test_geometry_invalid_type(self, geom_type: str, coordinates: List[float]):
        """잘못된 Geometry 타입 테스트"""
        with pytest.raises(ValidationError):
            Geometry(type=geom_type, coordinates=coordinates)
    
    def test_geometry_invalid_coordinates(self):
        """잘못된 좌표 타입 테스트"""
        # 명확히 잘못된 타입으로 테스트
        with pytest.raises(ValidationError):
            Geometry(type="Point", coordinates="invalid_string")
        
        with pytest.raises(ValidationError):
            Geometry(type="Point", coordinates={"invalid": "dict"})


class TestAreaModel:
    """Area 모델 테스트"""
    
    @given(
        name=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        geom_type=st.sampled_from(["Point", "Polygon"]),
        coordinates=st.lists(st.floats(min_value=-180, max_value=180), min_size=2, max_size=10)
    )
    def test_area_creation(self, name: Optional[str], geom_type: str, coordinates: List[float]):
        """Area 모델 생성 테스트"""
        geometry = Geometry(type=geom_type, coordinates=coordinates)
        area = Area(name=name, geometry=geometry)
        
        assert area.name == name
        assert area.geometry.type == geom_type
        assert area.geometry.coordinates == coordinates
    
    @given(
        geom_type=st.sampled_from(["Point", "Polygon"]),
        coordinates=st.lists(st.floats(min_value=-180, max_value=180), min_size=2, max_size=10)
    )
    def test_area_without_name(self, geom_type: str, coordinates: List[float]):
        """이름 없는 Area 모델 테스트"""
        geometry = Geometry(type=geom_type, coordinates=coordinates)
        area = Area(geometry=geometry)
        
        assert area.name is None
        assert area.geometry.type == geom_type


class TestCAEModel:
    """CAE 모델 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        headline=st.one_of(st.none(), st.text(min_size=1, max_size=200)),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        description=st.one_of(st.none(), st.text(min_size=1, max_size=500)),
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
    def test_cae_creation(self, event_id: str, sent_at: str, headline: Optional[str], 
                        severity: Severity, description: Optional[str], areas: List[Area]):
        """CAE 모델 생성 테스트"""
        cae = CAE(
            event_id=event_id,
            sent_at=sent_at,
            headline=headline,
            severity=severity,
            description=description,
            areas=areas
        )
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.headline == headline
        assert cae.severity == severity
        assert cae.description == description
        assert cae.areas == areas
        assert isinstance(cae.areas, list)
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_cae_minimal_fields(self, event_id: str, sent_at: str, severity: Severity):
        """최소 필드로 CAE 모델 생성 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.severity == severity
        assert cae.headline is None
        assert cae.description is None
        assert cae.areas == []
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.text(min_size=1, max_size=20).filter(lambda x: x not in ["minor", "moderate", "severe", "critical"])
    )
    def test_cae_invalid_severity(self, event_id: str, sent_at: str, severity: str):
        """잘못된 심각도 테스트"""
        with pytest.raises(ValidationError):
            CAE(event_id=event_id, sent_at=sent_at, severity=severity)  # type: ignore
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
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
            min_size=1, max_size=10
        )
    )
    def test_cae_with_multiple_areas(self, event_id: str, sent_at: str, severity: Severity, areas: List[Area]):
        """여러 영역을 가진 CAE 모델 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity, areas=areas)
        
        assert len(cae.areas) == len(areas)
        for i, area in enumerate(areas):
            assert cae.areas[i].name == area.name
            assert cae.areas[i].geometry.type == area.geometry.type
            assert cae.areas[i].geometry.coordinates == area.geometry.coordinates


class TestDecisionModel:
    """Decision 모델 테스트"""
    
    @given(
        trigger=st.booleans(),
        reason=st.text(min_size=1, max_size=200),
        level=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_decision_creation(self, trigger: bool, reason: str, level: Severity):
        """Decision 모델 생성 테스트"""
        decision = Decision(trigger=trigger, reason=reason, level=level)
        
        assert decision.trigger == trigger
        assert decision.reason == reason
        assert decision.level == level
    
    @given(
        trigger=st.booleans(),
        reason=st.text(min_size=1, max_size=200),
        level=st.text(min_size=1, max_size=20).filter(lambda x: x not in ["minor", "moderate", "severe", "critical"])
    )
    def test_decision_invalid_level(self, trigger: bool, reason: str, level: str):
        """잘못된 레벨 테스트"""
        with pytest.raises(ValidationError):
            Decision(trigger=trigger, reason=reason, level=level)  # type: ignore


class TestModelSerialization:
    """모델 직렬화/역직렬화 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_cae_serialization(self, event_id: str, sent_at: str, severity: Severity):
        """CAE 모델 직렬화 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        
        # Pydantic 모델을 딕셔너리로 변환
        cae_dict = cae.model_dump()
        
        assert isinstance(cae_dict, dict)
        assert cae_dict["event_id"] == event_id
        assert cae_dict["sent_at"] == sent_at
        assert cae_dict["severity"] == severity
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_cae_deserialization(self, event_id: str, sent_at: str, severity: Severity):
        """CAE 모델 역직렬화 테스트"""
        cae_dict = {
            "event_id": event_id,
            "sent_at": sent_at,
            "severity": severity
        }
        
        cae = CAE.model_validate(cae_dict)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.severity == severity
    
    @given(
        geom_type=st.sampled_from(["Point", "Polygon"]),
        coordinates=st.lists(st.floats(min_value=-180, max_value=180), min_size=2, max_size=10)
    )
    def test_geometry_serialization(self, geom_type: str, coordinates: List[float]):
        """Geometry 모델 직렬화 테스트"""
        geometry = Geometry(type=geom_type, coordinates=coordinates)
        
        geometry_dict = geometry.model_dump()
        
        assert isinstance(geometry_dict, dict)
        assert geometry_dict["type"] == geom_type
        assert geometry_dict["coordinates"] == coordinates
    
    @given(
        trigger=st.booleans(),
        reason=st.text(min_size=1, max_size=200),
        level=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_decision_serialization(self, trigger: bool, reason: str, level: Severity):
        """Decision 모델 직렬화 테스트"""
        decision = Decision(trigger=trigger, reason=reason, level=level)
        
        decision_dict = decision.model_dump()
        
        assert isinstance(decision_dict, dict)
        assert decision_dict["trigger"] == trigger
        assert decision_dict["reason"] == reason
        assert decision_dict["level"] == level


class TestModelValidation:
    """모델 검증 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        headline=st.one_of(st.none(), st.text(min_size=1, max_size=200)),
        description=st.one_of(st.none(), st.text(min_size=1, max_size=500))
    )
    def test_cae_field_validation(self, event_id: str, sent_at: str, severity: Severity, 
                                headline: Optional[str], description: Optional[str]):
        """CAE 필드 검증 테스트"""
        cae = CAE(
            event_id=event_id,
            sent_at=sent_at,
            severity=severity,
            headline=headline,
            description=description
        )
        
        # 모든 필드가 올바르게 설정되었는지 확인
        assert cae.event_id is not None and len(cae.event_id) > 0
        assert cae.sent_at is not None and len(cae.sent_at) > 0
        assert cae.severity in ["minor", "moderate", "severe", "critical"]
        assert cae.headline == headline
        assert cae.description == description
        assert isinstance(cae.areas, list)
    
    @given(
        geom_type=st.sampled_from(["Point", "Polygon"]),
        coordinates=st.lists(st.floats(min_value=-180, max_value=180), min_size=2, max_size=10)
    )
    def test_geometry_coordinate_validation(self, geom_type: str, coordinates: List[float]):
        """Geometry 좌표 검증 테스트"""
        geometry = Geometry(type=geom_type, coordinates=coordinates)
        
        assert geometry.type in ["Point", "Polygon"]
        assert isinstance(geometry.coordinates, list)
        assert len(geometry.coordinates) >= 2
        
        # 모든 좌표가 유효한 범위 내에 있는지 확인
        for coord in geometry.coordinates:
            assert -180 <= coord <= 180


class TestModelEdgeCases:
    """모델 엣지 케이스 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_cae_empty_areas(self, event_id: str, sent_at: str, severity: Severity):
        """빈 영역 리스트를 가진 CAE 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity, areas=[])
        
        assert cae.areas == []
        assert len(cae.areas) == 0
    
    @given(
        geom_type=st.sampled_from(["Point", "Polygon"]),
        coordinates=st.lists(st.floats(min_value=-180, max_value=180), min_size=2, max_size=2)
    )
    def test_geometry_minimal_coordinates(self, geom_type: str, coordinates: List[float]):
        """최소 좌표를 가진 Geometry 테스트"""
        geometry = Geometry(type=geom_type, coordinates=coordinates)
        
        assert len(geometry.coordinates) == 2
        assert geometry.coordinates == coordinates
    
    @given(
        trigger=st.booleans(),
        reason=st.text(min_size=1, max_size=1),  # 최소 길이 이유
        level=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_decision_minimal_reason(self, trigger: bool, reason: str, level: Severity):
        """최소 길이 이유를 가진 Decision 테스트"""
        decision = Decision(trigger=trigger, reason=reason, level=level)
        
        assert decision.reason == reason
        assert len(decision.reason) == 1
