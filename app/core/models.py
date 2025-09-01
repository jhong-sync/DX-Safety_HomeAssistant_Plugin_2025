"""
Core domain models for DX-Safety.

This module defines the core domain models using Pydantic v2
for type safety and validation.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

# 심각도 타입 정의
Severity = Literal["minor", "moderate", "severe", "critical"]

class Geometry(BaseModel):
    """지리적 형상 모델"""
    type: Literal["Point", "Polygon"]
    coordinates: list

class Area(BaseModel):
    """경보 영역 모델"""
    name: Optional[str] = None
    geometry: Geometry

class CAE(BaseModel):
    """Common Alerting Event 모델"""
    event_id: str
    sent_at: str
    headline: Optional[str] = None
    severity: Severity
    description: Optional[str] = None
    areas: List[Area] = Field(default_factory=list)

class Decision(BaseModel):
    """정책 평가 결과 모델"""
    trigger: bool
    reason: str
    level: Severity
