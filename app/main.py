import asyncio
from app.settings import Settings
from app.observability.logger import get_logger
from app.observability.health import start_health_server
from app.observability.metrics import Metrics
from app.ingestion.mqtt_ingestor import MqttIngestor
from app.normalize.normalizer import Normalizer
from app.policy.engine import PolicyEngine
from app.dedup.store import DedupStore
from app.dispatch.mqtt_publisher import MqttPublisher
from app.dispatch.ha_client import HAClient
from app.dispatch.tts import TTSDispatcher

log = get_logger()

async def update_dxsafety_sensors(ha_client: HAClient, cae: dict, decision):
    """DX-Safety 상태 센서들을 업데이트합니다."""
    try:
        # 마지막 알림 헤드라인
        await ha_client.set_state(
            "sensor.dxsafety_last_headline",
            cae.get("headline", "Unknown"),
            {"friendly_name": "DX-Safety Last Headline", "icon": "mdi:alert-circle"}
        )
        
        # 마지막 알림 레벨
        await ha_client.set_state(
            "sensor.dxsafety_last_level",
            decision.level,
            {"friendly_name": "DX-Safety Last Level", "icon": "mdi:signal"}
        )
        
        # 마지막 알림 강도
        await ha_client.set_state(
            "sensor.dxsafety_last_intensity",
            cae.get("intensity_value", "Unknown"),
            {"friendly_name": "DX-Safety Last Intensity", "icon": "mdi:gauge"}
        )
        
        # 마지막 대피소 정보
        shelter_name = "Unknown"
        if "shelter" in cae and isinstance(cae["shelter"], dict):
            shelter_name = cae["shelter"].get("name", "Unknown")
        elif "shelter" in cae and isinstance(cae["shelter"], str):
            shelter_name = cae["shelter"]
            
        await ha_client.set_state(
            "sensor.dxsafety_last_shelter",
            shelter_name,
            {"friendly_name": "DX-Safety Last Shelter", "icon": "mdi:home-city"}
        )
        
        log.info("DX-Safety sensors updated successfully")
    except Exception as e:
        log.error(f"Failed to update DX-Safety sensors: {e}")

async def send_test_alert(ha_client: HAClient):
    """테스트 알림을 발행합니다."""
    try:
        test_event = {
            "event_type": "dxsafety_alert",
            "payload": {
                "headline": "테스트 재난 경보",
                "description": "이것은 테스트용 재난 경보입니다.",
                "intensity_value": "moderate",
                "level": "moderate",
                "shelter": {"name": "테스트 대피소"},
                "links": ["https://example.com/test"]
            }
        }
        
        # Home Assistant 이벤트 발행
        success = await ha_client.call_service(
            "homeassistant", "fire_event",
            {"event_type": "dxsafety_alert", "event_data": test_event["payload"]}
        )
        
        if success:
            log.info("Test alert sent successfully")
            return True
        else:
            log.error("Failed to send test alert")
            return False
            
    except Exception as e:
        log.error(f"Error sending test alert: {e}")
        return False

async def main():
    cfg = Settings.load()
    metrics = Metrics(enabled=cfg.observability.metrics_enabled)

    dedup = DedupStore(ttl=cfg.reliability.idempotency_ttl_sec)
    normalizer = Normalizer()
    policy = PolicyEngine(cfg)

    local_pub = MqttPublisher(cfg.local_mqtt, metrics)
    ha_client = HAClient(
        timeout=cfg.homeassistant_api.timeout,
        base_url=cfg.homeassistant_api.url,
        token=cfg.homeassistant_api.token or None,
    )
    # Expose simple test endpoint via ingress server
    async def _trigger_test():
        return await send_test_alert(ha_client)
    await start_health_server(port=cfg.observability.http_port, metrics=metrics, on_trigger_test=_trigger_test)
    tts = TTSDispatcher(cfg.tts, local_pub)

    async def handle_raw(msg_bytes: bytes, topic: str):
        metrics.alerts_received_total.inc()
        try:
            log.info({"msg": "raw_message", "topic": topic, "payload": msg_bytes.decode(errors="ignore")})
            cae = normalizer.to_cae(msg_bytes)
            log.info({"msg": "normalized_cae", "eventId": cae["eventId"], "sentAt": cae["sentAt"]})
            metrics.alerts_valid_total.inc()
            if not dedup.accept(cae["eventId"], cae["sentAt"]):
                log.info({"msg": "duplicate_suppressed", "eventId": cae["eventId"]})
                return
            decision = policy.evaluate(cae)
            if not decision.trigger:
                log.info({"msg": "policy_not_triggered", "eventId": cae["eventId"]})
                return
            # Dispatch
            await local_pub.publish_alert(cae, decision)
            await ha_client.trigger(decision)
            await tts.maybe_say(cae, decision)
            
            # DX-Safety 상태 센서 업데이트
            await update_dxsafety_sensors(ha_client, cae, decision)
            
            metrics.alerts_triggered_total.inc()
        except Exception as e:
            log.exception("processing_error", extra={"err": str(e)})

    ingestor = MqttIngestor(cfg.remote_mqtt, on_message=handle_raw, metrics=metrics)
    await ingestor.run()

if __name__ == "__main__":
    asyncio.run(main())
