"""
Backends module - environment-specific recording implementations.

Provides a factory function to auto-select the appropriate backend
based on the current environment (container vs host).
"""

from .base import RecordingBackend
from .container import ContainerBackend
from .host import HostBackend
from ..core.config import is_container_environment


def get_backend() -> RecordingBackend:
    """Auto-select the appropriate recording backend.
    
    Returns:
        ContainerBackend if running in a container, HostBackend otherwise.
    """
    if is_container_environment():
        return ContainerBackend()
    return HostBackend()


__all__ = [
    "RecordingBackend",
    "ContainerBackend",
    "HostBackend",
    "get_backend",
]
