"""
hypothesis를 활용한 voice_template 모듈 테스트

이 모듈은 hypothesis 패키지를 사용하여 
음성 템플릿 함수들의 속성 기반 테스트를 수행합니다.
"""

import pytest
from hypothesis import given, strategies as st, settings, example
from hypothesis.strategies import composite, lists, text, integers, floats, booleans, dictionaries
from typing import List, Dict, Any, Optional, Union
from pydantic import ValidationError

from app.core.voice_template import (
    VoiceMessageTemplate, 
    create_voice_message, 
    SEVERITY_NAMES, 
    SEVERITY_VOLUMES
)
from app.core.models import CAE, Area, Geometry, Decision, Severity


class TestVoiceMessageTemplate:
    """VoiceMessageTemplate 클래스 테스트"""
    
    @given(
        language=st.text(min_size=2, max_size=10)
    )
    def test_voice_template_initialization(self, language: str):
        """VoiceMessageTemplate 초기화 테스트"""
        template = VoiceMessageTemplate(language)
        
        assert template.language == language
    
    @given(
        language=st.text(min_size=2, max_size=10)
    )
    def test_voice_template_default_initialization(self, language: str):
        """기본 언어로 VoiceMessageTemplate 초기화 테스트"""
        template = VoiceMessageTemplate()
        
        assert template.language == "ko-KR"  # 기본값
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        headline=st.one_of(st.none(), st.text(min_size=1, max_size=200)),
        description=st.one_of(st.none(), st.text(min_size=1, max_size=500)),
        trigger=st.booleans(),
        reason=st.text(min_size=1, max_size=200),
        level=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        language=st.sampled_from(["ko-KR", "en-US", "ja-JP", "zh-CN"]),
        location=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        include_time=st.booleans()
    )
    def test_create_alert_message(self, event_id: str, sent_at: str, severity: Severity,
                                headline: Optional[str], description: Optional[str],
                                trigger: bool, reason: str, level: Severity,
                                language: str, location: Optional[str], include_time: bool):
        """알림 메시지 생성 테스트"""
        cae = CAE(
            event_id=event_id,
            sent_at=sent_at,
            severity=severity,
            headline=headline,
            description=description
        )
        
        decision = Decision(trigger=trigger, reason=reason, level=level)
        
        template = VoiceMessageTemplate(language)
        message = template.create_alert_message(
            cae, decision, location=location, include_time=include_time
        )
        
        assert isinstance(message, str)
        assert len(message) > 0
        
        # 언어별 메시지 내용 확인
        if language.startswith("ko"):
            assert any(keyword in message for keyword in ["수준", "발령", "지역"])
        elif language.startswith("en"):
            assert any(keyword in message for keyword in ["level", "alert", "issued"])
        elif language.startswith("ja"):
            assert any(keyword in message for keyword in ["レベル", "警報", "発令"])
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        trigger=st.booleans(),
        reason=st.text(min_size=1, max_size=200),
        level=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_create_korean_message(self, event_id: str, sent_at: str, severity: Severity,
                                 trigger: bool, reason: str, level: Severity):
        """한국어 메시지 생성 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        decision = Decision(trigger=trigger, reason=reason, level=level)
        
        template = VoiceMessageTemplate("ko-KR")
        message = template._create_korean_message(cae, decision, None, True)
        
        assert isinstance(message, str)
        assert len(message) > 0
        
        # 한국어 메시지 특성 확인
        severity_name = SEVERITY_NAMES.get(severity, severity)
        assert severity_name in message or severity in message
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        trigger=st.booleans(),
        reason=st.text(min_size=1, max_size=200),
        level=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_create_english_message(self, event_id: str, sent_at: str, severity: Severity,
                                   trigger: bool, reason: str, level: Severity):
        """영어 메시지 생성 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        decision = Decision(trigger=trigger, reason=reason, level=level)
        
        template = VoiceMessageTemplate("en-US")
        message = template._create_english_message(cae, decision, None, True)
        
        assert isinstance(message, str)
        assert len(message) > 0
        
        # 영어 메시지 특성 확인
        assert severity.upper() in message
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        trigger=st.booleans(),
        reason=st.text(min_size=1, max_size=200),
        level=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_create_japanese_message(self, event_id: str, sent_at: str, severity: Severity,
                                   trigger: bool, reason: str, level: Severity):
        """일본어 메시지 생성 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        decision = Decision(trigger=trigger, reason=reason, level=level)
        
        template = VoiceMessageTemplate("ja-JP")
        message = template._create_japanese_message(cae, decision, None, True)
        
        assert isinstance(message, str)
        assert len(message) > 0
        
        # 일본어 메시지 특성 확인
        assert severity.upper() in message
    
    @given(
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_get_volume_for_severity(self, severity: Severity):
        """심각도별 볼륨 테스트"""
        template = VoiceMessageTemplate()
        volume = template.get_volume_for_severity(severity)
        
        assert isinstance(volume, float)
        assert 0.0 <= volume <= 1.0
        
        # 심각도별 볼륨 확인
        expected_volume = SEVERITY_VOLUMES.get(severity, 0.7)
        assert volume == expected_volume
    
    @given(
        severity=st.text(min_size=1, max_size=20).filter(
            lambda x: x not in ["minor", "moderate", "severe", "critical"]
        )
    )
    def test_get_volume_for_invalid_severity(self, severity: str):
        """잘못된 심각도로 볼륨 테스트"""
        template = VoiceMessageTemplate()
        volume = template.get_volume_for_severity(severity)
        
        assert isinstance(volume, float)
        assert 0.0 <= volume <= 1.0
        assert volume == 0.7  # 기본값
    
    @given(
        language=st.text(min_size=2, max_size=10)
    )
    def test_get_voice_for_language(self, language: str):
        """언어별 음성 테스트"""
        template = VoiceMessageTemplate()
        voice = template.get_voice_for_language(language)
        
        assert isinstance(voice, str)
        assert len(voice) > 0
        
        # 언어별 음성 코드 확인
        if language.startswith("ko"):
            assert voice == "ko-KR"
        elif language.startswith("en"):
            assert voice == "en-US"
        elif language.startswith("ja"):
            assert voice == "ja-JP"
        elif language.startswith("zh"):
            assert voice == "zh-CN"
        else:
            assert voice == "ko-KR"  # 기본값


class TestCreateVoiceMessage:
    """create_voice_message 함수 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        headline=st.one_of(st.none(), st.text(min_size=1, max_size=200)),
        description=st.one_of(st.none(), st.text(min_size=1, max_size=500)),
        trigger=st.booleans(),
        reason=st.text(min_size=1, max_size=200),
        level=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        language=st.sampled_from(["ko-KR", "en-US", "ja-JP", "zh-CN"]),
        location=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        include_time=st.booleans()
    )
    def test_create_voice_message(self, event_id: str, sent_at: str, severity: Severity,
                                headline: Optional[str], description: Optional[str],
                                trigger: bool, reason: str, level: Severity,
                                language: str, location: Optional[str], include_time: bool):
        """음성 메시지 생성 테스트"""
        cae = CAE(
            event_id=event_id,
            sent_at=sent_at,
            severity=severity,
            headline=headline,
            description=description
        )
        
        decision = Decision(trigger=trigger, reason=reason, level=level)
        
        voice_info = create_voice_message(
            cae, decision, language=language, location=location, include_time=include_time
        )
        
        assert isinstance(voice_info, dict)
        assert "message" in voice_info
        assert "voice" in voice_info
        assert "volume" in voice_info
        assert "language" in voice_info
        assert "severity" in voice_info
        assert "priority" in voice_info
        
        # 각 필드 타입 확인
        assert isinstance(voice_info["message"], str)
        assert isinstance(voice_info["voice"], str)
        assert isinstance(voice_info["volume"], float)
        assert isinstance(voice_info["language"], str)
        assert isinstance(voice_info["severity"], str)
        assert isinstance(voice_info["priority"], float)
        
        # 값 범위 확인
        assert len(voice_info["message"]) > 0
        assert len(voice_info["voice"]) > 0
        assert 0.0 <= voice_info["volume"] <= 1.0
        assert voice_info["language"] == language
        assert voice_info["severity"] == severity
        assert 0.0 <= voice_info["priority"] <= 1.0
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        trigger=st.booleans(),
        reason=st.text(min_size=1, max_size=200),
        level=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_create_voice_message_default_params(self, event_id: str, sent_at: str, severity: Severity,
                                               trigger: bool, reason: str, level: Severity):
        """기본 매개변수로 음성 메시지 생성 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        decision = Decision(trigger=trigger, reason=reason, level=level)
        
        voice_info = create_voice_message(cae, decision)
        
        assert isinstance(voice_info, dict)
        assert voice_info["language"] == "ko-KR"  # 기본 언어
        assert voice_info["severity"] == severity
        assert voice_info["volume"] == SEVERITY_VOLUMES.get(severity, 0.7)


class TestTimeFormatting:
    """시간 포맷팅 테스트"""
    
    @given(
        iso_time=st.text(min_size=10, max_size=30)
    )
    def test_format_time_korean(self, iso_time: str):
        """한국어 시간 포맷팅 테스트"""
        template = VoiceMessageTemplate("ko-KR")
        
        try:
            time_str = template._format_time_korean(iso_time)
            assert isinstance(time_str, str)
            assert len(time_str) > 0
        except:
            # 잘못된 ISO 시간 형식은 "방금 전" 반환
            time_str = template._format_time_korean(iso_time)
            assert time_str == "방금 전"
    
    @given(
        iso_time=st.text(min_size=10, max_size=30)
    )
    def test_format_time_english(self, iso_time: str):
        """영어 시간 포맷팅 테스트"""
        template = VoiceMessageTemplate("en-US")
        
        try:
            time_str = template._format_time_english(iso_time)
            assert isinstance(time_str, str)
            assert len(time_str) > 0
        except:
            # 잘못된 ISO 시간 형식은 "just now" 반환
            time_str = template._format_time_english(iso_time)
            assert time_str == "just now"
    
    @given(
        iso_time=st.text(min_size=10, max_size=30)
    )
    def test_format_time_japanese(self, iso_time: str):
        """일본어 시간 포맷팅 테스트"""
        template = VoiceMessageTemplate("ja-JP")
        
        try:
            time_str = template._format_time_japanese(iso_time)
            assert isinstance(time_str, str)
            assert len(time_str) > 0
        except:
            # 잘못된 ISO 시간 형식은 "今" 반환
            time_str = template._format_time_japanese(iso_time)
            assert time_str == "今"


class TestVoiceTemplateEdgeCases:
    """음성 템플릿 엣지 케이스 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        trigger=st.booleans(),
        reason=st.text(min_size=1, max_size=200),
        level=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_create_message_with_none_fields(self, event_id: str, sent_at: str, severity: Severity,
                                            trigger: bool, reason: str, level: Severity):
        """None 필드가 있는 메시지 생성 테스트"""
        cae = CAE(
            event_id=event_id,
            sent_at=sent_at,
            severity=severity,
            headline=None,
            description=None
        )
        
        decision = Decision(trigger=trigger, reason=reason, level=level)
        
        template = VoiceMessageTemplate("ko-KR")
        message = template.create_alert_message(cae, decision, location=None, include_time=False)
        
        assert isinstance(message, str)
        assert len(message) > 0
        
        # None 필드가 있어도 메시지는 생성되어야 함
        assert severity in message or SEVERITY_NAMES.get(severity, severity) in message
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        trigger=st.booleans(),
        reason=st.text(min_size=1, max_size=200),
        level=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        location=st.text(min_size=1, max_size=100)
    )
    def test_create_message_with_location(self, event_id: str, sent_at: str, severity: Severity,
                                         trigger: bool, reason: str, level: Severity, location: str):
        """위치 정보가 있는 메시지 생성 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        decision = Decision(trigger=trigger, reason=reason, level=level)
        
        template = VoiceMessageTemplate("ko-KR")
        message = template.create_alert_message(cae, decision, location=location, include_time=False)
        
        assert isinstance(message, str)
        assert len(message) > 0
        assert location in message
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        trigger=st.booleans(),
        reason=st.text(min_size=1, max_size=200),
        level=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        description=st.text(min_size=1, max_size=500)
    )
    def test_create_message_with_description(self, event_id: str, sent_at: str, severity: Severity,
                                           trigger: bool, reason: str, level: Severity, description: str):
        """설명이 있는 메시지 생성 테스트"""
        cae = CAE(
            event_id=event_id,
            sent_at=sent_at,
            severity=severity,
            description=description
        )
        
        decision = Decision(trigger=trigger, reason=reason, level=level)
        
        template = VoiceMessageTemplate("ko-KR")
        message = template.create_alert_message(cae, decision, location=None, include_time=False)
        
        assert isinstance(message, str)
        assert len(message) > 0
        assert description in message


class TestVoiceTemplateConsistency:
    """음성 템플릿 일관성 테스트"""
    
    @given(
        event_id=st.text(min_size=1, max_size=100),
        sent_at=st.text(min_size=1, max_size=50),
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"]),
        trigger=st.booleans(),
        reason=st.text(min_size=1, max_size=200),
        level=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_voice_template_consistency(self, event_id: str, sent_at: str, severity: Severity,
                                       trigger: bool, reason: str, level: Severity):
        """음성 템플릿 일관성 테스트"""
        cae = CAE(event_id=event_id, sent_at=sent_at, severity=severity)
        decision = Decision(trigger=trigger, reason=reason, level=level)
        
        # 여러 번 생성해도 결과가 일관되어야 함
        voice_info1 = create_voice_message(cae, decision)
        voice_info2 = create_voice_message(cae, decision)
        
        assert voice_info1["severity"] == voice_info2["severity"]
        assert voice_info1["volume"] == voice_info2["volume"]
        assert voice_info1["language"] == voice_info2["language"]
        assert voice_info1["voice"] == voice_info2["voice"]
        # 메시지는 동일할 수 있지만 항상 같지는 않을 수 있음 (시간 등)
    
    @given(
        severity=st.sampled_from(["minor", "moderate", "severe", "critical"])
    )
    def test_volume_severity_consistency(self, severity: Severity):
        """볼륨-심각도 일관성 테스트"""
        template = VoiceMessageTemplate()
        
        # 여러 번 호출해도 동일한 결과
        volume1 = template.get_volume_for_severity(severity)
        volume2 = template.get_volume_for_severity(severity)
        
        assert volume1 == volume2
        assert volume1 == SEVERITY_VOLUMES.get(severity, 0.7)
    
    @given(
        language=st.text(min_size=2, max_size=10)
    )
    def test_voice_language_consistency(self, language: str):
        """음성-언어 일관성 테스트"""
        template = VoiceMessageTemplate()
        
        # 여러 번 호출해도 동일한 결과
        voice1 = template.get_voice_for_language(language)
        voice2 = template.get_voice_for_language(language)
        
        assert voice1 == voice2
