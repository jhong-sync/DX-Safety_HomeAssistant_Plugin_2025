"""
hypothesis를 활용한 normalize 모듈 테스트

이 모듈은 hypothesis 패키지를 사용하여 
정규화 함수들의 속성 기반 테스트를 수행합니다.
"""

import pytest
from hypothesis import given, strategies as st, settings, example
from hypothesis.strategies import composite, lists, text, integers, floats, booleans, dictionaries
from typing import List, Dict, Any, Optional, Union
from pydantic import ValidationError

from app.core.normalize import to_cae
from app.core.models import CAE, Area, Geometry, Severity


class TestToCAEFunction:
    """to_cae 함수 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_to_cae_basic_fields(self, event_id: str, sent_at: str, severity: Severity):
        """기본 필드로 to_cae 테스트"""
        raw_data = {
            "id": event_id,
            "sentAt": sent_at,
            "severity": severity
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.severity == severity
        assert isinstance(cae.areas, list)
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_to_cae_alternative_field_names(self, event_id: str, sent_at: str, severity: Severity):
        """대체 필드명으로 to_cae 테스트"""
        raw_data = {
            "eventId": event_id,
            "sent_at": sent_at,
            "severity": severity
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.severity == severity
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_to_cae_identifier_field(self, event_id: str, sent_at: str, severity: Severity):
        """identifier 필드로 to_cae 테스트"""
        raw_data = {
            "identifier": event_id,
            "sent": sent_at,
            "severity": severity
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.severity == severity
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity_int=st.integers(min_value=1, max_value=5)
    )
    def test_to_cae_numeric_severity(self, event_id: str, sent_at: str, severity_int: int):
        """숫자 심각도로 to_cae 테스트"""
        raw_data = {
            "id": event_id,
            "sentAt": sent_at,
            "severity": severity_int
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        
        # 숫자 심각도 매핑 확인
        expected_severity = {
            1: "minor", 2: "minor", 3: "moderate", 4: "severe", 5: "critical"
        }.get(severity_int, "moderate")
        
        assert cae.severity == expected_severity
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.text(min_size=1, max_size=20).filter(
            lambda x: x.lower() not in ["minor", "moderate", "severe", "critical"]
        )
    )
    def test_to_cae_invalid_severity(self, event_id: str, sent_at: str, severity: str):
        """잘못된 심각도로 to_cae 테스트 (기본값 사용)"""
        raw_data = {
            "id": event_id,
            "sentAt": sent_at,
            "severity": severity
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.severity == "moderate"  # 기본값
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        headline=st.one_of(st.none(), st.text(min_size=1, max_size=200)),
        description=st.one_of(st.none(), st.text(min_size=1, max_size=500))
    )
    def test_to_cae_optional_fields(self, event_id: str, sent_at: str, severity: Severity,
                                  headline: Optional[str], description: Optional[str]):
        """선택적 필드로 to_cae 테스트"""
        raw_data = {
            "id": event_id,
            "sentAt": sent_at,
            "severity": severity,
            "headline": headline,
            "description": description
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.severity == severity
        assert cae.headline == headline
        assert cae.description == description
    
    def test_to_cae_with_areas(self):
        """영역 정보가 있는 to_cae 테스트"""
        # 유효한 영역 데이터
        valid_areas = [
            {
                "name": "Test Area 1",
                "geometry": {
                    "type": "Point",
                    "coordinates": [127.5, 37.5]
                }
            },
            {
                "name": "Test Area 2", 
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[127.0, 37.0], [128.0, 37.0], [128.0, 38.0], [127.0, 38.0], [127.0, 37.0]]]
                }
            }
        ]
        
        raw_data = {
            "id": "test_event",
            "sentAt": "2024-01-01T00:00:00Z",
            "severity": "moderate",
            "areas": valid_areas
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == "test_event"
        assert cae.sent_at == "2024-01-01T00:00:00Z"
        assert cae.severity == "moderate"
        assert isinstance(cae.areas, list)
        assert len(cae.areas) == 2
        
        # 유효한 영역만 처리되는지 확인
        for area in cae.areas:
            assert isinstance(area, Area)
            assert isinstance(area.geometry, Geometry)
            assert area.geometry.type in ["Point", "Polygon"]
            assert isinstance(area.geometry.coordinates, list)
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        sta_lat=st.floats(min_value=-90, max_value=90),
        sta_lon=st.floats(min_value=-180, max_value=180),
        location_info=st.one_of(st.none(), st.text(min_size=1, max_size=100))
    )
    def test_to_cae_with_sta_coordinates(self, event_id: str, sent_at: str, severity: Severity,
                                       sta_lat: float, sta_lon: float, location_info: Optional[str]):
        """STALatitude, STALongitude가 있는 to_cae 테스트"""
        parameters = {
            "STALatitude": sta_lat,
            "STALongitude": sta_lon
        }
        
        if location_info:
            parameters["Location.en"] = location_info
        
        raw_data = {
            "id": event_id,
            "sentAt": sent_at,
            "severity": severity,
            "parameters": parameters
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.severity == severity
        
        # STALatitude, STALongitude에서 영역이 생성되었는지 확인
        if cae.areas:
            area = cae.areas[0]
            assert area.geometry.type == "Point"
            assert len(area.geometry.coordinates) == 2
            assert area.geometry.coordinates[0] == sta_lon  # 경도
            assert area.geometry.coordinates[1] == sta_lat  # 위도
    
    def test_to_cae_with_invalid_sta_coordinates(self):
        """잘못된 STALatitude, STALongitude 타입으로 to_cae 테스트"""
        raw_data = {
            "id": "test_event",
            "sentAt": "2024-01-01T00:00:00Z",
            "severity": "moderate",
            "parameters": {
                "STALatitude": "invalid_lat",
                "STALongitude": "invalid_lon"
            }
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == "test_event"
        assert cae.sent_at == "2024-01-01T00:00:00Z"
        assert cae.severity == "moderate"
        # 잘못된 좌표는 무시되고 영역이 생성되지 않아야 함
        assert len(cae.areas) == 0
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        location_info=st.text(min_size=1, max_size=100)
    )
    def test_to_cae_with_location_info_only(self, event_id: str, sent_at: str, severity: Severity,
                                          location_info: str):
        """Location 정보만 있는 to_cae 테스트"""
        raw_data = {
            "id": event_id,
            "sentAt": sent_at,
            "severity": severity,
            "parameters": {
                "Location.en": location_info
            }
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.severity == severity
        
        # Location 정보로 영역이 생성되었는지 확인
        if cae.areas:
            area = cae.areas[0]
            assert area.name == location_info
            assert area.geometry.type == "Point"
            assert area.geometry.coordinates == [0, 0]  # 기본값
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_to_cae_empty_input(self, event_id: str, sent_at: str, severity: Severity):
        """빈 입력으로 to_cae 테스트"""
        raw_data = {
            "id": event_id,
            "sentAt": sent_at,
            "severity": severity,
            "areas": [],
            "parameters": {}
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.severity == severity
        assert cae.areas == []
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        areas=st.lists(
            st.one_of(
                st.text(),  # 잘못된 타입
                st.integers(),  # 잘못된 타입
                st.booleans()   # 잘못된 타입
            ),
            max_size=3
        )
    )
    def test_to_cae_invalid_areas(self, event_id: str, sent_at: str, severity: Severity, areas: List[Any]):
        """잘못된 영역 타입으로 to_cae 테스트"""
        raw_data = {
            "id": event_id,
            "sentAt": sent_at,
            "severity": severity,
            "areas": areas
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.severity == severity
        assert cae.areas == []  # 잘못된 영역은 무시됨
    
    def test_to_cae_various_parameters(self):
        """다양한 parameters로 to_cae 테스트"""
        # 유효한 parameters 테스트
        valid_parameters = {
            "Location.en": "Test Location",
            "STALatitude": "37.5",
            "STALongitude": "127.5",
            "some_other_param": "value"
        }
        
        raw_data = {
            "id": "test_event",
            "sentAt": "2024-01-01T00:00:00Z",
            "severity": "moderate",
            "parameters": valid_parameters
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == "test_event"
        assert cae.sent_at == "2024-01-01T00:00:00Z"
        assert cae.severity == "moderate"
        assert isinstance(cae.areas, list)
        
        # STALatitude, STALongitude가 있으면 영역이 생성되어야 함
        if "STALatitude" in valid_parameters and "STALongitude" in valid_parameters:
            assert len(cae.areas) > 0
        elif "Location.en" in valid_parameters:
            assert len(cae.areas) > 0


class TestToCAEEdgeCases:
    """to_cae 함수 엣지 케이스 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_to_cae_missing_required_fields(self, event_id: str, sent_at: str, severity: Severity):
        """필수 필드가 누락된 to_cae 테스트"""
        raw_data = {
            "severity": severity
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == ""  # 기본값
        assert cae.sent_at == ""   # 기본값
        assert cae.severity == severity
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_to_cae_none_values(self, event_id: str, sent_at: str, severity: Severity):
        """None 값이 있는 to_cae 테스트"""
        raw_data = {
            "id": event_id,
            "sentAt": sent_at,
            "severity": severity,
            "headline": None,
            "description": None,
            "areas": None,
            "parameters": None
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.severity == severity
        assert cae.headline is None
        assert cae.description is None
        assert cae.areas == []
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_to_cae_uppercase_severity(self, event_id: str, sent_at: str, severity: Severity):
        """대문자 심각도로 to_cae 테스트"""
        raw_data = {
            "id": event_id,
            "sentAt": sent_at,
            "severity": severity.upper()
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.severity == severity  # 소문자로 정규화됨
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_to_cae_mixed_case_severity(self, event_id: str, sent_at: str, severity: Severity):
        """혼합 대소문자 심각도로 to_cae 테스트"""
        mixed_severity = severity[0].upper() + severity[1:].lower()
        raw_data = {
            "id": event_id,
            "sentAt": sent_at,
            "severity": mixed_severity
        }
        
        cae = to_cae(raw_data)
        
        assert cae.event_id == event_id
        assert cae.sent_at == sent_at
        assert cae.severity == severity  # 소문자로 정규화됨
