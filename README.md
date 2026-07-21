# Conector Redis (CON-021)

Conector Ruvic de lectura y escritura de claves en Redis. Permite leer el
valor y TTL de una clave, escribir una clave con expiración opcional, y
listar claves que cumplen un patrón sin bloquear el servidor.

> **Este conector SÍ escribe.** A diferencia de los conectores de bases de
> datos relacionales del catálogo (MySQL, PostgreSQL, SQL Server, Oracle) y
> de MongoDB, no es de solo lectura: `write_key` modifica el estado de
> Redis.

## Instalación

```bash
pip install git+https://github.com/Dgirto/Redis.git#subdirectory=lib
```

Python 3.10+. Dependencia única: `redis>=5.0,<6.0`.

## Permisos recomendados en el servidor

Redis no tiene "roles" como una base de datos relacional, pero desde la
versión 6 soporta ACL con restricción por patrón de claves. Se recomienda
crear un usuario dedicado limitado al namespace que va a usar el agente,
en vez de usar la cuenta `default` con acceso a todo el keyspace:

```
ACL SETUSER ruvic_agent on >CAMBIA_ESTA_CONTRASEÑA ~ruvic:* +get +set +scan +ttl +ping
```

Esto limita al usuario `ruvic_agent` a:
- Solo claves con el prefijo `ruvic:` (`~ruvic:*`).
- Solo los comandos `GET`, `SET`, `SCAN`, `TTL` y `PING` — los mismos que
  usa el conector.

Si tu servidor Redis no soporta ACL (versiones anteriores a la 6) o usas
`requirepass`, la única barrera disponible es la contraseña compartida:
en ese caso, todas las claves del servidor quedan accesibles para el
conector.

## Variables de entorno (`RUVIC_REDIS_*`)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_REDIS_HOST` | Sí | Host del servidor |
| `RUVIC_REDIS_PORT` | No (default `6379`) | Puerto |
| `RUVIC_REDIS_USERNAME` | No | Usuario ACL (Redis 6+) |
| `RUVIC_REDIS_PASSWORD` | No, pero muy recomendada | Contraseña |
| `RUVIC_REDIS_DB` | No (default `0`) | Número de base de datos lógica |
| `RUVIC_REDIS_CONNECT_TIMEOUT` | No (default `10`) | Timeout de conexión en segundos |

## Pruebas locales

Con Docker:

```bash
docker run -d --name redis-test -p 6379:6379 redis:7 \
  --requirepass root123

docker exec -i redis-test redis-cli -a root123 ACL SETUSER ruvic_reader on ">reader123" "~ruvic:*" +get +set +scan +ttl +ping
```

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_REDIS_HOST=localhost
export RUVIC_REDIS_PORT=6379
export RUVIC_REDIS_USERNAME=ruvic_reader
export RUVIC_REDIS_PASSWORD=reader123

python test_connection.py
python validate_local.py
```

Prueba también los casos de error (contraseña incorrecta, host inalcanzable,
clave de tipo distinto a string) y verifica que los mensajes sean claros.

## Notas de integración

- `list_keys` usa `SCAN` (cursor incremental), nunca `KEYS` — evita bloquear
  el servidor incluso con millones de claves.
- `read_key` sobre una clave inexistente no lanza error: retorna
  `{"exists": False, "value": None, ...}`, igual que el comportamiento
  nativo de `GET` en Redis.
- Solo se soportan claves de tipo string. Leer o escribir sobre una clave
  de otro tipo (hash, list, set, etc.) lanza `RedisDataError` con un
  mensaje explicando el motivo (`WRONGTYPE`).
- `write_key` con `ttl_seconds=None` no aplica expiración (la clave
  persiste hasta que se sobrescriba o se elimine manualmente en el
  servidor — el conector no expone un comando `DELETE`).
