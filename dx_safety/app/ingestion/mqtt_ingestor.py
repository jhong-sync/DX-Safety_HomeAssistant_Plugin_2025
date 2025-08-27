import asyncio
import ssl
import time
import paho.mqtt.client as mqtt
from app.observability.logger import get_logger

log = get_logger()

class MqttIngestor:
    def __init__(self, cfg, on_message, metrics):
        self.cfg = cfg
        self.on_message_cb = on_message
        self.metrics = metrics
        self.client = mqtt.Client(clean_session=cfg.clean_session)
        if cfg.tls:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if cfg.ca_cert_path:
                ctx.load_verify_locations(cafile=cfg.ca_cert_path)
            if cfg.client_cert_path and cfg.client_key_path:
                ctx.load_cert_chain(certfile=cfg.client_cert_path, keyfile=cfg.client_key_path)
            self.client.tls_set_context(ctx)
        if cfg.username and cfg.password:
            self.client.username_pw_set(cfg.username, cfg.password)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.will_set("dxsafety/status", payload="offline", qos=1, retain=True)

    def _on_connect(self, client, userdata, flags, rc):
        log.info({"msg": "ingestor_connected", "rc": rc})
        client.subscribe(self.cfg.topic, qos=self.cfg.qos)
        client.publish("dxsafety/status", payload="online", qos=1, retain=True)

    def _on_disconnect(self, client, userdata, rc):
        log.info({"msg": "ingestor_disconnected", "rc": rc})
        self.metrics.ingestor_reconnects_total.inc()

    def _on_message(self, client, userdata, message):
        try:
            asyncio.run_coroutine_threadsafe(
                self.on_message_cb(message.payload, message.topic),
                asyncio.get_event_loop()
            )
        except RuntimeError:
            # fallback: 직접 호출 (동기)
            asyncio.get_event_loop().create_task(self.on_message_cb(message.payload, message.topic))

    async def run(self):
        backoff = 1
        while True:
            try:
                self.client.connect(self.cfg.host, self.cfg.port, keepalive=self.cfg.keepalive)
                self.client.loop_start()
                while True:
                    await asyncio.sleep(1)
            except Exception as e:
                log.exception("ingestor_error", extra={"err": str(e)})
                self.client.loop_stop()
                await asyncio.sleep(min(backoff, self.cfg.reliability.reconnect_max_backoff_sec) if hasattr(self.cfg, 'reliability') else backoff)
                backoff = min(backoff * 2, 120)