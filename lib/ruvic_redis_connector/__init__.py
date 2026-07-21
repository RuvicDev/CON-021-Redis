"""Conector Ruvic de lectura y escritura de claves en Redis."""

from .client import RedisClient
from .config import ENV_PREFIX, RedisConfig
from .exceptions import (
    RedisAuthError,
    RedisConnectorError,
    RedisDataError,
    RedisNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "RedisAuthError",
    "RedisClient",
    "RedisConfig",
    "RedisConnectorError",
    "RedisDataError",
    "RedisNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
