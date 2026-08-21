---
name: redis
description: >
  Usa la librería ruvic_redis_connector para leer y escribir claves en
  Redis - leer el valor y TTL de una clave (read_key), escribir una clave
  con expiración opcional (write_key) y listar claves que cumplen un
  patrón sin bloquear el servidor (list_keys). Úsala cuando el usuario
  pida consultar, guardar o expirar valores en un caché o almacén
  clave-valor Redis.
triggers:
- redis
- cache
- caché
- clave-valor
- key-value
- ttl
---

# Conector Redis (ruvic_redis_connector)

Librería Python para leer y escribir claves en Redis. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/Dgirto/Redis.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `redis` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_REDIS_HOST` | Host del servidor |
| `RUVIC_REDIS_PORT` | Puerto (default 6379) |
| `RUVIC_REDIS_USERNAME` | (opcional) usuario ACL |
| `RUVIC_REDIS_PASSWORD` | (opcional, recomendado) contraseña |
| `RUVIC_REDIS_DB` | (opcional) número de base de datos, default 0 |
| `RUVIC_REDIS_CONNECT_TIMEOUT` | (opcional) timeout en segundos |

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

## Este conector SÍ escribe

A diferencia de los conectores de bases de datos relacionales del catálogo (MySQL, PostgreSQL, SQL Server, Oracle, MongoDB), este conector modifica datos: `write_key` sobrescribe el valor de la clave indicada. No asumas que es de solo lectura.

## Conexión (siempre igual)

```python
from ruvic_redis_connector import RedisClient

client = RedisClient()  # lee RUVIC_REDIS_* del entorno automáticamente
```

## Capacidad 1 — Leer una clave

```python
result = client.read_key("sesion:123")
print(result)
# {'key': 'sesion:123', 'value': 'activa', 'exists': True, 'ttl_seconds': 3421}
```

Si la clave no existe, `value` es `None` y `exists` es `False` (no lanza excepción — es el comportamiento normal de Redis `GET`).

## Capacidad 2 — Escribir una clave (con TTL opcional)

```python
client.write_key("sesion:123", "activa", ttl_seconds=3600)  # expira en 1 hora
client.write_key("config:tema", "oscuro")                    # sin expiración
```

Sobrescribe el valor si la clave ya existía. Solo trabaja con claves de tipo string (no hashes, listas ni sets).

## Capacidad 3 — Listar claves por patrón

```python
keys = client.list_keys("sesion:*", limit=50)
for k in keys:
    print(k)
```

Usa `SCAN` internamente (no `KEYS`), por lo que no bloquea el servidor incluso con millones de claves. El patrón sigue la sintaxis glob de Redis (`*`, `?`, `[abc]`).

## Manejo de errores

```python
from ruvic_redis_connector import (
    RedisAuthError, RedisDataError, RedisNetworkError,
)

try:
    client.write_key("clave", "valor")
except RedisAuthError:
    print("Credenciales inválidas o sin permiso ACL sobre esa clave")
except RedisNetworkError:
    print("No se pudo alcanzar el servidor — revisa host/puerto/red")
except RedisDataError as e:
    print(f"Error de datos: {e}")  # ej. la clave existe pero no es string
```

## Comportamiento conversacional

### Cuándo pedir aclaración (y cuándo NO)

Redis no tiene agregaciones tipo `GROUP BY` — cada operación actúa sobre una
clave específica, así que la ambigüedad aquí es casi siempre sobre **cuál
clave**, no sobre cálculos. Pide aclaración solo cuando el usuario se refiere
a "la clave"/"la sesión"/etc. sin dar el nombre ni un patrón que la acote, y
`list_keys` devuelve más de una coincidencia razonable.

| Situación | ¿Preguntar? |
|---|---|
| El usuario da la clave exacta o un patrón claro (ej. "sesion:123", "las claves que empiecen con config:") | No — resuélvelo directo con `read_key`/`list_keys` |
| El usuario dice "la sesión del usuario" sin más contexto y `list_keys("sesion:*")` devuelve varias | Sí — pregunta cuál, mostrando las claves encontradas |
| El usuario pide sobrescribir una clave que ya tiene valor | No es ambigüedad, pero **sí conviene mostrar el valor actual antes de escribir** — es la única acción destructiva de este conector, y el usuario debería confirmarla a sabiendas de qué va a perder |

### Sugerencias de seguimiento

Ofrece una sugerencia de seguimiento solo si aporta algo no obvio. Ejemplo: si
leíste una clave con TTL bajo, puede tener sentido mencionar cuánto le queda
de vida; si el usuario ya tiene toda la información que pidió, no agregues
nada más.

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_REDIS_*` (el constructor de `RedisClient` ya lo hace).
2. Nunca imprimas `RUVIC_REDIS_PASSWORD` en logs ni en la salida.
3. Antes de escribir una clave importante, considera leerla primero con `read_key` para no sobrescribir algo sin que el usuario lo sepa.
4. Usa `limit` razonable en `list_keys` (default 100); con patrones muy amplios (`*`) en un keyspace grande, pide al usuario que acote el patrón.
5. Este conector no expone `DELETE` — para "borrar" una clave, usa `write_key` con un `ttl_seconds` corto, o indica al usuario que la eliminación directa no está disponible.
