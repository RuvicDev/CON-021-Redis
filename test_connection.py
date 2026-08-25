"""Prueba de conexión estándar del conector redis.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_REDIS_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Conecta a Redis y ejecuta PING usando las env vars RUVIC_REDIS_*."""
    try:
        from ruvic_redis_connector import (
            RedisAuthError,
            RedisClient,
            RedisDataError,
            RedisNetworkError,
        )
    except ImportError:
        return (
            False,
            (
                "La librería ruvic-redis-connector no está instalada. "
                "Instala con: pip install git+https://github.com/Dgirto/"
                "Redis.git#subdirectory=lib"
            ),
        )

    try:
        client = RedisClient()  # valida que existan las env vars
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except RedisAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except RedisNetworkError as exc:
        return False, f"Error de red: {exc}"
    except RedisDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # noqa: BLE001 - red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return (
        True,
        (
            f"Conexión exitosa a {client.config.host}:{client.config.port}/"
            f"db{client.config.db}"
        ),
    )


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
