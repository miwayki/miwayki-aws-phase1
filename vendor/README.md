# Vendor (terceros)

## Dify (`vendor/dify/`)

No se versiona en Git (es el repo completo de LangGenius, ~145MB+ de fuente).

Tras clonar **este** proyecto:

```bash
git clone --depth 1 https://github.com/langgenius/dify.git vendor/dify
```

La extensión de red Miwayki vive en **`compose/dify-docker-compose.miwayki.yml`**: cópiala al directorio desde el que levantas Dify (p. ej. `/var/opt/miwayki-dify/`) y úsala como segundo `-f` en `docker compose`. Detalle en `compose/README.md` §8.
