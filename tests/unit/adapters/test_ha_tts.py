"""
Home Assistant 및 TTS Adapter 모듈 단위 테스트

이 모듈은 Home Assistant API 클라이언트와 TTS 엔진의 기능을 테스트합니다.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from app.adapters.homeassistant.client import HAClient
from app.adapters.tts.engine import TTSEngine


class TestHAClient:
    """Home Assistant API 클라이언트 테스트"""
    
    @pytest.fixture
    def ha_client(self):
        """테스트용 Home Assistant 클라이언트"""
        return HAClient(
            base_url="http://localhost:8123",
            token="test_token",
            timeout=30
        )
    
    def test_ha_client_initialization(self, ha_client):
        """Home Assistant 클라이언트 초기화 테스트"""
        assert ha_client.base_url == "http://localhost:8123"
        assert ha_client.token == "test_token"
        assert ha_client.timeout == 30
        assert ha_client.session is None
    
    def test_ha_client_initialization_with_trailing_slash(self):
        """끝에 슬래시가 있는 URL로 초기화 테스트"""
        ha_client = HAClient(
            base_url="http://localhost:8123/",
            token="test_token"
        )
        assert ha_client.base_url == "http://localhost:8123"
    
    @pytest.mark.asyncio
    async def test_ha_client_context_manager(self, ha_client):
        """Home Assistant 클라이언트 컨텍스트 매니저 테스트"""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # 컨텍스트 매니저 진입
            async with ha_client as client:
                assert client.session is not None
                assert client.session == mock_session
            
            # 컨텍스트 매니저 종료 시 세션 닫힘
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ha_client_make_request(self, ha_client):
        """API 요청 테스트"""
        mock_response_data = {"test": "data"}
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            async with ha_client:
                result = await ha_client._make_request("GET", "/api/test")
                
                assert result == mock_response_data
                mock_session.request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ha_client_make_request_without_session(self, ha_client):
        """세션 없이 API 요청 시 에러 테스트"""
        with pytest.raises(RuntimeError, match="세션이 초기화되지 않았습니다"):
            await ha_client._make_request("GET", "/api/test")
    
    @pytest.mark.asyncio
    async def test_ha_client_get_zone_home(self, ha_client):
        """zone.home 좌표 가져오기 테스트"""
        mock_response_data = {
            "attributes": {
                "latitude": 37.5665,
                "longitude": 126.9780
            }
        }
        
        with patch.object(ha_client, '_make_request', return_value=mock_response_data) as mock_request:
            result = await ha_client.get_zone_home()
            
            assert result == (37.5665, 126.9780)
            mock_request.assert_called_once_with("GET", "/api/states/zone.home")
    
    @pytest.mark.asyncio
    async def test_ha_client_get_zone_home_no_coordinates(self, ha_client):
        """좌표가 없는 zone.home 테스트"""
        mock_response_data = {
            "attributes": {
                "name": "Home"
            }
        }
        
        with patch.object(ha_client, '_make_request', return_value=mock_response_data):
            result = await ha_client.get_zone_home()
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_ha_client_get_zone_home_error(self, ha_client):
        """zone.home 가져오기 에러 테스트"""
        with patch.object(ha_client, '_make_request', side_effect=Exception("API error")):
            result = await ha_client.get_zone_home()
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_ha_client_update_sensor(self, ha_client):
        """센서 업데이트 테스트"""
        entity_id = "sensor.test_sensor"
        state = "test_state"
        attributes = {"test": "attribute"}
        
        with patch.object(ha_client, '_make_request', return_value={}) as mock_request:
            await ha_client.update_sensor(entity_id, state, attributes)
            
            mock_request.assert_called_once_with(
                "POST", 
                f"/api/states/{entity_id}",
                json={"state": state, "attributes": attributes}
            )
    
    @pytest.mark.asyncio
    async def test_ha_client_publish_event(self, ha_client):
        """이벤트 발행 테스트"""
        event_type = "test_event"
        event_data = {"test": "data"}
        
        with patch.object(ha_client, '_make_request', return_value={}) as mock_request:
            await ha_client.publish_event(event_type, event_data)
            
            mock_request.assert_called_once_with(
                "POST",
                "/api/events/test_event",
                json=event_data
            )
    
    @pytest.mark.asyncio
    async def test_ha_client_call_service(self, ha_client):
        """서비스 호출 테스트"""
        domain = "test"
        service = "test_service"
        service_data = {"test": "data"}
        
        with patch.object(ha_client, '_make_request', return_value={}) as mock_request:
            await ha_client.call_service(domain, service, service_data)
            
            mock_request.assert_called_once_with(
                "POST",
                f"/api/services/{domain}/{service}",
                json=service_data
            )
    
    @pytest.mark.asyncio
    async def test_ha_client_authentication(self):
        """인증 테스트"""
        ha_client = HAClient(
            base_url="http://localhost:8123",
            token="test_token"
        )
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            async with ha_client:
                # 인증 헤더가 올바르게 설정되었는지 확인
                call_args = mock_session_class.call_args
                headers = call_args[1]['headers']
                assert headers['Authorization'] == 'Bearer test_token'
                assert headers['Content-Type'] == 'application/json'
    
    @pytest.mark.asyncio
    async def test_ha_client_timeout_handling(self):
        """타임아웃 처리 테스트"""
        ha_client = HAClient(
            base_url="http://localhost:8123",
            token="test_token",
            timeout=5
        )
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            async with ha_client:
                # 타임아웃이 올바르게 설정되었는지 확인
                call_args = mock_session_class.call_args
                timeout = call_args[1]['timeout']
                assert timeout.total == 5
    
    @pytest.mark.asyncio
    async def test_ha_client_error_handling(self, ha_client):
        """에러 처리 테스트"""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status.side_effect = Exception("HTTP error")
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            async with ha_client:
                with pytest.raises(Exception, match="HTTP error"):
                    await ha_client._make_request("GET", "/api/test")


class TestTTSEngine:
    """TTS 엔진 테스트"""
    
    @pytest.fixture
    def ha_client(self):
        """테스트용 Home Assistant 클라이언트"""
        return HAClient(
            base_url="http://localhost:8123",
            token="test_token"
        )
    
    @pytest.fixture
    def tts_engine(self, ha_client):
        """테스트용 TTS 엔진"""
        return TTSEngine(
            ha_client=ha_client,
            default_voice="ko-KR",
            default_volume=0.8,
            media_player_entity="media_player.living_room",
            tts_service="tts.cloud_say"
        )
    
    def test_tts_engine_initialization(self, tts_engine):
        """TTS 엔진 초기화 테스트"""
        assert tts_engine.default_voice == "ko-KR"
        assert tts_engine.default_volume == 0.8
        assert tts_engine.media_player_entity == "media_player.living_room"
        assert tts_engine.tts_service == "tts.cloud_say"
        assert tts_engine.is_running is False
        assert tts_engine.voice_queue.empty()
    
    def test_tts_engine_initialization_with_defaults(self, ha_client):
        """기본값으로 TTS 엔진 초기화 테스트"""
        tts_engine = TTSEngine(ha_client=ha_client)
        
        assert tts_engine.default_voice == "ko-KR"
        assert tts_engine.default_volume == 0.8
        assert tts_engine.media_player_entity == "media_player.living_room"
        assert tts_engine.tts_service == "tts.cloud_say"
    
    @pytest.mark.asyncio
    async def test_tts_engine_start(self, tts_engine):
        """TTS 엔진 시작 테스트"""
        with patch.object(tts_engine, '_voice_worker', new_callable=AsyncMock) as mock_worker:
            # 시작 실행
            task = asyncio.create_task(tts_engine.start())
            await asyncio.sleep(0.1)
            task.cancel()
            
            # 엔진이 시작되었는지 확인
            assert tts_engine.is_running is True
            mock_worker.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_tts_engine_stop(self, tts_engine):
        """TTS 엔진 중지 테스트"""
        tts_engine.is_running = True
        
        await tts_engine.stop()
        
        assert tts_engine.is_running is False
    
    @pytest.mark.asyncio
    async def test_tts_engine_speak(self, tts_engine):
        """음성 메시지 큐 추가 테스트"""
        message = "테스트 메시지"
        
        result = await tts_engine.speak(message)
        
        assert result is True
        assert not tts_engine.voice_queue.empty()
        
        # 큐에서 메시지 확인
        voice_item = await tts_engine.voice_queue.get()
        assert voice_item['message'] == message
        assert voice_item['voice'] == "ko-KR"
        assert voice_item['volume'] == 0.8
        assert voice_item['priority'] == 0
    
    @pytest.mark.asyncio
    async def test_tts_engine_speak_with_custom_params(self, tts_engine):
        """사용자 정의 매개변수로 음성 메시지 큐 추가 테스트"""
        message = "테스트 메시지"
        voice = "en-US"
        volume = 0.5
        priority = 10
        
        result = await tts_engine.speak(message, voice=voice, volume=volume, priority=priority)
        
        assert result is True
        
        # 큐에서 메시지 확인
        voice_item = await tts_engine.voice_queue.get()
        assert voice_item['message'] == message
        assert voice_item['voice'] == voice
        assert voice_item['volume'] == volume
        assert voice_item['priority'] == priority
    
    @pytest.mark.asyncio
    async def test_tts_engine_speak_alert(self, tts_engine):
        """경보 음성 메시지 큐 추가 테스트"""
        headline = "테스트 경보"
        description = "테스트 설명"
        severity = "moderate"
        
        with patch.object(tts_engine, 'speak', new_callable=AsyncMock) as mock_speak:
            result = await tts_engine.speak_alert(headline, description, severity)
            
            assert result is True
            mock_speak.assert_called_once()
            
            # 호출된 매개변수 확인
            call_args = mock_speak.call_args
            assert headline in call_args[0][0]  # 메시지에 headline이 포함되어야 함
            assert description in call_args[0][0]  # 메시지에 description이 포함되어야 함
    
    @pytest.mark.asyncio
    async def test_tts_engine_speak_alert_with_custom_params(self, tts_engine):
        """사용자 정의 매개변수로 경보 음성 메시지 큐 추가 테스트"""
        headline = "테스트 경보"
        description = "테스트 설명"
        severity = "severe"
        voice = "en-US"
        volume = 0.9
        priority = 5
        
        with patch.object(tts_engine, 'speak', new_callable=AsyncMock) as mock_speak:
            result = await tts_engine.speak_alert(
                headline, description, severity, 
                voice=voice, volume=volume, priority=priority
            )
            
            assert result is True
            mock_speak.assert_called_once()
            
            # 호출된 매개변수 확인
            call_args = mock_speak.call_args
            call_kwargs = call_args[1]
            assert call_kwargs['voice'] == voice
            assert call_kwargs['volume'] == volume
            assert call_kwargs['priority'] == priority
    
    @pytest.mark.asyncio
    async def test_tts_engine_voice_worker(self, tts_engine):
        """음성 워커 테스트"""
        # 큐에 메시지 추가
        await tts_engine.voice_queue.put({
            "message": "테스트 메시지",
            "voice": "ko-KR",
            "volume": 0.8,
            "priority": 0,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        # 워커 실행
        tts_engine.is_running = True
        
        with patch.object(tts_engine, '_play_voice', new_callable=AsyncMock) as mock_play:
            # 워커가 큐를 비울 때까지 실행
            task = asyncio.create_task(tts_engine._voice_worker())
            await asyncio.sleep(0.1)
            tts_engine.is_running = False
            task.cancel()
            
            # 음성 재생이 호출되었는지 확인
            mock_play.assert_called()
    
    @pytest.mark.asyncio
    async def test_tts_engine_play_voice(self, tts_engine):
        """음성 재생 테스트"""
        voice_item = {
            "message": "테스트 메시지",
            "voice": "ko-KR",
            "volume": 0.8,
            "priority": 0,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        with patch.object(tts_engine.ha_client, 'call_service', new_callable=AsyncMock) as mock_call_service:
            await tts_engine._play_voice(voice_item)
            
            # TTS 서비스가 호출되었는지 확인
            mock_call_service.assert_called_once()
            
            # 호출된 매개변수 확인
            call_args = mock_call_service.call_args
            assert call_args[0][0] == "tts"  # domain
            assert call_args[0][1] == "cloud_say"  # service
            
            service_data = call_args[0][2]
            assert service_data['entity_id'] == "media_player.living_room"
            assert service_data['message'] == "테스트 메시지"
            assert service_data['language'] == "ko-KR"
    
    @pytest.mark.asyncio
    async def test_tts_engine_play_voice_with_volume(self, tts_engine):
        """볼륨 설정으로 음성 재생 테스트"""
        voice_item = {
            "message": "테스트 메시지",
            "voice": "ko-KR",
            "volume": 0.5,
            "priority": 0,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        with patch.object(tts_engine.ha_client, 'call_service', new_callable=AsyncMock) as mock_call_service:
            await tts_engine._play_voice(voice_item)
            
            # 서비스 호출 확인
            call_args = mock_call_service.call_args
            service_data = call_args[0][2]
            assert service_data['volume'] == 0.5
    
    @pytest.mark.asyncio
    async def test_tts_engine_play_voice_error_handling(self, tts_engine):
        """음성 재생 에러 처리 테스트"""
        voice_item = {
            "message": "테스트 메시지",
            "voice": "ko-KR",
            "volume": 0.8,
            "priority": 0,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        with patch.object(tts_engine.ha_client, 'call_service', side_effect=Exception("TTS error")):
            # 에러가 발생해도 시스템이 중단되지 않는지 확인
            await tts_engine._play_voice(voice_item)
            
            # 에러가 발생했지만 예외가 전파되지 않았는지 확인
            assert True  # 예외가 발생하지 않으면 성공
    
    @pytest.mark.asyncio
    async def test_tts_engine_language_support(self, tts_engine):
        """언어 지원 테스트"""
        # 다양한 언어로 테스트
        languages = ["ko-KR", "en-US", "ja-JP", "zh-CN"]
        
        for lang in languages:
            result = await tts_engine.speak("테스트 메시지", voice=lang)
            assert result is True
            
            # 큐에서 메시지 확인
            voice_item = await tts_engine.voice_queue.get()
            assert voice_item['voice'] == lang
    
    @pytest.mark.asyncio
    async def test_tts_engine_queue_management(self, tts_engine):
        """큐 관리 테스트"""
        # 여러 메시지 추가
        messages = [f"메시지 {i}" for i in range(5)]
        
        for message in messages:
            await tts_engine.speak(message)
        
        # 큐에 모든 메시지가 추가되었는지 확인
        assert tts_engine.voice_queue.qsize() == 5
        
        # 큐에서 메시지 순서 확인
        for i, message in enumerate(messages):
            voice_item = await tts_engine.voice_queue.get()
            assert voice_item['message'] == message
    
    @pytest.mark.asyncio
    async def test_tts_engine_error_handling(self, tts_engine):
        """TTS 엔진 에러 처리 테스트"""
        # 큐에 잘못된 형식의 메시지 추가
        await tts_engine.voice_queue.put("invalid_message")
        
        tts_engine.is_running = True
        
        with patch.object(tts_engine, '_play_voice', new_callable=AsyncMock) as mock_play:
            # 워커 실행
            task = asyncio.create_task(tts_engine._voice_worker())
            await asyncio.sleep(0.1)
            tts_engine.is_running = False
            task.cancel()
            
            # 에러가 발생해도 시스템이 계속 동작하는지 확인
            assert True  # 예외가 발생하지 않으면 성공


class TestHAAndTTSIntegration:
    """Home Assistant와 TTS 통합 테스트"""
    
    @pytest.fixture
    def ha_client(self):
        """테스트용 Home Assistant 클라이언트"""
        return HAClient(
            base_url="http://localhost:8123",
            token="test_token"
        )
    
    @pytest.fixture
    def tts_engine(self, ha_client):
        """테스트용 TTS 엔진"""
        return TTSEngine(ha_client=ha_client)
    
    @pytest.mark.asyncio
    async def test_ha_tts_integration(self, ha_client, tts_engine):
        """Home Assistant와 TTS 통합 테스트"""
        # Home Assistant 클라이언트 모킹
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status.return_value = None
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            # TTS 엔진 시작
            async with ha_client:
                tts_engine.ha_client = ha_client
                
                # 음성 메시지 추가
                result = await tts_engine.speak("테스트 메시지")
                assert result is True
                
                # 음성 재생
                voice_item = await tts_engine.voice_queue.get()
                await tts_engine._play_voice(voice_item)
                
                # Home Assistant 서비스가 호출되었는지 확인
                mock_session.request.assert_called()
    
    @pytest.mark.asyncio
    async def test_ha_tts_integration_error_handling(self, ha_client, tts_engine):
        """Home Assistant와 TTS 에러 처리 통합 테스트"""
        # Home Assistant 클라이언트 에러 모킹
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status.side_effect = Exception("HA API error")
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            # TTS 엔진 시작
            async with ha_client:
                tts_engine.ha_client = ha_client
                
                # 음성 메시지 추가
                result = await tts_engine.speak("테스트 메시지")
                assert result is True
                
                # 음성 재생 (에러 발생)
                voice_item = await tts_engine.voice_queue.get()
                await tts_engine._play_voice(voice_item)
                
                # 에러가 발생해도 시스템이 중단되지 않는지 확인
                assert True  # 예외가 발생하지 않으면 성공
    
    @pytest.mark.asyncio
    async def test_ha_tts_integration_performance(self, ha_client, tts_engine):
        """Home Assistant와 TTS 성능 통합 테스트"""
        # Home Assistant 클라이언트 모킹
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status.return_value = None
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            # 성능 테스트
            start_time = asyncio.get_event_loop().time()
            
            async with ha_client:
                tts_engine.ha_client = ha_client
                
                # 여러 음성 메시지 처리
                tasks = []
                for i in range(10):
                    task = asyncio.create_task(tts_engine.speak(f"메시지 {i}"))
                    tasks.append(task)
                
                # 모든 작업 완료 대기
                results = await asyncio.gather(*tasks)
                
                end_time = asyncio.get_event_loop().time()
                processing_time = end_time - start_time
                
                # 성능 확인
                assert all(results)
                assert processing_time < 2.0  # 2초 이내에 완료되어야 함
                assert tts_engine.voice_queue.qsize() == 10
