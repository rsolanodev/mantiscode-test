# Delta spec: stack-smoke-verification

## Purpose

Define la verificación automatizada del stack: un servicio one-shot en Python que valida, desde dentro de la red de Compose, que Postgres y Redis funcionan, persisten datos y respetan la configuración del entorno, con resultado claro de éxito o fallo.

## ADDED Requirements

### Requirement: Verificación one-shot con código de salida

El servicio de verificación SHALL ejecutarse como tarea one-shot (`docker compose run --rm smoke`), SHALL terminar con código `0` cuando todas las comprobaciones pasan y con código distinto de `0` cuando alguna falla.

#### Scenario: Stack sano

- **WHEN** el stack está healthy y se ejecuta `docker compose run --rm smoke`
- **THEN** el comando termina con código `0` y el contenedor se elimina al terminar

#### Scenario: Dependencia caída

- **WHEN** `redis` está detenido y se ejecuta `docker compose run --rm smoke`
- **THEN** el comando termina con código distinto de `0` e indica qué comprobación falló

### Requirement: Cobertura funcional de las comprobaciones

La verificación SHALL cubrir, como mínimo: conexión autenticada a Postgres y a Redis, ciclo de escritura/lectura/borrado en ambos, y expiración por TTL en Redis.

#### Scenario: Ciclo de datos en Postgres

- **WHEN** se ejecuta la verificación contra un Postgres healthy
- **THEN** se crea una tabla de trabajo temporal, se inserta y lee una fila de prueba y se limpia sin dejar objetos residuales

#### Scenario: Ciclo de datos y TTL en Redis

- **WHEN** se ejecuta la verificación contra un Redis healthy
- **THEN** se escribe, lee y borra una clave de prueba, y una clave con TTL expira dentro del plazo definido

### Requirement: Salida legible por comprobación

Cada comprobación SHALL imprimir un resultado visible (p. ej. `PASS`/`FAIL`) con su nombre, y los fallos SHALL incluir el motivo.

#### Scenario: Reporte en salida estándar

- **WHEN** termina una ejecución de la verificación
- **THEN** la salida lista cada comprobación con su resultado y un resumen final con el total de aciertos y fallos

### Requirement: Build reproducible del verificador

La imagen del verificador SHALL construirse desde el contexto `docker/smoke/` con dependencias fijadas en un manifest, usando `build.network: host` para descargar paquetes, y el build SHALL completarse sin intervención manual.

#### Scenario: Build desde cero

- **WHEN** la imagen del verificador no existe y se ejecuta `docker compose build smoke`
- **THEN** la imagen se construye correctamente instalando las dependencias por la red del host

### Requirement: Uso de credenciales del entorno

El verificador SHALL leer las mismas variables de configuración que los servicios del stack (host por nombre de servicio, credenciales y contraseña incluidas), sin valores fijados en el código.

#### Scenario: Rotación de credenciales

- **WHEN** se cambia la contraseña de Redis en `.env`, se recrea el stack y se ejecuta la verificación
- **THEN** la verificación pasa usando la nueva contraseña sin cambios en el código
