"""Scam Shield UAE: evidence-linked verification of documented UAE scam patterns."""
from .engine import ENGINE_VERSION, CheckResult, check_message

__version__ = ENGINE_VERSION
__all__ = ["check_message", "CheckResult", "__version__"]
