import json
import paho.mqtt.client as mqtt

class MqttPublisher:
    def __init__(self, cfg, metrics):
        self.cfg = cfg
        self.metrics = metrics
        self.client = mqtt.Client()
        self.client.connect(cfg.host, cfg.port, keepalive=30)
        self.client.loop_start()
    async def publish_alert(self, cae: dict, decision):
        topic = f"{self.cfg.topic_prefix}/{decision.target_topic}/{cae['eventId']}"
        payload = json.dumps({"headline": cae["headline"], "severity": cae["severity"]}, ensure_ascii=False)
        self.client.publish(topic, payload=payload, qos=self.cfg.qos, retain=self.cfg.retain)