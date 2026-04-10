# Fake site local para pruebas Chatwoot

## Objetivo

Probar el widget de Chatwoot y el flujo de integración sin tocar producción.

## Levantar servidor local (macOS host)

Desde la raíz del proyecto:

```bash
python3 -m http.server 8080 --directory chatwoot_fake_site
```

Luego abre:

```text
http://127.0.0.1:8080
```

## Requisitos previos

- Chatwoot corriendo en `http://127.0.0.1:3000`
- Inbox web creado con token válido

## Nota

Cuando migremos a AWS, se reemplaza `baseUrl` por el dominio real de Chatwoot
y se usa el token del inbox de ese entorno.
