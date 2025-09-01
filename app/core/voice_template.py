"""
Voice notification message templates for DX-Safety.

This module provides message templates for converting
alert information into natural language for TTS.
"""

from typing import Dict, Optional, List
from app.core.models import CAE, Decision
from app.observability.logger import get_logger

log = get_logger()

# 심각도별 한국어 표현
SEVERITY_NAMES = {
    "minor": "경미",
    "moderate": "보통", 
    "severe": "심각",
    "critical": "매우 심각"
}

# 심각도별 볼륨 설정
SEVERITY_VOLUMES = {
    "minor": 0.6,
    "moderate": 0.7,
    "severe": 0.8,
    "critical": 0.9
}

class VoiceMessageTemplate:
    """음성 알림 메시지 템플릿"""
    
    def __init__(self, language: str = "ko-KR"):
        """
        초기화합니다.
        
        Args:
            language: 언어 코드
        """
        self.language = language
        
    def create_alert_message(self, 
                           cae: CAE,
                           decision: Decision,
                           *,
                           location: Optional[str] = None,
                           include_time: bool = True) -> str:
        """
        경보 메시지를 생성합니다.
        
        Args:
            cae: CAE 모델
            decision: 정책 평가 결과
            location: 위치 정보
            include_time: 시간 정보 포함 여부
            
        Returns:
            음성 메시지
        """
        if self.language.startswith("ko"):
            return self._create_korean_message(cae, decision, location, include_time)
        elif self.language.startswith("en"):
            return self._create_english_message(cae, decision, location, include_time)
        elif self.language.startswith("ja"):
            return self._create_japanese_message(cae, decision, location, include_time)
        else:
            return self._create_korean_message(cae, decision, location, include_time)
    
    def _create_korean_message(self, 
                             cae: CAE,
                             decision: Decision,
                             location: Optional[str],
                             include_time: bool) -> str:
        """한국어 메시지 생성"""
        severity_name = SEVERITY_NAMES.get(cae.severity, cae.severity)
        
        # 기본 메시지 구성
        if location:
            message = f"{location} 지역에 {severity_name} 수준의 {cae.headline}가 발령되었습니다."
        else:
            message = f"{severity_name} 수준의 {cae.headline}가 발령되었습니다."
        
        # 시간 정보 추가
        if include_time and cae.sent_at:
            # ISO 시간을 한국어로 변환
            time_str = self._format_time_korean(cae.sent_at)
            message += f" 발령 시간은 {time_str}입니다."
        
        # 추가 정보가 있으면 포함
        if cae.description:
            message += f" {cae.description}"
        
        return message
    
    def _create_english_message(self, 
                               cae: CAE,
                               decision: Decision,
                               location: Optional[str],
                               include_time: bool) -> str:
        """영어 메시지 생성"""
        severity_name = cae.severity.upper()
        
        # 기본 메시지 구성
        if location:
            message = f"A {severity_name} level {cae.headline} alert has been issued for {location} area."
        else:
            message = f"A {severity_name} level {cae.headline} alert has been issued."
        
        # 시간 정보 추가
        if include_time and cae.sent_at:
            time_str = self._format_time_english(cae.sent_at)
            message += f" Issued at {time_str}."
        
        # 추가 정보가 있으면 포함
        if cae.description:
            message += f" {cae.description}"
        
        return message
    
    def _create_japanese_message(self, 
                                cae: CAE,
                                decision: Decision,
                                location: Optional[str],
                                include_time: bool) -> str:
        """일본어 메시지 생성"""
        severity_name = cae.severity.upper()
        
        # 기본 메시지 구성
        if location:
            message = f"{location}地域に{severity_name}レベルの{cae.headline}警報が発令されました。"
        else:
            message = f"{severity_name}レベルの{cae.headline}警報が発令されました。"
        
        # 시간 정보 추가
        if include_time and cae.sent_at:
            time_str = self._format_time_japanese(cae.sent_at)
            message += f"発令時刻は{time_str}です。"
        
        # 추가 정보가 있으면 포함
        if cae.description:
            message += f" {cae.description}"
        
        return message
    
    def _format_time_korean(self, iso_time: str) -> str:
        """ISO 시간을 한국어로 변환"""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
            return f"{dt.hour}시 {dt.minute}분"
        except:
            return "방금 전"
    
    def _format_time_english(self, iso_time: str) -> str:
        """ISO 시간을 영어로 변환"""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
            return f"{dt.hour:02d}:{dt.minute:02d}"
        except:
            return "just now"
    
    def _format_time_japanese(self, iso_time: str) -> str:
        """ISO 시간을 일본어로 변환"""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
            return f"{dt.hour}時{dt.minute}分"
        except:
            return "今"
    
    def get_volume_for_severity(self, severity: str) -> float:
        """
        심각도에 따른 볼륨을 가져옵니다.
        
        Args:
            severity: 심각도
            
        Returns:
            볼륨 (0.0 ~ 1.0)
        """
        return SEVERITY_VOLUMES.get(severity, 0.7)
    
    def get_voice_for_language(self, language: str) -> str:
        """
        언어에 따른 음성을 가져옵니다.
        
        Args:
            language: 언어 코드
            
        Returns:
            음성 코드
        """
        voice_map = {
            "ko": "ko-KR",
            "en": "en-US", 
            "ja": "ja-JP",
            "zh": "zh-CN"
        }
        
        lang_code = language.split("-")[0] if "-" in language else language
        return voice_map.get(lang_code, "ko-KR")

def create_voice_message(cae: CAE,
                        decision: Decision,
                        *,
                        language: str = "ko-KR",
                        location: Optional[str] = None,
                        include_time: bool = True) -> Dict[str, any]:
    """
    음성 메시지를 생성합니다.
    
    Args:
        cae: CAE 모델
        decision: 정책 평가 결과
        language: 언어 코드
        location: 위치 정보
        include_time: 시간 정보 포함 여부
        
    Returns:
        음성 메시지 정보
    """
    template = VoiceMessageTemplate(language)
    
    message = template.create_alert_message(
        cae, decision, location=location, include_time=include_time
    )
    
    volume = template.get_volume_for_severity(cae.severity)
    voice = template.get_voice_for_language(language)
    
    return {
        "message": message,
        "voice": voice,
        "volume": volume,
        "language": language,
        "severity": cae.severity,
        "priority": SEVERITY_VOLUMES.get(cae.severity, 1)
    }
