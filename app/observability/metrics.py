"""
Metrics definitions for DX-Safety.

This module defines Prometheus metrics for monitoring
the alert processing pipeline.
"""

from prometheus_client import Counter, Histogram, Gauge

# 카운터 메트릭
alerts_received = Counter(
    "alerts_received_total",
    "Number of raw alerts received",
    ["source"]
)

alerts_valid = Counter(
    "alerts_valid_total", 
    "Number of alerts that passed schema/normalization",
    ["severity"]
)

alerts_triggered = Counter(
    "alerts_triggered_total",
    "Number of alerts that passed policy and triggered",
    ["severity", "level"]
)

alerts_duplicate = Counter(
    "alerts_duplicate_total",
    "Number of duplicate alerts filtered out"
)

publish_retries = Counter(
    "publish_retries_total",
    "MQTT publish retries",
    ["topic"]
)

reconnects = Counter(
    "mqtt_reconnects_total",
    "MQTT client reconnects",
    ["client"]
)

# 히스토그램 메트릭
normalize_seconds = Histogram(
    "normalize_duration_seconds",
    "Time spent normalizing alerts",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

policy_seconds = Histogram(
    "policy_duration_seconds",
    "Time spent evaluating policy",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

end_to_end_seconds = Histogram(
    "end_to_end_duration_seconds",
    "Total processing latency",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
)

# 게이지 메트릭
queue_depth = Gauge(
    "internal_queue_depth",
    "Current depth of orchestrator queue"
)

outbox_size = Gauge(
    "outbox_size",
    "Current number of items in outbox"
)

idem_store_size = Gauge(
    "idem_store_size", 
    "Current number of items in idempotency store"
)

uptime_seconds = Gauge(
    "uptime_seconds",
    "Service uptime in seconds"
)