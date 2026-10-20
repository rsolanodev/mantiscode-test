# Diseño: Stack de desarrollo local con Docker Compose

## Context

Repositorio vacío (`mantiscode-test`) cuya finalidad es probar el flujo de creación de proyectos en MantisCode. El sandbox dispone de Docker 29.9.1 y Compose v5.6.0 sin `sudo`, con restricciones conocidas:

- El bridge por defecto **no tiene NAT de salida**: los contenedores no alcanzan internet en runtime; sí se resuelven por nombre de servicio y alcanzan puertos publicados en localhost.
- Los builds que descargan dependencias requieren `docker build --network host` (o `build.network: host` en Compose).
- `docker pull` lo realiza el daemon (sí tiene salida), por lo que las imágenes oficiales se pueden descargar.
- Imágenes, volúmenes y build cache cuentan contra el disco del workspace (`docker system df`).

La motivación está en `proposal.md` — Why; los requisitos en los deltas de `specs/`.

## Goals / Non-Goals

**Goals:**

- Un solo comando levanta un stack dev/infra útil y observable (Postgres + Redis + Adminer).
- Ejercitar de forma deliberada las piezas de Compose: healthchecks, `depends_on` con condiciones, perfiles, volúmenes nombrados, red dedicada, interpolación `.env` y `run --rm` one-shot.
- Un único build de imagen (verificador Python) para validar el flujo `build.network: host` sin alargar el ciclo.
- Verificación automática del stack ejecutable en cualquier momento con un comando.

**Non-Goals:**

- No hay aplicación de negocio ni API: es un entorno dev/infra.
- No se busca CI, TLS, réplicas, clustering de Redis ni alta disponibilidad.
- No se publica nada fuera de `127.0.0.1`.

## Decisions

1. **Imágenes oficiales con tags mayores fijados.** `postgres:17-alpine`, `redis:7-alpine`, `adminer:4` y `rediscommander/redis-commander:latest` (tag menor a confirmar con `docker pull` en implementación). *Alternativa descartada:* `latest` puro (no reproducible) o builds propios de estas piezas (coste y mantenimiento innecesarios para la prueba).

2. **`compose.yaml` en la raíz del repo y contexto de build en `docker/smoke/`.** La raíz es lo idiomático para un proyecto Compose único. *Alternativa descartada:* subdirectorio `stack/` (solo útil si hubiera varios stacks).

3. **Defaults inline + `.env.example`.** Todas las variables usan sintaxis `${VAR:-default}` para que `up -d` funcione sin `.env`; `.env.example` documenta el set completo y se copia a `.env` para personalizar. *Alternativa descartada:* exigir `.env` (fricción para una prueba de arranque rápido).

4. **Verificador como servicio one-shot con perfil `check`.** Python 3.12-slim, `psycopg[binary]` + `redis` con versiones fijadas en `docker/smoke/requirements.txt`, ejecutado con `docker compose run --rm smoke`. *Alternativas descartadas:* script en el host (requiere dependencias locales y no prueba la red interna), o `docker run` manual (más fricción y no integra perfiles/variables).

5. **Build del verificador con `build.network: host`.** Necesario para pip en este sandbox; se declara en el propio `compose.yaml` para que `docker compose build smoke` funcione sin flags extra.

6. **Healthchecks nativos.** Postgres: `pg_isready` con `CMD-SHELL` y variables del contenedor; Redis: `redis-cli ping` (con `-a` a la contraseña del contenedor si está definida). Los servicios dependientes usan `depends_on: condition: service_healthy`. *Alternativa descartada:* waits con `sleep` o scripts externos (frágiles).

7. **Persistencia con volúmenes nombrados explícitos** (`devstack_pgdata`, `devstack_redisdata` con AOF) y red dedicada `devstack` generada por Compose, sin contenedores extra (no `network_mode: host`: innecesario y expone más de lo debido).

8. **Puertos publicados en `127.0.0.1`.** Adminer y Redis Commander en puertos altos (p. ej. 8081/8082 por defecto) para evitar colisiones; Postgres/Redis publicados también en localhost para uso desde el host.

## Risks / Trade-offs

- [El daemon no puede descargar imágenes (red)] → Primera tarea de implementación: `docker pull` de las 5 imágenes y confirmación de tags reales antes de escribir el resto.
- [Redis Commander solo publica tag `latest` estable] → Fijar digest o versión confirmada en `docker pull`; dejar la versión en `.env` para actualizarla sin tocar `compose.yaml`.
- [Adminer 4.x está en mantenimiento] → Aceptable para desarrollo local; anotar en README que la UI es solo para el sandbox.
- [Puertos ya ocupados en el host] → Puertos por defecto altos y sobreescribibles por `.env`; los healthchecks fallarían de forma visible si hay colisión.
- [Disco del workspace] → Imágenes alpine/slim y limpieza documentada: `docker compose down -v --rmi local` + `docker system df` en el README.
- [Sin salida a internet en runtime] → Ninguna verificación ni servicio necesita internet tras el build; solo pip (host) y `docker pull` (daemon) lo usan.

## Migration Plan

No aplica (repo nuevo). Rollback: `docker compose down -v --rmi local` y borrar los ficheros añadidos; `openspec archive` del change al validar.

## Open Questions

- Tag menor exacto de `adminer` y `rediscommander/redis-commander`: **resuelto en implementación**. `adminer:4` apunta a **4.17.1** (tag exacto `adminer:4.17.1` verificado con el mismo digest de manifiesto). `rediscommander/redis-commander` no publica tags de versión en Docker Hub (solo `latest` y ramas dev): se fija por digest `sha256:19cd0c49f418779fa2822a0496c5e6516d0c792effc39ed20089e6268477e40a` como default inline en `compose.yaml` y en `.env.example`.
