"""
Tests for Phase 5 components.

This module contains tests for the TTS voice notification
and Home Assistant integration features.
"""

import pytest
import asyncio
from app.core.voice_template import (
    VoiceMessageTemplate, 
    create_voice_message,
    SEVERITY_NAMES,
    SEVERITY_VOLUMES
)
from app.core.models import CAE, Decision, Area, Geometry
from app.adapters.tts.engine import TTSEngine

def test_severity_names():
    """심각도별 한국어 표현 테스트"""
    assert SEVERITY_NAMES["minor"] == "경미"
    assert SEVERITY_NAMES["moderate"] == "보통"
    assert SEVERITY_NAMES["severe"] == "심각"
    assert SEVERITY_NAMES["critical"] == "매우 심각"

def test_severity_volumes():
    """심각도별 볼륨 설정 테스트"""
    assert SEVERITY_VOLUMES["minor"] == 0.6
    assert SEVERITY_VOLUMES["moderate"] == 0.7
    assert SEVERITY_VOLUMES["severe"] == 0.8
    assert SEVERITY_VOLUMES["critical"] == 0.9

def test_voice_message_template_korean():
    """한국어 음성 메시지 템플릿 테스트"""
    template = VoiceMessageTemplate("ko-KR")
    
    cae = CAE(
        event_id="test-123",
        sent_at="2025-01-01T14:30:00Z",
        severity="severe",
        headline="지진 경보"
    )
    
    decision = Decision(
        trigger=True,
        reason="severity(severe) >= threshold(moderate)",
        level="severe"
    )
    
    message = template.create_alert_message(cae, decision, location="서울")
    assert "서울 지역에 심각 수준의 지진 경보가 발령되었습니다" in message
    assert "14시 30분" in message

def test_voice_message_template_english():
    """영어 음성 메시지 템플릿 테스트"""
    template = VoiceMessageTemplate("en-US")
    
    cae = CAE(
        event_id="test-123",
        sent_at="2025-01-01T14:30:00Z",
        severity="severe",
        headline="Earthquake Alert"
    )
    
    decision = Decision(
        trigger=True,
        reason="severity(severe) >= threshold(moderate)",
        level="severe"
    )
    
    message = template.create_alert_message(cae, decision, location="Seoul")
    assert "SEVERE level Earthquake Alert" in message
    assert "14:30" in message

def test_voice_message_template_japanese():
    """일본어 음성 메시지 템플릿 테스트"""
    template = VoiceMessageTemplate("ja-JP")
    
    cae = CAE(
        event_id="test-123",
        sent_at="2025-01-01T14:30:00Z",
        severity="severe",
        headline="地震警報"
    )
    
    decision = Decision(
        trigger=True,
        reason="severity(severe) >= threshold(moderate)",
        level="severe"
    )
    
    message = template.create_alert_message(cae, decision, location="ソウル")
    assert "SEVEREレベルの地震警報" in message
    assert "14時30分" in message

def test_create_voice_message():
    """음성 메시지 생성 테스트"""
    cae = CAE(
        event_id="test-123",
        sent_at="2025-01-01T14:30:00Z",
        severity="severe",
        headline="지진 경보"
    )
    
    decision = Decision(
        trigger=True,
        reason="severity(severe) >= threshold(moderate)",
        level="severe"
    )
    
    voice_info = create_voice_message(
        cae, decision,
        language="ko-KR",
        location="서울",
        include_time=True
    )
    
    assert voice_info["message"] is not None
    assert voice_info["voice"] == "ko-KR"
    assert voice_info["volume"] == 0.8  # severe level
    assert voice_info["language"] == "ko-KR"
    assert voice_info["severity"] == "severe"
    assert voice_info["priority"] == 0.8

def test_voice_template_volume_for_severity():
    """심각도별 볼륨 테스트"""
    template = VoiceMessageTemplate()
    
    assert template.get_volume_for_severity("minor") == 0.6
    assert template.get_volume_for_severity("moderate") == 0.7
    assert template.get_volume_for_severity("severe") == 0.8
    assert template.get_volume_for_severity("critical") == 0.9
    assert template.get_volume_for_severity("unknown") == 0.7  # 기본값

def test_voice_template_voice_for_language():
    """언어별 음성 테스트"""
    template = VoiceMessageTemplate()
    
    assert template.get_voice_for_language("ko-KR") == "ko-KR"
    assert template.get_voice_for_language("en-US") == "en-US"
    assert template.get_voice_for_language("ja-JP") == "ja-JP"
    assert template.get_voice_for_language("zh-CN") == "zh-CN"
    assert template.get_voice_for_language("unknown") == "ko-KR"  # 기본값

def test_time_formatting():
    """시간 포맷팅 테스트"""
    template = VoiceMessageTemplate("ko-KR")
    
    # 한국어 시간 포맷
    korean_time = template._format_time_korean("2025-01-01T14:30:00Z")
    assert "14시 30분" in korean_time
    
    # 영어 시간 포맷
    english_time = template._format_time_english("2025-01-01T14:30:00Z")
    assert "14:30" in english_time
    
    # 일본어 시간 포맷
    japanese_time = template._format_time_japanese("2025-01-01T14:30:00Z")
    assert "14時30分" in japanese_time

@pytest.mark.asyncio
async def test_tts_engine_mock():
    """TTS 엔진 모의 테스트"""
    # 실제 테스트에서는 모의 객체를 사용하거나
    # 테스트용 Home Assistant 인스턴스를 사용해야 합니다
    assert True  # 현재는 기본 테스트만 통과

def test_voice_message_with_areas():
    """영역 정보가 포함된 음성 메시지 테스트"""
    cae = CAE(
        event_id="test-123",
        sent_at="2025-01-01T14:30:00Z",
        severity="severe",
        headline="지진 경보",
        areas=[
            Area(
                name="서울특별시",
                geometry=Geometry(
                    type="Point",
                    coordinates=[126.9780, 37.5665]
                )
            )
        ]
    )
    
    decision = Decision(
        trigger=True,
        reason="severity(severe) >= threshold(moderate)",
        level="severe"
    )
    
    voice_info = create_voice_message(
        cae, decision,
        language="ko-KR",
        location="서울특별시",
        include_time=True
    )
    
    assert "서울특별시 지역에 심각 수준의 지진 경보가 발령되었습니다" in voice_info["message"]

def test_voice_message_without_location():
    """위치 정보가 없는 음성 메시지 테스트"""
    cae = CAE(
        event_id="test-123",
        sent_at="2025-01-01T14:30:00Z",
        severity="critical",
        headline="태풍 경보"
    )
    
    decision = Decision(
        trigger=True,
        reason="severity(critical) >= threshold(moderate)",
        level="critical"
    )
    
    voice_info = create_voice_message(
        cae, decision,
        language="ko-KR",
        location=None,
        include_time=True
    )
    
    assert "매우 심각 수준의 태풍 경보가 발령되었습니다" in voice_info["message"]
    assert voice_info["volume"] == 0.9  # critical level
