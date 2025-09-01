"""
Core domain models and pure functions for DX-Safety.

This module contains the domain models and pure business logic
that are independent of external I/O and infrastructure concerns.
"""

from .models import CAE, Decision, Area, Geometry, Severity
from .normalize import to_cae
from .policy import evaluate

__all__ = ["CAE", "Decision", "Area", "Geometry", "Severity", "to_cae", "evaluate"]
