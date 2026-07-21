"""Validación local del conector redis: ejercita las 3 capacidades.

Uso:
    python validate_local.py

Requiere las variables RUVIC_REDIS_* exportadas en el entorno. No
necesita ninguna clave previa: escribe una clave de prueba, la lee y la
lista, luego la deja expirar por su TTL (no la borra explícitamente,
para probar también el flujo de expiración).
"""

from ruvic_redis_connector import RedisClient, setup_logging

setup_logging("INFO")
client = RedisClient()

print("== 1. Escribir clave con TTL ==")
written = client.write_key("ruvic:validate_local:prueba", "hola-mundo", ttl_seconds=120)
print(f"  {written}")

print("== 2. Leer la clave ==")
read = client.read_key("ruvic:validate_local:prueba")
print(f"  {read}")
assert read["exists"] and read["value"] == "hola-mundo", "El valor leído no coincide"
assert read["ttl_seconds"] is not None and read["ttl_seconds"] <= 120, "El TTL no se aplicó"

print("== 3. Listar claves por patrón ==")
keys = client.list_keys("ruvic:validate_local:*", limit=10)
print(f"  {keys}")
assert "ruvic:validate_local:prueba" in keys, "La clave no aparece en el listado"

print("\nTodo OK: write_key, read_key y list_keys funcionan.")
print("(La clave expira sola en 120s; no se elimina manualmente.)")
