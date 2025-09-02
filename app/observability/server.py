"""
HTTP server runner for DX-Safety observability.

This module provides a simple way to run the FastAPI server
for health checks and metrics exposure.
"""

import uvicorn
import asyncio
from app.observability.health import create_app
from app.settings import Settings
from app.observability.logging_setup import setup_logging_dev, get_logger

def run_http_server(settings: Settings, host: str = "0.0.0.0", port: int = None):
    """
    HTTP 서버를 실행합니다.
    
    Args:
        settings: 애플리케이션 설정
        host: 바인딩할 호스트
        port: 바인딩할 포트 (None이면 설정에서 가져옴)
    """
    # 로거 설정
    setup_logging_dev(level=settings.observability.log_level)
    log = get_logger("dxsafety.observability")
    
    # 포트 설정
    if port is None:
        port = settings.observability.http_port
    
    # FastAPI 앱 생성
    app = create_app(settings)
    
    log.info(f"HTTP 서버 시작 중 host:{host} port:{port}")
    
    # uvicorn으로 서버 실행
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=settings.observability.log_level.lower(),
        access_log=True
    )

if __name__ == "__main__":
    # 설정 로드
    settings = Settings.load()
    
    # 서버 실행
    run_http_server(settings)
