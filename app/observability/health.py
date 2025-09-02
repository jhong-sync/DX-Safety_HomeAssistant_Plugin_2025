"""
HTTP endpoints for DX-Safety observability.

This module implements health, readiness, metrics, and info endpoints
for monitoring and operational visibility.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import time
from app.settings import Settings
from app.observability.logging_setup import get_logger

log = get_logger()

def create_app(settings: Settings) -> FastAPI:
    """FastAPI 애플리케이션을 생성합니다."""
    app = FastAPI(
        title=settings.observability.service_name,
        version=settings.observability.build_version,
        description="DX-Safety Alert Processing Service"
    )
    
    start_time = time.time()
    
    @app.get("/health")
    async def health():
        """헬스 체크 엔드포인트"""
        return JSONResponse({
            "status": "ok",
            "service": settings.observability.service_name,
            "timestamp": time.time()
        })
    
    @app.get("/ready")
    async def ready():
        """레디니스 체크 엔드포인트"""
        # TODO: Phase 4에서 브로커 연결, DB 파일 RW 등 체크 추가
        return JSONResponse({
            "status": "ready",
            "service": settings.observability.service_name,
            "timestamp": time.time()
        })
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus 메트릭 엔드포인트"""
        if not settings.observability.metrics_enabled:
            raise HTTPException(status_code=503, detail="Metrics disabled")
        
        try:
            return Response(
                generate_latest(),
                media_type=CONTENT_TYPE_LATEST
            )
        except Exception as e:
            log.error(f"메트릭 생성 오류: {e}")
            raise HTTPException(status_code=500, detail="Metrics generation failed")
    
    @app.get("/info")
    async def info():
        """서비스 정보 엔드포인트"""
        uptime = time.time() - start_time
        return JSONResponse({
            "service": settings.observability.service_name,
            "version": settings.observability.build_version,
            "build_date": settings.observability.build_date,
            "uptime_seconds": int(uptime),
            "metrics_enabled": settings.observability.metrics_enabled,
            "log_level": settings.observability.log_level
        })
    
    @app.get("/")
    async def root():
        """루트 엔드포인트"""
        return JSONResponse({
            "service": settings.observability.service_name,
            "version": settings.observability.build_version,
            "endpoints": {
                "health": "/health",
                "ready": "/ready", 
                "metrics": "/metrics",
                "info": "/info"
            }
        })
    
    return app
