"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_REDIS_.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_REDIS_"


@dataclass(frozen=True)
class RedisConfig:
    """Parámetros de conexión a Redis."""

    host: str
    port: int
    password: str | None
    username: str | None
    db: int
    connect_timeout: int = 10

    @classmethod
    def from_env(cls) -> "RedisConfig":
        """Construye la configuración desde las variables RUVIC_REDIS_*.

        Raises:
            ValueError: si falta alguna variable obligatoria.

        Ejemplo:
            >>> config = RedisConfig.from_env()
            >>> config.host
            'cache.empresa.com'
        """
        missing = [
            f"{ENV_PREFIX}{name}" for name in ("HOST",) if not os.environ.get(f"{ENV_PREFIX}{name}")
        ]
        if missing:
            raise ValueError(
                "Faltan variables de entorno del conector redis: "
                + ", ".join(missing)
                + ". Configura el conector en Settings → Conectores."
            )
        return cls(
            host=os.environ[f"{ENV_PREFIX}HOST"],
            port=int(os.environ.get(f"{ENV_PREFIX}PORT", "6379")),
            password=os.environ.get(f"{ENV_PREFIX}PASSWORD") or None,
            username=os.environ.get(f"{ENV_PREFIX}USERNAME") or None,
            db=int(os.environ.get(f"{ENV_PREFIX}DB", "0")),
            connect_timeout=int(os.environ.get(f"{ENV_PREFIX}CONNECT_TIMEOUT", "10")),
        )
