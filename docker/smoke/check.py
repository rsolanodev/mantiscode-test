#!/usr/bin/env python3
"""Verificación de salud del stack dev (smoke check).

Ejecuta una batería de comprobaciones contra Postgres y Redis desde dentro
de la red de Compose, usando la misma configuración de entorno que los
servicios del stack (compose.yaml la inyecta en `environment`).

Comprobaciones:
  1. Postgres: conexión autenticada
  2. Postgres: ciclo insert/lectura/borrado en tabla de trabajo
  3. Redis: conexión autenticada (PING)
  4. Redis: ciclo SET/GET/DEL
  5. Redis: expiración por TTL

Salida: una línea `PASS:` o `FAIL:` por comprobación (los fallos incluyen
el motivo) y un resumen final. Código de salida 0 si todo pasa, 1 en caso
contrario.
"""

import os
import sys
import time

import psycopg
import redis

# Variables de configuración obligatorias (las inyecta compose.yaml).
REQUIRED_ENV = (
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_PASSWORD",
)

# Parámetros opcionales de la propia prueba.
PG_TABLE = os.environ.get("SMOKE_PG_TABLE", "smoke_test")
REDIS_SMOKE_TTL = float(os.environ.get("REDIS_SMOKE_TTL", "2"))
REDIS_KEY = os.environ.get("SMOKE_REDIS_KEY", "smoke:test")


def load_config() -> dict:
    """Lee la configuración del entorno; KeyError si falta alguna variable."""
    cfg = {key: os.environ[key] for key in REQUIRED_ENV}
    cfg["POSTGRES_PORT"] = int(cfg["POSTGRES_PORT"])
    cfg["REDIS_PORT"] = int(cfg["REDIS_PORT"])
    return cfg


def pg_connect(cfg: dict) -> psycopg.Connection:
    return psycopg.connect(
        host=cfg["POSTGRES_HOST"],
        port=cfg["POSTGRES_PORT"],
        dbname=cfg["POSTGRES_DB"],
        user=cfg["POSTGRES_USER"],
        password=cfg["POSTGRES_PASSWORD"],
        connect_timeout=5,
    )


def redis_client(cfg: dict) -> redis.Redis:
    return redis.Redis(
        host=cfg["REDIS_HOST"],
        port=cfg["REDIS_PORT"],
        password=cfg["REDIS_PASSWORD"] or None,
        decode_responses=True,
        socket_connect_timeout=5,
    )


def check_pg_connect(cfg: dict) -> str:
    with pg_connect(cfg) as conn:
        row = conn.execute("SELECT version()").fetchone()
    return (row[0] or "").split(",")[0]


def check_pg_data_cycle(cfg: dict) -> str:
    conn = pg_connect(cfg)
    try:
        with conn.transaction():
            conn.execute(
                f'CREATE TABLE "{PG_TABLE}" ('
                "id integer PRIMARY KEY, payload text NOT NULL)"
            )
            conn.execute(
                f'INSERT INTO "{PG_TABLE}" (id, payload) VALUES (%s, %s)',
                (1, "smoke"),
            )
        row = conn.execute(
            f'SELECT id, payload FROM "{PG_TABLE}" WHERE id = %s', (1,)
        ).fetchone()
        if row != (1, "smoke"):
            raise AssertionError(f"fila leída no coincide: {row!r}")
        return f"insert/lectura/borrado en '{PG_TABLE}'"
    finally:
        conn.execute(f'DROP TABLE IF EXISTS "{PG_TABLE}"')
        conn.commit()
        conn.close()


def check_redis_ping(cfg: dict) -> str:
    client = redis_client(cfg)
    pong = client.ping()
    if pong is not True:
        raise AssertionError(f"respuesta inesperada a PING: {pong!r}")
    return f"autenticado contra {cfg['REDIS_HOST']}:{cfg['REDIS_PORT']}"


def check_redis_data_cycle(cfg: dict) -> str:
    client = redis_client(cfg)
    client.set(REDIS_KEY, "smoke-value")
    value = client.get(REDIS_KEY)
    if value != "smoke-value":
        raise AssertionError(f"valor leído no coincide: {value!r}")
    deleted = client.delete(REDIS_KEY)
    if deleted != 1:
        raise AssertionError(f"DELETE devolvió {deleted!r}")
    if client.get(REDIS_KEY) is not None:
        raise AssertionError("la clave sigue presente tras DELETE")
    return "SET/GET/DEL de clave de prueba"


def check_redis_ttl(cfg: dict) -> str:
    client = redis_client(cfg)
    ttl_key = f"{REDIS_KEY}:ttl"
    client.set(ttl_key, "will-expire", ex=REDIS_SMOKE_TTL)
    if client.get(ttl_key) != "will-expire":
        raise AssertionError("la clave con TTL no se lee antes de expirar")
    time.sleep(REDIS_SMOKE_TTL + 1)
    if client.get(ttl_key) is not None:
        raise AssertionError(
            f"la clave {ttl_key!r} sigue viva tras {REDIS_SMOKE_TTL + 1}s"
        )
    return f"clave expirada en <= {REDIS_SMOKE_TTL + 1}s"


CHECKS = (
    ("postgres: conexión autenticada", lambda cfg: check_pg_connect(cfg)),
    ("postgres: ciclo insert/lectura/borrado", lambda cfg: check_pg_data_cycle(cfg)),
    ("redis: conexión autenticada (PING)", lambda cfg: check_redis_ping(cfg)),
    ("redis: ciclo SET/GET/DEL", lambda cfg: check_redis_data_cycle(cfg)),
    ("redis: expiración por TTL", lambda cfg: check_redis_ttl(cfg)),
)


def main() -> int:
    print("== Verificación del stack (smoke) ==")
    try:
        cfg = load_config()
    except KeyError as exc:
        print(f"FAIL: configuración — falta la variable de entorno {exc}")
        return 1

    print(
        "Config: postgres={h}:{p}/{db} redis={rh}:{rp}".format(
            h=cfg["POSTGRES_HOST"],
            p=cfg["POSTGRES_PORT"],
            db=cfg["POSTGRES_DB"],
            rh=cfg["REDIS_HOST"],
            rp=cfg["REDIS_PORT"],
        )
    )

    results: list[tuple[str, bool, str]] = []
    for name, fn in CHECKS:
        try:
            detail = fn(cfg)
            print(f"PASS: {name}" + (f" — {detail}" if detail else ""))
            results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001 — cada fallo se reporta y sigue
            print(f"FAIL: {name} — {exc}")
            results.append((name, False, str(exc)))

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\nResumen: {passed}/{total} comprobaciones superadas")
    if passed < total:
        for name, ok, reason in results:
            if not ok:
                print(f"  falló: {name} — {reason}")
        print("Resultado: FAIL")
        return 1
    print("Resultado: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
