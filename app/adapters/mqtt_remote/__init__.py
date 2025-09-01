"""
Remote MQTT ingestion adapter for DX-Safety.

This module provides the implementation of AlertIngestPort
for receiving alerts from remote MQTT brokers.
"""

from .client import RemoteMqttIngestor

__all__ = ["RemoteMqttIngestor"]
