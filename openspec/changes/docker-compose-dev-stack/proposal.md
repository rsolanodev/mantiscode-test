# Propuesta: Stack de desarrollo local (dev/infra) con Docker Compose

## Why

Queremos poner a prueba el flujo de creación de proyectos en MantisCode con docker compose. Un stack dev/infra basado en imágenes oficiales preconstruidas (Postgres, Redis, Adminer) es la prueba más rápida y aislable: ejercita la orquestación en runtime (redes, volúmenes, healthchecks, perfiles, puertos) sin builds largos, y añade un único servicio Python mínimo para validar el flujo de build de imágenes, necesario en este sandbox (`build.network: host`).

## What Changes

- Proyecto Compose nuevo en la raíz del repo con los servicios:
  - `postgres`: imagen oficial de Postgres (tag `alpine`), con healthcheck (`pg_isready`), volumen persistente y credenciales/base de datos configurables por `.env`.
  - `redis`: imagen oficial de Redis (tag `alpine`), con healthcheck, contraseña configurable y persistencia AOF en volumen.
  - `adminer`: UI web para inspeccionar Postgres, publicado solo en `localhost`.
  - `tools` (perfil opcional `tools`): Redis Commander, UI web para inspeccionar Redis.
  - `smoke` (perfil `check`): servicio one-shot en Python 3.12 construido localmente que ejecuta una batería de verificaciones de conectividad y funcionalidad contra Postgres y Redis.
- Red interna dedicada para el stack; los contenedores se resuelven por nombre de servicio.
- Volúmenes nombrados explícitos para persistencia de datos de Postgres y AOF de Redis.
- Archivo `.env.example` con toda la configuración (puertos publicados, credenciales, versiones de imagen) y `README.md` con el ciclo de vida (`up`, `ps`, `logs`, `down`, smoke tests).
- Healthchecks y `depends_on` con `condition: service_healthy` en todos los servicios dependientes.

## Capabilities

### New Capabilities

- `local-dev-stack`: definición y comportamiento del stack Compose — servicios, red interna, volúmenes, puertos publicados, healthchecks, perfiles y configuración por `.env`.
- `stack-smoke-verification`: verificación automatizada en Python (servicio `smoke`) que valida la salud del stack: conexión a Postgres y Redis, escritura/lectura de datos, persistencia entre reinicios y alcance de los puertos publicados.

### Modified Capabilities

- (ninguna — repositorio nuevo, no existen specs previas)

## Impact

- Repositorio nuevo: crea `compose.yaml`, `.env.example`, `docker/smoke/` (Dockerfile + script de verificación) y actualiza `README.md`.
- Dependencias: imágenes oficiales públicas (`postgres`, `redis`, `adminer`, `rediscommander/redis-commander`, `python`), obtenidas por `docker pull` desde el daemon del sandbox.
- Restricción del entorno: los contenedores en runtime no tienen salida a internet (bridge sin NAT); el build del servicio `smoke` necesita `build.network: host` para instalar dependencias pip.
- Volúmenes, imágenes y build cache consumen disco del workspace (verificar con `docker system df` al terminar).
