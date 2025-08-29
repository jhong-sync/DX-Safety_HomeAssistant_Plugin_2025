import asyncio
import aiohttp
import json
import os
from typing import Dict, Any, Optional

class HAClient:
    def __init__(self, timeout=5.0, base_url: str | None = None, token: str | None = None):
        self.timeout = timeout
        self.base_url = base_url or "http://supervisor/core"
        # Prefer explicit token, fallback to Supervisor env
        self.token = token or os.getenv("SUPERVISOR_TOKEN")
        
    async def trigger(self, decision):
        # TODO: Home Assistant 내부 서비스 호출(e.g., scene.turn_on, notify.*)
        await asyncio.sleep(0)
    
    async def set_state(self, entity_id: str, state: str, attrs: Optional[Dict[str, Any]] = None) -> bool:
        """Home Assistant 엔티티 상태를 설정합니다."""
        if not self.token:
            print("Warning: SUPERVISOR_TOKEN not available")
            return False
            
        url = f"{self.base_url}/api/states/{entity_id}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "state": state,
            "attributes": attrs or {}
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        print(f"Failed to set state: {response.status}")
                        return False
        except Exception as e:
            print(f"Error setting state: {e}")
            return False
    
    async def call_service(self, domain: str, service: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Home Assistant 서비스를 호출합니다."""
        if not self.token:
            print("Warning: SUPERVISOR_TOKEN not available")
            return False
            
        url = f"{self.base_url}/api/services/{domain}/{service}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = data or {}
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        print(f"Failed to call service: {response.status}")
                        return False
        except Exception as e:
            print(f"Error calling service: {e}")
            return False
