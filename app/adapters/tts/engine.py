"""
TTS (Text-to-Speech) engine for DX-Safety.

This module provides TTS functionality for converting
alert messages to speech and playing them through Home Assistant.
"""

import asyncio
from typing import Dict, Optional, List
from app.observability.logger import get_logger
from app.adapters.homeassistant.client import HAClient
from app.common.retry import retry_with_backoff

log = get_logger()

class TTSEngine:
    """TTS 엔진"""
    
    def __init__(self, 
                 ha_client: HAClient,
                 *,
                 default_voice: str = "ko-KR",
                 default_volume: float = 0.8,
                 media_player_entity: str = "media_player.living_room",
                 tts_service: str = "tts.cloud_say"):
        """
        초기화합니다.
        
        Args:
            ha_client: Home Assistant 클라이언트
            default_voice: 기본 음성 (언어 코드)
            default_volume: 기본 볼륨 (0.0 ~ 1.0)
            media_player_entity: 미디어 플레이어 엔티티 ID
            tts_service: TTS 서비스 이름
        """
        self.ha_client = ha_client
        self.default_voice = default_voice
        self.default_volume = default_volume
        self.media_player_entity = media_player_entity
        self.tts_service = tts_service
        
        # 음성 큐
        self.voice_queue: asyncio.Queue = asyncio.Queue()
        self.is_running = False
        
        log.info("TTS 엔진 초기화됨", 
                default_voice=default_voice,
                media_player=media_player_entity,
                tts_service=tts_service)
    
    async def start(self) -> None:
        """TTS 엔진을 시작합니다."""
        self.is_running = True
        worker = asyncio.create_task(self._voice_worker())
        log.info("TTS 엔진 시작됨")
        await worker
    
    async def stop(self) -> None:
        """TTS 엔진을 중지합니다."""
        self.is_running = False
        log.info("TTS 엔진 중지됨")
    
    async def speak(self, 
                   message: str,
                   *,
                   voice: Optional[str] = None,
                   volume: Optional[float] = None,
                   priority: int = 0) -> bool:
        """
        음성 메시지를 큐에 추가합니다.
        
        Args:
            message: 음성으로 변환할 메시지
            voice: 음성 (언어 코드)
            volume: 볼륨 (0.0 ~ 1.0)
            priority: 우선순위 (높을수록 우선)
            
        Returns:
            큐 추가 성공 여부
        """
        try:
            voice_item = {
                "message": message,
                "voice": voice or self.default_voice,
                "volume": volume or self.default_volume,
                "priority": priority,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            await self.voice_queue.put(voice_item)
            log.debug("음성 메시지 큐에 추가됨", 
                      message=message[:50] + "..." if len(message) > 50 else message,
                      voice=voice_item["voice"])
            return True
            
        except Exception as e:
            log.error("음성 메시지 큐 추가 실패", error=str(e))
            return False
    
    async def speak_alert(self, 
                         headline: str,
                         severity: str,
                         *,
                         location: Optional[str] = None,
                         voice: Optional[str] = None,
                         volume: Optional[float] = None) -> bool:
        """
        경보 메시지를 음성으로 변환하여 큐에 추가합니다.
        
        Args:
            headline: 경보 제목
            severity: 심각도
            location: 위치 정보
            voice: 음성 (언어 코드)
            volume: 볼륨 (0.0 ~ 1.0)
            
        Returns:
            큐 추가 성공 여부
        """
        # 심각도에 따른 우선순위 설정
        priority_map = {
            "minor": 1,
            "moderate": 2,
            "severe": 3,
            "critical": 4
        }
        priority = priority_map.get(severity, 1)
        
        # 메시지 템플릿 생성
        if location:
            message = f"{location} 지역에 {severity} 수준의 {headline} 경보가 발령되었습니다."
        else:
            message = f"{severity} 수준의 {headline} 경보가 발령되었습니다."
        
        return await self.speak(message, voice=voice, volume=volume, priority=priority)
    
    async def _voice_worker(self) -> None:
        """음성 큐를 처리하는 워커"""
        while self.is_running:
            try:
                # 큐에서 음성 아이템 가져오기
                voice_item = await asyncio.wait_for(self.voice_queue.get(), timeout=1.0)
                
                # TTS 서비스 호출
                success = await self._call_tts_service(voice_item)
                
                if success:
                    log.info("음성 알림 재생됨", 
                            message=voice_item["message"][:50] + "..." if len(voice_item["message"]) > 50 else voice_item["message"],
                            voice=voice_item["voice"])
                else:
                    log.error("음성 알림 재생 실패", 
                             message=voice_item["message"][:50] + "..." if len(voice_item["message"]) > 50 else voice_item["message"])
                
                # 큐 작업 완료 표시
                self.voice_queue.task_done()
                
                # 재생 간격 (중복 방지)
                await asyncio.sleep(0.5)
                
            except asyncio.TimeoutError:
                # 타임아웃 시 계속 진행
                continue
            except Exception as e:
                log.error("음성 워커 오류", error=str(e))
                await asyncio.sleep(1.0)
    
    async def _call_tts_service(self, voice_item: Dict) -> bool:
        """
        Home Assistant TTS 서비스를 호출합니다.
        
        Args:
            voice_item: 음성 아이템
            
        Returns:
            호출 성공 여부
        """
        try:
            # TTS 서비스 호출
            tts_success = await self.ha_client.call_service(
                "tts",
                self.tts_service.replace("tts.", ""),
                entity_id=self.media_player_entity,
                message=voice_item["message"],
                language=voice_item["voice"]
            )
            
            if not tts_success:
                return False
            
            # 볼륨 설정
            if voice_item["volume"] != self.default_volume:
                volume_success = await self.ha_client.call_service(
                    "media_player",
                    "volume_set",
                    entity_id=self.media_player_entity,
                    volume_level=voice_item["volume"]
                )
                
                if not volume_success:
                    log.warning("볼륨 설정 실패", volume=voice_item["volume"])
            
            return True
            
        except Exception as e:
            log.error("TTS 서비스 호출 실패", error=str(e))
            return False
    
    async def get_available_voices(self) -> List[str]:
        """
        사용 가능한 음성 목록을 가져옵니다.
        
        Returns:
            음성 목록
        """
        try:
            # Home Assistant에서 TTS 서비스 정보 가져오기
            config = await self.ha_client.get_config()
            if config and "components" in config:
                tts_config = config["components"].get("tts", {})
                if "services" in tts_config:
                    services = tts_config["services"]
                    voices = []
                    for service_name, service_info in services.items():
                        if "fields" in service_info:
                            for field_name, field_info in service_info["fields"].items():
                                if field_name in ["language", "voice"]:
                                    if "options" in field_info:
                                        voices.extend(field_info["options"])
                    return list(set(voices))  # 중복 제거
            
            # 기본 음성 목록 반환
            return ["ko-KR", "en-US", "ja-JP", "zh-CN"]
            
        except Exception as e:
            log.error("음성 목록 가져오기 실패", error=str(e))
            return ["ko-KR", "en-US", "ja-JP", "zh-CN"]
    
    async def get_queue_size(self) -> int:
        """
        음성 큐의 크기를 가져옵니다.
        
        Returns:
            큐 크기
        """
        return self.voice_queue.qsize()
    
    async def clear_queue(self) -> None:
        """음성 큐를 비웁니다."""
        while not self.voice_queue.empty():
            try:
                self.voice_queue.get_nowait()
                self.voice_queue.task_done()
            except asyncio.QueueEmpty:
                break
        
        log.info("음성 큐 비움됨")
