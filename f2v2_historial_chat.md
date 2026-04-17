# Historial de Chat y Operaciones — MiWayki Fase 2 v2

A continuación se registra todo el historial de decisiones y operaciones técnicas ejecutadas durante la migración de **Fase 2 (Dify)** a **Fase 2 v2 (Langflow + NocoDB + Bridge)**, en una Mac M1 Pro.

---

## 1. Alineación Técnica a Fase 2 v2
Se ejecutaron los siguientes cambios sobre el repositorio para lograr paridad con `fase2localv2.md`:

### Base de Datos y Sesiones
- **Problema:** Un script global había reemplazado textos de Dify por Langflow, pero los scripts SQL estaban intactos y seguían mandando a armar tablas legacy (`bridge.dify_sessions`). Esto causaba un crasheo entre el código Python que leía una tabla de nombre nuevo y una base de datos que no existía.
- **Solución:** Se editó `sql/migrations/001_bridge_phase2.sql` para oficializar la tabla `bridge.langflow_sessions` y la columna `langflow_conversation_id`.

### Adaptador de Langflow (Bridge Tool Calling)
- **Problema:** En `bridge/app/adapters/langflow.py`, el payload enviado a la API `/run/{flow_id}` seguía metiendo el `session_id` dentro del JSON hijo `"tweaks": {}`. Esto era un remanente visual-teórico de Dify. 
- **Solución:** Se ajustó para cumplir con la API Oficial V1 de Langflow, mandando el param `"session_id"` suelto en la raíz del objeto, dejando `"tweaks": {}` vacío pero listo para expansiones modulares. 

### Recuperación del Widget de Fake Site
- **Problema:** Tras limpiar contenedores de Dify, el script principal de orquestación local (`miwayki-compose.sh`) no volvía a levantar la UI de demostración, aislando al usuario del Sandbox de Chatwoot.
- **Solución:** Se redactó `compose/docker-compose.fakesite.yml` y se inyectó como flag `-f` al `miwayki-compose.sh`. Retornó en un servidor local liviano bajo la red `miwayki-core-net` en `localhost:8080`.

### Solución de NocoDB Crash Error
- **Problema:** Al inicializar Docker, el contenedor de Postgres nativo para NocoDB (`miwayki-nocodb-pg`) fallaba fatalmente abortando en el log con el error *"Database is uninitialized and superuser password is not specified"*.
- **Solución:** Se introdujeron secretamente en local variables cruciales al archivo real `compose/.env`, específicamente `NOCODB_PG_PASSWORD` y `NOCODB_JWT_SECRET`. Esto permitió que Postgres entrase en modo *healthy* y que el frontend de NocoDB se recreara operativamente.

### Limpieza de Código y Operaciones
- Se eliminaron y purgaron scripts Bash de RSYNC de Dify caducos y "Checklists" obsoletos.
- Se agregó el `docs/RUNBOOKS/langflow_editorial_runbook.md`, documento vital que enseña al equipo de copy a adjuntar archivos de Markdown en NocoDB y Langflow, sin intervenir negativamente el Node Principal HTTP.

---

## 2. Método Oficial y Probado para Levantar el Servidor Local en Mac M1 Pro

> **Aviso Importante:** Al trabajar en macOS (Apple Silicon) con `Lima`, el shell en general puede "olvidar" atajos dependiendo del perfil, lo que produce fallos críticos en comandos standard. Docker en el Host suele no tener conectividad ya que corre dentro de una sub-VM llamada `miwayki-linux`.

Esta es la ruta irrompible técnica a ejecutar cuando Antigravity asiste, o un miembro de desarrollo humano opere localmente:

1. **Ubicar el Controlador en Homebrew (evitar fallos de PATH)**
   Nunca llamar a `limactl` directo. Usar la ruta absoluta del binario:
   ```bash
   /opt/homebrew/bin/limactl list
   ```

2. **Encender la Máquina Virtual Linux**
   ```bash
   /opt/homebrew/bin/limactl start miwayki-linux
   ```
   *Nota: Esperar al status 'running'*

3. **Ejecutar el Set y Orquestador de Docker-Compose DENTRO de Lima**
   La Mac no tiene un daemon docker directo. Nunca ejecutar o hacer build externo, si no que hay que invocarlo dentro y pidiendo remoción de huérfanos:
   ```bash
   /opt/homebrew/bin/limactl shell miwayki-linux /bin/bash -c "cd /Users/armandosilva/DATA/SMC/CS_79C_cloud/Final_Project && ./miwayki-compose.sh up -d --remove-orphans"
   ```

**Puertos habilitados una vez saludable el ecosistema (+/- 30 segundos):**
- Langflow UI: `http://127.0.0.1:7860`
- NocoDB UI: `http://127.0.0.1:8090`
- Bridge Health: `http://127.0.0.1:8000/health`
- Chatwoot Dashboard: `http://127.0.0.1:3000`
- Chatwoot Fakesite Widget: `http://127.0.0.1:8080`



# Documentación Técnica — Implementación Langflow: Flow "MiWayki Comercial"

***

## 1. Contexto y Stack General

El proyecto MiWayki es una plataforma de ventas de tours. El stack relevante para este documento es:

| Componente | Tecnología | Ubicación |
|---|---|---|
| Orquestador de IA | Langflow 1.x (build con imports `lfx.*`) | `http://127.0.0.1:7860` |
| LLM | Gemini 2.5 Flash (Google AI) | Cloud API |
| Backend comercial | MiWayki Bridge — FastAPI + uvicorn | `http://miwayki-bridge:8000` (interno Docker) / `http://localhost:8000` (host) |
| Base de datos | PostgreSQL | Contenedor `miwayki-postgres`, DB `miwayki`, user `miwayki_app` |
| Runtime de contenedores | Docker Compose (Linux VM vía Lima en macOS) | Proyecto en `~/DATA/SMC/CS_79C_cloud/Final_Project` |

***

## 2. Descripción del Flow en Langflow

### 2.1 Nombre y Identificación

- **Nombre del flow:** `MiWayki Comercial`
- **Flow ID:** `70ae51a1-6b52-45f6-b7a5-e63aa7c91a4b`
- **Proyecto Langflow:** `Starter Project`
- **Endpoint REST del flow:**
  ```
  POST http://127.0.0.1:7860/api/v1/run/70ae51a1-6b52-45f6-b7a5-e63aa7c91a4b
  ```
- **Payload de invocación esperado:**
  ```json
  {
    "input_value": "<mensaje del usuario>",
    "input_type": "chat",
    "output_type": "chat",
    "session_id": "<identificador de sesión>"
  }
  ```
- **Campo de respuesta relevante:** `outputs[0].outputs[0].results.message.text`

***

### 2.2 Arquitectura del Flow — Grafo de Nodos

El flow tiene exactamente **4 nodos** conectados de la siguiente manera:

```
Chat Input ──────────────────────────► Agent ──► Chat Output
                                          ▲
Cerebro Comercial MiWayki (Toolset) ─────┘
```

**Conexiones exactas:**
- `Chat Input` → puerto `Input` del `Agent`
- `Agent` → puerto `Input` del `Chat Output` (puerto `Response` del Agent conectado a `Chat Output`)
- `Cerebro Comercial MiWayki` → puerto `Toolset` conectado al puerto `Tools` del `Agent`

***

### 2.3 Nodo: Chat Input

- **Tipo:** componente nativo de Langflow, categoría `Input & Output`
- **Función:** recibe el mensaje del usuario que llega al flow como string de texto
- **Puerto de salida:** `Message` → conectado al `Agent`
- **Configuración actual:** sin modificaciones respecto al default; acepta el campo `input_value` del payload REST

***

### 2.4 Nodo: Chat Output

- **Tipo:** componente nativo de Langflow, categoría `Input & Output`
- **Función:** emite la respuesta final del Agent como salida del flow
- **Puerto de entrada:** `Text` recibe el output del `Agent`
- **Configuración actual:** sin modificaciones respecto al default

***

### 2.5 Nodo: Agent

- **Tipo:** componente nativo de Langflow, categoría `Models & Agents`
- **Función:** orquestador principal; recibe el mensaje del usuario, razona sobre qué herramienta usar, ejecuta la herramienta `Cerebro Comercial MiWayki` mediante el protocolo de tool calling de Gemini, y genera la respuesta final en lenguaje natural
- **Modelo de lenguaje configurado:** `gemini-2.5-flash` (Google Gemini)
- **Credencial:** campo `API Key` configurado con variable `GOOGLE_API_KEY`
- **Puerto de entrada Tools:** conectado al puerto `Toolset` del custom component
- **Puerto de entrada Input:** conectado al `Chat Output` del `Chat Input`
- **Puerto de salida Response:** conectado al `Chat Output`

**Agent Instructions (prompt de sistema completo):**
```
Eres el asistente comercial de MiWayki. Tu trabajo es atender prospectos de tours y usar la herramienta "Cerebro Comercial MiWayki" cuando corresponda.

Reglas:
- Si el usuario comparte nombre, email, teléfono, destino, fechas o cantidad de personas, usa la acción "register_lead".
- Si el usuario pide ver tours o catálogo, usa la acción "list_tours".
- Si el usuario pide precio o cotización, usa la acción "calculate_quote".
- Si el usuario pide cómo pagar, usa la acción "payment_instructions".
- Si el usuario indica que ya envió comprobante o voucher, usa la acción "register_voucher".
- Cuando uses la herramienta, llena "payload_json" con JSON válido y solo con los campos necesarios.
- Nunca inventes precios, tours, variantes ni disponibilidad.
- Si faltan datos necesarios para cotizar o registrar, pídelos de forma breve y clara.
- Responde siempre en español.
```

***

### 2.6 Nodo: Cerebro Comercial MiWayki

Este es el nodo más crítico del flow. Es un **Custom Component** escrito en Python, registrado en Langflow con **Tool Mode activado**, lo que permite al `Agent` invocarlo como herramienta mediante el mecanismo de function calling de Gemini.

#### 2.6.1 Metadatos del componente

| Campo | Valor |
|---|---|
| `display_name` | `Cerebro Comercial MiWayki` |
| `description` | `Motor comercial unificado para MiWayki Bridge.` |
| `icon` | `bridge` |
| `name` (class identifier) | `cerebro_comercial_miwayki` |
| `Component ID` (Langflow interno) | `C5wjZ` |
| **Tool Mode** | **Activado** |

#### 2.6.2 Imports del componente

```python
import json
import requests

from lfx.custom.custom_component.component import Component
from lfx.io import Output, StrInput, DropdownInput, MultilineInput
from lfx.schema.data import Data
```

**Nota crítica:** esta versión de Langflow usa el namespace `lfx.*` en lugar del namespace `langflow.*` que aparece en la documentación pública estándar. Cualquier refactor debe mantener estos imports o actualizarlos al namespace que corresponda al build instalado. Usar `langflow.*` en este build produce `ModuleNotFoundError`.

#### 2.6.3 Inputs declarados (atributos de clase)

```python
inputs = [
    StrInput(
        name="bridge_url",
        display_name="Bridge URL",
        value="http://miwayki-bridge:8000",
        info="URL interna del bridge dentro de Docker/Compose."
    ),
    StrInput(
        name="session_id",
        display_name="Session ID",
        value="",
        info="ID de conversación inyectado desde Chat Input o desde otra parte del flujo."
    ),
    DropdownInput(
        name="action",
        display_name="Action",
        options=[
            "register_lead",
            "list_tours",
            "calculate_quote",
            "payment_instructions",
            "register_voucher",
        ],
        value="list_tours",
        info="Acción que ejecutará el bridge.",
        tool_mode=True
    ),
    MultilineInput(
        name="payload_json",
        display_name="Payload JSON",
        value="{}",
        info="JSON con los campos adicionales requeridos por la acción."
    ),
]
```

**Notas de diseño:**
- `bridge_url` es un `StrInput` editable directamente en el canvas de Langflow, lo que permite cambiar el host del bridge sin tocar código.
- `session_id` actualmente está configurado con valor manual `12345` en el canvas de pruebas. **En producción con chat web, este campo debe recibir el `session_id` del cliente web**, ya sea inyectado desde una variable del flow o desde el payload de entrada del endpoint REST.
- `action` usa `DropdownInput` con `tool_mode=True`. Este es el parámetro que expone la herramienta al Agent: Gemini recibe la lista de opciones válidas y elige cuál acción ejecutar según el contexto de la conversación.
- `payload_json` es un `MultilineInput` que recibe un JSON string. La lógica interna lo parsea con `json.loads()`.

#### 2.6.4 Output declarado

```python
outputs = [
    Output(
        name="output",
        display_name="Output",
        method="run_action",
    ),
]
```

El output devuelve un objeto `Data` de Langflow. Cuando Tool Mode está activado, el puerto de salida se transforma en **Toolset**, que es el puerto que se conecta al puerto `Tools` del `Agent`.

#### 2.6.5 Lógica del método `run_action`

El método `run_action` es el executor central. Su lógica completa:

1. **Sanitización de inputs:** extrae y limpia `bridge_url`, `session_id`, `action`, y parsea `payload_json` con `json.loads()`. Si el JSON es inválido, retorna `Data` con `success: false` y mensaje de error sin hacer ninguna llamada HTTP.

2. **Inyección de `conversation_id`:** para las acciones `register_lead`, `calculate_quote`, y `register_voucher`, el `session_id` se inyecta automáticamente en el payload como campo `conversation_id` antes de hacer el request. Esto vincula la interacción con el registro en la base de datos del bridge.

3. **Routing por acción:** cada valor del dropdown mapea a un endpoint específico del bridge:

| Acción | Método HTTP | Endpoint |
|---|---|---|
| `register_lead` | `POST` | `/lead/upsert` |
| `list_tours` | `GET` | `/catalog/tours` |
| `calculate_quote` | `POST` | `/quote/calculate` |
| `payment_instructions` | `POST` | `/reservation/payment-instructions` |
| `register_voucher` | `POST` | `/reservation/voucher` |

4. **Headers:** todas las peticiones llevan `Content-Type: application/json` y timeout de **20 segundos**.

5. **Manejo de respuesta:** intenta parsear la respuesta como JSON; si falla, captura el texto raw en `raw_text`. Retorna un objeto `Data` con los campos `success`, `status_code`, `action` y `response`.

6. **Manejo de errores:** dos bloques de excepción separados:
   - `requests.exceptions.RequestException` → `error_type: "HTTP_BRIDGE_ERROR"` (fallo de conectividad, timeout, DNS)
   - `Exception` genérico → `error_type: "INTERNAL_COMPONENT_ERROR"` (error inesperado dentro del componente)

7. **`self.status`:** se actualiza con `f"{action}: {response.status_code}"` para que Langflow muestre el estado en el canvas visualmente.

***

## 3. Problemas Encontrados y Resueltos Durante la Sesión

### 3.1 Problema: Imports incompatibles

**Síntoma:** el custom component no compilaba porque se usaban imports del namespace `langflow.*` en vez del namespace `lfx.*` que corresponde al build instalado.

**Resolución:** se reemplazaron todos los imports por:
```python
from lfx.custom.custom_component.component import Component
from lfx.io import Output, StrInput, DropdownInput, MultilineInput
from lfx.schema.data import Data
```

### 3.2 Problema: `tool_mode=True` en `StrInput`

**Síntoma:** el parámetro `tool_mode=True` en un `StrInput` no era reconocido correctamente por el build instalado.

**Resolución:** se migró el input `action` de `StrInput` a `DropdownInput`, que sí soporta `tool_mode=True` en este build. El `DropdownInput` expone las opciones válidas al LLM como parte del schema de la herramienta.

### 3.3 Problema: Bridge devolvía 404 en `/catalog/tours`

**Síntoma:** la traza de Langflow mostraba `status_code: 404, detail: "Not Found"` al ejecutar `list_tours`.

**Causa raíz:** los routers de FastAPI para los endpoints comerciales (`/catalog`, `/lead`, `/quote`, `/reservation`) no estaban registrados con `include_router()` en el archivo principal de la app del bridge, o las rutas tenían prefijos distintos.

**Resolución:** Antigravity corrigió el bridge para que los endpoints quedaran accesibles bajo los paths que el componente espera.

### 3.4 Problema: Bridge devolvía 500 en `/lead/upsert`

**Síntoma:** la traza de Langflow mostraba `status_code: 500, raw_text: "Internal Server Error"` al ejecutar `register_lead`.

**Causa raíz (cadena de 3 problemas resueltos por Antigravity):**
1. La variable de entorno `BRIDGE_DATABASE_URL` no existía en `compose/.env.bridge`, por lo que FastAPI hacía fallback al string hardcodeado en `settings.py` con credenciales incorrectas (`change_me` o similar).
2. El usuario `miwayki_app` en PostgreSQL tenía un password distinto al que intentaba usar el bridge.
3. Una vez corregidas las credenciales, el error cambió a `asyncpg.exceptions.UndefinedTableError: relation "bridge.leads" does not exist` porque las migraciones SQL no habían sido ejecutadas contra la base de datos.

**Resolución por Antigravity:**
- Agregó `BRIDGE_DATABASE_URL=postgresql://miwayki_app:Miwayki20261014@postgres:5432/miwayki` a `compose/.env.bridge`
- Verificó y corrigió el password del usuario en el contenedor `miwayki-postgres`
- Ejecutó las migraciones con:
  ```bash
  docker exec -i miwayki-postgres psql -U miwayki_app -d miwayki < sql/migrations/001_bridge_phase2.sql
  ```
- Reinició el contenedor del bridge para que tomara las nuevas variables de entorno

***

## 4. Estado Actual de las 5 Acciones (Post-Fix)

| Acción | Endpoint | HTTP Result | Comportamiento del Agent | Observación |
|---|---|---|---|---|
| `register_lead` | `POST /lead/upsert` | **200 OK** | Llama RUN ACTION, registra lead, responde confirmación | Operativo. `lead_id: 1` confirmado en primera prueba |
\n
***

## 5. Gestión de API Keys en Langflow y Autenticación de Endpoints

### 5.1 Recuperar API Key Existente

La API Key de Langflow requerida para invocar el flow desde clientes externos (como webhook) se encuentra en **Settings → Langflow API Keys**. Si el valor exacto fue olvidado y solo aparece enmascarado (`sk-Zv4Ki********`), puede ser recuperado de las siguientes formas:

**Opción 1 — Vía Base de Datos Interna:**
```bash
# Entrar al contenedor de Langflow (o si corre directo en VM) y extraerla de SQLite
docker exec -it miwayki-langflow bash
sqlite3 ~/.local/share/langflow/langflow.db "SELECT api_key FROM apikey WHERE name LIKE '%Project%';"
```

**Opción 2 — Desde la UI:**
Hacer clic en el ícono de "Refresh" (reset/regenerate) situado junto a la papelera en el panel de `Langflow API Keys` o simplemente crear una clave fresca con el botón "Add New".

### 5.2 Sintaxis Correcta de Invocación REST

Una vez obtenida la API Key completa, todas las llamadas REST al orquestador Langflow usando su Endpoint (`/api/v1/run/{flow_id}`) deben incluir la cabecera transaccional de autorización `x-api-key`.

**Ejemplo de Petición cURL Standard:**
```bash
curl -X POST http://127.0.0.1:7860/api/v1/run/70ae51a1-6b52-45f6-b7a5-e63aa7c91a4b \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk-Zv4Ki..." \
  -d '{
    "input_value": "hola, quiero ver los tours",
    "input_type": "chat",
    "output_type": "chat",
    "session_id": "sesion-001"
  }'
```


***

### 5.3 Rol de la API Key en Arquitecturas End-to-End

#### Para qué sí sirve la clave generada
Sirve estrictamente para que un backend proxy (el FastAPI Bridge), un script directo, operaciones tipo Antigravity o el propio Chatwoot-trigger abstraído realicen llamadas controladas a tu flow de Langflow autenticándose mediante la cabecera `x-api-key`. 

La documentación oficial insta a establecer este patrón: enviar `x-api-key: $LANGFLOW_API_KEY` al endpoint `/api/v1/run/$FLOW_ID` para ejecutar el flow en modo _headless_, evadiendo las protecciones de sesión de la UI de Langflow.

#### En el Caso de MiWayki Fase 2 v2
Nuestra integración con Chatwoot pasa estructuralmente a través del **FastAPI Bridge** (el backend intermedio). Es éste backend el que dispara la llamada hacia Langflow vía HTTP. Por ello, la validación se resguarda configurando dinámicamente dicha key bajo la variable `LANGFLOW_API_KEY` en el entorno `.env.bridge`.
(Alternativamente, si se usara el componente nativo Webhook de Langflow con `LANGFLOW_WEBHOOK_AUTH_ENABLE=True`, la misma clave servirá para autenticación).

### 5.4 Snippet Final Integrado (cURL a MiWayki Comercial)

El siguiente es el payload y request exacto con la clave sellada, listo para invocarse desde el puente web o testing manual.

```bash
curl --request POST \
     --url 'http://127.0.0.1:7860/api/v1/run/70ae51a1-6b52-45f6-b7a5-e63aa7c91a4b?stream=false' \
     --header 'Content-Type: application/json' \
     --header "x-api-key: sk-7JEuqlaXYeOJIsDbUadoI1DihsHLr6XMvApsXCsW2aY" \
     --data '{
       "output_type": "chat",
       "input_type": "chat",
       "input_value": "hello world!",
       "session_id": "YOUR_SESSION_ID_HERE"
     }'
```
