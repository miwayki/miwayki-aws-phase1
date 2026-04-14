# MIWAYKI.COM – Fase 2 (Motor Comercial Operativo)

**Nombre del proyecto:** Plataforma de captación, cualificación y gestión de leads con chat web + IA + handoff humano  
**Estado del documento:** Documento maestro de arquitectura y desarrollo (Fase 2)  
**Versión:** 2.0  
**Fecha:** 2026-04-14  
**Propietario:** miwayki.com  
**Uso previsto:** Guía técnica para el desarrollo de la Fase 2 en el entorno local, orientada al equipo de agentes de Antigravity para implementar las funcionalidades de negocio.  

## 0. Propósito del documento
Este documento describe con detalle la **Fase 2** del proyecto Miwayki.com, centrada en convertir el prototipo local (Fase 1) en un **motor comercial operativo** completo. A diferencia de la Fase 1, que validó el canal conversacional básico y la integración inicial, en esta fase implementaremos la lógica de negocio real en un entorno local. La Fase 2 integrará un catálogo editable (NocoDB), reglas de precios, gestión de estados comerciales y flujos de conversación avanzados mediante IA.  

## 1. Resumen ejecutivo
En la Fase 2 construiremos la capa comercial del chatbot de Miwayki con los siguientes componentes clave:

- **Canal conversacional (Chatwoot):** Sigue siendo el punto de entrada de mensajes, con etiquetas y notas privadas. El historial se almacena aquí y los agentes humanos pueden intervenir cuando sea necesario.  
- **Bridge (FastAPI):** Controla toda la **lógica de negocio**: aplica el motor de precios, gestiona estados comerciales, almacena la memoria del lead y decide cuándo escalar a un humano. Actúa como capa estratégica entre la IA y los datos del negocio.  
- **Dify (IA conversacional):** Asume el **flujo conversacional principal**. Detecta intenciones, extrae datos estructurados (destino, fechas, personas, presupuesto, etc.), responde preguntas frecuentes, maneja objeciones y realiza llamadas HTTP al Bridge para cotizar o actualizar información.  
- **Base de datos editable (NocoDB):** Un catálogo vivo con información de tours, rutas, temporadas, reglas de precio y cuentas bancarias. Administrado por supervisores, permite ajustar precios y promociones en tiempo real sin modificar el código.  

El resultado será un flujo de ventas automatizado donde el usuario consulta desde el chat, la IA recopila datos y cotiza en tiempo real, y el Bridge controla estados como `awaiting_payment` o `voucher_received`. El equipo de ventas solo intervendrá en casos excepcionales (ej. solicitudes complejas o confirmación final).

## 2. Arquitectura funcional
La arquitectura en Fase 2 se basa en cuatro componentes principales:

- **Chatwoot:** Desplegado localmente para administrar conversaciones. Permite etiquetar leads (p.ej. “Interesado”, “Enviado voucher”) y añadir notas privadas. El usuario inicia el chat web aquí.  
- **FastAPI Bridge:** Servidor que implementa:
  - *Motor de precios:* Calcula cotizaciones reales según destino, temporada, recargos y tipo de grupo.  
  - *Reglas de negocio:* Determina qué consultas se resuelven automáticamente y cuándo es necesario escalar a humano.  
  - *Máquina de estados:* Gestiona estados del lead (`new_inquiry`, `quoted`, `awaiting_payment`, `voucher_received`, `closed_won`/`lost`).  
  - *Memoria estructurada:* Guarda en base de datos los datos clave del lead (destino, fecha, personas, últimas cotizaciones, etc.).  
  - *APIs internas:* Endpoints REST como `/quote/calculate`, `/lead/update` y `/reservation/voucher` para ser invocados por Dify.  
- **Dify:** Motor de IA que:
  - *Intake conversacional:* Identifica el tipo de consulta (cotización, pago, voucher).  
  - *Extracción avanzada:* Obtiene nombre, correo, teléfono, destino, fechas, número de personas, presupuesto, tipo de grupo, urgencia.  
  - *Genera diálogo:* Formula preguntas para completar información faltante y responde a objeciones (“En temporada alta el precio sube debido a la demanda”).  
  - *Retrieval de información:* Busca datos del catálogo (itinerarios, FAQs, restricciones) para enriquecer respuestas.  
  - *Llamadas al Bridge:* Usa tool-calling HTTP para cotizar (`/quote/calculate`) o actualizar el lead (`/lead/update`).  
- **NocoDB (catálogo editable):** Base de datos con:
  - *Tours y variantes:* Lista de productos turísticos y opciones de ruta.  
  - *Temporadas y feriados:* Rangos de fechas con recargos definidos.  
  - *Reglas de precio:* Descuentos o recargos según grupo, temporada, promociones.  
  - *Cuentas bancarias:* Datos para pagos por transferencia.  
  - *Excepciones comerciales:* Casos puntuales o promociones especiales.  
  Supervisores pueden editar estos datos vía UI, impactando dinámicamente el motor de cotización y la información que presenta Dify.

Todo corre localmente (p.ej. Docker Compose en un equipo de desarrollo). No se utilizan recursos en la nube en esta fase.

## 3. Catálogo comercial vivo
Un catálogo editable es crítico para la Fase 2:

- **Herramienta:** NocoDB (preferido), desplegado en local. (Alternativa: Airtable con adaptador personalizado).  
- **Entidades:** *Tours* (productos), *Variantes/Rutas* dentro de cada tour, *Temporadas* (rango de fechas), *Reglas de feriado*, *Reglas de precios* (por pax, grupo, colegios), *Cuentas bancarias*, *Excepciones comerciales*.  
- **Acciones:** Los supervisores pueden modificar precios, activar/desactivar tours o promociones sin tocar código.  
- **Integración:** El Bridge accederá a esta base como fuente de verdad para precios y listados. Por ejemplo, el adaptador del Bridge hará consultas a NocoDB para obtener tarifas y reglas vigentes.

Este catálogo vivo asegura flexibilidad total: cualquier cambio necesario se hace en NocoDB y el sistema lo utiliza de inmediato.

## 4. Dify como asistente de venta
En esta fase, Dify amplía su rol:

- **Inicio inteligente:** Clasifica la intención inicial (p.ej. “consultar tour” vs “enviar voucher”).  
- **Recolección de datos:** Pregunta naturalmente por datos faltantes (e.g. “¿Cuándo planean viajar?” si no se mencionó fecha).  
- **Llamadas al Bridge:** Invoca endpoints como `/quote/calculate` para obtener el precio, `/lead/update` para guardar datos ingresados, o `/reservation/voucher` al recibir el comprobante.  
- **Respuestas enriquecidas:** Explica cotizaciones (“El precio total es $X”), proporciona detalles del tour, y maneja objeciones (“No incluimos vuelos, solo transporte terrestre”).  
- **Gestión del pago:** Si el usuario acepta la cotización, Dify solicita confirmación y luego muestra instrucciones de pago obtenidas desde el Bridge.  
- **Confirmación de voucher:** Al detectar el envío del comprobante, informa al usuario (“Voucher recibido, procesaremos su reserva”) y llama al Bridge.  
- **Uso de retrieval:** Integra información del catálogo (por ejemplo, itinerarios o inclusiones del tour) al conversar.

Con Dify como asistente activo, la conversación fluye de forma automatizada; el humano solo participa si el Bridge lo marca.

## 5. FastAPI Bridge: reglas comerciales
El **Bridge** es el núcleo del negocio:

- **Cotización en vivo:** Calcula el precio final del tour usando:
  - Tarifa base del tour y variante.  
  - Recargos por temporada y feriados.  
  - Ajustes por tamaño de grupo (descuentos por colecciones o recargos por grupos grandes).  
  - Datos actualizados desde NocoDB.  
- **Máquina de estados:** Controla los estados del lead:
  - `new_inquiry`: Lead nuevo sin cotizar.  
  - `quoted`: Se presentó cotización al usuario.  
  - `awaiting_payment`: Usuario aceptó y debe pagar.  
  - `voucher_received`: Se recibió comprobante de pago.  
  - `closed_won`/`closed_lost`: Reservas completadas o cerradas sin venta.  
- **Señales de escalamiento:** Evalúa condiciones para `handoff_required` y aplica etiquetas en Chatwoot si:
  - El grupo excede un umbral configurado.  
  - La ruta/fecha no figura en el catálogo.  
  - El usuario solicita un pago (Stripe) no soportado.  
- **Memoria estructurada:** Guarda la información crucial del lead en base de datos (destino, fechas, presupuesto, últimas cotizaciones, etc.) para facilitar diálogos posteriores.  
- **APIs internas:** Endpoints disponibles para Dify y clientes:
  - `POST /quote/calculate`: genera una cotización según datos ingresados.  
  - `POST /lead/upsert`: crea o actualiza el registro del lead.  
  - `POST /reservation/payment-instructions`: devuelve datos para pago por transferencia.  
  - `POST /reservation/voucher`: registra el voucher del usuario.  
  - `GET /catalog/tours`: devuelve tours y variantes disponibles.  
- **Integración con catálogo:** Consulta NocoDB en tiempo real para obtener precios y reglas efectivas.  
- **Handoffs:** Cuando se activa un caso especial, el Bridge:
  - Cambia el estado a `hand off`.  
  - Etiqueta el chat en Chatwoot (“Atención: Handoff”).  
  - (Opcional) Notifica internamente al equipo de ventas.

Este servicio FastAPI se desplegará localmente con logging detallado para cada transacción (cotizaciones, actualizaciones de lead, etc.).

## 6. Flujo de venta
El proceso de venta en Fase 2 consiste en:

1. **Solicitud inicial:** El usuario inicia chat con una consulta sobre un tour.  
2. **Recopilación de datos:** Dify reúne la información necesaria (destino deseado, fechas, número de viajeros, tipo de grupo). El Bridge crea el lead (`new_inquiry`).  
3. **Cotización:** Una vez recogida la información mínima, Dify llama a `/quote/calculate`. El Bridge devuelve el precio final. Dify lo comunica al usuario y cambia estado a `quoted`.  
4. **Aceptación:** Si el usuario confirma, Dify solicita proceder al pago. Llama a `/reservation/payment-instructions` para obtener cuenta bancaria y monto, cambiando estado a `awaiting_payment`. El usuario recibe instrucciones de depósito.  
5. **Voucher:** El usuario envía el comprobante por el chat. Dify informa al Bridge con `/reservation/voucher`, que cambia el estado a `voucher_received`.  
6. **Cierre final:** Un agente humano revisa el voucher. Según la validación, actualiza el estado a `closed_won` o `closed_lost` en el sistema.  

En caso de excepciones (grupo grande, ruta no reconocida, etc.), el Bridge activa un **handoff**, y Dify notifica que un agente tomará el caso. Todas las transiciones se prueban exhaustivamente en local.

## 7. Colaboración humano-IA
La interacción preserva el contexto entre IA y humanos:

- **Notas y etiquetas en Chatwoot:** Al escalar, se deja una nota privada con el resumen y se etiquetan las conversaciones con palabras clave relevantes.  
- **Atributos del contacto:** El Bridge puede actualizar campos personalizados del lead en Chatwoot (destino, personas, presupuesto) para facilitar la vista del agente.  
- **Retroalimentación humana:** El agente puede cambiar manualmente el estado del lead (p.ej. a `closed_won`) y registrar observaciones. El Bridge monitorea estos cambios para informes posteriores.  

Así, la experiencia de venta es continua, sin repreguntas innecesarias, y el humano ve todo lo capturado por la IA.

## 8. Handoffs críticos
Se derivará siempre a humano si:

- El grupo supera el límite establecido.  
- La reserva es para una escuela/grupo grande.  
- La ruta o fecha no existe en el catálogo.  
- No hay regla clara para cotizar.  
- Se intenta usar un método de pago no automatizado (Stripe).  

En cada caso, el Bridge marcará `handoff_required`, etiquetará el chat (“Handoff”), y Dify informará que un agente lo contactará. Esto garantiza atención humana cuando la automatización no puede resolverlo completamente.

## 9. Exclusiones de la Fase 2
Para mantener el foco, **no se implementa** en esta fase:

- **Marketing o campañas:** Nada de Mautic ni envíos automáticos (eso queda para Fase 3).  
- **RAG en pricing:** No se usarán modelos de recuperación para calcular precios; se seguirán reglas explícitas.  
- **Despliegue en nube:** Todo es local. No se usa AWS.  
- **Pagos automáticos:** No integración con Stripe. El pago es manual por transferencia.  
- **Orquestadores extras:** No se agrega n8n u otro workflow de terceros; el Bridge es el coordinador único.

Este enfoque simplifica el alcance a la funcionalidad esencial de ventas.

## 10. Plan de implementación
Se implementará en etapas secuenciales:

1. **Catálogo viviente:** Definir tablas en NocoDB y poblar datos iniciales.  
2. **Adaptador de catálogo:** Conectar el Bridge a NocoDB (p.ej. mediante la API) y probar lectura de tours/reglas.  
3. **Cotizador básico:** Implementar `POST /quote/calculate` en el Bridge con reglas simples y probar con ejemplos.  
4. **Integración Dify:** Extender flujos de IA para llamar al Bridge y procesar respuestas. Validar diálogo completo de cotización.  
5. **Lógica de pago:** Agregar `/reservation/payment-instructions` y enseñar a Dify a guiar al usuario en el pago.  
6. **Manejo de voucher:** Implementar `/reservation/voucher` y probar la transición a `voucher_received`.  
7. **Máquina de estados:** Configurar la persistencia de estados en la base de datos y verificar las transiciones `quoted → awaiting_payment → voucher_received → closed_won`.  
8. **Handoffs:** Definir reglas en el Bridge y probar escalados correctos con etiquetas visibles.  

Cada fase tendrá pruebas unitarias e integración. El código se gestionará con control de versiones y despliegue local automatizado (por ejemplo, Docker Compose rebuild).

## 11. Conclusiones
Al finalizar la Fase 2, contaremos con un chatbot que cotiza tours en tiempo real y gestiona reservas locales. Esto valida el modelo de negocio antes de avanzar a marketing y despliegue a escala. La Fase 3 se enfocará en campañas automatizadas (Mautic) y preparación de la infraestructura en la nube. La Fase 2 garantiza que la lógica central de ventas funciona antes de escalar.