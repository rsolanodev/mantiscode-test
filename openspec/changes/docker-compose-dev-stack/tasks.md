# Tareas: Stack de desarrollo local con Docker Compose

## 1. Verificación previa del entorno

- [x] 1.1 Confirmar que el daemon responde y hay disco disponible (`docker info`, `docker system df`)
- [x] 1.2 Descargar las imágenes oficiales con `docker pull` (`postgres:17-alpine`, `redis:7-alpine`, `adminer:4`, `rediscommander/redis-commander`, `python:3.12-slim`) y fijar el tag menor/digest real de `adminer` y `redis-commander` (resuelve la Open Question del design)

## 2. Configuración base del stack

- [x] 2.1 Crear `compose.yaml` en la raíz con los servicios `postgres`, `redis` y `adminer`: imágenes fijadas, healthchecks (`pg_isready`, `redis-cli ping` con CMD-SHELL), `depends_on` con `condition: service_healthy`, red dedicada y volúmenes nombrados (`devstack_pgdata`, `devstack_redisdata` con AOF)
- [x] 2.2 Publicar puertos solo en `127.0.0.1` con sintaxis `${VAR:-default}` inline para que el stack funcione sin `.env`
- [x] 2.3 Añadir los servicios con perfil: `tools` (Redis Commander) y `check` (one-shot `smoke`, con `build.network: host` apuntando a `docker/smoke/`)
- [x] 2.4 Crear `.env.example` documentando todas las variables (puertos, credenciales, nombre de BD, contraseña de Redis, versiones de imagen)

## 3. Verificador Python (servicio smoke)

- [ ] 3.1 Crear `docker/smoke/Dockerfile` (base `python:3.12-slim`) y `docker/smoke/requirements.txt` con `psycopg[binary]` y `redis` con versiones fijadas
- [ ] 3.2 Implementar `docker/smoke/check.py`: conexión autenticada a Postgres y Redis por nombre de servicio, ciclo insert/lectura/borrado en ambos, expiración TTL en Redis, salida `PASS`/`FAIL` por comprobación con resumen final y código de salida 0/no-0
- [ ] 3.3 Leer toda la configuración desde variables de entorno (host, credenciales, contraseña) sin valores fijados en el código
- [x] 3.4 Construir y probar la imagen: `docker compose build smoke` y validar el build con `build.network: host`

## 4. Validación del stack contra los specs

- [x] 4.1 `docker compose up -d` desde cero: los tres servicios base quedan `running` y `healthy`, y `adminer`/`smoke` no arrancan antes de que `postgres`/`redis` estén healthy
- [ ] 4.2 `docker compose run --rm smoke` termina con código 0, imprime PASS/FAIL por comprobación y el contenedor se elimina
- [ ] 4.3 Persistencia: escribir fila en Postgres y clave TTL en Redis, `docker compose down` + `up -d`, y repetir la verificación (los datos sobreviven)
- [ ] 4.4 Idempotencia: un segundo `docker compose up -d` no recrea contenedores sanos (`docker compose ps` sin restarts)
- [ ] 4.5 Escenarios de fallo: detener `redis` y confirmar que `smoke` falla con código no-0 indicando la comprobación fallida; restaurar después
- [ ] 4.6 Configuración: cambiar un puerto y la contraseña de Redis vía `.env`, recrear y validar que el stack y `smoke` siguen funcionando; borrar `.env` y validar arranque con defaults
- [ ] 4.7 Perfiles: `up -d` por defecto no levanta `tools`/`check`; `--profile tools up -d` deja la UI de Redis accesible en su puerto

## 5. Documentación y cierre

- [ ] 5.1 Actualizar `README.md`: propósito del stack, tabla de servicios y puertos, ciclo de vida (`up`, `ps`, `logs`, `down`, `run --rm smoke`), perfiles, configuración por `.env` y limpieza de disco (`docker compose down -v --rmi local`, `docker system df`)
- [ ] 5.2 Validar el change con `openspec validate` y dejar el repo limpio de ficheros temporales
