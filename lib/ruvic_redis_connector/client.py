"""Cliente de lectura y escritura de claves en Redis.

Capacidades:
- read_key():   leer el valor de una clave.
- write_key():  escribir el valor de una clave, con TTL opcional.
- list_keys():  listar claves que cumplen un patrón (vía SCAN, no KEYS).

Las credenciales SIEMPRE provienen de variables de entorno RUVIC_REDIS_*
(ver config.RedisConfig.from_env). Prohibido hardcodearlas.

A diferencia de los conectores de bases de datos relacionales del
catálogo, este conector SÍ escribe: write_key modifica el estado de
Redis. No hay barrera de "solo lectura" — el control de acceso depende
de las credenciales y, si el servidor lo soporta, de un usuario ACL
restringido a un patrón de claves.
"""

from __future__ import annotations

from typing import Any

import redis
from redis.exceptions import (
    AuthenticationError,
    ConnectionError as RedisConnectionError,
    ResponseError,
    TimeoutError as RedisTimeoutError,
)

from .config import RedisConfig
from .exceptions import (
    RedisAuthError,
    RedisConnectorError,
    RedisDataError,
    RedisNetworkError,
)
from .logging_utils import get_logger

_SCAN_COUNT_HINT = 200
_MAX_LIST_LIMIT = 10_000


def _validate_key(key: str) -> str:
    key = (key or "").strip()
    if not key:
        raise RedisDataError("key no puede estar vacía.")
    return key


def _wrap_response_error(exc: ResponseError) -> RedisConnectorError:
    """Traduce un error de respuesta de Redis a una excepción propia, sin
    dejar escapar nunca el tipo crudo del driver."""
    message = str(exc)
    if "NOPERM" in message or "WRONGPASS" in message:
        return RedisAuthError(
            "El usuario no tiene permiso para esta operación o esta clave. "
            "Revisa las reglas ACL del usuario en el servidor."
        )
    if "WRONGTYPE" in message:
        return RedisDataError(
            "La clave existe pero no es de tipo string (es hash, list, set, "
            "etc.). Este conector solo lee/escribe claves de tipo string."
        )
    return RedisDataError(f"Error de datos: {exc}")


class RedisClient:
    """Cliente de lectura y escritura de claves en Redis.

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_REDIS_* (comportamiento estándar
            en el runtime de la plataforma).

    Ejemplo:
        >>> client = RedisClient()          # lee RUVIC_REDIS_* del entorno
        >>> client.write_key("sesion:123", "activa", ttl_seconds=3600)
        {'key': 'sesion:123', 'ttl_seconds': 3600}
    """

    def __init__(self, config: RedisConfig | None = None) -> None:
        self.config = config or RedisConfig.from_env()
        self._logger = get_logger()
        self._client: redis.Redis | None = None

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def _get_client(self) -> redis.Redis:
        if self._client is not None:
            return self._client
        self._client = redis.Redis(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            username=self.config.username,
            password=self.config.password,
            socket_connect_timeout=self.config.connect_timeout,
            socket_timeout=self.config.connect_timeout,
            decode_responses=True,
        )
        return self._client

    def ping(self) -> bool:
        """Verifica la conexión con el comando PING.

        Returns:
            True si la conexión funciona.

        Raises:
            RedisAuthError / RedisNetworkError / RedisDataError según el fallo.
        """
        try:
            self._get_client().ping()
        except AuthenticationError as exc:
            raise RedisAuthError(
                "Autenticación fallida: usuario o contraseña inválidos."
            ) from exc
        except (RedisConnectionError, RedisTimeoutError) as exc:
            raise RedisNetworkError(
                f"No se pudo conectar a {self.config.host}:{self.config.port} "
                f"(timeout {self.config.connect_timeout}s). Verifica host, puerto "
                "y acceso de red."
            ) from exc
        except ResponseError as exc:
            raise _wrap_response_error(exc) from exc
        self._logger.info("Ping exitoso a %s:%s", self.config.host, self.config.port)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: leer una clave
    # ------------------------------------------------------------------ #

    def read_key(self, key: str) -> dict[str, Any]:
        """Lee el valor y el TTL de una clave.

        Args:
            key: nombre de la clave.

        Returns:
            Dict con: key, value (None si no existe), exists (bool),
            ttl_seconds (None si no existe o no tiene expiración, -1 en
            versiones antiguas de Redis para "sin expiración").

        Ejemplo:
            >>> client.read_key("sesion:123")
            {'key': 'sesion:123', 'value': 'activa', 'exists': True, 'ttl_seconds': 3421}
        """
        key = _validate_key(key)
        client = self._get_client()
        try:
            value = client.get(key)
            ttl = client.ttl(key) if value is not None else None
        except (RedisConnectionError, RedisTimeoutError) as exc:
            raise RedisNetworkError(f"No se pudo leer la clave: {exc}") from exc
        except ResponseError as exc:
            raise _wrap_response_error(exc) from exc
        if ttl is not None and ttl < 0:
            ttl = None  # -1: sin expiración configurada
        self._logger.info("Leída clave %r (exists=%s)", key, value is not None)
        return {
            "key": key,
            "value": value,
            "exists": value is not None,
            "ttl_seconds": ttl,
        }

    # ------------------------------------------------------------------ #
    # Capacidad 2: escribir una clave (con TTL opcional)
    # ------------------------------------------------------------------ #

    def write_key(
        self, key: str, value: str, ttl_seconds: int | None = None
    ) -> dict[str, Any]:
        """Escribe (o sobrescribe) el valor de una clave, con expiración
        opcional.

        Args:
            key: nombre de la clave.
            value: valor a guardar (se convierte a texto).
            ttl_seconds: segundos hasta que la clave expire (opcional; sin
                TTL la clave persiste indefinidamente).

        Returns:
            Dict con: key, ttl_seconds (el aplicado).

        Ejemplo:
            >>> client.write_key("sesion:123", "activa", ttl_seconds=3600)
            {'key': 'sesion:123', 'ttl_seconds': 3600}
        """
        key = _validate_key(key)
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise RedisDataError("ttl_seconds debe ser un entero positivo.")
        client = self._get_client()
        try:
            client.set(key, str(value), ex=ttl_seconds)
        except (RedisConnectionError, RedisTimeoutError) as exc:
            raise RedisNetworkError(f"No se pudo escribir la clave: {exc}") from exc
        except ResponseError as exc:
            raise _wrap_response_error(exc) from exc
        self._logger.info(
            "Escrita clave %r (ttl_seconds=%s)", key, ttl_seconds
        )
        return {"key": key, "ttl_seconds": ttl_seconds}

    # ------------------------------------------------------------------ #
    # Capacidad 3: listar claves por patrón
    # ------------------------------------------------------------------ #

    def list_keys(self, pattern: str = "*", limit: int = 100) -> list[str]:
        """Lista las claves que cumplen un patrón, usando SCAN (no bloquea
        el servidor, a diferencia de KEYS).

        Args:
            pattern: patrón estilo glob de Redis (ej. "sesion:*"). Default
                "*" (todas las claves).
            limit: máximo de claves a retornar (default 100, máximo 10000).

        Returns:
            Lista de nombres de clave que cumplen el patrón.

        Ejemplo:
            >>> client.list_keys("sesion:*", limit=10)
            ['sesion:123', 'sesion:456']
        """
        pattern = (pattern or "*").strip() or "*"
        limit = max(1, min(int(limit), _MAX_LIST_LIMIT))
        client = self._get_client()
        keys: list[str] = []
        try:
            for key in client.scan_iter(match=pattern, count=_SCAN_COUNT_HINT):
                keys.append(key)
                if len(keys) >= limit:
                    break
        except (RedisConnectionError, RedisTimeoutError) as exc:
            raise RedisNetworkError(f"No se pudo listar claves: {exc}") from exc
        except ResponseError as exc:
            raise _wrap_response_error(exc) from exc
        self._logger.info(
            "Listadas %d claves con patrón %r (limit=%d)", len(keys), pattern, limit
        )
        return keys
