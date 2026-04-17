#!/usr/bin/env bash
# Ejecuta docker compose como si estuvieras en compose/ con los tres -f.
# Uso desde la raíz del repo: ./miwayki-compose.sh up -d --build bridge
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

if ! docker info >/dev/null 2>&1; then
  cat >&2 <<'EOF'
[miwayki-compose] ERROR: en ESTA máquina el cliente `docker` no habla con ningún daemon (docker info falla).

Sin Docker local activo aquí no puedes hacer --build desde esta shell.

Si "curl http://127.0.0.1:8000/health" devuelve JSON pero solo {"status":"ok"} (sin bridge_build):
  - En muchos setups con Lima, el puerto 8000 lo reenvía limactl → el bridge corre DENTRO de la VM.
  - Comprueba en la Mac:  lsof -nP -iTCP:8000 -sTCP:LISTEN
    Si ves "limactl", abre shell en la VM y ejecuta este mismo script ALLÍ (donde está el repo y docker compose):
      limactl shell <nombre-vm>
      cd …/Final_Project && ./miwayki-compose.sh up -d --build bridge

Si el stack lo corres con Docker solo en la Mac (sin Lima en 8000):
  - Arranca el daemon que uses (p. ej. Docker Desktop) hasta que  docker info  funcione, y vuelve a ejecutar ./miwayki-compose.sh

Tras un build correcto (puerto host = BRIDGE_HOST_PORT en compose/.env, por defecto 8000):
  curl -sS http://127.0.0.1:8000/health
  Debe incluir "bridge_build" (p. ej. "0.4-minimal-default").
EOF
  exit 1
fi

cd "$ROOT/compose"
exec docker compose \
  -f docker-compose.yml \
  -f docker-compose.chatwoot.yml \
  -f docker-compose.bridge.yml \
  -f docker-compose.nocodb.yml \
  -f docker-compose.langflow.yml \
  -f docker-compose.fakesite.yml \
  "$@"
