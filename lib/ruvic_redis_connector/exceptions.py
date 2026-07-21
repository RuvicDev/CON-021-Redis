"""Excepciones propias del conector Redis.

Separan los tres tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor y datos. Nunca exponemos excepciones
crípticas del driver subyacente.
"""


class RedisConnectorError(Exception):
    """Error base del conector."""


class RedisAuthError(RedisConnectorError):
    """Credenciales inválidas o permisos insuficientes (ACL)."""


class RedisNetworkError(RedisConnectorError):
    """No se pudo alcanzar el servidor (host/puerto/red/timeout)."""


class RedisDataError(RedisConnectorError):
    """La operación es válida pero la clave/valor/patrón es inválido."""
