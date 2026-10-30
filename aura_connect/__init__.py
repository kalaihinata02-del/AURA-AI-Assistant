"""Aura Connect subsystem.

This package adds the local gateway, device registry, pairing flow, and
protocol definitions used by Aura AI to reach companion devices.
"""

from .service import AuraConnectService, get_service

__all__ = ["AuraConnectService", "get_service"]
