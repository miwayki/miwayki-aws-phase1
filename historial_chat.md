# Historial de conversación del proyecto Miwayki

> Regla operativa local (acordada en chat): mantener este archivo actualizado de forma periódica con el detalle de lo conversado para poder pausar y retomar el proyecto en otro momento.

## 2026-04-08 - Inicio de bitácora

### Contexto inicial acordado
- El documento fuente principal del proyecto es `miwayki_master_spec.md`.
- Se trabajará primero en local y, tras validar y probar todo, se migrará a AWS.
- Entorno del usuario: macOS Tahoe en Apple Silicon (M1 Pro).
- Objetivo técnico inicial: levantar un servidor Linux ligero (preferencia Ubuntu LTS) usando virtualización nativa de macOS.

### Plan previo acordado antes de desarrollo
- Seguir una secuencia tipo roadmap:
  - Preparación de base.
  - Infra local equivalente a "EC2 simulada".
  - Chatwoot.
  - Bridge FastAPI.
  - Capa IA.
  - Hardening.
  - Migración final a AWS cuando esté estable.

### Trabajo ejecutado en terminal (resumen)
- Verificación de herramientas de compilación:
  - `xcode-select --install` -> ya estaba instalado.
- Instalación/actualización de Lima:
  - `brew install lima`
  - Resultado: `limactl version 2.1.1`.
- Creación de instancia Linux:
  - Se ejecutó `limactl create` para `miwayki-linux` con backend `vz`.
  - Se mostró menú interactivo de confirmación (comportamiento normal en versiones recientes).
  - Preferencia confirmada por el usuario: Ubuntu LTS.
- Descarga y aprovisionamiento de imagen:
  - Descarga de Ubuntu cloud image ARM64 completada.
  - Conversión de imagen y expansión de disco completadas.
  - Descarga de componentes adicionales (nerdctl archive) completada.
- Inicio de VM:
  - `limactl start miwayki-linux` completado.
  - VM en estado `READY`.
- Acceso a shell de la VM:
  - `limactl shell miwayki-linux`.
  - Prompt dentro de la VM confirmado (`lima-miwayki-linux`).
  - Se observó carpeta del proyecto montada en `/Users/armandosilva/DATA/SMC/CS_79C_cloud/Final_Project`.

### Decisiones y preferencias explícitas del usuario
- Preferencia por Ubuntu LTS por estabilidad/universalidad.
- Solicitud de mantener historial detallado de esta conversación en `historial_chat.md`.
- No usar una regla de `.cursor/rules`; mantenerlo como regla local de trabajo en esta conversación/proyecto.

### Estado actual al cierre de esta entrada
- VM local Linux (Ubuntu LTS sobre `vz`) creada y operativa.
- Acceso por shell funcional.
- Archivo `historial_chat.md` inicializado como bitácora.

### Próxima actualización comprometida
- A partir de este punto, agregar nuevas entradas con:
  - qué se decidió,
  - qué comandos se ejecutaron,
  - qué resultados se obtuvieron,
  - y qué tareas quedan pendientes.

## 2026-04-08 - Entrada #2 (continuación de infraestructura local)

### Objetivo de esta fase
- Continuar el proyecto dejando la VM Ubuntu lista para ejecutar el stack del MVP con patrón tipo EC2 + Compose.

### Verificaciones realizadas
- Estado de instancia:
  - `limactl list` -> `miwayki-linux` en `Running`.
- Sistema invitado confirmado:
  - Ubuntu `24.04.4 LTS` (`noble`), arquitectura `aarch64`.

### Instalación ejecutada dentro de `miwayki-linux`
- Se instaló Docker Engine oficial con repositorio de Docker para Ubuntu Noble:
  - Paquetes base: `ca-certificates`, `curl`, `gnupg`.
  - Repositorio y llave GPG de Docker.
  - Paquetes Docker:
    - `docker-ce`
    - `docker-ce-cli`
    - `containerd.io`
    - `docker-buildx-plugin`
    - `docker-compose-plugin`
- Servicio Docker:
  - `systemctl enable --now docker` completado.
- Usuario:
  - Se ejecutó `usermod -aG docker $USER` para acceso sin `sudo`.

### Resultado técnico
- Versiones instaladas:
  - `Docker version 29.4.0`
  - `Docker Compose version v5.1.1`
- Validación de acceso:
  - `docker ps` sin `sudo` todavía devuelve permiso denegado en la sesión actual (esperado hasta refrescar grupo).
  - `sudo docker ps` funciona correctamente.

### Próximo paso inmediato
- Refrescar grupo de sesión en la VM para usar Docker sin `sudo`:
  - `newgrp docker`
  - volver a validar con `docker ps`.

### Pendientes de la siguiente fase
- Crear `docker-compose.yml` base del proyecto local:
  - `postgres`
  - `redis`
  - red y volúmenes persistentes
  - base para integrar Chatwoot + Bridge FastAPI.

## 2026-04-08 - Entrada #3 (base Compose operativa)

### Objetivo de esta fase
- Crear y validar la capa base de infraestructura local con Docker Compose, alineada al documento maestro (`compose/` con archivos separados por entorno).

### Archivos creados
- `compose/docker-compose.yml`
- `compose/docker-compose.dev.yml`
- `compose/docker-compose.prod.yml`
- `compose/.env.example`
- `compose/.env`
- `compose/README.md`

### Diseño aplicado
- Servicios base:
  - `postgres` (`postgres:16-alpine`)
  - `redis` (`redis:7-alpine`)
- Volúmenes persistentes:
  - `postgres_data`
  - `redis_data`
- Red dedicada:
  - `miwayki-core-net`
- Publicación de puertos en desarrollo solo en loopback:
  - `127.0.0.1:5432 -> postgres`
  - `127.0.0.1:6379 -> redis`
- Perfil prod definido con puertos no publicados.

### Validaciones ejecutadas
- Render de configuración compose en la VM: correcto.
- Arranque de stack local:
  - `docker compose ... up -d` ejecutado en `compose/`.
- Estado final:
  - `miwayki-postgres`: `healthy`
  - `miwayki-redis`: `healthy`
- Logs revisados:
  - PostgreSQL listo para aceptar conexiones.
  - Redis listo para aceptar conexiones.

### Notas operativas
- En la VM, la ruta montada del proyecto puede comportarse como solo lectura para algunas operaciones puntuales; por eso se dejó `.env` preparado desde host.
- El warning de overcommit de Redis queda como nota de optimización para más adelante (no bloquea desarrollo local).

### Estado actual
- Infra base local lista y funcionando para continuar con:
  - despliegue de Chatwoot (fase siguiente del roadmap), o
  - scaffolding del bridge FastAPI.

## 2026-04-08 - Entrada #4 (Chatwoot levantado en local)

### Ajustes previos importantes
- Se corrigió `.env` para eliminar un espacio no deseado en la contraseña:
  - de `POSTGRES_PASSWORD= Miwayki20261014`
  - a `POSTGRES_PASSWORD=Miwayki20261014`
- Se detectó que ejecutar `limactl` dentro de la VM devuelve `command not found` (esperado). `limactl` se ejecuta desde macOS host, no desde el guest Ubuntu.

### Implementación de fase Chatwoot
- Se agregaron archivos:
  - `compose/.env.chatwoot.example`
  - `compose/.env.chatwoot`
  - `compose/docker-compose.chatwoot.yml`
- Se amplió `compose/README.md` con pasos de inicialización de Chatwoot.

### Incidencia y corrección técnica
- Primera ejecución de `db:chatwoot_prepare` falló por falta de extensión `vector` en PostgreSQL.
- Se cambió la imagen de Postgres:
  - de `postgres:16-alpine`
  - a `pgvector/pgvector:pg16`
- Se recreó stack y volúmenes para iniciar limpio.

### Inicialización y estado
- Base `chatwoot_production` creada.
- Migración/preparación ejecutada con:
  - `bundle exec rails db:chatwoot_prepare`
- Servicios activos:
  - `miwayki-chatwoot` en `127.0.0.1:3000`
  - `miwayki-chatwoot-sidekiq`
  - `miwayki-postgres` (healthy)
  - `miwayki-redis` (healthy)

### Pendiente inmediato de seguridad
- Reemplazar en `compose/.env.chatwoot`:
  - `SECRET_KEY_BASE=replace_with_long_random_secret`
  por un valor real generado con `openssl rand -hex 64`.

## 2026-04-08 - Entrada #5 (reinicio con variables actualizadas)

### Acción realizada
- Usuario actualizó `compose/.env.chatwoot` y guardó cambios.
- Se reiniciaron servicios para aplicar configuración:
  - `chatwoot`
  - `chatwoot-sidekiq`

### Validación de estado
- Servicios operativos:
  - `miwayki-chatwoot` (`127.0.0.1:3000`)
  - `miwayki-chatwoot-sidekiq`
  - `miwayki-postgres` (healthy)
  - `miwayki-redis` (healthy)

### Validación HTTP
- `curl -I http://127.0.0.1:3000` respondió `HTTP/1.1 302 Found`.
- Redirección a `/installation/onboarding`, confirmando que Chatwoot está arriba y listo para onboarding.

### Nota de seguridad
- Mantener `SECRET_KEY_BASE` como cadena aleatoria larga para evitar valores semánticos predecibles.

## 2026-04-08 - Entrada #8 (incidencia 404 en fake site)

### Problema observado
- El servidor `python3 -m http.server 8080 --directory chatwoot_fake_site` respondió `404 File not found`.

### Causa probable
- Comando ejecutado desde `compose/` dentro de la VM, por lo que la ruta relativa `chatwoot_fake_site` no existe en ese nivel.

### Corrección
- Ejecutar el servidor con ruta absoluta o con ruta relativa correcta (`../chatwoot_fake_site`) desde `compose/`.

### Nota operativa
- Dentro de la VM no se debe usar `limactl`; ese comando es del host macOS.

## 2026-04-08 - Entrada #9 (fake site cargando correctamente)

### Validación visual
- Se confirmó en navegador que `http://127.0.0.1:8080` carga correctamente la página:
  - título: `Sandbox local de Chatwoot`
  - texto de prueba y badge de modo local visibles.

### Resultado
- El problema de `404` quedó resuelto.
- Entorno listo para prueba funcional del widget (mensaje de prueba end-to-end hacia Chatwoot).

## 2026-04-08 - Entrada #10 (validación E2E widget -> inbox)

### Prueba realizada
- Se envió mensaje desde `http://127.0.0.1:8080` usando el widget embebido.
- Se verificó recepción en Chatwoot inbox `Miwayki`.

### Resultado
- Flujo E2E local validado:
  - Fake site (widget) -> Chatwoot Web Inbox -> conversación visible en panel agente.
- El concepto base de captura por chat web funciona en entorno local.

### Próximo paso acordado
- Implementar Bridge FastAPI mínimo para comenzar integración entre Chatwoot y servicios de negocio/IA.

## 2026-04-08 - Entrada #6 (widget token obtenido)

### Resultado de onboarding Chatwoot
- Se completó la creación del inbox web en Chatwoot.
- Se obtuvo snippet de integración del widget con:
  - `baseUrl`: `http://localhost:3000`
  - `websiteToken`: `ELsmms2CKZGLGCAuSNNZvLaV`

### Snippet registrado
```html
<script>
  (function(d,t) {
    var BASE_URL="http://localhost:3000";
    var g=d.createElement(t),s=d.getElementsByTagName(t)[0];
    g.src=BASE_URL+"/packs/js/sdk.js";
    g.async = true;
    s.parentNode.insertBefore(g,s);
    g.onload=function(){
      window.chatwootSDK.run({
        websiteToken: 'ELsmms2CKZGLGCAuSNNZvLaV',
        baseUrl: BASE_URL
      })
    }
  })(document,"script");
</script>
```

### Nota operativa
- Este snippet es válido para entorno local.
- En staging/prod se debe reemplazar `BASE_URL` por dominio público de Chatwoot y mantener el token del inbox correspondiente.

## 2026-04-08 - Entrada #7 (sitio fake local + prioridad de validación)

### Decisión funcional
- Se acordó no usar web productiva para pruebas.
- Se crea página local fake para validar concepto sin riesgo.

### Implementación
- Carpeta nueva: `chatwoot_fake_site/`
- Archivos:
  - `chatwoot_fake_site/index.html` con widget Chatwoot embebido.
  - `chatwoot_fake_site/README.md` con comando de arranque local.

### Enfoque de trabajo acordado
- Priorizar validación del flujo end-to-end primero:
  - Chatwoot <-> Bridge <-> servicios base
- Dejar ajustes finos (atributos custom, mejoras adicionales) para fase posterior, una vez validado el concepto.

## 2026-04-08 - Entrada #11 (bridge FastAPI MVP implementado)

### Objetivo
- Construir el bridge mínimo para recibir webhooks de Chatwoot y responder automáticamente al hilo para cerrar el loop técnico.

### Implementación realizada
- Nueva carpeta de servicio: `bridge/`
- Archivos creados:
  - `bridge/app/main.py`
  - `bridge/requirements.txt`
  - `bridge/Dockerfile`
- Lógica incluida:
  - `GET /health` para verificación de vida.
  - `POST /webhooks/chatwoot` para procesar eventos.
  - Filtrado anti-loop (ignora mensajes de `agent`/`bot` y salientes).
  - Respuesta automática simple en la conversación vía API de Chatwoot.

### Integración en Compose
- Archivos nuevos:
  - `compose/docker-compose.bridge.yml`
  - `compose/.env.bridge.example`
  - `compose/.env.bridge`
- `compose/README.md` actualizado con sección de arranque y prueba del bridge.

### Variables requeridas para respuesta automática real
- `CHATWOOT_BASE_URL` (default interno: `http://chatwoot:3000`)
- `CHATWOOT_API_TOKEN` (token API de Chatwoot con permisos)
- `BRIDGE_AUTO_REPLY` (mensaje automático de prueba)

### Estado
- Skeleton funcional de bridge completado y listo para levantar junto a Chatwoot.
- Siguiente validación: registrar webhook en Chatwoot apuntando a `http://bridge:8000/webhooks/chatwoot` (intra red Docker) y confirmar respuesta automática en conversación.

## 2026-04-08 - Entrada #12 (stack bridge levantado y health validado)

### Comandos ejecutados
- `limactl start miwayki-linux`
- `limactl shell miwayki-linux -- bash -lc "cd .../compose && sudo docker compose -f docker-compose.yml -f docker-compose.chatwoot.yml -f docker-compose.bridge.yml up -d --build"`
- `limactl shell miwayki-linux -- bash -lc "curl -sS http://127.0.0.1:8000/health"`
- `limactl shell miwayki-linux -- bash -lc "cd .../compose && sudo docker compose ... ps"`

### Resultado
- VM `miwayki-linux` en estado `Running`.
- Servicio `bridge` construido y levantado correctamente.
- Estado de stack:
  - `miwayki-postgres`: healthy
  - `miwayki-redis`: healthy
  - `miwayki-chatwoot`: up
  - `miwayki-chatwoot-sidekiq`: up
  - `miwayki-bridge`: up (`127.0.0.1:8000->8000`)
- Healthcheck del bridge validado:
  - respuesta: `{"status":"ok"}`

### Bloqueo pendiente para auto-reply real
- `compose/.env.bridge` mantiene `CHATWOOT_API_TOKEN` vacío.
- Sin ese token, el webhook se recibe pero no publica respuesta en la conversación.

### Próximo paso inmediato
- Crear/obtener API Access Token en Chatwoot, pegarlo en `.env.bridge`, reiniciar `bridge` y registrar webhook `http://bridge:8000/webhooks/chatwoot`.

## 2026-04-08 - Entrada #13 (token bridge cargado + reinicio exitoso)

### Acción realizada
- Se actualizó `compose/.env.bridge` con `CHATWOOT_API_TOKEN` y se corrigió formato retirando espacio inicial en el valor.

### Comandos ejecutados
- Reinicio del servicio bridge:
  - `sudo docker compose -f docker-compose.yml -f docker-compose.chatwoot.yml -f docker-compose.bridge.yml up -d bridge`
- Verificación de estado:
  - `sudo docker compose ... ps bridge`
- Verificación funcional:
  - `curl http://127.0.0.1:8000/health`
  - `sudo docker compose ... logs --tail=30 bridge`

### Resultado
- `miwayki-bridge` recreado y en estado `Up`.
- Healthcheck responde `{"status":"ok"}`.
- Logs de Uvicorn sin errores al arranque.

### Siguiente paso
- Registrar webhook en Chatwoot (Settings -> Integrations -> Webhooks):
  - URL: `http://bridge:8000/webhooks/chatwoot`
  - Evento: `message_created`
- Probar desde widget fake y validar auto-reply en conversación.

## 2026-04-08 - Entrada #14 (fix validación URL webhook Chatwoot)

### Problema
- Chatwoot UI rechazó `http://bridge:8000/webhooks/chatwoot` como URL inválida.

### Ajuste aplicado
- Se agregó alias de red Docker para bridge:
  - archivo: `compose/docker-compose.bridge.yml`
  - alias: `bridge.local`

### Validación técnica
- Se recreó `miwayki-bridge`.
- Desde contenedor `chatwoot`, resolución DNS correcta:
  - `getent hosts bridge.local` -> resuelve a la IP del servicio bridge.

### URL a usar en Chatwoot
- `http://bridge.local:8000/webhooks/chatwoot`

## 2026-04-08 - Entrada #15 (`.env.bridge` completo + verificación HMAC)

### Estado de configuración
- Usuario completó `compose/.env.bridge` con `CHATWOOT_WEBHOOK_SECRET` (valor del modal de Chatwoot al crear webhook).
- Webhook registrado en UI apuntando a `http://bridge.local:8000/webhooks/chatwoot`, evento `message_created`.

### Cambio en código
- `bridge/app/main.py`: si `CHATWOOT_WEBHOOK_SECRET` está definido, se valida firma según documentación Chatwoot (`X-Chatwoot-Signature`, `X-Chatwoot-Timestamp`, payload `"{timestamp}.{raw_body}"`).
- Si el secret está vacío, no se exige firma (útil solo en desarrollo).

### Despliegue
- Rebuild y reinicio de contenedor `miwayki-bridge` en VM.

### Próximo paso operativo para el usuario
- Abrir sitio fake del widget, enviar un mensaje de prueba y comprobar en Chatwoot que aparece la respuesta automática configurada en `BRIDGE_AUTO_REPLY`.
- Opcional: `sudo docker compose ... logs -f bridge` para ver requests del webhook.

## 2026-04-08 - Entrada #16 (E2E bridge validado por el usuario)

### Resultado
- Usuario confirmó ver la respuesta automática en el widget y en el inbox de Chatwoot.
- Mensaje de prueba observado: el configurado en `BRIDGE_AUTO_REPLY` (“Recibido. Este es el bridge MVP de prueba conectado correctamente.”).
- Con esto queda cerrado el loop técnico: widget → Chatwoot → webhook → FastAPI bridge → API Chatwoot → mensaje visible en conversación.

### Significado para el roadmap
- Fase 3 (Bridge) mínima operativa; siguiente bloque lógico según spec: capa IA / reglas de negocio sobre el mismo puente, sin rehacer la integración con Chatwoot.

## 2026-04-08 - Entrada #17 (pausa: continuación al día siguiente)

### Cierre de sesión
- Se acordó pausar el trabajo; continuación prevista **al día siguiente** (mañana).

### Estado del proyecto al cierre
- **Infra local (VM Lima + Docker Compose):** Postgres (`pgvector`), Redis, Chatwoot + Sidekiq, Bridge FastAPI.
- **Validación E2E:** widget en sitio fake (`chatwoot_fake_site`) → Chatwoot → webhook → bridge → respuesta automática vía API Chatwoot; usuario confirmó ver el mensaje de `BRIDGE_AUTO_REPLY` en widget e inbox.
- **Configuración relevante:** `compose/.env`, `compose/.env.chatwoot`, `compose/.env.bridge` (incluye `CHATWOOT_WEBHOOK_SECRET`); webhook en Chatwoot: `http://bridge.local:8000/webhooks/chatwoot`, evento `message_created` (alias `bridge.local` por validación de URL en UI).

### Aclaración de arquitectura acordada en chat (alineada con `miwayki_master_spec.md`)
- **Dify** como orquestador de IA (lógica + conexión al LLM en esa capa).
- Flujo canónico del spec: **Chatwoot emite webhook al Bridge** → Bridge llama a **Dify por API** → Bridge **publica en Chatwoot con la API de Chatwoot** (no el flujo principal “Dify → Chatwoot por webhook”).
- Próximo bloque de implementación lógico: **despliegue de Dify** y sustitución del texto fijo del bridge por llamada al orquestador + adaptador.

### Para retomar mañana (sugerencia)
1. Decidir **dónde** levantar Dify self-hosted (misma VM Lima vs. host separado) y revisar requisitos de recursos.
2. Seguir documentación oficial Dify (Docker Compose) y enlazar variables de entorno.
3. En bridge: stub o cliente HTTP hacia Dify; luego sustituir `BRIDGE_AUTO_REPLY` por respuesta del flujo Dify.
4. Mantener interfaz de **adaptador de orquestador** para no acoplar el código solo a Dify (criterio del spec).

## 2026-04-09 - Entrada #18 (retoma del trabajo: arranque del entorno)

### Contexto recordado (Entrada #17)
- Stack objetivo: VM **Lima** `miwayki-linux`, Docker Compose con Postgres (`pgvector`), Redis, Chatwoot + Sidekiq, Bridge FastAPI.
- Webhook Chatwoot → `http://bridge.local:8000/webhooks/chatwoot` (alias Docker).
- Próximo bloque de producto según `miwayki_master_spec.md`: **Dify** como orquestador; Bridge llama a Dify por API y publica en Chatwoot por API.

### Estado al iniciar el día
- VM `miwayki-linux` estaba **Stopped** (normal tras apagar el Mac o `limactl stop`).
- Tras `limactl start`, los contenedores volvieron; **Chatwoot** entró en bucle de reinicio por archivo obsoleto `server.pid` (mensaje Rails: *A server is already running (pid: 1, file: /app/tmp/pids/server.pid)*).

### Corrección aplicada
- `docker compose stop chatwoot` + `docker rm -f miwayki-chatwoot` + `docker compose ... up -d chatwoot` para **recrear** el contenedor y limpiar el PID huérfano.
- Verificación: Puma escuchando en `0.0.0.0:3000`; desde el host macOS `curl http://127.0.0.1:3000/` → HTTP 200.
- Bridge: `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`.

### Qué debe estar corriendo para trabajar hoy
| Pieza | Dónde | Cómo |
|-------|--------|------|
| VM Lima | Mac | `limactl start miwayki-linux` si está parada |
| Docker (Postgres, Redis, Chatwoot, Sidekiq, Bridge) | Dentro de la VM | `cd .../compose && sudo docker compose -f docker-compose.yml -f docker-compose.chatwoot.yml -f docker-compose.bridge.yml up -d` |
| Sitio fake del widget | **Host Mac** (recomendado) | `python3 -m http.server 8080 --directory /ruta/al/proyecto/chatwoot_fake_site` |
| Chatwoot UI / widget | Navegador | `http://127.0.0.1:3000` (Lima reenvía puertos al host) |

### Nota operativa
- Si Chatwoot vuelve a mostrar el error del `server.pid` tras un reinicio brusco, la recreación del contenedor `chatwoot` (sin tocar volúmenes de Postgres) suele bastar.

### Próximo paso de desarrollo (sin cambiar aún)
- Iniciar **deploy de Dify** (self-hosted) y cablear el bridge al API del orquestador, según roadmap del spec.

## 2026-04-09 - Entrada #19 (Dify desplegado en VM Lima + ajustes de recurso)

### Objetivo
- Poner en marcha **Dify** (Docker Compose oficial) en la **misma VM Lima**, conectado a la red `miwayki-core-net` para que el **bridge** pueda usar `http://api:5001`.

### Archivos añadidos en el repo
- `vendor/dify/` — clon upstream (rama release **1.13.3**).
- `compose/dify-docker-compose.miwayki.yml` — une el servicio `api` de Dify a la red externa `miwayki-core-net` (copiar al directorio de despliegue de Dify; `vendor/dify` no se versiona en Git).
- `compose/dify.env.overrides` — `EXPOSE_NGINX_PORT=9080`, `EXPOSE_NGINX_SSL_PORT=9443` (evita ocupar 80/443 en el host).
- `compose/README.md` — sección 8 actualizada con procedimiento.
- `.gitignore` — `vendor/dify/docker/.env` (secretos locales).
- `scripts/rsync-dify-docker-to-vm.sh` — sincroniza `vendor/dify/docker/` → `/var/opt/miwayki-dify/` en la VM.

### Problemas encontrados y solución
1. **Disco insuficiente (20 GiB):** al extraer la imagen `dify-api`, Docker devolvió *no space left on device*. Se amplió la VM con `limactl edit miwayki-linux --disk 48 --memory 6` (disco **48 GiB**, RAM **6 GiB**).
2. **Montaje RO del proyecto en Lima:** no se podían crear `vendor/dify/docker/volumes/*` en el bind mount. Se desplegó desde **`/var/opt/miwayki-dify/`** (copia/rsync al disco escribible de la VM).

### Estado al cierre
- `docker compose -p dify ... up -d` ejecutado desde `/var/opt/miwayki-dify/`.
- UI Dify accesible desde el Mac: `http://127.0.0.1:9080/install` (HTTP 307/redirect esperable en raíz).
- DNS: desde un contenedor en `miwayki-core-net`, `api` resuelve al API de Dify (verificado con `getent hosts api` desde `chatwoot`).

### Próximo paso técnico
- Completar asistente `/install` en Dify (cuenta admin).
- Configurar proveedor LLM (p. ej. Bedrock u otro) en la consola Dify.
- En el bridge: variable `DIFY_API_URL=http://api:5001` (o workflow con API key) y sustituir respuesta fija por llamada al orquestador.

### Nota de contexto (decisión de arquitectura, misma conversación)
- Se acordó desplegar **Dify en la misma VM Lima** para alinear con el plan futuro de **una EC2** con todo dockerizado.
- **Buena práctica:** Dify en su propio `docker compose`, datos y Postgres/Redis/Weaviate propios, sin mezclar código con el bridge; en AWS se repite el patrón contenedor por servicio en una máquina.

## 2026-04-09 - Entrada #20 (síntoma: `/install` colgado en spinner; diagnóstico)

### Qué reportó el usuario
- Navegador en `http://127.0.0.1:9080/install` con **pantalla blanca y spinner** (carga infinita).
- Uso de RAM en Mac ~**79%** (posible presión al hipervisor Lima).

### Comprobaciones hechas (VM / Docker)
- Logs **web**: mensaje *"Using localhost as base URL in server environment, please configure accordingly."* (indicativo de revisar URLs si hubiera CORS/API incorrecta; no era la única causa).
- `.env` en `/var/opt/miwayki-dify/`: `CONSOLE_API_URL`, `APP_API_URL`, etc. **vacíos** (valor por defecto mismo origen vía Nginx).
- **Nginx** servía estáticos `/_next/static/...` con **200**; el fallo era **tráfico hacia la API**.
- `curl` desde la VM a `http://127.0.0.1:9080/console/api/...` → **timeout** (sin bytes).
- `curl` desde contenedor **nginx** a `http://api:5001/...` → **timeout**.
- `curl` / `urllib` **dentro de `dify-api-1`** a `http://127.0.0.1:5001/console/api/setup` → **timeout** (conexión que no completaba respuesta HTTP a tiempo).
- Conectividad **TCP** desde `api` a `db_postgres`, `redis`, `weaviate` → **OK** (no era red a datos).
- `/proc/net/tcp` en `api`: puerto **5001** en estado de escucha; proceso parecía vivo pero **no respondía** HTTP en la práctica.

### Acción que desbloqueó
- `sudo docker restart dify-api-1` y espera ~15 s.
- Tras reinicio: `curl` a `http://127.0.0.1:5001/` devolvió **HTTP 404** con cabeceras **gunicorn** (respuesta válida; 404 esperable en raíz).

### Hipótesis de causa (para futuro si reaparece)
- **Primera subida:** migraciones Alembic largas + arranque de workers/gevent; posible ventana donde el worker no atiende aún.
- **Recursos:** muchos contenedores Dify + Chatwoot + bridge en **6 GiB** RAM VM; competencia y latencia.
- **Estado intermedio** del proceso Gunicorn (atasco transitorio); el reinicio del contenedor `api` suele ser el atajo más rápido.

### Comando de referencia
```bash
sudo docker restart dify-api-1
# Ver logs: sudo docker logs -f dify-api-1
```

## 2026-04-09 - Entrada #21 (Dify ya muestra pantalla de admin; demora explicada)

### Resultado observado por el usuario
- Pantalla **"Setting up an admin account"** en `http://127.0.0.1:9080/install` (formulario email / username / password / botón Set up).
- Queja: **demoró mucho** hasta llegar ahí.

### Explicación acordada (por qué tarda la primera vez)
1. **Descarga y extracción de imágenes** (especialmente `dify-api`, muy pesada).
2. **Migraciones de base de datos** en el primer arranque (cadena larga de upgrades hasta *Database migration successful!*).
3. **Muchos servicios en paralelo** (api, worker, worker_beat, web, nginx, weaviate, postgres, redis, sandbox, plugin_daemon, ssrf_proxy).
4. **Arranque en frío** de la VM y presión de **RAM** (host + invitado).
5. Los **siguientes arranques** deberían ser notablemente más rápidos (capas en disco, migraciones ya aplicadas).

### Si vuelve a colgarse la UI
- Esperar **varios minutos** en primer boot; si no avanza, reiniciar `dify-api-1` y recargar el navegador (ver Entrada #20).

## 2026-04-09 - Entrada #22 (bitácora: incorporar conversación faltante)

### Petición del usuario
- Mantener **`historial_chat.md`** como registro **cronológico y detallado** de decisiones, síntomas, comandos y conclusiones, para **localizar problemas** si algo falla después.

### Acción realizada
- Incorporadas en este archivo las entradas **#20–#22**, cubriendo:
  - decisión previa Dify en misma VM / dockerización / EC2 futura;
  - incidente **spinner `/install`** y diagnóstico técnico;
  - confirmación de **pantalla de setup admin** y motivos de **lentitud inicial**;
  - esta meta-entrada de continuidad del historial.

### Próximo registro sugerido (cuando ocurra)
- Completar cuenta admin en Dify y anotar si se configuró proveedor LLM (Bedrock u otro).
- Primer cambio de código en **bridge** hacia API Dify (variables env, endpoint, prueba).

## 2026-04-09 - Entrada #23 (Gemini en Dify + Chatflow “Prueba Gemini” operativo en Preview)

### Lo que el usuario ya completó (resumen)
1. **Google AI Studio:** API key para **Gemini API** (proyecto default / flujo descrito en chat; key no documentada en este archivo por seguridad).
2. **Dify:** plugin **Gemini** instalado; **Model Provider** configurado con la API key (indicador verde en credencial).
3. **Default Model Settings** (según guía en conversación): modelo de razonamiento por defecto del workspace donde aplica.
4. **App en Studio:** **Chatflow** llamada **“Prueba Gemini”** (no Chatbot simple): nodo **LLM** (Gemini) → nodo **ANSWER**; prueba en **Preview** con respuesta correcta en español (ej. “¿qué es Dify?”).

### Nota técnica
- Para **pruebas**, Gemini vía **AI Studio + API key** es más ágil que Vertex con service account; Bedrock/Nova queda como objetivo de arquitectura productiva según spec, sin bloquear el desarrollo local.

### Qué falta para el plan Miwayki (orden sugerido)
1. **Publicar** la app **Prueba Gemini** (botón **Publish** en el editor del Chatflow) para que la **API de servicio** quede activa con la versión actual.
2. **API de la app:** dentro de la app, abrir **API Access** / **Access API** / **Develop** (según UI); **generar API Key** de la aplicación (formato típico `app-...`). Guardarla solo en servidor (`.env` del bridge), nunca en el widget ni en git.
3. **Base URL para el bridge:** desde el contenedor `bridge`, usar **`http://api:5001/v1`** (servicio `api` del compose Dify en `miwayki-core-net`). El navegador puede usar `http://127.0.0.1:9080/v1`; el bridge debe usar la URL **interna**.
4. **Integración bridge (siguiente implementación):** `POST /v1/chat-messages` con cabecera `Authorization: Bearer <APP_API_KEY>`, cuerpo con `query` (texto del visitante), `user` estable (ej. `chatwoot-{conversation_id}`), `conversation_id` devuelto por Dify en la primera respuesta para mantener hilo, `response_mode: blocking`, `inputs` según variables del Chatflow (vacío `{}` si no hay variables).
5. **Prueba E2E:** mensaje en widget fake → Chatwoot → webhook → bridge → Dify → texto de respuesta → API Chatwoot al hilo (sustituye o complementa `BRIDGE_AUTO_REPLY`).

### Riesgos / buenas prácticas
- Rotar o revocar la API key de Gemini si se expuso en capturas o chat.
- No commitear `.env` del bridge con `DIFY_*` ni la app key de Dify.

## 2026-04-09 - Entrada #24 (integración bridge → Dify + aviso de seguridad de API key)

### Contexto
- Usuario generó **API Secret** de la app **Prueba Gemini** en Dify (pantalla API Access) y compartió en chat el valor y la URL mostrada por la UI (`http://127.0.0.1/v1`).

### Seguridad (obligatorio)
- La **app API key** quedó expuesta en conversación y capturas → debe **revocarse en Dify** (crear nueva secret key) y **no reutilizar** la filtrada.
- **No** se copió ninguna clave secreta al repositorio; en `compose/.env.bridge` quedó `DIFY_API_KEY=` vacío para que el usuario pegue **solo localmente** una clave nueva.

### Corrección de URL (importante)
- La UI de Dify muestra `http://127.0.0.1/v1` para llamadas **desde el navegador del host**.
- Desde el contenedor **bridge**, `127.0.0.1` no es Dify → usar **`http://api:5001/v1`** (servicio `api` del compose Dify en `miwayki-core-net`).

### Cambios en código
- `bridge/app/main.py`:
  - Variables `DIFY_API_BASE` (default `http://api:5001/v1`) y `DIFY_API_KEY`.
  - Si `DIFY_API_KEY` está definida: `POST .../chat-messages` con `response_mode: blocking`, `user: chatwoot-{conversation_id}`, `conversation_id` reutilizado por mapa en memoria por hilo Chatwoot.
  - Texto del visitante desde webhook (`content` o `message.content`).
  - Si no hay key Dify: se mantiene comportamiento anterior con `BRIDGE_AUTO_REPLY`.
  - Respuesta JSON del webhook incluye `source`: `dify` o `static_auto_reply`.
- `compose/.env.bridge.example` y `compose/README.md`: documentación de `DIFY_*`.

### Qué debe hacer el usuario
1. Revocar/rotar la app key expuesta; pegar la **nueva** en `compose/.env.bridge` como `DIFY_API_KEY=app-...`.
2. `DIFY_API_BASE=http://api:5001/v1` (ya indicado en `.env.bridge`).
3. Rebuild/restart bridge en la VM: `sudo docker compose ... up -d --build bridge`.
4. Probar mensaje desde el widget → respuesta debe venir de **Gemini/Dify**.

## 2026-04-08 - Entrada #25 (bitácora: conversación bridge/Dify, Docker por terminal/VM, diagnóstico puerto 8000)

### Propósito de esta entrada
- Dejar en **un solo lugar** el hilo de esta conversación (aclaraciones, errores de terminal, cambios de repo y conclusiones) para que **lecturas futuras** (humano o asistente) no asuman un entorno distinto al real.
- Aclarar explícitamente **cómo se usa Docker en este proyecto** según lo indicado por el usuario: **línea de comandos** y **VM (p. ej. Lima)**, no depender de la narrativa “solo Docker Desktop en Mac”.

### Contexto operativo de Docker (importante para futuras respuestas)
- El stack Miwayki + Chatwoot + bridge (+ Dify en la misma VM según entradas anteriores) se opera con **`docker` / `docker compose` desde el terminal**, típicamente **dentro de la VM** donde el daemon sí está activo.
- **No** confundir: decir “abre Docker Desktop” puede ser **irrelevante o engañoso** si el trabajo real es en **Lima/VM** o si en la Mac **no** se usa el daemon de Docker Desktop sino otro contexto.
- Si el **daemon no responde** en la máquina donde se ejecuta el comando (`Cannot connect to the Docker daemon`, socket `unix://.../docker.sock`), **no habrá** `build` ni `up` válidos hasta que ese daemon esté accesible (VM encendida, servicio Docker arriba, o usar la máquina correcta).
- Si algo queda **desconectado o inconsistente**, la vía habitual es **volver a levantar** la VM/servicio Docker y los contenedores (`docker compose up`, reinicios de contenedor concretos como en Entrada #20 para `dify-api-1`), según el síntoma.

### Puertos y rutas de red recordados (referencia rápida)
| Qué | Dónde / notas |
|-----|----------------|
| UI Dify (navegador en host/VM) | `http://127.0.0.1:9080` (nginx frontal; entradas previas). |
| API Dify en documentación UI | Suele mostrarse `http://127.0.0.1/v1` para **curl desde el host** (no es la URL del contenedor `bridge`). |
| API Dify desde contenedor **bridge** | `http://api:5001/v1` (hostname Docker `api`, red `miwayki-core-net`). El **5001** es **puerto interno del contenedor** Dify API, no “el puerto de Chatwoot”. |
| Chatwoot (desde bridge) | `http://chatwoot:3000` (interno). |
| Bridge expuesto en host | `127.0.0.1:8000` (mapeo en `docker-compose.bridge.yml`). |
| Postgres / Redis | Publicados en localhost con variables en `compose/.env` (p. ej. 5432, 6379) según configuración local. |

### Aclaración 127.0.0.1 vs `api:5001` (pregunta del usuario)
- **`127.0.0.1`** = “esta máquina”, pero **desde el navegador en el host** es el host; **desde dentro del contenedor bridge** es el **propio contenedor**, no Dify.
- Por eso la UI de Dify muestra `http://127.0.0.1/v1` (válido para pruebas **desde el host**) y el bridge debe usar **`http://api:5001/v1`** hacia el servicio `api` en la red Docker.

### Lo conversado y hecho en esta sesión (cronológico resumido)
1. **Claves Dify:** usuario rotó la app API key y la pegó en `compose/.env.bridge`; recordatorio de no filtrar claves en chat.
2. **Reinicio/pruebas:** se intentó reiniciar el bridge desde el entorno del asistente; a veces **Docker no estaba accesible** en ese entorno → no sustituye ejecutar los comandos donde el usuario tiene el daemon.
3. **Ruta de `docker compose`:** error `open .../Final_Project/docker-compose.yml: no such file` al ejecutar desde la **raíz del repo** sin prefijo `compose/`. Los YAML viven en **`compose/`**.
4. **Wrapper `miwayki-compose.sh`:** script en la raíz del repo que hace `cd compose` y aplica los tres `-f` (`docker-compose.yml`, `docker-compose.chatwoot.yml`, `docker-compose.bridge.yml`).
5. **Intento de `docker-compose.yml` en raíz con `include`:** Docker Compose reportó **`networks.core_net conflicts with imported resource`** al incluir los tres fragmentos vía `include`; la fusión equivalente a **`-f` múltiple desde el mismo directorio** sí funciona. Se **no** dejó un compose raíz roto; la solución operativa es **`./miwayki-compose.sh`** o `cd compose && docker compose -f ...`.
6. **Síntoma `GET /health/dify` → 404:** el proceso que respondía en `:8000` era **código antiguo** (imagen no reconstruida) u **otro proceso** en el puerto; no es un bucle de “mismo parche” sin deploy.
7. **Mac + daemon:** en terminal del usuario apareció `Cannot connect to the Docker daemon at unix:///Users/.../docker.sock` → **sin build**; aun así **`curl :8000/health`** podía responder → indica **desalineación** (otro listener o contenedor no gestionado por ese CLI).
8. **Mejoras de diagnóstico en repo:**
   - `GET /health` incluye `bridge_build` (p. ej. `"0.2-dify-probe"`) y lista de `endpoints`; si solo aparece `{"status":"ok"}`, **no** es la imagen nueva.
   - `miwayki-compose.sh` hace **preflight** `docker info`; si falla, mensaje en **español** con pistas (`lsof` en 8000, ejecutar compose en VM, comprobar `bridge_build`).
   - Se mantiene `GET /health/dify` para ping al `/health` del API Dify (sin app key).
9. **`curl` en una sola línea:** dos comandos pegados sin `;` o salto de línea pueden ejecutarse mal; usar **líneas separadas** o `;`.
10. **Documentación:** `compose/README.md` actualizado (wrapper, `COMPOSE_FILE` + `--project-directory`, criterio `bridge_build`).

### Comandos de referencia (copiar según ubicación)
```bash
# Desde la raíz del repo (Final_Project/)
./miwayki-compose.sh up -d --build bridge

# Equivalente
cd compose && docker compose -f docker-compose.yml -f docker-compose.chatwoot.yml -f docker-compose.bridge.yml up -d --build bridge

# Desde la raíz sin script (Compose v2)
COMPOSE_FILE=compose/docker-compose.yml:compose/docker-compose.chatwoot.yml:compose/docker-compose.bridge.yml \
  docker compose --project-directory compose up -d --build bridge

# ¿Quién escucha 8000 en la Mac?
lsof -nP -iTCP:8000 -sTCP:LISTEN

# Comprobar versión expuesta del bridge
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/health/dify
```

### Próximos pasos del plan (sin duplicar spec completo)
- Con Docker operativo **en la máquina que ejecuta los contenedores**: rebuild bridge, verificar `bridge_build` y `/health/dify`, luego **E2E** widget → Chatwoot → webhook → Dify.
- Continuar alineación con **`miwayki_master_spec.md`** (atributos, scoring, prod Bedrock/Nova cuando toque).

### Nota para el asistente en lecturas futuras de este archivo
- Antes de insistir en **Docker Desktop**, revisar si el flujo real es **VM + terminal**; priorizar **diagnóstico de daemon/socket** y **máquina correcta** donde corre `docker compose`.
- Tras cambios en `bridge/app`, sin **`--build`** el contenedor puede seguir sirviendo **código viejo**; validar con **`bridge_build`** en `/health`.

## 2026-04-08 - Entrada #26 (plan: custom attributes Chatwoot + scoring heurístico MVP)

### Dónde iba el plan
- Tras integrar **Dify** en el webhook (respuesta al hilo), el spec (`miwayki_master_spec.md` §12.4 y §13) pide **sincronizar la conversación en Chatwoot** (`custom_attributes`, más adelante etiquetas y salida estructurada del orquestador).

### Implementación realizada
- **`bridge/app/main.py`** (`bridge_build` **0.3-chatwoot-attrs**):
  - Tras **POST** del mensaje saliente a Chatwoot, si `BRIDGE_SYNC_CHATWOOT_ATTRIBUTES` está activo (por defecto sí): **GET** conversación, **fusión** de `custom_attributes` existentes con campos nuevos, **PATCH** `{"custom_attributes": merged}`.
  - Atributos escritos (MVP): `lead_score`, `lead_temperature`, `handoff_recommended`, `last_ai_summary` (recorte del texto de la IA), `ai_source` (`dify` / `static_auto_reply`), `miwayki_bridge_build`.
  - **Heurística** de scoring/temperatura sobre el **mensaje del usuario** (palabras clave y longitud), alineada a umbrales §13.3 hasta que Dify exponga contrato §12.3 (JSON estructurado). Si la fuente es `static_auto_reply`, se fuerza score bajo / frío.
  - Si el PATCH de atributos falla, el **webhook no devuelve 502** por eso: la respuesta incluye `chatwoot_custom_attributes` con `ok: false` y detalle HTTP.
- **`compose/.env.bridge.example`**: variable `BRIDGE_SYNC_CHATWOOT_ATTRIBUTES`.
- **`compose/README.md`**: nota sobre `bridge_build` y la sync de atributos.

### Pendiente lógico (siguiente iteración del plan)
- Sustituir o enriquecer la heurística por **salida estructurada del Chatflow Dify** (`extracted_fields`, `lead_score` del modelo).
- Opcional §13.4: **etiquetas** Chatwoot o estado sugerido cuando `lead_score >= 70`.
- **E2E** en VM: rebuild bridge, mensaje widget → comprobar atributos visibles en la conversación Chatwoot.

## 2026-04-08 - Entrada #27 (decisión: minimalismo primero; atributos Chatwoot después)

### Criterio acordado con el usuario
- **Buena práctica:** cerrar primero la **rebanada vertical mínima**: enviar y recibir mensajes **Chatwoot ↔ bridge ↔ Dify** sin depender de extras.
- **Después**, cuando el puente básico esté validado, activar y afinar **custom attributes**, scoring avanzado y el resto del spec.

### Cambio en el código
- `BRIDGE_SYNC_CHATWOOT_ATTRIBUTES` pasa a **false por defecto** (solo se ejecuta GET/PATCH de atributos si en `.env.bridge` se pone `1`).
- La lógica de atributos y heurística **permanece** en el repo para no reescribir luego; el camino por defecto solo hace POST del mensaje de respuesta.
- `bridge_build` **0.4-minimal-default** para distinguir esta política en `/health`.

## 2026-04-08 - Entrada #28 (mapa de puertos + BRIDGE_HOST_PORT configurable)

### Problema señalado por el usuario
- Riesgo de **choque** al asumir siempre **8000** en el host para nuevos servicios; otros proyectos o instancias pueden usar el mismo puerto; hay que saber **qué está activo** y poder **cambiar** el mapeo sin reescribir a ciegas.

### Inventario documentado (compose/README.md)
- Tabla de puertos por defecto: Postgres, Redis, Chatwoot, bridge, fake site 8080, Dify 9080/9443; aclaración de **interno Docker** (`api:5001`, `bridge.local:8000`) vs host.
- Nota de que **CHROMA_PORT=8000** en vendor Dify es interno al stack Dify, no el bridge del Mac.

### Cambio técnico
- `compose/docker-compose.bridge.yml`: mapeo `127.0.0.1:${BRIDGE_HOST_PORT:-8000}:8000`.
- `compose/.env.example`: variable `BRIDGE_HOST_PORT=8000` con comentario.
- El **puerto interno del contenedor bridge sigue siendo 8000**; Chatwoot/webhook en red Docker **no cambia** al mover solo el puerto del host.

## 2026-04-09 - Entrada #29 (rebuild bridge en Lima + verificación Dify)

### Acción
- VM **miwayki-linux** ya estaba **Running**; `docker compose` en la Mac no era el contexto correcto para el stack.
- Desde el host: `limactl shell miwayki-linux -- bash -lc 'cd /Users/armandosilva/DATA/SMC/CS_79C_cloud/Final_Project && ./miwayki-compose.sh up -d --build bridge'`.

### Resultados
- Imagen **compose-bridge** reconstruida; contenedor **miwayki-bridge** recreado y **Started**.
- `curl http://127.0.0.1:8000/health` en la VM: `bridge_build` **0.4-minimal-default**.
- `GET /health/dify`: **reachable**, Dify API `http://api:5001/health` → 200, versión **1.13.3**.
- Smoke test **POST /chat-messages** (blocking) desde **dentro** de `miwayki-bridge` con variables de entorno del contenedor → **HTTP 200**, respuesta coherente (prueba corta con Gemini/Dify).

### Pendiente manual (E2E producto)
- Enviar mensaje desde **widget** / Chatwoot y confirmar respuesta en el hilo (webhook ya configurado en entradas previas).

### Regla operativa (bridge + Lima) — recordatorio fijo
- **Siempre que cambies código del bridge:** entrar a **Lima** (`limactl shell miwayki-linux`) y ejecutar **`./miwayki-compose.sh up -d --build bridge`** **desde el repo dentro de la VM** (misma ruta montada, p. ej. `Final_Project`).
- **No** basta con ejecutar solo en la **Mac** si el `docker` de esa terminal no es el daemon que gestiona **miwayki-postgres**, **miwayki-bridge**, etc. (en el setup actual el stack corre en la VM; en la Mac suele verse el forward vía **limactl** en los puertos).

## 2026-04-09 - Entrada #30 (sitio fake + URL para probar widget Chatwoot)

### URL del sitio fake (host)
- Tras levantar el servidor estático: **http://127.0.0.1:8080**
- Comando desde la **raíz del repo** (Mac o VM, según donde pruebes el navegador):

```bash
python3 -m http.server 8080 --directory chatwoot_fake_site
```

### Requisitos
- Chatwoot accesible donde el `baseUrl` del widget apunte (en entradas previas del historial: **http://127.0.0.1:3000** vía forward Lima).
- Inbox web con **websiteToken** válido en `chatwoot_fake_site/index.html`.

## 2026-04-09 - Entrada #31 (Git local + criterio para GitHub)

### Git local
- `git init` en la raíz del repo; rama **`main`**; commit inicial con código propio (bridge, compose, fake site, docs, scripts).
- **`vendor/dify/`** en **`.gitignore`**: no subir ~145MB del clon oficial; instrucciones en **`vendor/README.md`** (`git clone --depth 1`).

### Overlay Dify → Miwayki
- Archivo de red **`compose/dify-docker-compose.miwayki.yml`** (versionado). Eliminado del árbol el duplicado bajo `vendor/dify/docker/`; despliegue en VM: copiar con `rsync`/script o `docker compose -f … -f dify-docker-compose.miwayki.yml`.
- **`scripts/rsync-dify-docker-to-vm.sh`** actualizado para copiar también ese YAML a `/var/opt/miwayki-dify/`.

### Recomendación GitHub (peso)
- **Sí conviene** publicar: el repo queda **ligero** (sin `vendor/dify`, sin `.env` con secretos).
- Límite útil de GitHub: archivos **>100MB** rechazados; repos grandes son incómodos pero **~3k líneas** de código no son problema.
- Tras `git remote add` / `push`, quien clone debe ejecutar el clone de Dify en `vendor/dify` según `vendor/README.md`.

### Pendiente (usuario)
- Crear repo vacío en GitHub y: `git remote add origin …`, `git push -u origin main`.


## 2026-04-09 - Entrada #32 (cierre de sesión: puente validado y continuidad mañana)

### Estado al cierre
- Flujo mínimo validado: widget/sitio fake -> Chatwoot -> webhook -> bridge -> Dify -> respuesta en el hilo.
- Bridge reconstruido en Lima y verificado con `bridge_build` actual en `/health` y conectividad Dify en `/health/dify`.
- Prueba de `POST /chat-messages` desde el contenedor bridge con respuesta HTTP 200.

### Decisiones vigentes
- Mantener enfoque minimalista: primero puente estable; atributos/scoring avanzados quedan para la siguiente fase.
- `BRIDGE_SYNC_CHATWOOT_ATTRIBUTES` permanece desactivado por defecto para no agregar complejidad temprana.
- Operación del stack: cambios del bridge siempre con rebuild en VM Lima (daemon real del proyecto).

### Próximo paso (mañana)
- Continuar con contrato de salida estructurada en Dify y consumo en bridge; después activar atributos de Chatwoot de forma incremental.

## 2026-04-11 - Entrada #33 (Gemini CLI integrado + Contrato JSON Dify validado)

### Objetivo de la sesión
- Integrar **Gemini CLI** como agente de arquitectura (`miwayki-architect`) para gestionar el ciclo de vida del proyecto.
- Implementar el contrato estructurado **JSON** entre el Bridge y Dify según el Master Spec.
- Estabilizar el stack local y validar el flujo comercial de MiWayki.

### Cambios realizados
- **Configuración de agente**:
  - Se creó `GEMINI.md`.
  - Se configuró el agente local `miwayki-architect` con el contexto maestro del proyecto.
- **Actualización del Bridge**:
  - `bridge/app/main.py` actualizado a la versión `0.5-dify-json`.
  - Se implementó parseo JSON en `_dify_blocking_reply`.
  - Se añadió fallback robusto: si Dify responde texto plano, el Bridge lo encapsula automáticamente como `reply_text`.
  - Se adaptó `chatwoot_webhook` para consumir resultado estructurado y mantener fallback heurístico para `lead_score`, `lead_temperature` y `handoff_recommended`.
- **Infraestructura y stack**:
  - Rebuild exitoso del contenedor `bridge` en la VM Lima.
  - Se detectó inestabilidad en `miwayki-chatwoot` (restart loop con `exit=1`); se recreó el contenedor y quedó operativo.
  - `chatwoot_fake_site` servido localmente con `python3 -m http.server 8080`.

### Resultados técnicos y validación
- **Healthcheck del Bridge**:
  - `GET /health` -> `bridge_build: "0.5-dify-json"`.
  - `GET /health/dify` -> `reachable: true`.
- **Confirmación de app activa en Dify**:
  - El Bridge estaba llamando a la app `Prueba Gemini` mediante `DIFY_API_KEY`.
- **Cambio de comportamiento en Dify**:
  - Se actualizó el **System Prompt** del nodo LLM en `Prueba Gemini`, pasando de asistente genérico a **asistente comercial de MiWayki**.
  - La app fue publicada desde la UI de Dify.
- **Prueba E2E**:
  - Se validó el flujo completo desde el widget servido en `127.0.0.1:8080`.
  - El bot respondió con estilo comercial de MiWayki ante la consulta:
    - “Hola, quiero información de Lunahuaná para 2 personas este sábado”
  - Respuesta observada en widget:
    - “¡Hola! Qué buena elección para este sábado. Para preparar tu cotización para 2 personas, ¿buscan un tour que incluya transporte desde Lima o prefieren solo las actividades de aventura allá?”

### Estado actual
- El Bridge ya puede procesar tanto texto plano como JSON estructurado desde Dify.
- El stack local quedó operativo: Postgres, Redis, Chatwoot, Bridge y Dify.
- La integración técnica **Chatwoot -> Bridge -> Dify -> Chatwoot** quedó validada.
- Próximo paso recomendado:
  - Configurar salida JSON estructurada en Dify.
  - Activar `BRIDGE_SYNC_CHATWOOT_ATTRIBUTES=1`.
  - Validar scoring y atributos en Chatwoot.


## 2026-04-11 - Entrada #34 (Depuración de persistencia en Chatwoot + Diagnóstico de Webhooks)

### Objetivo de la sesión
- Instrumentar el Bridge con logs detallados para trazar el flujo de sincronización de atributos.
- Validar el contrato estructurado JSON devuelto por Dify en condiciones reales.
- Identificar la causa raíz de la falta de persistencia de `custom_attributes` en Chatwoot.

### Cambios realizados
- **Configuración del Entorno**:
  - Setup del proyecto Gemini CLI completado.
  - Creación de `GEMINI.md` y carga del agente local `miwayki-architect`.
- **Actualización del Bridge**:
  - `bridge/app/main.py` actualizado para soportar el parseo de JSON de Dify con fallback seguro a texto plano.
  - Se añadió log temporal prefijado con `[ATTR_SYNC]` para el seguimiento detallado de la sincronización de atributos.
  - Se implementó `flush=True` en los `print` para visibilidad inmediata en logs de Docker.
- **Infraestructura**:
  - Rebuild exitoso del Bridge en la VM Lima.
  - Estabilización de `miwayki-chatwoot`: contenedor recreado tras detectar inestabilidad.
  - `chatwoot_fake_site` servido localmente en `127.0.0.1:8080`.

### Resultados técnicos y validación
- **Healthcheck**:
  - `GET /health` confirmó `bridge_build: "0.5-dify-json-debug"`.
  - `GET /health/dify` confirmó conectividad con el contenedor `api` de Dify.
- **Validación E2E del Widget**:
  - Prueba exitosa con respuesta comercial estilo MiWayki.
  - Los logs del Bridge confirmaron la recepción de la salida estructurada de Dify: `reply_text`, `lead_score`, `lead_temperature`, `handoff_recommended`, `reasoning_summary`, `extracted_fields`, `next_best_action`.
- **Diagnóstico de Persistencia (Hallazgo Crítico)**:
  - Se verificó que el flujo de sincronización en el Bridge se ejecuta y envía los atributos mezclados.
  - **Prueba Manual A**: `PATCH` a `/conversations/3` devuelve HTTP 200 pero **no persiste** los atributos (Strong Params en Chatwoot los filtra).
  - **Prueba Manual B**: `POST` a `/conversations/3/custom_attributes` **sí persiste** los atributos correctamente.
  - **Confirmación**: Un `GET` posterior a la conversación devolvió los valores persistidos bajo `custom_attributes`.
  - **Conclusión**: El problema de persistencia reside en el endpoint de escritura seleccionado en Chatwoot, no en Dify ni en la lógica de mezcla del Bridge.

### Estado actual
- Se validó manualmente que el endpoint correcto para atributos de conversación es el dedicado (`POST .../custom_attributes`).
- El Bridge ya procesa la salida estructurada de Dify correctamente.
- **Próximo paso**: Actualizar la llamada de escritura en el Bridge (`_chatwoot_merge_custom_attributes`) para usar el endpoint validado y revalidar la persistencia E2E.

## 2026-04-11 - Entrada #35 (Persistencia en Chatwoot validada E2E + Fix de Endpoint)

### Objetivo de la sesión
- Corregir el fallo de persistencia de `custom_attributes` en Chatwoot mediante el uso del endpoint dedicado.
- Validar el flujo completo: Widget -> Chatwoot -> Bridge -> Dify -> Bridge -> Chatwoot Persistence.

### Cambios realizados
- **Actualización del Bridge**:
    - `bridge/app/main.py` actualizado a la versión `0.6-chatwoot-persistence-fix`.
    - Se cambió el método de escritura de atributos de `PATCH` en el endpoint de conversación a `POST` en el endpoint específico: `/api/v1/accounts/{id}/conversations/{id}/custom_attributes`.
    - Se mantuvo la lógica de "GET-then-merge" para preservar atributos previos no gestionados por el Bridge.
    - Se mantuvieron los logs de depuración `[ATTR_SYNC]` con `flush=True`.
- **Infraestructura**:
    - Rebuild y despliegue exitoso del Bridge en la VM Lima.

### Resultados técnicos y validación
- **Healthcheck**: 
    - `GET /health` confirmó `bridge_build: "0.6-chatwoot-persistence-fix"`.
- **Prueba E2E (Widget)**:
    - Se envió un mensaje inicial: "Hola".
    - Respuesta de la IA: "¡Hola! Bienvenido a MiWayki. Estoy aquí para ayudarte a planear tu próximo viaje. ¿Qué destino tienes en mente para tu aventura?".
- **Logs del Bridge (`[ATTR_SYNC]`)**:
    - `BRIDGE_SYNC_CHATWOOT_ATTRIBUTES=True` detectado.
    - `GET conversation result: True`.
    - `exact POST URL: http://chatwoot:3000/api/v1/accounts/1/conversations/3/custom_attributes`.
    - `POST HTTP status code: 200`.
    - El cuerpo de la respuesta confirmó la persistencia de los campos enviados.
- **Validación de Persistencia (GET)**:
    - Un `GET` a la conversación confirmó que los atributos ahora residen en la base de datos de Chatwoot:
        - `ai_source: "dify"`
        - `debug_attr: "final_fix_verification"` (persistido de prueba previa)
        - `lead_score: 10`
        - `lead_temperature: "cold"`
        - `handoff_recommended: false`
        - `last_ai_summary: "El usuario inició la conversación con un saludo, no hay datos aún."`
        - `miwayki_bridge_build: "0.6-chatwoot-persistence-fix"`

### Estado actual
- **Fix validado E2E**: El Bridge ahora persiste correctamente los `custom_attributes` de la conversación en Chatwoot.
- El flujo **Dify (Salida estructurada) -> Bridge (Parsing) -> Chatwoot (Persistencia)** está totalmente validado en el entorno local.
- El sistema es resiliente a respuestas de texto plano y gestiona correctamente la memoria de la conversación en Dify.
- Próximo paso: Limpieza de logs de depuración, actualización de documentación y continuación con los ítems restantes de la fase básica local.

## 2026-04-11 - Entrada #36 (Flujo local validado E2E sin logs temporales)

### Objetivo de la sesión
- Revalidar el flujo local después de la limpieza de logs temporales del Bridge.
- Confirmar que la persistencia de `custom_attributes` en Chatwoot sigue intacta tras el cleanup.
- Verificar que el stack local continúa operativo sin instrumentación de depuración `[ATTR_SYNC]`.

### Cambios realizados
- **Limpieza del Bridge**:
    - `bridge/app/main.py` fue depurado para eliminar los `print` temporales prefijados con `[ATTR_SYNC]`.
    - Se retiraron las salidas de depuración sin alterar la lógica de negocio validada previamente.
    - Se conservó la lógica de parseo JSON de Dify con fallback seguro a texto plano.
    - Se conservó la escritura por `POST` al endpoint correcto de Chatwoot:
      `/api/v1/accounts/{account_id}/conversations/{conversation_id}/custom_attributes`.
    - Se conservó la lógica `GET-then-merge` para no sobrescribir atributos ya existentes en la conversación.
- **Infraestructura**:
    - Rebuild exitoso del contenedor `bridge` en la VM Lima.

### Resultados técnicos y validación
- **Healthcheck**:
    - `GET /health` confirmó `bridge_build: "0.6-chatwoot-persistence-fix"`.
- **Validación de autenticación Chatwoot API**:
    - Se verificó correctamente el `CHATWOOT_API_TOKEN` real mediante `GET /api/v1/profile`.
- **Prueba E2E (Widget)**:
    - Se validó respuesta comercial del asistente para el mensaje:
      `"Necesito cotizar un viaje a Cusco para mayo"`.
- **Validación de Persistencia (GET)**:
    - `GET /api/v1/accounts/1/conversations/3` confirmó persistencia de `custom_attributes` en la conversación.
    - El estado observado incluyó:
        - `ai_source: "dify"`
        - `debug_attr: "final_fix_verification"`
        - `lead_score: 45`
        - `lead_temperature: "warm"`
        - `handoff_recommended: false`
        - `last_ai_summary: "El usuario indicó el destino (Cusco) y el mes (mayo), pero faltan la cantidad de personas y las fechas exactas."`
        - `miwayki_bridge_build: "0.6-chatwoot-persistence-fix"`
- **Validación post-cleanup**:
    - Se verificó que ya no aparecen logs `[ATTR_SYNC]` en `docker logs miwayki-bridge`.
- **Observación operativa**:
    - El error `OSError: [Errno 48] Address already in use` al intentar levantar `python3 -m http.server 8080` no correspondió a caída del sitio, sino a que el puerto `8080` ya estaba ocupado por una instancia activa del servidor local.

### Estado actual
- El flujo local **Widget -> Chatwoot -> Bridge -> Dify -> Bridge -> Chatwoot** está validado E2E.
- La persistencia de `custom_attributes` en Chatwoot sigue funcionando correctamente después del cleanup.
- El Bridge quedó en estado limpio, sin logs temporales de depuración.
- Próximo paso: actualizar documentación/runbooks del flujo validado y luego continuar con el siguiente ítem pendiente de la fase básica local.


## 2026-04-11 - Entrada #36 (Auto-label "hot" validado E2E + verificación de fake site)

### Objetivo de la sesión
- Validar la asignación automática de etiqueta en Chatwoot para leads con `lead_score >= 70`.
- Confirmar que el flujo local completo sigue operativo tras el cambio a `v0.7-auto-label-hot`.
- Verificar el estado real de `chatwoot_fake_site` en `127.0.0.1:8080`.

### Cambios realizados
- **Actualización del Bridge**:
  - `bridge/app/main.py` quedó corriendo con `bridge_build: "0.7-auto-label-hot"`.
  - Se habilitó la asignación automática de la etiqueta `hot` cuando el `lead_score` final alcanza o supera 70.
- **Validación del entorno local**:
  - Rebuild exitoso del contenedor `bridge`.
  - Healthcheck exitoso posterior al rebuild.
  - `chatwoot_fake_site` levantado en `127.0.0.1:8080` con `python3 -m http.server`.

### Resultados técnicos y validación
- **Healthcheck**:
  - `GET http://127.0.0.1:8000/health` devolvió:
    - `bridge_build: "0.7-auto-label-hot"`
- **Prueba E2E del Widget**:
  - Mensaje enviado:
    - `"Quiero reservar ahora, mi whatsapp es 999999999 y necesito precio para Cusco"`
  - Respuesta del asistente:
    - `"¡Excelente elección, Cusco es increíble! Para darte la mejor cotización y asegurar tu cupo, por favor confírmame: ¿para qué fecha planeas viajar y cuántas personas son? Con esto te contacto de inmediato."`
- **Validación de persistencia en Chatwoot**:
  - `GET /api/v1/accounts/1/conversations/3` devolvió:
    - `custom_attributes.ai_source: "dify"`
    - `custom_attributes.lead_score: 90`
    - `custom_attributes.lead_temperature: "hot"`
    - `custom_attributes.handoff_recommended: true`
    - `custom_attributes.last_ai_summary: "El cliente tiene intención de compra inmediata y proporcionó su número de teléfono. Faltan la fecha de viaje y la cantidad de personas para proceder con la reserva."`
    - `custom_attributes.miwayki_bridge_build: "0.7-auto-label-hot"`
    - `labels: ["hot"]`
- **Verificación de fake site**:
  - `lsof -iTCP:8080 -sTCP:LISTEN` confirmó un proceso `python3` escuchando en el puerto `8080`.
  - El error `OSError: [Errno 48] Address already in use` ocurrió al intentar iniciar un segundo servidor sobre el mismo puerto, no por caída del sitio ya activo.

### Estado actual
- El flujo local **Widget -> Chatwoot -> Bridge -> Dify -> Bridge -> Chatwoot** sigue operativo con la versión `0.7-auto-label-hot`.
- La persistencia de `custom_attributes` continúa funcionando correctamente.
- La asignación automática de la etiqueta `hot` quedó validada end-to-end.
- `chatwoot_fake_site` sigue siendo dependiente de un servidor HTTP local separado del stack Docker y debe verificarse/levantarse manualmente después de reinicios del entorno.
- Próximo paso: documentar el arranque seguro de `chatwoot_fake_site` y continuar con los siguientes ítems de lógica comercial/handoff de la fase básica local.

## 2026-04-11 - Entrada #37 (Reconciliación de etiqueta "hot" validada E2E)

### Objetivo de la sesión
- Implementar y validar la reconciliación automática de la etiqueta "hot" en Chatwoot basada en el `lead_score`.
- Asegurar que la etiqueta se elimine si el score baja de 70 y se añada si es mayor o igual a 70.
- Mantener la integridad del flujo de sincronización de atributos y contactos.

### Cambios realizados
- **Actualización del Bridge**:
  - `bridge/app/main.py` actualizado a la versión `0.9-hot-label-fix`.
  - Se mejoró el helper `_chatwoot_sync_labels` para soportar `add_labels` y `remove_labels` de forma atómica.
  - Se actualizó el webhook para aplicar la lógica de reconciliación de etiquetas en el Paso 3.
- **Infraestructura**:
  - Rebuild exitoso del contenedor `bridge` en la VM Lima.

### Resultados técnicos y validación
- **Healthcheck**:
  - `GET http://127.0.0.1:8000/health` -> `bridge_build: "0.9-hot-label-fix"`.
- **Prueba E2E (Widget)**:
  - **Caso Frío**: Mensaje "Hola" resultó en score < 70 y la eliminación exitosa de la etiqueta "hot" (labels: `[]`).
  - **Caso Caliente**: Mensaje con intención de compra y datos resultó en score >= 70 y la re-adición exitosa de la etiqueta "hot" (labels: `["hot"]`).
- **Persistencia**:
  - Los `custom_attributes` de la conversación se persistieron correctamente con la versión de build `0.9-hot-label-fix`.
  - La sincronización de contacto (`contact_sync`) se validó como funcional y persistente.

### Estado actual
- El flujo local **Widget -> Chatwoot -> Bridge -> Dify -> Bridge -> Chatwoot (Attributes + Labels + Contact)** está validado end-to-end.
- La lógica de etiquetas ahora es bidireccional y se reconcilia con el estado del lead.
- Próximo paso: limpieza de logs de depuración y preparación para el siguiente bloque de lógica comercial.

## 2026-04-11 - Entrada #38 (Captura de Notas Privadas como Contexto validada)

### Objetivo de la sesión
- Implementar la captura de Notas Privadas (Seller Feedback) para enriquecer el contexto de la IA.
- Asegurar que el feedback del vendedor se inyecte en el siguiente mensaje del usuario y se consuma correctamente.
- Mantener la integridad de los flujos previos (JSON, Atributos, Contactos, Etiquetas).

### Cambios realizados
- **Actualización del Bridge**:
  - `bridge/app/main.py` actualizado a la versión `0.10-private-note-context`.
  - Intercepción de notas privadas de agentes antes del filtro de mensajes de usuario.
  - Almacenamiento del feedback en el atributo `pending_seller_feedback` de la conversación.
  - Pre-fetch de la conversación en mensajes de usuario para inyectar el contexto: `[CONTEXTO VENDEDOR]: {feedback}`.
  - Limpieza del atributo `pending_seller_feedback` tras la respuesta exitosa de la IA, solo si fue consumido en ese turno.
- **Eficiencia**:
  - Se eliminó la doble llamada GET a la conversación reutilizando los datos del pre-fetch en el bloque de sincronización.

### Resultados técnicos y validación (Prevista)
- **Healthcheck**: `bridge_build: "0.10-private-note-context"`.
- **Flujo**:
  1. Nota privada guardada en Chatwoot.
  2. Mensaje de usuario recibe respuesta de Dify que considera la nota.
  3. El atributo se limpia automáticamente en Chatwoot.

### Estado actual
- El Bridge ya soporta la colaboración híbrida humano-IA mediante notas privadas.
- Fase básica local funcionalmente completa.

## 2026-04-11 - Entrada #39 (Validación E2E de Contexto por Nota Privada)

### Objetivo de la sesión
- Validar end-to-end la inyección de contexto mediante Notas Privadas en el flujo conversacional.
- Confirmar la persistencia y limpieza automática del atributo `pending_seller_feedback`.

### Resultados de la validación
- **Bridge Build**: `0.10-private-note-context` verificado mediante `/health`.
- **Captura exitosa**: Se ingresó una nota privada con el texto: "El cliente busca Cusco para mayo, presupuesto 500 USD por persona". El atributo `pending_seller_feedback` se persistió correctamente en Chatwoot.
- **Inyección y Respuesta**: Al enviar un mensaje de usuario ("Hola, ¿tienes disponibilidad?"), la IA reflejó explícitamente el contexto de la nota (destino Cusco, mes mayo y presupuesto de 500 USD) en su respuesta.
- **Consumo y Limpieza**: Tras la respuesta de la IA, el atributo `pending_seller_feedback` fue eliminado automáticamente de la conversación en Chatwoot, confirmando el ciclo de vida del contexto.
- **Estado final de la prueba**:
  - `lead_score`: 60
  - `lead_temperature`: "warm"
  - `handoff_recommended`: false
  - `labels`: `[]` (reconciliación de etiquetas funcionando correctamente)
- **Integridad**: Se confirmó que la persistencia de atributos, la sincronización de contactos y las reglas de etiquetas "hot" se mantienen operativas sin regresiones.

### Estado actual
- La **fase básica local** está funcionalmente validada en su totalidad: flujo E2E, scoring, persistencia de atributos, sincronización de contactos, reconciliación de etiquetas y colaboración híbrida mediante notas privadas.
- El siguiente paso es la revisión de cierre de los ítems de la fase básica local y la preparación de documentación final antes de la transición a infraestructura en la nube.

## 2026-04-11 - Entrada #40 (CIERRE DE FASE BÁSICA LOCAL)

### Objetivo
- Formalizar el cierre de la fase básica local tras completar todas las validaciones funcionales.
- Entregar la documentación operativa necesaria para reproducir el stack.

### Resumen de hitos alcanzados
- **Integración E2E**: El flujo completo entre Widget, Chatwoot, Bridge y Dify es estable y maneja tanto JSON como texto plano.
- **Persistencia Avanzada**: Atributos de conversación, etiquetas dinámicas ("hot") y sincronización de contactos validados.
- **Colaboración Humano-IA**: Implementada la captura de notas privadas como contexto enriquecido para la IA.
- **Salud del Sistema**: Endpoints de monitoreo (`/health`, `/health/dify`) operativos.

### Entregables de cierre
- **Runbook**: Creado `docs/RUNBOOKS/local_operations.md` con los procedimientos de arranque, rebuild y validación.
- **Actualización de Docs**: `compose/README.md` y `GEMINI.md` reflejan el estado final de la fase (`build 0.10`).

### Estado actual
- **FASE BÁSICA LOCAL: CERRADA Y VALIDADA.**
- El stack local es reproducible y funcionalmente completo según el Master Spec.
- Próxima etapa: Planificación de transición a la nube (AWS EC2) y revisión de portabilidad.
