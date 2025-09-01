"""
Policy evaluation functions for DX-Safety.

This module contains pure functions for evaluating alert policies
based on severity thresholds and other criteria.
"""

from .models import CAE, Decision, Severity

# 심각도 순서 정의 (낮음 -> 높음)
SEVERITY_ORDER = {
    "minor": 0,
    "moderate": 1, 
    "severe": 2,
    "critical": 3
}

def evaluate(cae: CAE, *, threshold: Severity = "moderate") -> Decision:
    """
    CAE를 기반으로 정책을 평가합니다.
    
    Args:
        cae: 평가할 CAE 모델
        threshold: 심각도 임계값
        
    Returns:
        정책 평가 결과
    """
    # 심각도 비교
    trig = SEVERITY_ORDER[cae.severity] >= SEVERITY_ORDER[threshold]
    
    # 이유 생성
    reason = f"severity({cae.severity}) >= threshold({threshold})" if trig else "below threshold"
    
    # 레벨 설정
    level: Severity = cae.severity
    
    return Decision(
        trigger=trig,
        reason=reason,
        level=level
    )
