# Miwayki AWS / Chatwoot / Dify Handoff Técnico para Cursor

**Fecha del handoff:** 2026-04-13  
**Objetivo del documento:** entregar a otra IA/ingeniero todo el contexto técnico de lo ya diagnosticado, lo ya resuelto, lo que sigue fallando, dónde está cada componente, qué credenciales se usaron durante la prueba y cuáles son los siguientes pasos más probables.

---

## 1. Resumen ejecutivo

El problema principal **ya no está en Dify**.  
El sistema está en este estado:

- **Dify API responde correctamente** desde el bridge.
- **La app `miwayki-chat` existe, tiene LLM configurado y ya fue publicada.**
- **El webhook de Chatwoot llega al bridge** y el bridge procesa el mensaje.
- **El bridge llama a Dify y Dify responde `200 OK`**.
- **El fallo actual ocurre al publicar la respuesta del bot en Chatwoot**, porque Chatwoot devuelve:

```text
401 {"error":"Invalid Access Token"}
```

Por tanto, el cuello de botella actual es:

> **el token de API de Chatwoot que usa el bridge para hacer POST de vuelta a Chatwoot es inválido / está desactualizado / no fue realmente actualizado en la ruta efectiva que usa el contenedor.**

---

## 2. Topología real de la instalación

Hay que separar muy bien qué corre en AWS y qué corre en la Mac local.

### 2.1. Componentes en AWS EC2

Instancia EC2:

- **AWS host:** `34.207.15.203`
- Usuario SSH: `ubuntu`

En AWS están corriendo al menos estos componentes relevantes:

- **Chatwoot** (accedido por túnel local en `127.0.0.1:3000`)
- **Bridge FastAPI / Uvicorn** (`miwayki-bridge`) accesible por túnel en `127.0.0.1:8000`
- **Dify** (UI y API) accesible por túnel en `127.0.0.1:9080`
- Contenedor Dify API: `dify-api-1`
- Contenedor bridge: `miwayki-bridge`

### 2.2. Componentes en la Mac local

**La web fake NO está en AWS. Está en la Mac local.**  
Eso es fundamental para no perder tiempo.

Se levantó así:

```bash
python3 -m http.server 8080 --directory chatwoot_fake_site
```

Se verificó con:

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
curl -I http://127.0.0.1:8080
```

Y devolvía:

- servidor: `SimpleHTTP/0.6 Python/3.13.9`
- contenido servido desde el directorio local `chatwoot_fake_site`

**Conclusión:**

- `127.0.0.1:8080` = sitio fake local en la Mac
- `127.0.0.1:3000` = Chatwoot remoto en AWS, expuesto por SSH tunnel
- `127.0.0.1:8000` = bridge remoto en AWS, expuesto por SSH tunnel
- `127.0.0.1:9080` = Dify remoto en AWS, expuesto por SSH tunnel

---

## 3. Credenciales, claves y datos compartidos durante la prueba

> Este bloque contiene secretos de la prueba piloto porque el usuario pidió explícitamente incluirlos para el handoff a Cursor. No usar esto en producción.

### 3.1. AWS

- **AWS host:** `34.207.15.203`
- **Ruta local del PEM SSH:**

```text
/Users/armandosilva/.ssh/miwayki-phase1-trial-key-20260412-134526.pem
```

### 3.2. Dify

Hubo dos API keys visibles durante la sesión:

#### Key antigua / inválida encontrada en el bridge env

```text
app-9u37s2QW63nHmlUUjYJVTOfX
```

Esta fue la que aparecía inicialmente dentro del contenedor `miwayki-bridge` y generaba:

```json
{"code":"unauthorized","message":"Access token is invalid","status":401}
```

#### Key nueva / válida creada desde la UI de Dify

```text
app-9jN5ctFMkX9EsIqb36yuiqkn
```

Con esta key el bridge pudo llamar exitosamente a Dify y obtener respuesta `200`.

### 3.3. Chatwoot

#### Access Token de Chatwoot mostrado desde Profile > Settings

```text
e4LgfcqwdD62dK7daJjssdmq
```

Este token fue compartido por el usuario para reemplazar el token inválido que el bridge estaba usando hacia Chatwoot.

### 3.4. Identificadores útiles

- **Dify app / URL visible en UI:**

```text
http://127.0.0.1:9080/app/9e2da6b8-fbe7-4940-b482-5a266f4355e3/workflow
```

- **Nombre de la app Dify:** `miwayki-chat`
- **Workspace Dify:** `miwayki's Workspace`
- **Modo Dify:** `advanced-chat`

---

## 4. Comandos base usados en la Mac

### 4.1. SSH tunnel a AWS

Este fue el túnel local usado:

```bash
ssh -N \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o StrictHostKeyChecking=accept-new \
  -L 3000:127.0.0.1:3000 \
  -L 8000:127.0.0.1:8000 \
  -L 9080:127.0.0.1:9080 \
  -i "$AWS_KEY" \
  ubuntu@"$AWS_HOST"
```

Cuando ya había un túnel abierto aparecía:

```text
bind [127.0.0.1]:3000: Address already in use
bind [127.0.0.1]:8000: Address already in use
bind [127.0.0.1]:9080: Address already in use
Could not request local forwarding.
```

Eso no significaba que AWS estuviera mal; normalmente solo indicaba que **ya existía otro túnel activo**.

### 4.2. Fake site local

```bash
cd /Users/armandosilva/DATA/SMC/CS_79C_cloud/Final_Project
python3 -m http.server 8080 --directory chatwoot_fake_site
```

### 4.3. Variables usadas frecuentemente

```bash
export AWS_HOST="34.207.15.203"
export AWS_KEY="/Users/armandosilva/.ssh/miwayki-phase1-trial-key-20260412-134526.pem"
```

---

## 5. Qué se logró realmente

### 5.1. Se verificó que el fake site local sí funciona

Cuando estaba levantado correctamente:

```bash
curl -I http://127.0.0.1:8080
```

respondía `HTTP/1.0 200 OK` desde `SimpleHTTP/0.6`.

### 5.2. Se verificó que el bridge está vivo

Health del bridge:

```json
{"status":"ok","bridge_build":"0.10-private-note-context","endpoints":["/health","/health/dify","/webhooks/chatwoot"]}
```

### 5.3. Se arregló la conectividad bridge -> Dify API

Inicialmente el bridge devolvía `502` al webhook y había evidencia de que Dify no era alcanzable correctamente por DNS/red interna.

Se conectó el contenedor `dify-api-1` a la red `miwayki-core-net` con alias `api`, y se verificó esto:

- `DIFY_API_BASE=http://api:5001/v1`
- `GET http://api:5001/health` accesible desde el bridge
- `/health/dify` del bridge devolvía `reachable: true`

### 5.4. Se confirmó que la Dify app existe y responde

Desde dentro del bridge se ejecutó un POST a:

```text
POST /v1/chat-messages
```

con la key correcta y la app ya publicada, y respondió `200 OK` con payload válido, por ejemplo:

```json
{
  "event": "message",
  "mode": "advanced-chat",
  "answer": "...",
  "conversation_id": "34aacb64-5bf1-4b4a-bf21-46da9fca6a77"
}
```

### 5.5. Se confirmó que el webhook de Chatwoot sí llega al bridge

Los logs muestran entradas como:

```text
INFO: 172.18.0.6:xxxxx - "POST /webhooks/chatwoot HTTP/1.1" ...
```

### 5.6. Se añadió instrumentación de debug al bridge

Se modificó `/app/app/main.py` dentro del contenedor `miwayki-bridge` para imprimir:

- `CHATWOOT_DEBUG_START / END`
- `DIFY_DEBUG_START`
- `DIFY_DEBUG status=...`
- `CHATWOOT_SEND status=...`
- `CHATWOOT_SEND_FAILED`
- `CHATWOOT_SEND_OK`

Esto permitió aislar el problema real.

---

## 6. Qué está fallando ahora exactamente

### 6.1. Síntoma actual

El usuario escribe en el widget y se observa este patrón en logs:

```text
CHATWOOT_DEBUG_START
CHATWOOT_DEBUG event=message_created message_type=incoming private=False content_type=text sender_type=None content=hola debug 008
CHATWOOT_DEBUG_END
DIFY_DEBUG_START
DIFY_DEBUG query=hola debug 008
DIFY_DEBUG chatwoot_conversation_id=3
DIFY_DEBUG status=200
DIFY_DEBUG body={...respuesta válida de Dify...}
CHATWOOT_SEND status=401
CHATWOOT_SEND body={"error":"Invalid Access Token"}
CHATWOOT_SEND_FAILED
INFO: 172.18.0.6:52686 - "POST /webhooks/chatwoot HTTP/1.1" 502 Bad Gateway
```

### 6.2. Diagnóstico

El bridge ya:

1. recibe el mensaje desde Chatwoot,
2. lo filtra como mensaje entrante válido,
3. llama a Dify,
4. Dify responde bien,
5. luego el bridge intenta publicar la respuesta de vuelta a Chatwoot,
6. y **ahí Chatwoot rechaza con 401 invalid access token**.

### 6.3. Punto exacto de fallo en el flujo

En `/app/app/main.py`, la ruta `@app.post("/webhooks/chatwoot")` arma este POST:

```python
msg_url = (
    f"{CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}"
    f"/conversations/{conversation_id}/messages"
)
msg_body = {"content": reply_text, "message_type": "outgoing", "private": False}
headers = {"api_access_token": CHATWOOT_API_TOKEN}
response = await client.post(msg_url, json=msg_body, headers=headers)
```

El `401` sucede en ese `client.post(...)`.

**No es un problema de Dify.**  
**No es un problema de publicación de la app.**  
**No es un problema del webhook de entrada.**

Es un problema de **token Chatwoot efectivo cargado/consumido por el bridge**.

---

## 7. Evidencia técnica recopilada

### 7.1. Dify info correcta desde el bridge

Se obtuvo desde dentro del contenedor:

```text
BASE = http://api:5001/v1
STATUS: 200
{"name":"miwayki-chat","description":"","tags":[],"mode":"advanced-chat","author_name":"miwayki"}
```

### 7.2. Error previo de Dify antes de publicar la app

Antes de publicar el workflow, el bridge devolvía:

```json
{"code":"invalid_param","message":"Workflow not published","status":400}
```

Eso ya quedó resuelto cuando el usuario publicó la app.

### 7.3. Error previo de Dify con key inválida

Antes de reemplazar la key vieja por la nueva:

```json
{"code":"unauthorized","message":"Access token is invalid","status":401}
```

Eso ya quedó resuelto.

### 7.4. Error actual definitivo

Ahora el error definitivo es:

```json
{"error":"Invalid Access Token"}
```

pero **devuelto por Chatwoot**, no por Dify.

---

## 8. Estado del código del bridge que ya se inspeccionó

Archivo inspeccionado dentro del contenedor:

```text
/app/app/main.py
```

Se vio claramente:

- helper `_is_incoming_user_message(...)`
- helper `_dify_blocking_reply(...)`
- ruta `@app.post("/webhooks/chatwoot")`
- `reply_text` obtenido desde Dify
- POST de vuelta a Chatwoot usando header `api_access_token`

### 8.1. Fragmento funcional clave

- `DIFY_API_BASE` se usa para `POST /chat-messages`
- `CHATWOOT_API_TOKEN` se usa para publicar la respuesta de vuelta a Chatwoot
- `BRIDGE_SYNC_CHATWOOT_ATTRIBUTES` existe y controla sincronización adicional

### 8.2. Importante

Aunque se intentaron parches rápidos dentro del contenedor, **no quedó demostrado que el token efectivo de Chatwoot haya sido actualizado en la fuente correcta**.

Es decir, todavía hay que revisar con precisión una de estas posibilidades:

1. `CHATWOOT_API_TOKEN` se define al inicio del archivo desde `os.getenv(...)` y el contenedor sigue cargando el valor viejo.
2. El valor viejo está en `docker-compose.yml`, `.env`, `compose`, script wrapper o variable exportada por `miwayki-compose.sh`.
3. Se parcheó una referencia textual pero no la ruta real de carga del token.
4. El contenedor fue recreado desde una fuente persistente que volvió a inyectar el token inválido.

---

## 9. Qué se intentó y en qué punto quedó

### 9.1. Intentos exitosos

- levantar fake web local en la Mac
- levantar túneles SSH a `3000`, `8000`, `9080`
- validar `health` del bridge
- validar `health/dify`
- conectar `dify-api-1` a la red del bridge (`miwayki-core-net`) con alias `api`
- obtener Dify `200 OK` desde el bridge
- publicar la app Dify y confirmar que `chat-messages` ya responde `200`
- agregar logs de debug en `main.py`
- aislar el fallo final en `CHATWOOT_SEND status=401`

### 9.2. Intentos incompletos / fallidos

- parchear de forma estable el token de Chatwoot en la configuración persistente del bridge
- confirmar que el `CHATWOOT_API_TOKEN` nuevo (`e4LgfcqwdD62dK7daJjssdmq`) quedó efectivamente cargado por el contenedor y usado por la constante `CHATWOOT_API_TOKEN`

---

## 10. Qué debería hacer Cursor ahora

### 10.1. Objetivo inmediato

**Arreglar el token que el bridge usa para llamar a Chatwoot.**

### 10.2. Plan recomendado

#### Paso A. Encontrar el origen real del token Chatwoot

Buscar en AWS, en el proyecto que levanta el bridge, todas las referencias a:

- `CHATWOOT_API_TOKEN`
- `CHATWOOT_BASE_URL`
- `miwayki-bridge`
- `miwayki-compose.sh`
- archivos `.env`
- `docker-compose.yml`, `compose.yaml`, overrides, scripts shell

Comandos sugeridos en AWS:

```bash
cd /opt || true
find / -type f \( -name '*.yml' -o -name '*.yaml' -o -name '.env' -o -name '*.sh' -o -name '*.py' \) 2>/dev/null \
  | xargs grep -nH 'CHATWOOT_API_TOKEN\|CHATWOOT_BASE_URL\|miwayki-bridge\|DIFY_API_KEY' 2>/dev/null
```

#### Paso B. Inspeccionar env real del contenedor

```bash
docker inspect miwayki-bridge --format '{{range .Config.Env}}{{println .}}{{end}}' | sort
```

Verificar explícitamente qué valor tiene `CHATWOOT_API_TOKEN` dentro de `.Config.Env`.

#### Paso C. Inspeccionar cómo se define `CHATWOOT_API_TOKEN` en `/app/app/main.py`

Buscar en la parte superior del archivo:

```bash
docker exec miwayki-bridge sh -lc 'nl -ba /app/app/main.py | sed -n "1,120p"'
```

Hay que confirmar una línea de este estilo:

```python
CHATWOOT_API_TOKEN = os.getenv("CHATWOOT_API_TOKEN", "")
```

Si eso existe, parchear el body del POST no basta: el valor correcto debe entrar por env o redefinirse explícitamente.

#### Paso D. Reemplazar el token en la fuente persistente, no solo en caliente

Probablemente habrá que actualizar algún `.env` o compose del proyecto y luego hacer:

```bash
./miwayki-compose.sh up -d --build bridge
```

o equivalente.

#### Paso E. Validar de extremo a extremo

1. enviar un mensaje desde el widget
2. ver logs del bridge
3. confirmar:

```text
DIFY_DEBUG status=200
CHATWOOT_SEND status=200
CHATWOOT_SEND_OK
```

4. comprobar que la respuesta del bot aparece en el widget de Chatwoot

---

## 11. Hipótesis técnica más probable

La hipótesis más probable es:

> **el bridge sigue usando un `CHATWOOT_API_TOKEN` viejo, invalidado o distinto del token nuevo mostrado en Settings > Profile de Chatwoot, porque ese valor está definido persistentemente en un `.env` / compose / script y no se ha reemplazado en la fuente que realmente se usa al recrear el contenedor.**

La segunda hipótesis más probable es:

> el token nuevo sí es correcto, pero el bridge está apuntando a otra instancia/base URL de Chatwoot distinta a la esperada; menos probable, porque el webhook sí entra y la infraestructura principal parece ser la misma.

La tercera hipótesis:

> el token compartido es de perfil pero la API endpoint usada por el bridge exige otro token/usuario/contexto distinto. Esto hay que verificar en la documentación de la versión concreta de Chatwoot desplegada, pero el error textual `Invalid Access Token` sugiere más bien token inválido directo.

---

## 12. URLs y puertos importantes

### Local Mac

- Fake site: `http://127.0.0.1:8080`
- Chatwoot via tunnel: `http://127.0.0.1:3000`
- Bridge via tunnel: `http://127.0.0.1:8000`
- Dify via tunnel: `http://127.0.0.1:9080`

### AWS internals relevantes

- Bridge health local al host remoto: `http://127.0.0.1:8000/health`
- Bridge Dify health: `http://127.0.0.1:8000/health/dify`
- Dify API base interna al contenedor: `http://api:5001/v1`
- Dify health interna: `http://api:5001/health`

---

## 13. Contenedores y redes observados

### Contenedores relevantes

- `miwayki-bridge`
- `dify-api-1`

### Redes observadas en `dify-api-1`

- `dify_default`
- `dify_ssrf_proxy_network`
- `miwayki-core-net`

Se conectó `dify-api-1` a `miwayki-core-net` con alias `api`, y eso fue importante para que el bridge resolviera `http://api:5001`.

---

## 14. Comandos útiles para reproducir y seguir el diagnóstico

### 14.1. Ver logs del bridge

```bash
ssh -i "$AWS_KEY" ubuntu@"$AWS_HOST" 'docker logs -f --since=2m miwayki-bridge'
```

### 14.2. Ver env del bridge

```bash
ssh -i "$AWS_KEY" ubuntu@"$AWS_HOST" 'docker inspect miwayki-bridge --format "{{range .Config.Env}}{{println .}}{{end}}" | sort'
```

### 14.3. Ver código del bridge dentro del contenedor

```bash
ssh -i "$AWS_KEY" ubuntu@"$AWS_HOST" 'docker exec miwayki-bridge sh -lc "nl -ba /app/app/main.py | sed -n \"1,220p\""'
```

### 14.4. Test directo a Dify desde dentro del bridge

```bash
ssh -i "$AWS_KEY" ubuntu@"$AWS_HOST" 'docker exec -i miwayki-bridge python - <<"PY"
import os, httpx, json
base = os.environ["DIFY_API_BASE"]
key = os.environ["DIFY_API_KEY"]
payload = {
    "inputs": {},
    "query": "diag-cursor-test",
    "response_mode": "blocking",
    "user": "chatwoot-diag"
}
r = httpx.post(
    f"{base}/chat-messages",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json=payload,
    timeout=60.0,
)
print("STATUS:", r.status_code)
print(r.text)
PY'
```

### 14.5. Test directo al health del bridge

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/health/dify
```

---

## 15. Estado final al cerrar este handoff

### Funciona

- túneles SSH
- fake site local en Mac
- bridge online
- conectividad bridge -> Dify
- Dify API key válida
- app Dify publicada
- Dify responde con `200`
- webhook Chatwoot entra al bridge
- debug logs agregados

### No funciona todavía

- bridge -> Chatwoot POST de respuesta del bot

### Error final vigente

```text
CHATWOOT_SEND status=401
CHATWOOT_SEND body={"error":"Invalid Access Token"}
```

---

## 16. Conclusión para Cursor

No reiniciar todo desde cero.

El estado actual ya descarta varios frentes:

- **no hay que volver a depurar la red hacia Dify** salvo que se destruya la topología
- **no hay que volver a depurar la publicación del workflow Dify**
- **no hay que volver a perseguir el problema inicial de `Workflow not published`**
- **no hay que volver a perseguir el problema inicial de `Dify Access token is invalid`**

El trabajo pendiente es **quirúrgico**:

1. encontrar dónde se inyecta realmente `CHATWOOT_API_TOKEN` al bridge,
2. reemplazarlo por `e4LgfcqwdD62dK7daJjssdmq` en la fuente persistente real,
3. recrear el bridge,
4. verificar que el POST de salida a Chatwoot ya devuelve `200`.

Si Cursor quiere ser eficiente, debe enfocarse en:

- env real del contenedor
- compose/.env/script fuente
- definición superior de `CHATWOOT_API_TOKEN` en `main.py`
- confirmación del `CHATWOOT_BASE_URL`

Nada más debería bloquear el piloto una vez corregido ese token.
