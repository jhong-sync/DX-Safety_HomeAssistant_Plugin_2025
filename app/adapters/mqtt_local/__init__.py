"""
Local MQTT publishing adapter for DX-Safety.

This module provides the implementation of AlertDispatchPort
for publishing alerts to local MQTT brokers.
"""

from .publisher import LocalMqttPublisher

__all__ = ["LocalMqttPublisher"]
