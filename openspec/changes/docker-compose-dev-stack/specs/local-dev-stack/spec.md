# Delta spec: local-dev-stack

## Purpose

Define el comportamiento del stack de desarrollo local orquestado con Docker Compose: qué servicios se levantan, cómo se comunican, cómo persisten datos y cómo se configura, de modo que el entorno sea reproducible con un solo comando.

## ADDED Requirements

### Requirement: Arranque del stack con un comando

El stack SHALL levantar los servicios base (`postgres`, `redis`, `adminer`) con `docker compose up -d` sin intervención adicional, y el comando SHALL ser idempotente (un segundo `up -d` no debe recrear contenedores sanos).

#### Scenario: Arranque limpio desde cero

- **WHEN** se ejecuta `docker compose up -d` sin ningún contenedor previo
- **THEN** los tres servicios base quedan en estado `running` y `healthy` en un plazo razonable

#### Scenario: Arranque idempotente

- **WHEN** se ejecuta `docker compose up -d` por segunda vez sin cambios de configuración
- **THEN** ningún contenedor sano se recrea ni se reinicia

### Requirement: Healthchecks como barrera de arranque

Los servicios `postgres` y `redis` SHALL definir healthchecks, y ningún servicio que dependa de ellos SHALL iniciarse antes de que reporten `healthy` (`depends_on` con `condition: service_healthy`).

#### Scenario: Orden de arranque garantizado

- **WHEN** se levanta el stack desde cero
- **THEN** `adminer` y el servicio de verificación no arrancan hasta que `postgres` y `redis` reportan `healthy`

### Requirement: Red interna con resolución por nombre de servicio

El stack SHALL usar una red interna dedicada en la que los contenedores se alcancen entre sí por nombre de servicio. En este entorno el DNS embebido de Docker no está disponible, por lo que la resolución de nombres SHALL garantizarse con IPs estáticas asignadas por Compose en la red dedicada y entradas `extra_hosts` (alias nombre→IP en `/etc/hosts`), de modo que ningún servicio dependiente lleve IPs en su propia configuración.

#### Scenario: Resolución entre contenedores

- **WHEN** un contenedor del stack intenta alcanzar `postgres` o `redis` por nombre de servicio
- **THEN** la conexión se establece por la red interna usando el mapeo nombre→IP gestionado por Compose (`extra_hosts`), sin IPs en la configuración de aplicación de los servicios

### Requirement: Persistencia en volúmenes nombrados

Los datos de Postgres y la persistencia AOF de Redis SHALL almacenarse en volúmenes nombrados explícitos, y los datos SHALL sobrevivir a un ciclo de `down`/`up` sin `-v`.

#### Scenario: Datos de Postgres sobreviven al reinicio

- **WHEN** se escribe una fila de prueba, se ejecuta `docker compose down` y luego `up -d`
- **THEN** la fila de prueba sigue presente en la base de datos

#### Scenario: Claves de Redis sobreviven al reinicio

- **WHEN** se escribe una clave con TTL, se ejecuta `docker compose down` y luego `up -d`
- **THEN** la clave sigue presente si su TTL no ha expirado

### Requirement: Puertos publicados solo en localhost

Los puertos de administración (UI de Adminer) SHALL publicarse en `127.0.0.1` del host, y Postgres/Redis SHALL publicarse en el host solo para uso de desarrollo local.

#### Scenario: Adminer accesible desde el host

- **WHEN** el stack está healthy y se abre la URL de Adminer configurada en el host
- **THEN** la interfaz responde y permite iniciar sesión en Postgres con las credenciales del `.env`

### Requirement: Configuración por entorno sin editar compose.yaml

Toda la configuración variable (puertos publicados, credenciales, base de datos, contraseña de Redis, versiones de imagen) SHALL leerse de variables con valores por defecto inline en `compose.yaml`, de modo que el stack funcione sin `.env` y un `.env.example` documente todas las variables.

#### Scenario: Cambio de puerto vía .env

- **WHEN** se define otro puerto para Postgres en `.env` y se recrea el stack
- **THEN** el nuevo puerto queda publicado en el host y el resto de la configuración no cambia

#### Scenario: Funcionamiento sin .env

- **WHEN** no existe archivo `.env` y se ejecuta `docker compose up -d`
- **THEN** el stack arranca con los valores por defecto declarados en `compose.yaml`

### Requirement: Perfiles opcionales fuera del arranque por defecto

Los servicios auxiliares `tools` (UI de Redis) y `check` (verificación) SHALL declararse en perfiles, de modo que no arranquen con `up -d` por defecto.

#### Scenario: Arranque por defecto sin auxiliares

- **WHEN** se ejecuta `docker compose up -d` sin perfiles
- **THEN** los contenedores de `tools` y `check` no aparecen en `docker compose ps`

#### Scenario: Activación de perfil tools

- **WHEN** se ejecuta `docker compose --profile tools up -d`
- **THEN** el servicio de UI de Redis queda en ejecución y accesible en su puerto
