"""
HTTP endpoints for DX-Safety observability.

This module implements health, readiness, metrics, and info endpoints
for monitoring and operational visibility.
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import Response, JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import time
from app.settings import Settings
from app.observability.logging_setup import get_logger
from app.adapters.homeassistant.client import HAClient
from app.features.shelter_nav import ShelterNavigator

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
    
    @app.post("/shelter/notify")
    async def shelter_notify(payload: dict = Body(default={})):
        """가까운 대피소 알림을 발송합니다."""
        if not settings.shelter_nav.enabled:
            raise HTTPException(status_code=400, detail="shelter_nav disabled")
        
        try:
            ha = HAClient(settings.ha.base_url, settings.ha.token, settings.ha.timeout_sec)
            nav = ShelterNavigator(ha, settings.shelter_nav.file_path, settings.shelter_nav.appname)
            
            notify_group = payload.get("notify_group") or settings.shelter_nav.notify_group or None
            await nav.notify_all_devices(notify_group)
            
            log.info(f"대피소 알림 요청 처리 완료 notify_group:{notify_group}")
            return {"ok": True, "message": "대피소 알림 발송 완료"}
            
        except Exception as e:
            log.error(f"대피소 알림 요청 처리 실패 error:{str(e)}")
            raise HTTPException(status_code=500, detail=f"Notification failed: {str(e)}")
    
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
                "info": "/info",
                "shelter_notify": "/shelter/notify"
            }
        })
    
    return app
