# Langflow — Guía Editorial para Markdown (Operación Nivel 1)

**Proyecto:** MiWayki  
**Fase:** Fase 2 v2 (Desacople Documental)  
**Propósito:** Explicar cómo Marketing debe actualizar itinerarios y FAQs sin tocar el canvas crítico orientando las iteraciones hacia Langflow.

---

## 1. Contexto

En Fase 2.0 determinamos que:
* **NocoDB:** Almacena reglas estrictas (fechas, booleanos, identificadores, precios, cupos).
* **Langflow:** Orquesta la conversación, y además procesa datos narrativos no estructurados extraídos de archivos `.md` de itinerario/FAQ. Todo desde Markdown y sin cálculos extraños.

## 2. Flujo Editorial

Cuando el equipo de producto cambia un itinerario, la temporada climática o las inclusiones, el equipo de UX/Copy debe realizar lo siguiente:

### Pasos Generales:
1. **Verificar que en NocoDB `(tabla: tours)`** el tour tiene el mismo `slug` que el archivo de Markdown a subir (Ej. `cusco-clasico-premium`). No mezclar Nombres Cortos con URLs limpias.
2. **Generar Archivo de Markdown:**
   Cree o edite el archivo utilizando la [plantilla oficial documentada en `fase2localv2.md`](fase2localv2.md) asegurándose de añadir el Metadato Superior.
3. **Subida en Langflow (UI):**
   * Vaya al Dashboard Principal de su Langflow.
   * Acceda al bloque global o "Componentes/Flows de Ingestión Documental de Knowledge Base" (`Flow 2` según arquitectura).
   * Adjunte el/los `.md` generados en el Data Loader o Vector Store.
   * **Ejecute el nodo extractor/vectorizador.**

### Lo que NUNCA debe hacer Marketing:

* 🚫 Borrar el `session_id` del Chat API node.
* 🚫 Tocar la lógica HTTP en los nodos: `/quote/calculate`, `/lead/upsert`.
* 🚫 Hardcodear el precio real del ticket en los Markdown – porque esto causará choques contra el cálculo en Vivo (Bridge > NocoDB).

## 3. Ejemplos de uso del Markdown de Itinerario:

Si el usuario dice:  _"¿Qué llevo en el Día 2?"_  
El Bridge lo detecta como intención semántica -> Langflow lo abstrae buscando en Vector Store (My Files/Chroma).  
El resultado proviene netamente de sus subidas de Markdown. El Bridge no lee FAQs, sólo valida el negocio.

### Reingestas Automáticas (Nota técnica):
En Fase 2 local, la ingesta puede ser manual a través de la UI de flow, no por API de la infraestructura local aún, salvo que configuren un webhook adicional.
