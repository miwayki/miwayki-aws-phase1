# Compose local - Miwayki

Base de infraestructura local para el proyecto:
- PostgreSQL
- Redis

Nota: PostgreSQL usa imagen con `pgvector` para compatibilidad con Chatwoot.

## Mapa de puertos (qué escucha qué)

Todo lo que publica **localhost** en este proyecto (valores por defecto). Si algo “no responde”, otro proceso puede haber ocupado el puerto: `lsof -nP -iTCP:<puerto> -sTCP:LISTEN`.

| Puerto (host) | Qué es | Dónde se define |
|---------------|--------|-----------------|
| **5432** | PostgreSQL (Miwayki/Chatwoot) | `compose/.env` → `POSTGRES_PORT` |
| **6379** | Redis | `compose/.env` → `REDIS_PORT` |
| **3000** | Chatwoot (UI + widget) | Fijo en `docker-compose.chatwoot.yml` |
| **8000** | Bridge FastAPI (salud + webhook) | `compose/.env` → **`BRIDGE_HOST_PORT`** (por defecto 8000). **Dentro** de Docker el servicio sigue en `:8000`; Chatwoot debe seguir apuntando a `http://bridge.local:8000/...`. |
| **8080** | Sitio de prueba del widget (`chatwoot_fake_site/`) | No es Docker; servidor estático local (ver README de esa carpeta). |
| **9080** / **9443** | Langflow (nginx HTTP/HTTPS en el host) | `compose/langflow.env.overrides` → copiar a `.env` de Langflow (`EXPOSE_NGINX_PORT`, etc.). No forma parte del compose Miwayki. |

**Red Docker interna (sin puerto en el Mac):** entre contenedores en `miwayki-core-net`, p. ej. `chatwoot:3000`, servicio `bridge` (alias `bridge.local`) en el puerto **8000** interno, API Langflow **`api:5001`**.

**Nota:** En `vendor/langflow`, variables como `CHROMA_PORT=8000` son **internas** al stack Langflow (contenedor a contenedor), no el mismo puerto que el bridge en tu Mac.

## 1) Preparar variables

Desde `compose/`:

```bash
cp .env.example .env
```

Edita `.env` y coloca credenciales fuertes.

## 2) Levantar servicios (modo desarrollo)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## 3) Ver estado y logs

```bash
docker compose ps
docker compose logs -f postgres redis
```

## 4) Bajar servicios

```bash
docker compose down
```

Para bajar y eliminar volúmenes de datos (destructivo):

```bash
docker compose down -v
```

## 5) Perfil producción local (sin puertos publicados)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 6) Chatwoot (fase 2 del roadmap)

Preparar variables:

```bash
cp .env.chatwoot.example .env.chatwoot
```

Generar un `SECRET_KEY_BASE` robusto (ejemplo):

```bash
openssl rand -hex 64
```

Pegar ese valor en `.env.chatwoot`.

Crear la base de datos de Chatwoot en PostgreSQL:

```bash
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE DATABASE chatwoot_production;"
```

Ejecutar migraciones/seed de Chatwoot:

```bash
docker compose -f docker-compose.yml -f docker-compose.chatwoot.yml run --rm chatwoot bundle exec rails db:chatwoot_prepare
```

Levantar Chatwoot + Sidekiq:

```bash
docker compose -f docker-compose.yml -f docker-compose.chatwoot.yml up -d
```

Ver estado:

```bash
docker compose -f docker-compose.yml -f docker-compose.chatwoot.yml ps
```

## 7) Bridge FastAPI mínimo (fase 3 inicial)

Los archivos `docker-compose*.yml` viven en **`compose/`**. Si ejecutas comandos desde la **raíz del repositorio** (`Final_Project/`), usa el wrapper (evita el error *no such file*):

```bash
./miwayki-compose.sh up -d --build bridge
```

Equivalente manual:

```bash
cd compose && docker compose -f docker-compose.yml -f docker-compose.chatwoot.yml -f docker-compose.bridge.yml up -d --build bridge
```

O desde la raíz sin script (variable `COMPOSE_FILE` + directorio del proyecto):

```bash
COMPOSE_FILE=compose/docker-compose.yml:compose/docker-compose.chatwoot.yml:compose/docker-compose.bridge.yml \
  docker compose --project-directory compose up -d --build bridge
```

Preparar variables:

```bash
cp .env.bridge.example .env.bridge
```

En **`compose/.env`** (el mismo que Postgres/Redis), opcional: `BRIDGE_HOST_PORT` si el **8000** del host ya lo usa otro proyecto (el webhook **sigue** siendo `http://bridge.local:8000` en red Docker).

Configura en `.env.bridge`:
- `CHATWOOT_BASE_URL=http://chatwoot:3000`
- `CHATWOOT_API_TOKEN=<token API de Chatwoot>`
- `BRIDGE_AUTO_REPLY=<mensaje de prueba>`
- `CHATWOOT_WEBHOOK_SECRET=<secret del webhook en Chatwoot>` (el bridge valida `X-Chatwoot-Signature`; si queda vacío, no verifica firma)
- `LANGFLOW_API_BASE=http://api:5001/v1` (desde el bridge; **no** uses `http://127.0.0.1/v1` dentro del contenedor)
- `LANGFLOW_API_KEY=<secret de la app en Langflow → API Access>` (formato `app-...`). Si `LANGFLOW_API_KEY` está vacío, el bridge usa solo `BRIDGE_AUTO_REPLY`.

### Flujo E2E, Persistencia y Contexto (Validado en v0.10)

El flujo completo **Widget -> Chatwoot -> Bridge -> Langflow -> Bridge -> Chatwoot** ha sido validado localmente en su totalidad con la versión `0.10-private-note-context`.

**1. Operaciones validadas:**
- **Contrato Langflow:** Parseo JSON con fallback a texto plano.
- **Atributos:** Persistencia real en Chatwoot (endpoint `POST .../custom_attributes`).
- **Contactos:** Sincronización de nombre, email, teléfono (E.164) y atributos de viaje.
- **Etiquetas:** Reconciliación automática de la etiqueta `hot` (score ≥ 70).
- **Contexto Híbrido:** Captura de notas privadas (`pending_seller_feedback`) e inyección como contexto AI.

**2. Procedimientos de verificación:**

```bash
# Rebuild y salud (v0.10)
./miwayki-compose.sh up -d --build bridge
curl -sS http://127.0.0.1:8000/health | jq .bridge_build
```

Para operaciones detalladas, ver `docs/RUNBOOKS/local_operations.md`.


Levantar bridge junto al stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.chatwoot.yml -f docker-compose.bridge.yml up -d --build
```

Probar salud:

```bash
# Sustituye 8000 si en compose/.env pusiste otro BRIDGE_HOST_PORT
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/health/langflow | python3 -m json.tool
```

Tras un `--build` reciente, `GET /health` debe incluir `bridge_build` acorde al código (p. ej. `0.4-minimal-default`). Si **solo** aparece `{"status":"ok"}`, el proceso en el puerto 8000 **no** es la imagen nueva (Docker no reconstruyó o hay otro servidor en ese puerto).

**Prioridad:** validar primero el flujo mínimo (widget → Chatwoot → webhook → Langflow → respuesta en el hilo). La sync de **custom attributes** está **desactivada por defecto** (`BRIDGE_SYNC_CHATWOOT_ATTRIBUTES=0`); activar con `1` cuando ese flujo ya funcione.

`GET /health/langflow` comprueba que el bridge alcanza el contenedor Langflow `api` (GET `/health` del API, sin usar la clave de la app). Tras cambiar `.env.bridge`, reconstruye el bridge (`--build`) para que el código nuevo entre en la imagen.

Reinicio solo del bridge:

```bash
docker compose -f docker-compose.yml -f docker-compose.chatwoot.yml -f docker-compose.bridge.yml up -d --build bridge
```

## 8) Langflow (orquestador IA, mismo host / misma VM)

El código de referencia de Langflow va en `vendor/langflow/` (**no** está en Git; clonar con `git clone --depth 1 https://github.com/langgenius/langflow.git vendor/langflow`, ver `vendor/README.md`). El **bridge no comparte código** con Langflow; solo habla por red Docker.

La pieza propia de Miwayki para la red Docker es **`compose/langflow-docker-compose.miwayki.yml`** (copiarla al directorio de despliegue de Langflow junto al `docker-compose.yaml` oficial).

### Requisitos

- Red Docker `miwayki-core-net` (levantar al menos una vez el compose Miwayki).
- **Disco / RAM:** el stack Langflow es pesado (muchas imágenes). En Lima, **20 GiB de disco suele ser insuficiente**; se recomienda **≥ 48 GiB** de disco y **≥ 6 GiB** de RAM para VM, por ejemplo:
  - `limactl stop miwayki-linux`
  - `limactl edit miwayki-linux --disk 48 --memory 6`
  - `limactl start miwayki-linux`

### Montaje solo lectura (Lima) y datos escribibles

Si el proyecto está montado **read-only** en la VM, Docker **no puede crear** `vendor/langflow/docker/volumes/`. En ese caso se usa una copia en disco local de la VM:

- Ruta usada en despliegue: **`/var/opt/miwayki-langflow/`** (sincronizada desde el repo del host).

Sincronizar después de cambiar archivos bajo `vendor/langflow/docker/` (plantillas, etc.) y **siempre** el overlay de red:

```bash
limactl shell miwayki-linux -- bash -lc 'sudo rsync -a \
  /Users/armandosilva/DATA/SMC/CS_79C_cloud/Final_Project/vendor/langflow/docker/ \
  /var/opt/miwayki-langflow/ && sudo cp \
  /Users/armandosilva/DATA/SMC/CS_79C_cloud/Final_Project/compose/langflow-docker-compose.miwayki.yml \
  /var/opt/miwayki-langflow/'
```

(Ajusta la ruta del repo si no coincide; dentro de Lima suele ser la misma ruta montada.)

Copiar `.env` generado en el Mac (o editar en la VM):

```bash
cp vendor/langflow/docker/.env.example vendor/langflow/docker/.env
cat compose/langflow.env.overrides >> vendor/langflow/docker/.env
# luego rsync como arriba, o crear /var/opt/miwayki-langflow/.env a mano.
```

Añade `vendor/langflow/docker/.env` al `.gitignore` del proyecto (ya listado) para no versionar secretos.

### Levantar Langflow (dentro de la VM)

```bash
cd /var/opt/miwayki-langflow
sudo docker compose -p langflow -f docker-compose.yaml -f langflow-docker-compose.miwayki.yml up -d
```

(Desde `vendor/langflow/docker` en el host **solo** si el montaje es **escribible** y `volumes/` puede crearse.)

### Acceso UI (instalación inicial)

- En el navegador del Mac: `http://127.0.0.1:9080/install` (Nginx de Langflow; puerto `9080` vía `compose/langflow.env.overrides`).

### Integración con el bridge

- El servicio `api` de Langflow está en la red `miwayki-core-net` (archivo `langflow-docker-compose.miwayki.yml` en el directorio de Langflow).
- Desde el contenedor `bridge`, URL interna típica: **`http://api:5001`**.

### Ver estado

```bash
cd /var/opt/miwayki-langflow
sudo docker compose -p langflow ps
```
