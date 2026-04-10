#!/usr/bin/env bash
# Sincroniza vendor/dify/docker -> /var/opt/miwayki-dify en la VM Lima (disco escribible).
# Uso: ./scripts/rsync-dify-docker-to-vm.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
limactl shell miwayki-linux -- bash -lc "sudo mkdir -p /var/opt/miwayki-dify && sudo rsync -a '${ROOT}/vendor/dify/docker/' /var/opt/miwayki-dify/ && sudo chown -R \"\$(whoami)\" /var/opt/miwayki-dify"
echo "OK: /var/opt/miwayki-dify sincronizado desde ${ROOT}/vendor/dify/docker/"
