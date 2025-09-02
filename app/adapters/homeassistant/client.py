"""
Home Assistant API client for DX-Safety.

This module provides a client for interacting with Home Assistant API
to retrieve zone information, device states, and other HA data.
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Tuple
from app.observability.logging_setup import get_logger
from app.common.retry import retry_with_backoff

log = get_logger("dxsafety.ha")

class HAClient:
    """Home Assistant API 클라이언트"""
    
    def __init__(self, 
                 base_url: str, 
                 token: str, 
                 timeout: int = 30):
        """
        초기화합니다.
        
        Args:
            base_url: Home Assistant API 기본 URL
            token: Home Assistant 장기 토큰
            timeout: 요청 타임아웃 (초)
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        
        log.info("Home Assistant 클라이언트 초기화됨")
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            },
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        API 요청을 수행합니다.
        
        Args:
            method: HTTP 메서드
            endpoint: API 엔드포인트
            **kwargs: 추가 요청 매개변수
            
        Returns:
            응답 데이터
        """
        if not self.session:
            raise RuntimeError("세션이 초기화되지 않았습니다. async with를 사용하세요.")
        
        url = f"{self.base_url}{endpoint}"
        
        async def _request():
            async with self.session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
        
        return await retry_with_backoff(_request, max_retries=3)
    
    async def get_zone_home(self) -> Optional[Tuple[float, float]]:
        """
        zone.home의 좌표를 가져옵니다.
        
        Returns:
            (위도, 경도) 또는 None
        """
        try:
            data = await self._make_request("GET", "/api/states/zone.home")
            
            if data and "attributes" in data:
                attrs = data["attributes"]
                if "latitude" in attrs and "longitude" in attrs:
                    lat = float(attrs["latitude"])
                    lon = float(attrs["longitude"])
                    log.info(f"zone.home 좌표 가져옴 lat:{lat} lon:{lon}")
                    return (lat, lon)
            
            log.warning("zone.home 좌표를 찾을 수 없습니다")
            return None
            
        except Exception as e:
            log.error(f"zone.home 좌표 가져오기 실패 error:{str(e)}")
            return None
    
    async def get_zones(self) -> List[Dict]:
        """
        모든 zone을 가져옵니다.
        
        Returns:
            zone 목록
        """
        try:
            data = await self._make_request("GET", "/api/states")
            
            zones = []
            for entity_id, state in data.items():
                if entity_id.startswith("zone."):
                    zones.append({
                        "entity_id": entity_id,
                        "name": state.get("attributes", {}).get("friendly_name", entity_id),
                        "latitude": state.get("attributes", {}).get("latitude"),
                        "longitude": state.get("attributes", {}).get("longitude"),
                        "radius": state.get("attributes", {}).get("radius")
                    })
            
            log.info(f"zone 목록 가져옴 count:{len(zones)}")
            return zones
            
        except Exception as e:
            log.error(f"zone 목록 가져오기 실패 error:{str(e)}")
            return []
    
    async def get_device_states(self, device_ids: List[str]) -> Dict[str, Dict]:
        """
        특정 디바이스들의 상태를 가져옵니다.
        
        Args:
            device_ids: 디바이스 ID 목록
            
        Returns:
            디바이스 상태 딕셔너리
        """
        try:
            data = await self._make_request("GET", "/api/states")
            
            device_states = {}
            for entity_id, state in data.items():
                # 디바이스 ID로 필터링 (entity_id에서 추출)
                for device_id in device_ids:
                    if device_id in entity_id:
                        device_states[entity_id] = {
                            "state": state.get("state"),
                            "attributes": state.get("attributes", {}),
                            "last_updated": state.get("last_updated")
                        }
            
            log.info(f"디바이스 상태 가져옴 count:{len(device_states)}")
            return device_states
            
        except Exception as e:
            log.error(f"디바이스 상태 가져오기 실패 error:{str(e)} device_ids:{device_ids}")
            return {}
    
    async def call_service(self, domain: str, service: str, **kwargs) -> bool:
        """
        Home Assistant 서비스를 호출합니다.
        
        Args:
            domain: 서비스 도메인 (예: "light", "switch")
            service: 서비스 이름 (예: "turn_on", "turn_off")
            **kwargs: 서비스 매개변수
            
        Returns:
            호출 성공 여부
        """
        try:
            await self._make_request(
                "POST", 
                f"/api/services/{domain}/{service}",
                json=kwargs
            )
            
            log.info(f"서비스 호출 성공 domain:{domain} service:{service}")
            return True
            
        except Exception as e:
            log.error(f"서비스 호출 실패 domain:{domain} service:{service} error:{str(e)}")
            return False
    
    async def get_config(self) -> Optional[Dict]:
        """
        Home Assistant 설정을 가져옵니다.
        
        Returns:
            설정 정보 또는 None
        """
        try:
            data = await self._make_request("GET", "/api/config")
            log.info(f"Home Assistant 설정 가져옴 data:{data}")
            return data
            
        except Exception as e:
            log.error(f"Home Assistant 설정 가져오기 실패 error:{str(e)}")
            return None

    async def list_notify_mobile_services(self) -> list[str]:
        """모바일 앱 notify 서비스 목록을 가져옵니다."""
        try:
            svcs = await self._make_request("GET", "/api/services")
            mobile_services = []
            for service in svcs:
                if service.get("domain") == "notify":
                    for name in service.get("services", {}).keys():
                        if name.startswith("mobile_app_"):
                            mobile_services.append(name)
            log.info(f"모바일 notify 서비스 목록 가져옴 count:{len(mobile_services)}")
            return mobile_services
        except Exception as e:
            log.error(f"모바일 notify 서비스 목록 가져오기 실패 error:{str(e)}")
            return []

    async def get_device_trackers(self) -> list[dict]:
        """위치 추적 가능한 디바이스 목록을 가져옵니다."""
        try:
            states = await self._make_request("GET", "/api/states")
            devices = []
            for st in states:
                if st.get("entity_id", "").startswith("device_tracker."):
                    attrs = st.get("attributes", {})
                    if "latitude" in attrs and "longitude" in attrs:
                        devices.append({
                            "entity_id": st["entity_id"],
                            "name": attrs.get("friendly_name", st["entity_id"]),
                            "lat": float(attrs["latitude"]),
                            "lon": float(attrs["longitude"]),
                        })
            log.info(f"위치 추적 디바이스 목록 가져옴 count:{len(devices)}")
            return devices
        except Exception as e:
            log.error(f"위치 추적 디바이스 목록 가져오기 실패 error:{str(e)}")
            return []

    async def notify(self, service: str, title: str, message: str, url: str, 
                    sound: Optional[Dict] = None, actions: Optional[List[Dict]] = None):
        """모바일 앱에 푸시 알림을 발송합니다."""
        try:
            payload = {
                "title": title,
                "message": message,
                "data": {"url": url, "clickAction": url},
            }
            
            # 소리 설정 추가
            if sound:
                payload["data"]["push"] = {"sound": sound}
            
            # 액션 버튼 추가
            if actions:
                payload["data"]["actions"] = actions
            
            result = await self._make_request(
                "POST", f"/api/services/notify/{service}", json=payload
            )
            log.info(f"푸시 알림 발송 성공 service:{service} title:{title}")
            return result
        except Exception as e:
            log.error(f"푸시 알림 발송 실패 service:{service} error:{str(e)}")
            raise
