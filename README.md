# mantiscode-test — Stack de desarrollo local (dev/infra)

Stack Docker Compose para desarrollo local con **Postgres**, **Redis** y **Adminer**,
más un verificador Python (`smoke`) que valida la salud del stack con un solo comando.

## Servicios y puertos

Todos los puertos se publican **solo en `127.0.0.1`** (nada accesible desde fuera del host).

| Servicio           | Imagen                             | Puerto host (por defecto) | Perfil  | Notas                                   |
| ------------------ | ---------------------------------- | ------------------------- | ------- | --------------------------------------- |
| `postgres`         | `postgres:17-alpine`               | `5432`                    | —       | Healthcheck `pg_isready`; datos en volumen `devstack_pgdata` |
| `redis`            | `redis:7-alpine`                   | `6379`                    | —       | Contraseña (`requirepass`) + AOF; volumen `devstack_redisdata` |
| `adminer`          | `adminer:4.17.1`                   | `8081`                    | —       | UI web para Postgres: http://127.0.0.1:8081 |
| `redis-commander`  | `rediscommander/redis-commander` (digest fijado) | `8082`      | `tools` | UI web para Redis: http://127.0.0.1:8082 |
| `smoke`            | build local (`docker/smoke/`)      | —                         | `check` | One-shot; se ejecuta con `run --rm`     |

Los servicios se resuelven por nombre en la red interna `devstack`; los dependientes
esperan a que `postgres`/`redis` reporten `healthy` (`depends_on: service_healthy`).

## Ciclo de vida

```bash
docker compose up -d            # levanta postgres, redis y adminer
docker compose ps               # estado (postgres/redis deben estar healthy)
docker compose logs -f postgres # seguir logs de un servicio
docker compose run --rm smoke   # verificación del stack (perfil check, one-shot)
docker compose down             # parar y quitar contenedores (conserva volúmenes)
```

`up -d` es idempotente: un segundo `up -d` no recrea contenedores sanos.
Los datos persisten en volúmenes nombrados y sobreviven a `down`/`up -d` (sin `-v`).

## Verificación (smoke)

```bash
docker compose run --rm smoke
```

Ejecuta el verificador Python (`docker/smoke/check.py`) dentro de la red del stack:

- conexión autenticada a Postgres y Redis,
- ciclo de insert/lectura/borrado en ambos,
- expiración por TTL en Redis.

Imprime `PASS`/`FAIL` por comprobación con un resumen final; termina con código
de salida `0` si todo pasa y distinto de `0` si algo falla. El contenedor se
elimina al terminar (`--rm`).

## Perfiles

- Por defecto (`docker compose up -d`): solo `postgres`, `redis` y `adminer`.
- `--profile tools up -d`: añade **Redis Commander** (UI de Redis) en `http://127.0.0.1:8082`.
- `check`: lo activa automáticamente `docker compose run --rm smoke`.

## Configuración (`.env`)

Todo es configurable sin editar `compose.yaml`. Copia y edita:

```bash
cp .env.example .env
```

Variables (todas con valor por defecto inline en `compose.yaml`, así que el stack
funciona **sin** `.env`):

- Imágenes: `POSTGRES_IMAGE`, `REDIS_IMAGE`, `ADMINER_IMAGE`, `REDIS_COMMANDER_IMAGE`.
- Puertos: `POSTGRES_PORT` (5432), `REDIS_PORT` (6379), `ADMINER_PORT` (8081),
  `REDIS_COMMANDER_PORT` (8082).
- Postgres: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
- Redis: `REDIS_PASSWORD` (lo usa `requirepass`, el healthcheck y el verificador).

Tras cambiar `.env`, recrea con `docker compose up -d` (o `down` + `up -d`).
Para actualizar una imagen: cambia su variable `*_IMAGE` en `.env` y ejecuta
`docker compose pull <servicio>` + `up -d`.

## Limpieza de disco

```bash
docker compose down -v --rmi local   # contenedores + volúmenes + imagen local del smoke
docker system df                     # uso real de imágenes, volúmenes y build cache
```

`-v` borra los volúmenes de datos (Postgres y Redis) — destruye los datos del stack.
