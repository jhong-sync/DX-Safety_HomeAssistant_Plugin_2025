import asyncio
import aiohttp
import os
from pathlib import Path
from typing import Dict, Any, Optional

_SUP_TOKEN_PATH = Path("/data/supervisor/token")

class HAClient:
    def __init__(self, timeout: float = 5.0, base_url: Optional[str] = None, token: Optional[str] = None):
        self.timeout = timeout
        self.base_url = base_url or "http://supervisor/core"
        self.token = token or os.getenv("SUPERVISOR_TOKEN") or self._read_token_file()
        self._session: Optional[aiohttp.ClientSession] = None

    def _read_token_file(self) -> Optional[str]:
        try:
            return _SUP_TOKEN_PATH.read_text(encoding="utf-8").strip()
        except Exception:
            return None

    async def _ensure_session(self):
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))

    def _headers(self) -> Dict[str, str]:
        if not self.token:
            raise RuntimeError("SUPERVISOR_TOKEN not available (env or /data/supervisor/token). "
                               "Ensure homeassistant_api:true in add-on config.")
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def health(self) -> bool:
        """간단한 헬스체크: /api 확인"""
        await self._ensure_session()
        url = f"{self.base_url}/api/"
        async with self._session.get(url, headers=self._headers()) as r:
            return 200 <= r.status < 300

    async def set_state(self, entity_id: str, state: str, attrs: Optional[Dict[str, Any]] = None) -> bool:
        """엔티티 상태 설정 (ad-hoc 상태 주입)."""
        await self._ensure_session()
        url = f"{self.base_url}/api/states/{entity_id}"
        payload = {"state": state, "attributes": attrs or {}}
        try:
            async with self._session.post(url, headers=self._headers(), json=payload) as resp:
                if 200 <= resp.status < 300:
                    return True
                text = await resp.text()
                print(f"[set_state] HTTP {resp.status}: {text}")
                return False
        except Exception as e:
            print(f"[set_state] Error: {e}")
            return False

    async def get_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """엔티티 상태 조회."""
        await self._ensure_session()
        url = f"{self.base_url}/api/states/{entity_id}"
        try:
            async with self._session.get(url, headers=self._headers()) as resp:
                if 200 <= resp.status < 300:
                    return await resp.json()
                return None
        except Exception:
            return None

    async def call_service(self, domain: str, service: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """서비스 호출 (예: scene.turn_on, notify.mobile_app_*, light.turn_on 등)."""
        await self._ensure_session()
        url = f"{self.base_url}/api/services/{domain}/{service}"
        try:
            async with self._session.post(url, headers=self._headers(), json=(data or {})) as resp:
                if 200 <= resp.status < 300:
                    return True
                text = await resp.text()
                print(f"[call_service] HTTP {resp.status}: {text}")
                return False
        except Exception as e:
            print(f"[call_service] Error: {e}")
            return False

    async def fire_event(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """이벤트 발행 (automation 트리거에 유용)."""
        await self._ensure_session()
        url = f"{self.base_url}/api/events/{event_type}"
        try:
            async with self._session.post(url, headers=self._headers(), json=(data or {})) as resp:
                return 200 <= resp.status < 300
        except Exception:
            return False

    async def trigger(self, decision):
        """의사결정 오브젝트를 받아 서비스 호출/상태변경/이벤트발행을 오케스트레이션."""
        # 예: notify
        # await self.call_service("notify", "mobile_app_pixel", {"message": "Alert!", "title": "DX-Safety"})
        await asyncio.sleep(0)

# 사용 예시
async def main():
    client = HAClient()
    ok = await client.health()
    print("HA reachable:", ok)

    # 상태 주입 (테스트 센서)
    await client.set_state("sensor.dxsafety_last_alert", "ok", {"source": "addon", "severity": "info"})

    # 서비스 호출 (장면 실행)
    await client.call_service("scene", "turn_on", {"entity_id": "scene.livingroom_night"})

    # 이벤트 발행
    await client.fire_event("dxsafety_alert", {"severity": "warning", "msg": "aftershock detected"})

    await client.close()

# asyncio.run(main())
