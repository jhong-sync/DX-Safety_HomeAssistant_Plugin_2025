"""
Structured logging for DX-Safety.

This module provides structured logging configuration
with JSON formatting for better observability.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict

class JsonFormatter(logging.Formatter):
    """JSON 형식 로그 포매터"""
    
    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON 형식으로 변환합니다."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 예외 정보 추가
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # 추가 필드들
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logger(name: str = "dxsafety", level: str = "INFO") -> logging.Logger:
    """
    구조화된 로거를 설정합니다.
    
    Args:
        name: 로거 이름
        level: 로그 레벨
        
    Returns:
        설정된 로거
    """
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정되어 있으면 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 핸들러 설정
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 상위 로거로 전파하지 않음
    logger.propagate = False
    
    return logger

def get_logger(name: str = "dxsafety") -> logging.Logger:
    """
    로거를 가져옵니다.
    
    Args:
        name: 로거 이름
        
    Returns:
        로거 인스턴스
    """
    return logging.getLogger(name)

def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs):
    """
    컨텍스트 정보와 함께 로그를 기록합니다.
    
    Args:
        logger: 로거 인스턴스
        level: 로그 레벨
        message: 로그 메시지
        **kwargs: 추가 컨텍스트 정보
    """
    extra = {}
    for key, value in kwargs.items():
        if key in ["correlation_id", "user_id"]:
            extra[key] = value
    
    log_func = getattr(logger, level.lower())
    log_func(message, extra=extra)