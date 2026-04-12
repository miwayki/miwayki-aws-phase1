# Runbook: Operaciones Locales (Fase Básica)

Este documento describe los procedimientos estrictamente validados para operar y verificar el stack MiWayki en el entorno local (macOS + Lima VM).

## 1. Ciclo de Rebuild y Verificación del Bridge

Cada vez que se modifica el código en `bridge/app/main.py`, se debe reconstruir el contenedor desde la Mac usando el daemon de la VM:

```bash
# Rebuild del bridge desde la Mac (usando limactl)
limactl shell miwayki-linux -- bash -lc 'cd /Users/armandosilva/DATA/SMC/CS_79C_cloud/Final_Project && ./miwayki-compose.sh up -d --build bridge'

# Esperar a que el servicio responda
until curl -fsS http://127.0.0.1:8000/health; do sleep 2; done

# Verificar versión y salud
curl -sS http://127.0.0.1:8000/health | jq .
# Target: bridge_build: "0.10-private-note-context"
```

## 2. Arranque del Sitio Fake (Widget)

El sitio de prueba debe servirse por separado. **Nota Operativa:** Puede ser necesario reiniciar este servidor si hay cambios en el widget o tras ciclos de limpieza del stack.

```bash
cd /Users/armandosilva/DATA/SMC/CS_79C_cloud/Final_Project/chatwoot_fake_site
python3 -m http.server 8080
```
Acceso: `http://127.0.0.1:8080`

## 3. Secuencia de Validación E2E (Estado Final v0.10)

Para confirmar el flujo completo y la persistencia:

1.  **Validación de Atributos y Etiquetas:**
    ```bash
    # Sustituir $TOKEN con el valor real de .env.bridge
    curl -sS -H "api_access_token: $TOKEN" \
      "http://127.0.0.1:3000/api/v1/accounts/1/conversations/3" | jq .custom_attributes

    curl -sS -H "api_access_token: $TOKEN" \
      "http://127.0.0.1:3000/api/v1/accounts/1/conversations/3" | jq .labels
    ```

2.  **Validación de Contacto:**
    ```bash
    curl -sS -H "api_access_token: $TOKEN" \
      "http://127.0.0.1:3000/api/v1/accounts/1/contacts/3" \
      | jq '.payload | {name: .name, email: .email, phone_number: .phone_number, custom_attributes: .custom_attributes}'
    ```

3.  **Flujo de Nota Privada (Contexto):**
    - En Chatwoot, añadir nota: *"El cliente busca Cusco para mayo"*.
    - En el widget, enviar: *"¿Qué opciones tienes?"*.
    - **Resultado esperado:** La IA responde mencionando el contexto de la nota.
    - **Consumo:** Verificar que `pending_seller_feedback` sea `null` tras la respuesta.
