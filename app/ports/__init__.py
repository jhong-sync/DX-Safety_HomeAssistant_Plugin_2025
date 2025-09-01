"""
Port interfaces for DX-Safety hexagonal architecture.

This module defines the port interfaces (Protocols) that define
the contracts between the core domain and external adapters.
"""

from .ingest import AlertIngestPort
from .dispatch import AlertDispatchPort
from .kvstore import KVStorePort
from .metrics import MetricsPort

__all__ = ["AlertIngestPort", "AlertDispatchPort", "KVStorePort", "MetricsPort"]
