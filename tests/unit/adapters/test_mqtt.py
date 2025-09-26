"""
MQTT Adapter 모듈 단위 테스트

이 모듈은 MQTT 관련 어댑터들의 기능을 테스트합니다.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from app.adapters.mqtt_remote.client_async import RemoteMqttIngestor
from app.adapters.mqtt_local.publisher_async import LocalMqttPublisher
from app.core.models import CAE, Decision, Area, Geometry, Severity


class TestRemoteMqttIngestor:
    """원격 MQTT 수집 어댑터 테스트"""
    
    @pytest.fixture
    def mqtt_ingestor(self):
        """테스트용 MQTT 수집 어댑터"""
        return RemoteMqttIngestor(
            broker_host="test.mqtt.broker",
            broker_port=1883,
            topic="test/topic",
            username="test_user",
            password="test_pass",
            tls=True
        )
    
    def test_mqtt_ingestor_initialization(self, mqtt_ingestor):
        """MQTT 수집 어댑터 초기화 테스트"""
        assert mqtt_ingestor.broker_host == "test.mqtt.broker"
        assert mqtt_ingestor.broker_port == 1883
        assert mqtt_ingestor.topic == "test/topic"
        assert mqtt_ingestor.username == "test_user"
        assert mqtt_ingestor.password == "test_pass"
        assert mqtt_ingestor.tls is True
    
    def test_mqtt_ingestor_initialization_with_defaults(self):
        """기본값으로 MQTT 수집 어댑터 초기화 테스트"""
        ingestor = RemoteMqttIngestor(
            broker_host="localhost",
            broker_port=1883,
            topic="test/topic"
        )
        
        assert ingestor.broker_host == "localhost"
        assert ingestor.broker_port == 1883
        assert ingestor.topic == "test/topic"
        assert ingestor.username is None
        assert ingestor.password is None
        assert ingestor.tls is False
    
    @pytest.mark.asyncio
    async def test_mqtt_ingestor_connection(self, mqtt_ingestor):
        """MQTT 연결 테스트"""
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # 연결 테스트
            async with mqtt_ingestor._connect():
                mock_client.assert_called_once()
                mock_client_instance.subscribe.assert_called_with("test/topic")
    
    @pytest.mark.asyncio
    async def test_mqtt_ingestor_disconnection(self, mqtt_ingestor):
        """MQTT 연결 해제 테스트"""
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # 연결 해제 테스트
            async with mqtt_ingestor._connect():
                pass
            
            # 연결이 정상적으로 해제되었는지 확인
            mock_client_instance.disconnect.assert_called()
    
    @pytest.mark.asyncio
    async def test_mqtt_ingestor_reconnection(self, mqtt_ingestor):
        """MQTT 재연결 테스트"""
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.subscribe.side_effect = Exception("Connection failed")
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # 재연결 로직 테스트
            with patch.object(mqtt_ingestor, '_reconnect', new_callable=AsyncMock) as mock_reconnect:
                try:
                    async with mqtt_ingestor._connect():
                        pass
                except Exception:
                    pass
                
                # 재연결이 시도되었는지 확인
                mock_reconnect.assert_called()
    
    @pytest.mark.asyncio
    async def test_mqtt_ingestor_message_reception(self, mqtt_ingestor):
        """MQTT 메시지 수신 테스트"""
        mock_message = Mock()
        mock_message.topic = "test/topic"
        mock_message.payload = json.dumps({"test": "message"}).encode()
        
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.subscribe.return_value = None
            mock_client_instance.messages.__aiter__.return_value = [mock_message]
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # 메시지 수신 테스트
            messages = []
            async with mqtt_ingestor._connect() as client:
                async for message in client.messages:
                    messages.append(message)
                    break
            
            assert len(messages) == 1
            assert messages[0] == mock_message
    
    @pytest.mark.asyncio
    async def test_mqtt_ingestor_error_handling(self, mqtt_ingestor):
        """MQTT 에러 처리 테스트"""
        with patch('aiomqtt.Client') as mock_client:
            mock_client.side_effect = Exception("MQTT connection failed")
            
            # 에러가 발생해도 시스템이 중단되지 않는지 확인
            with pytest.raises(Exception, match="MQTT connection failed"):
                async with mqtt_ingestor._connect():
                    pass
    
    @pytest.mark.asyncio
    async def test_mqtt_ingestor_tls_configuration(self):
        """MQTT TLS 설정 테스트"""
        ingestor = RemoteMqttIngestor(
            broker_host="secure.mqtt.broker",
            broker_port=8883,
            topic="test/topic",
            tls=True
        )
        
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # TLS 연결 테스트
            async with ingestor._connect():
                mock_client.assert_called_once()
                # TLS 설정이 올바르게 전달되었는지 확인
                call_args = mock_client.call_args
                assert call_args[1]['tls'] is True
    
    @pytest.mark.asyncio
    async def test_mqtt_ingestor_authentication(self):
        """MQTT 인증 테스트"""
        ingestor = RemoteMqttIngestor(
            broker_host="auth.mqtt.broker",
            broker_port=1883,
            topic="test/topic",
            username="test_user",
            password="test_pass"
        )
        
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # 인증 연결 테스트
            async with ingestor._connect():
                mock_client.assert_called_once()
                # 인증 정보가 올바르게 전달되었는지 확인
                call_args = mock_client.call_args
                assert call_args[1]['username'] == "test_user"
                assert call_args[1]['password'] == "test_pass"


class TestLocalMqttPublisher:
    """로컬 MQTT 발송 어댑터 테스트"""
    
    @pytest.fixture
    def mqtt_publisher(self):
        """테스트용 MQTT 발송 어댑터"""
        mock_outbox = AsyncMock()
        return LocalMqttPublisher(
            broker_host="localhost",
            broker_port=1883,
            topic_prefix="test",
            outbox=mock_outbox,
            username="test_user",
            password="test_pass",
            tls=False
        )
    
    def test_mqtt_publisher_initialization(self, mqtt_publisher):
        """MQTT 발송 어댑터 초기화 테스트"""
        assert mqtt_publisher.broker_host == "localhost"
        assert mqtt_publisher.broker_port == 1883
        assert mqtt_publisher.topic_prefix == "test"
        assert mqtt_publisher.username == "test_user"
        assert mqtt_publisher.password == "test_pass"
        assert mqtt_publisher.tls is False
    
    def test_mqtt_publisher_initialization_with_defaults(self):
        """기본값으로 MQTT 발송 어댑터 초기화 테스트"""
        mock_outbox = AsyncMock()
        publisher = LocalMqttPublisher(
            broker_host="localhost",
            broker_port=1883,
            topic_prefix="test",
            outbox=mock_outbox
        )
        
        assert publisher.broker_host == "localhost"
        assert publisher.broker_port == 1883
        assert publisher.topic_prefix == "test"
        assert publisher.username is None
        assert publisher.password is None
        assert publisher.tls is False
    
    @pytest.mark.asyncio
    async def test_mqtt_publisher_connection(self, mqtt_publisher):
        """MQTT 연결 테스트"""
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # 연결 테스트
            async with mqtt_publisher._connect():
                mock_client.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mqtt_publisher_message_sending(self, mqtt_publisher):
        """MQTT 메시지 발송 테스트"""
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity=Severity.MODERATE,
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        mock_decision = Decision(trigger=True, reason="test", level="test")
        
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # 메시지 발송 테스트
            await mqtt_publisher._publish_message(mock_cae, mock_decision)
            
            # 메시지가 발송되었는지 확인
            mock_client_instance.publish.assert_called()
    
    @pytest.mark.asyncio
    async def test_mqtt_publisher_qos_handling(self, mqtt_publisher):
        """MQTT QoS 처리 테스트"""
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity=Severity.MODERATE,
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        mock_decision = Decision(trigger=True, reason="test", level="test")
        
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # QoS 설정으로 메시지 발송 테스트
            await mqtt_publisher._publish_message(mock_cae, mock_decision, qos=2)
            
            # QoS가 올바르게 설정되었는지 확인
            call_args = mock_client_instance.publish.call_args
            assert call_args[1]['qos'] == 2
    
    @pytest.mark.asyncio
    async def test_mqtt_publisher_retain_flag(self, mqtt_publisher):
        """MQTT retain 플래그 테스트"""
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity=Severity.MODERATE,
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        mock_decision = Decision(trigger=True, reason="test", level="test")
        
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # retain 플래그로 메시지 발송 테스트
            await mqtt_publisher._publish_message(mock_cae, mock_decision, retain=True)
            
            # retain 플래그가 올바르게 설정되었는지 확인
            call_args = mock_client_instance.publish.call_args
            assert call_args[1]['retain'] is True
    
    @pytest.mark.asyncio
    async def test_mqtt_publisher_error_handling(self, mqtt_publisher):
        """MQTT 에러 처리 테스트"""
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity=Severity.MODERATE,
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        mock_decision = Decision(trigger=True, reason="test", level="test")
        
        with patch('aiomqtt.Client') as mock_client:
            mock_client.side_effect = Exception("MQTT connection failed")
            
            # 에러가 발생해도 시스템이 중단되지 않는지 확인
            with pytest.raises(Exception, match="MQTT connection failed"):
                await mqtt_publisher._publish_message(mock_cae, mock_decision)
    
    @pytest.mark.asyncio
    async def test_mqtt_publisher_reconnection(self, mqtt_publisher):
        """MQTT 재연결 테스트"""
        mock_cae = CAE(
            event_id="test_event",
            sent_at="2024-01-01T00:00:00Z",
            severity=Severity.MODERATE,
            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
        )
        mock_decision = Decision(trigger=True, reason="test", level="test")
        
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.publish.side_effect = Exception("Connection lost")
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # 재연결 로직 테스트
            with patch.object(mqtt_publisher, '_reconnect', new_callable=AsyncMock) as mock_reconnect:
                try:
                    await mqtt_publisher._publish_message(mock_cae, mock_decision)
                except Exception:
                    pass
                
                # 재연결이 시도되었는지 확인
                mock_reconnect.assert_called()
    
    @pytest.mark.asyncio
    async def test_mqtt_publisher_start(self, mqtt_publisher):
        """MQTT 발송 어댑터 시작 테스트"""
        with patch.object(mqtt_publisher, '_process_outbox', new_callable=AsyncMock) as mock_process:
            # 시작 실행
            task = asyncio.create_task(mqtt_publisher.start())
            await asyncio.sleep(0.1)
            task.cancel()
            
            # outbox 처리가 시작되었는지 확인
            mock_process.assert_called()
    
    @pytest.mark.asyncio
    async def test_mqtt_publisher_outbox_processing(self, mqtt_publisher):
        """Outbox 처리 테스트"""
        mock_outbox_item = Mock()
        mock_outbox_item.id = "test_id"
        mock_outbox_item.topic = "test/topic"
        mock_outbox_item.payload = '{"test": "message"}'
        mock_outbox_item.qos = 1
        mock_outbox_item.retain = False
        
        mqtt_publisher.outbox.get_pending = AsyncMock(return_value=[mock_outbox_item])
        mqtt_publisher.outbox.mark_sent = AsyncMock()
        mqtt_publisher.outbox.mark_failed = AsyncMock()
        
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # outbox 처리 테스트
            await mqtt_publisher._process_outbox()
            
            # outbox 항목이 처리되었는지 확인
            mqtt_publisher.outbox.get_pending.assert_called()
            mock_client_instance.publish.assert_called()
            mqtt_publisher.outbox.mark_sent.assert_called_with("test_id")
    
    @pytest.mark.asyncio
    async def test_mqtt_publisher_outbox_error_handling(self, mqtt_publisher):
        """Outbox 에러 처리 테스트"""
        mock_outbox_item = Mock()
        mock_outbox_item.id = "test_id"
        mock_outbox_item.topic = "test/topic"
        mock_outbox_item.payload = '{"test": "message"}'
        mock_outbox_item.qos = 1
        mock_outbox_item.retain = False
        
        mqtt_publisher.outbox.get_pending = AsyncMock(return_value=[mock_outbox_item])
        mqtt_publisher.outbox.mark_failed = AsyncMock()
        
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.publish.side_effect = Exception("Publish failed")
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # outbox 에러 처리 테스트
            await mqtt_publisher._process_outbox()
            
            # 에러가 발생했을 때 실패로 표시되었는지 확인
            mqtt_publisher.outbox.mark_failed.assert_called_with("test_id")


class TestMqttIntegration:
    """MQTT 통합 테스트"""
    
    @pytest.fixture
    def mqtt_ingestor(self):
        """테스트용 MQTT 수집 어댑터"""
        return RemoteMqttIngestor(
            broker_host="test.mqtt.broker",
            broker_port=1883,
            topic="test/topic"
        )
    
    @pytest.fixture
    def mqtt_publisher(self):
        """테스트용 MQTT 발송 어댑터"""
        mock_outbox = AsyncMock()
        return LocalMqttPublisher(
            broker_host="localhost",
            broker_port=1883,
            topic_prefix="test",
            outbox=mock_outbox
        )
    
    @pytest.mark.asyncio
    async def test_mqtt_message_flow_integration(self, mqtt_ingestor, mqtt_publisher):
        """MQTT 메시지 플로우 통합 테스트"""
        # 수집 어댑터에서 메시지 수신
        mock_message = Mock()
        mock_message.topic = "test/topic"
        mock_message.payload = json.dumps({"test": "message"}).encode()
        
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.subscribe.return_value = None
            mock_client_instance.messages.__aiter__.return_value = [mock_message]
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # 메시지 수신 테스트
            messages = []
            async with mqtt_ingestor._connect() as client:
                async for message in client.messages:
                    messages.append(message)
                    break
            
            assert len(messages) == 1
            
            # 발송 어댑터로 메시지 전송
            mock_cae = CAE(
                event_id="test_event",
                sent_at="2024-01-01T00:00:00Z",
                severity=Severity.MODERATE,
                areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
            )
            mock_decision = Decision(trigger=True, reason="test", level="test")
            
            await mqtt_publisher._publish_message(mock_cae, mock_decision)
            
            # 메시지가 발송되었는지 확인
            mock_client_instance.publish.assert_called()
    
    @pytest.mark.asyncio
    async def test_mqtt_security_integration(self, mqtt_ingestor, mqtt_publisher):
        """MQTT 보안 통합 테스트"""
        # TLS 설정 테스트
        secure_ingestor = RemoteMqttIngestor(
            broker_host="secure.mqtt.broker",
            broker_port=8883,
            topic="test/topic",
            tls=True,
            username="secure_user",
            password="secure_pass"
        )
        
        secure_publisher = LocalMqttPublisher(
            broker_host="secure.mqtt.broker",
            broker_port=8883,
            topic_prefix="test",
            outbox=AsyncMock(),
            tls=True,
            username="secure_user",
            password="secure_pass"
        )
        
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # 보안 연결 테스트
            async with secure_ingestor._connect():
                pass
            
            async with secure_publisher._connect():
                pass
            
            # TLS와 인증 설정이 올바르게 전달되었는지 확인
            assert mock_client.call_count == 2
            for call in mock_client.call_args_list:
                assert call[1]['tls'] is True
                assert call[1]['username'] == "secure_user"
                assert call[1]['password'] == "secure_pass"
    
    @pytest.mark.asyncio
    async def test_mqtt_reconnection_integration(self, mqtt_ingestor, mqtt_publisher):
        """MQTT 재연결 통합 테스트"""
        with patch('aiomqtt.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.subscribe.side_effect = Exception("Connection lost")
            mock_client_instance.publish.side_effect = Exception("Connection lost")
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # 재연결 로직 테스트
            with patch.object(mqtt_ingestor, '_reconnect', new_callable=AsyncMock) as mock_ingestor_reconnect:
                with patch.object(mqtt_publisher, '_reconnect', new_callable=AsyncMock) as mock_publisher_reconnect:
                    try:
                        async with mqtt_ingestor._connect():
                            pass
                    except Exception:
                        pass
                    
                    try:
                        mock_cae = CAE(
                            event_id="test_event",
                            sent_at="2024-01-01T00:00:00Z",
                            severity=Severity.MODERATE,
                            areas=[Area(name="Test Area", geometry=Geometry(type="Point", coordinates=[0, 0]))]
                        )
                        mock_decision = Decision(trigger=True, reason="test", level="test")
                        await mqtt_publisher._publish_message(mock_cae, mock_decision)
                    except Exception:
                        pass
                    
                    # 재연결이 시도되었는지 확인
                    mock_ingestor_reconnect.assert_called()
                    mock_publisher_reconnect.assert_called()
