# MIWAYKI.COM - DOCUMENTO MAESTRO DEL PROYECTO

**Nombre del proyecto:** Plataforma de captacion, cualificacion y seguimiento de leads con chat web + IA + handoff humano  
**Estado del documento:** Aprobado como documento maestro de arquitectura y desarrollo  
**Version:** 1.0  
**Fecha:** 2026-04-05  
**Propietario:** miwayki.com  
**Uso previsto:** Documento raiz para Cursor, desarrollo tecnico, decisiones de arquitectura, operacion DevOps, incorporacion de nuevos miembros y control de cambios.

---

## 0. Proposito del documento

Este archivo es la fuente principal de verdad del proyecto. Su objetivo es dejar definido, de forma profesional, modular y ejecutable, **que se va a construir, por que se va a construir, como se va a construir, con que componentes, bajo que reglas operativas y con que criterios de calidad**.

Este documento existe para evitar los problemas clasicos de los proyectos que empiezan rapido y luego se vuelven dificiles de mantener:

- decisiones tecnicas tomadas sin contexto;
- contradicciones entre lo que se habla y lo que se implementa;
- dependencias ocultas en servicios o proveedores;
- falta de modularidad;
- ausencia de normas DevOps;
- perdida de trazabilidad durante el desarrollo con IA asistida en Cursor.

A partir de este momento, cualquier desarrollo del repositorio debe respetar este documento. Si una decision arquitectonica cambia, primero se actualiza este archivo y luego se cambia el codigo.

---

## 1. Resumen ejecutivo

### 1.1 Que se va a construir

Se va a construir una plataforma propia de captacion y pre-cierre comercial para **miwayki.com**, basada en un **widget de chat web**, una **bandeja de conversacion para vendedores** y un **motor de IA con memoria por cliente**.

El flujo objetivo es el siguiente:

1. Un visitante entra a miwayki.com.
2. El visitante inicia una conversacion en el chat web.
3. La IA atiende la conversacion en tiempo real.
4. La IA solicita y captura datos de contacto como telefono y correo.
5. La IA califica la intencion de compra y calcula una temperatura del lead.
6. El vendedor humano ve la conversacion en Chatwoot con indicadores visuales.
7. Si el lead esta caliente, el vendedor toma el control dentro del mismo hilo.
8. Si el lead abandona el sitio, ya quedan retenidos los datos y el contexto.
9. Si el vendedor conversa por telefono o WhatsApp manual y agrega notas internas, esa informacion se reincorpora a la memoria del lead.
10. En una fase posterior, el sistema envia correos personalizados a leads frios o sin seguimiento, usando Mautic.

### 1.2 Resultado de negocio esperado

El sistema reemplaza la dependencia del WhatsApp Business gratuito como punto central de captacion, reduce el riesgo de bloqueos por Meta, mejora la velocidad de respuesta y ordena el trabajo comercial con prioridad visual sobre los leads mas prometedores.

### 1.3 Decision de arquitectura aprobada

La arquitectura aprobada para el MVP y la primera version productiva es:

- **Chatwoot** como widget e inbox de vendedores.
- **Servicio puente propio en FastAPI** como integrador y capa de reglas de negocio.
- **Orquestador de IA desacoplado por adaptador**.
- **PostgreSQL** como base de datos principal.
- **Redis** como cache y cola liviana.
- **Mautic** como modulo de seguimiento por email en fase posterior.
- **Despliegue principal en una EC2 fija** con Docker Compose para el core de aplicacion.

### 1.4 Correcciones importantes respecto al borrador original

El borrador previo fue util, pero tenia varios puntos que debian corregirse para que el proyecto quede tecnicamente consistente:

1. **EC2 t3.large no queda aprobada como tamano productivo base.** Es valida para desarrollo, staging o un MVP muy recortado, pero no es el tamano recomendado para el stack completo en produccion.
2. **El proyecto no debe quedar acoplado rigidamente a Dify.** Dify puede usarse para una implementacion inicial por rapidez, pero el sistema debe programarse con una interfaz de adaptador para poder reemplazarlo por Langflow u otro orquestador si cambia la decision de licenciamiento o de operacion.
3. **La capa de modelo de IA no debe quedar incrustada en la logica del sistema.** Debe ser intercambiable: self-hosted OSS LLM o proveedor externo si la empresa decide permitirlo.
4. **Mautic no entra en la primera entrega obligatoria del MVP.** Queda preparado como modulo fase 2.
5. **No se aprueba una arquitectura innecesariamente distribuida con ECS Express, Fargate o ALB para el MVP.** El core del sistema arrancara con EC2 fija por costo/eficiencia operativa.

---

## 2. Contexto del negocio

### 2.1 Situacion actual

miwayki.com recibe trafico alto y variable. La operacion historica ha redirigido leads a un numero de WhatsApp Business gratuito, donde el equipo comercial responde y cierra ventas manualmente.

Ese modelo tiene problemas estructurales:

- depende de la tolerancia de Meta a patrones de alto volumen;
- concentra demasiados leads en un canal no disenado para ese volumen sin API oficial;
- genera riesgo alto de bloqueo del numero;
- no deja una clasificacion automatica del lead;
- no ofrece contexto estructurado reutilizable;
- dificulta hacer seguimiento profesional y trazable.

### 2.2 Naturaleza del negocio

La operacion esta ligada al turismo. Eso implica:

- estacionalidad;
- picos por feriados, vacaciones y temporadas altas;
- variaciones mensuales fuertes;
- necesidad de reaccion rapida ante leads calientes;
- importancia de capturar contexto, fechas, destinos, numero de pasajeros, urgencia y presupuesto.

### 2.3 Datos operativos suministrados por el cliente

Con base en los datos y capturas compartidos en esta conversacion, se asumen como referencia operativa interna los siguientes patrones:

- una captura de analitica muestra **566K active users** y **562K new users** en el periodo visualizado;
- una captura de Google Ads muestra **4.04M impresiones**, **364K clicks**, **70.3K conversiones** y **$23.3K de costo** para el periodo exportado;
- el export CSV adjunto muestra que hubo trimestres con conversiones significativamente mas altas que la base promedio, lo cual confirma estacionalidad y picos;
- tambien se observa comportamiento por franja horaria y por dia de semana, lo cual sugiere que el sistema debe estar listo para soportar dias tranquilos y dias con burst relevante.

**Interpretacion de negocio aprobada:** el sistema debe construirse para un flujo normal de decenas de conversaciones diarias, con capacidad de absorber picos de varias veces la base sin rediseño estructural del core.

---

## 3. Problema a resolver

### 3.1 Problema principal

El negocio necesita una forma **propia, controlada, abierta y escalable** de conversar con leads desde la web, sin depender de WhatsApp gratuito como punto de entrada.

### 3.2 Problemas secundarios

1. No existe una memoria central bien estructurada por lead.
2. No existe una puntuacion objetiva y visible de calor comercial.
3. El vendedor no sabe rapidamente en que conversaciones conviene entrar.
4. Si el lead abandona el sitio, se pierde parte del valor de la interaccion.
5. No hay un documento tecnico maestro para coordinar desarrollo, despliegue y evolucion.

---

## 4. Objetivos del proyecto

### 4.1 Objetivos de negocio

- eliminar la dependencia de WhatsApp Business gratuito como mecanismo de captacion;
- aumentar la tasa de atencion y orden comercial;
- priorizar mejor los leads con mayor probabilidad de cierre;
- retener datos y contexto aunque el lead abandone el sitio;
- habilitar seguimiento automatizado posterior.

### 4.2 Objetivos tecnicos

- construir una arquitectura modular y desacoplada;
- usar software open source real para el core del sistema;
- permitir despliegue y operacion en AWS con control total del equipo DevOps;
- soportar picos estacionales sin rehacer la aplicacion;
- dejar una base solida para evolucionar hacia HA, colas, RAG o multi-servidor;
- permitir que Cursor use este documento como contexto raiz durante todo el desarrollo.

### 4.3 Objetivos DevOps

- versionar arquitectura, codigo y despliegue;
- separar configuracion por entorno;
- automatizar backups y restauracion;
- tener logs, metricas y alertas desde el dia uno;
- minimizar trabajo manual repetitivo;
- documentar interfaces internas y reglas de negocio.

---

## 5. Alcance del MVP

### 5.1 Incluido en el MVP

- widget web de chat embebido en miwayki.com mediante Chatwoot;
- inbox de vendedores en Chatwoot;
- servicio puente FastAPI entre Chatwoot y el orquestador de IA;
- agente IA con memoria por lead;
- captura de nombre, email y telefono dentro de la conversacion;
- scoring del lead en categorias frio, tibio, caliente y score numerico;
- actualizacion de atributos personalizados en Chatwoot;
- handoff manual al vendedor dentro del mismo hilo;
- base de datos PostgreSQL;
- Redis para cache y tareas ligeras;
- despliegue en una EC2 fija con Docker Compose;
- backups, logs y monitoreo basico;
- documentacion base del repositorio.

### 5.2 Fuera del MVP pero previstos

- Mautic operativo con flujos completos de email;
- RAG sobre catalogos o documentos de viajes;
- paneles BI y dashboards avanzados;
- modelos locales sobre GPU dedicadas;
- despliegue multi-AZ o alta disponibilidad;
- integracion CRM externa;
- multi-idioma avanzado;
- automatizaciones de remarketing complejas.

---

## 6. Restricciones y principios no negociables

### 6.1 Restricciones del negocio

- no usar n8n;
- evitar soluciones con limites ocultos tipo trial o freemium que fuercen pago por conversaciones;
- el equipo debe tener soberania operativa sobre la infraestructura;
- el sistema debe poder refactorizarse sin depender de un proveedor cerrado;
- la base del proyecto debe ser entendible por un equipo DevOps pequeno.

### 6.2 Principios de arquitectura

1. **Modularidad antes que comodidad visual.**
2. **Adaptadores antes que acoplamiento directo.**
3. **Simplicidad operacional en el MVP.**
4. **Persistencia clara por lead.**
5. **Datos del negocio visibles en Chatwoot.**
6. **Capacidad de reemplazar componentes sin reescribir todo el sistema.**
7. **Documentacion primero, codigo despues, cambio controlado siempre.**

---

## 7. Decisiones de arquitectura

### 7.1 Decision A: usar Chatwoot como front conversacional e inbox

**Aprobado.**

**Por que:**

- resuelve el widget web;
- resuelve el inbox humano;
- tiene webhooks, API y Agent Bots;
- permite custom attributes y notas privadas;
- da continuidad del hilo entre bot y vendedor.

### 7.2 Decision B: usar un servicio puente propio

**Aprobado.**

**Por que:**

- evita acoplar Chatwoot directamente al orquestador;
- centraliza reglas del negocio;
- permite traducir eventos de Chatwoot a contratos internos estables;
- permite cambiar el orquestador de IA sin tocar Chatwoot;
- permite validar firmas, normalizar datos, aplicar scoring, deduplicar eventos y gestionar errores.

### 7.3 Decision C: usar adaptador de orquestador y adaptador de modelo

**Aprobado.**

El proyecto no quedara acoplado a una sola herramienta de IA.

Se definiran dos interfaces internas:

- `OrchestratorAdapter`
- `ModelProviderAdapter`

Con esto, la implementacion inicial puede ser Dify o Langflow, y el modelo puede ser OSS self-hosted o un proveedor gestionado, sin reescribir la logica del puente ni la integracion con Chatwoot.

### 7.4 Decision D: usar EC2 fija para el core

**Aprobado.**

Se descarta Fargate/Express como plataforma principal del MVP por costo base adicional y por no aportar suficiente valor en esta fase.

### 7.5 Decision E: no aprobar t3.large como tamano productivo base

**Aprobado.**

`EC2 t3.large` queda clasificada asi:

- valida para laboratorio;
- valida para pruebas internas;
- valida para un MVP recortado y con trafico controlado;
- **no aprobada como tamano base de produccion**.

El tamano base de referencia para el core sera:

- **x86:** `t3.xlarge` o `t3a.xlarge`;
- **ARM / Graviton:** `m7g.xlarge` como opcion preferente si se valida compatibilidad.

### 7.6 Decision F: Mautic entra en fase 2

**Aprobado.**

Se prepararan interfaces y modelos de datos desde el inicio, pero no se obliga su despliegue en la primera liberacion.

---

## 8. Evaluacion de infraestructura aprobada

### 8.1 Por que no se aprueba t3.large como base

Aunque una t3.large parece atractiva por precio, presenta varias limitaciones:

- 2 vCPU y 8 GiB de RAM son insuficientes como margen sano para Chatwoot, bridge, orquestador de IA, Nginx, PostgreSQL, Redis y procesos auxiliares;
- la familia T es burstable y se gobierna por creditos CPU;
- en picos o procesos sostenidos, puede haber degradacion o cargos adicionales por uso prolongado por encima del baseline;
- deja muy poco margen para troubleshooting, logs, workers, actualizaciones o crecimientos de trafico.

### 8.2 Perfil de despliegue aprobado para produccion inicial

#### Perfil recomendado x86

- 1 EC2 `t3.xlarge` o `t3a.xlarge`
- 4 vCPU
- 16 GiB RAM
- 150 GB gp3
- Docker + Docker Compose
- Ubuntu 22.04 LTS o Amazon Linux 2023

#### Perfil recomendado ARM

- 1 EC2 `m7g.xlarge`
- 4 vCPU
- 16 GiB RAM
- 150 GB gp3
- solo si imagenes, dependencias y plugins se validan en ARM64

### 8.3 Perfil economico de desarrollo

- 1 EC2 `t3.large`
- entornos: dev, qa o staging reducido
- no usar como base definitiva del productivo si se despliegan todos los modulos.

### 8.4 Servicios que viviran en la EC2 principal

- Nginx
- Chatwoot web
- Chatwoot worker
- FastAPI bridge
- PostgreSQL
- Redis
- observabilidad basica
- opcion de orquestador IA si el consumo real lo permite

### 8.5 Servicios que pueden quedar fuera de la EC2 principal

Segun evolucion del proyecto, estos componentes podran externalizarse:

- Mautic
- orquestador IA
- endpoint de LLM local
- almacenamiento de adjuntos
- sistema de colas

---

## 9. Arquitectura logica del sistema

```text
[Cliente en miwayki.com]
        |
        v
[Widget Chatwoot]
        |
        v  (webhook / event)
[FastAPI Bridge]
        |
        +------------------------------+
        |                              |
        v                              v
[Orchestrator Adapter]          [Chatwoot API Adapter]
        |
        v
[Orquestador IA: Dify o Langflow]
        |
        v
[Model Provider Adapter]
        |
        +------------------------------+
        |                              |
        v                              v
[LLM self-hosted OSS]          [Proveedor gestionado opcional]

[PERSISTENCIA]
- PostgreSQL
- Redis

[FASE 2]
- Mautic Adapter
- Email follow-up workflows
```

### 9.1 Descripcion de capas

#### Capa 1: Interaccion cliente

El usuario interactua con el widget de Chatwoot desde el navegador.

#### Capa 2: Entrada de eventos

Chatwoot genera eventos y webhooks hacia el bridge.

#### Capa 3: Reglas del negocio

El bridge valida, normaliza, enruta, gestiona sesiones, aplica scoring y sincroniza atributos.

#### Capa 4: Orquestacion IA

Un orquestador genera respuesta, mantiene memoria y produce salida estructurada.

#### Capa 5: Persistencia

El estado del sistema y del lead se conserva en PostgreSQL y Redis.

#### Capa 6: Operacion comercial

Los vendedores ven la conversacion en Chatwoot, reciben contexto y toman control cuando corresponde.

---

## 10. Componentes detallados

## 10.1 Chatwoot

### Responsabilidades

- servir el widget de chat;
- recibir mensajes del cliente;
- mantener el historial conversacional visible al vendedor;
- emitir eventos al bridge;
- mostrar atributos personalizados de negocio;
- permitir notas privadas internas;
- servir como punto de handoff de bot a humano.

### Datos importantes dentro de Chatwoot

- `conversation_id`
- `contact_id`
- inbox
- estado de la conversacion
- etiquetas
- atributos personalizados
- notas privadas

### Reglas operativas

- toda conversacion nueva debe quedar asociada a un inbox de sitio web;
- todo inbox automatizado debe estar conectado a un Agent Bot cuyo `outgoing_url` apunte al bridge;
- las resoluciones manuales deben requerir atributos minimos definidos por negocio;
- los vendedores no deben editar arbitrariamente atributos estructurados calculados por IA sin dejar nota.

## 10.2 FastAPI Bridge

### Responsabilidades

- recibir webhooks de Chatwoot;
- validar firmas y origen;
- prevenir loops;
- traducir `conversation_id` a `session_id` interno;
- invocar el orquestador;
- normalizar la salida de la IA;
- actualizar Chatwoot con mensaje, etiquetas y custom attributes;
- registrar eventos tecnicos y funcionales;
- aplicar reintentos controlados;
- desacoplar el negocio de cualquier herramienta concreta.

### Este componente es estrategico

El bridge es el verdadero corazon de la arquitectura. Si el proyecto evoluciona y cambia el orquestador, el bridge permanece como pieza estable.

### Modulos internos del bridge

- `webhook_ingress`
- `signature_validation`
- `event_router`
- `chatwoot_adapter`
- `orchestrator_adapter`
- `lead_scoring_policy`
- `contact_extraction`
- `audit_logger`
- `retry_policy`
- `mautic_adapter` (fase 2)

## 10.3 Orquestador IA

### Opcion A: Dify

Ventajas:

- rapido de montar;
- UI util para prototipado;
- workflows y herramientas;
- buena comunidad y actividad.

Riesgos:

- no usa licencia MIT pura;
- la licencia del repositorio tiene condiciones adicionales;
- por eso **no debe acoplarse el sistema a Dify directamente**.

### Opcion B: Langflow

Ventajas:

- licencia MIT;
- orientado a pipelines y componentes;
- adecuado si se prioriza pureza de licenciamiento y desacoplamiento.

Desventajas:

- puede requerir mas trabajo de montaje funcional para casos muy concretos.

### Decision aprobada

El codigo del proyecto debe permitir **cualquiera de las dos opciones**. La primera implementacion puede salir con una de ellas, pero el contrato interno sera propio.

## 10.4 Model Provider Adapter

### Responsabilidades

- recibir el prompt final y el contexto estructurado;
- invocar el backend de modelo;
- devolver una salida normalizada;
- registrar uso y latencia;
- separar el sistema de cualquier backend puntual.

### Backends previstos


- `aws bedrock`
- `other_provider_optional`

### Politica aprobada

El sistema se desarrolla para ser compatible con modelo open source self-hosted. Si la empresa decide usar un proveedor gestionado por costo o tiempo, sera una configuracion, no una dependencia estructural.

## 10.5 PostgreSQL

### Uso en el MVP

- almacenamiento principal de metadatos de integracion;
- tablas de mapeo de sesiones;
- auditoria del bridge;
- estado funcional del sistema;
- datos del orquestador si aplica.

### Principios

- una sola instancia/logical cluster en el MVP;
- bases o esquemas separados por servicio;
- backups diarios;
- restauracion probada;
- no exponer el puerto al exterior.

## 10.6 Redis

### Uso en el MVP

- cache temporal;
- locks ligeros;
- tareas de fondo sencillas;
- rate limiting interno si se necesita.

## 10.7 Mautic

### Rol en fase 2

- automatizar correos de seguimiento;
- almacenar leads para campañas;
- disparar nurtures a leads tibios y frios;
- recibir contexto resumido desde el bridge.

---

## 11. Flujo funcional aprobado

### 11.1 Flujo de atencion principal

1. El visitante abre el widget.
2. Escribe un mensaje.
3. Chatwoot registra la conversacion y envia el evento al bridge.
4. El bridge valida firma y tipo de evento.
5. El bridge determina si debe responder la IA o un humano.
6. Si responde la IA:
   - recupera la sesion;
   - compone el contexto;
   - llama al orquestador;
   - recibe texto y salida estructurada.
7. El bridge publica la respuesta en Chatwoot.
8. El bridge actualiza atributos personalizados.
9. Si el score supera el umbral, marca la conversacion como caliente y visible.
10. Un vendedor entra y continua la conversacion.

### 11.2 Flujo de captura de datos

El agente debe solicitar de forma natural:

- nombre o forma de tratamiento;
- correo electronico;
- telefono;
- destino o producto de interes;
- fechas estimadas;
- numero de personas;
- urgencia;
- restricciones o necesidades especiales.

### 11.3 Flujo de handoff

Se activa handoff cuando ocurre cualquiera de estas condiciones:

- `lead_score >= threshold_hot`
- el usuario pide hablar con una persona
- el agente detecta objeciones complejas o negociacion comercial
- el usuario pide una llamada o medio humano
- el vendedor decide manualmente entrar

### 11.4 Flujo de abandono

Si el lead abandona el sitio:

- el contexto queda guardado;
- el vendedor puede seguir manualmente fuera del sistema;
- en fase 2, Mautic podra enviar seguimiento automatizado.

### 11.5 Flujo de feedback humano

1. El vendedor habla por telefono o WhatsApp manual.
2. Agrega una nota privada en Chatwoot.
3. El bridge captura la nota privada como feedback de negocio.
4. El feedback se resume y agrega a la memoria del lead.
5. La siguiente respuesta de IA o correo toma en cuenta esa informacion.

---

## 12. Contratos internos de datos

### 12.1 Contrato de entrada desde Chatwoot al bridge

Campos minimos relevantes:

- `event`
- `conversation.id`
- `conversation.status`
- `message.id`
- `message.content`
- `message.message_type`
- `message.private`
- `contact.id`
- `contact.email`
- `contact.phone_number`
- `inbox.id`

### 12.2 Contrato interno de sesion

```json
{
  "session_id": "cw_12345",
  "conversation_id": 12345,
  "contact_id": 6789,
  "state": "bot_active",
  "last_seen_at": "2026-04-05T00:00:00Z",
  "lead_temperature": "warm",
  "lead_score": 62,
  "collected_data": {
    "name": null,
    "email": null,
    "phone": null,
    "product_interest": null,
    "travel_date": null,
    "party_size": null
  }
}
```

### 12.3 Contrato de salida del orquestador

El orquestador debe devolver una respuesta estandarizada. El texto libre no basta.

```json
{
  "reply_text": "Texto a mostrar al cliente",
  "lead_score": 78,
  "lead_temperature": "hot",
  "handoff_recommended": true,
  "reasoning_summary": "El usuario pidio precio, fechas y medio de pago.",
  "extracted_fields": {
    "name": "Juan",
    "email": "juan@example.com",
    "phone": "+51999999999",
    "product_interest": "Paquete Cusco",
    "travel_date": "2026-07",
    "party_size": 4
  },
  "next_best_action": "alert_sales"
}
```

### 12.4 Contrato de actualizacion hacia Chatwoot

Se deben sincronizar como minimo:

- custom attributes de la conversacion
- tags o labels
- estado sugerido
- nota privada opcional con resumen

Custom attributes sugeridos:

- `lead_score`
- `lead_temperature`
- `customer_name`
- `customer_email`
- `customer_phone`
- `product_interest`
- `travel_date`
- `party_size`
- `last_ai_summary`
- `handoff_recommended`

---

## 13. Politica de scoring de leads

### 13.1 Objetivo

El scoring no es decorativo. Debe ayudar al vendedor a decidir a donde entrar primero.

### 13.2 Version inicial aprobada

Se usara una politica heuristica + salida estructurada del modelo.

#### Frio

- pregunta muy general
- no deja datos
- no muestra urgencia
- solo navega o explora

#### Tibio

- muestra interes real
- responde varias preguntas
- deja al menos un dato parcial
- consulta opciones, condiciones, disponibilidad o detalles

#### Caliente

- pregunta precio, fecha, cierre, pago o disponibilidad concreta
- pide ser contactado
- deja telefono o email valido
- busca reserva, cierre o confirmacion

### 13.3 Umbrales iniciales

- `0-39`: frio
- `40-69`: tibio
- `70-100`: caliente

### 13.4 Regla operacional

Si `lead_score >= 70`, el bridge:

- marca `handoff_recommended=true`
- actualiza `lead_temperature=hot`
- aplica etiqueta o atributo visible
- opcionalmente cambia el estado sugerido para que el vendedor lo vea de inmediato

---

## 14. Memoria por cliente

### 14.1 Requisito funcional clave

El sistema no puede comportarse como un chatbot generico que responde igual a todos.

### 14.2 Principio de implementacion

Cada conversacion debe quedar asociada a un `session_id` estable, derivado de `conversation_id` o del mapping interno.

### 14.3 Elementos de memoria

- historial resumido de la conversacion
- datos de contacto recopilados
- intereses del lead
- temperatura del lead
- notas privadas del vendedor
- ultimo resumen comercial util

### 14.4 Reglas de memoria

- la memoria debe ser persistente mas alla de una sola pagina cargada;
- debe existir resumen incremental para no enviar historiales infinitos al modelo;
- los datos extraidos no deben depender solo del texto libre; deben guardarse estructurados;
- la nota privada del vendedor vale como input autorizado del sistema.

---

## 15. Requisitos no funcionales

### 15.1 Disponibilidad

- objetivo inicial: servicio disponible en horario comercial extendido con recuperacion rapida ante falla;
- el MVP puede tolerar una sola zona y una sola maquina, siempre que existan backups y runbooks claros.

### 15.2 Rendimiento

Objetivos iniciales:

- tiempo de aceptacion del webhook: bajo;
- tiempo de respuesta end-to-end normal: util para conversacion humana razonable;
- degradacion controlada cuando el orquestador tarde;
- no bloquear el hilo de Chatwoot por tareas secundarias.

### 15.3 Seguridad

- HTTPS obligatorio;
- no exponer Postgres ni Redis a internet;
- secretos fuera del repositorio;
- minimo privilegio en IAM y usuarios del host;
- validacion de firmas de webhook.

### 15.4 Mantenibilidad

- codigo por modulos;
- contratos documentados;
- tests de componentes criticos;
- adapters separados;
- ADRs para cambios mayores.

### 15.5 Portabilidad

- despliegue con Docker Compose;
- sin dependencias irreproducibles;
- futura migracion a ECS, Kubernetes o multi-servidor sin reescribir el dominio.

---

## 16. Diseno DevOps aprobado

### 16.1 Principios DevOps del proyecto

1. infraestructura declarativa;
2. cambios pequenos y trazables;
3. observabilidad desde el inicio;
4. secretos fuera del codigo;
5. despliegues repetibles;
6. rollback simple;
7. documentacion junto al codigo.

### 16.2 Estilo de despliegue del MVP

- Docker Compose como orquestador local del host;
- un repositorio central;
- ramas por feature;
- build reproducible por Dockerfiles versionados;
- `.env` por entorno;
- scripts de bootstrap y operacion.

### 16.3 Ambientes

Se aprueban tres ambientes conceptuales:

- `dev`
- `staging`
- `prod`

Si el presupuesto obliga, `dev` puede correr local o en otra EC2 mas pequena. `prod` no comparte `.env` con otros ambientes.

### 16.4 Infraestructura como codigo

No es bloqueante para el primer commit, pero queda aprobada la meta de usar:

- Terraform para red, SG, EC2, IAM, snapshots y S3 de backups;
- plantillas por entorno;
- variables versionadas.

### 16.5 Politica de cambios

Todo cambio a:

- puertos
- dominios
- variables de entorno
- modelo de datos
- scoring
- orquestador
- politica de handoff
- infraestructura base

requiere actualizar:

- este documento
- `CHANGELOG.md`
- un ADR si el cambio es estructural

---

## 17. Estructura del repositorio aprobada

```text
miwayki-platform/
├── README.md
├── CHANGELOG.md
├── Makefile
├── .env.example
├── compose/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── docker-compose.prod.yml
├── infra/
│   ├── terraform/
│   └── cloud-init/
├── nginx/
│   ├── nginx.conf
│   └── conf.d/
├── bridge/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── domain/
│   │   ├── adapters/
│   │   ├── services/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   └── config/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── docs/
│   ├── MASTER_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── RUNBOOKS/
│   ├── ADR/
│   └── API_CONTRACTS/
├── scripts/
│   ├── bootstrap.sh
│   ├── backup.sh
│   ├── restore.sh
│   ├── certbot-init.sh
│   ├── healthcheck.sh
│   └── rotate-logs.sh
├── sql/
│   ├── init/
│   └── migrations/
└── monitoring/
    ├── prometheus/
    ├── grafana/
    └── alerts/
```

### 17.1 Regla de estructura

El bridge debe seguir una separacion clara entre:

- dominio del negocio;
- adaptadores externos;
- persistencia;
- capa HTTP;
- configuracion.

No se aprueba mezclar toda la logica en un `main.py` grande.

---

## 18. Diseno del bridge por capas

### 18.1 Capa HTTP

Responsable de:

- exponer endpoints;
- parsear requests;
- devolver respuestas HTTP;
- no contener logica del negocio.

### 18.2 Capa de servicios

Responsable de:

- coordinar casos de uso;
- llamar adaptadores;
- manejar decisiones operativas.

### 18.3 Capa de dominio

Responsable de:

- entidades;
- value objects;
- reglas del negocio;
- scoring;
- estados.

### 18.4 Capa de adaptadores

Responsable de integrarse con:

- Chatwoot;
- orquestador IA;
- modelo;
- Mautic;
- almacenamiento;
- email.

### 18.5 Capa de persistencia

Responsable de:

- repositorios;
- conexiones DB;
- consultas;
- auditoria;
- mapeos.

---

## 19. Estados operativos de una conversacion

Se define una maquina simple de estados:

- `new`
- `bot_active`
- `warm`
- `hot`
- `human_handoff`
- `human_active`
- `abandoned`
- `followup_pending`
- `closed`

### 19.1 Reglas

- `new -> bot_active` cuando la primera respuesta la da la IA
- `bot_active -> warm` si supera cierto umbral de interes
- `warm -> hot` si supera umbral de cierre
- `hot -> human_handoff` cuando se recomienda intervencion humana
- `human_handoff -> human_active` cuando el vendedor toma el hilo
- `bot_active|warm -> abandoned` cuando no hay actividad por el umbral definido
- `abandoned -> followup_pending` cuando el lead ya tiene datos utiles para seguimiento
- cualquier estado -> `closed` al finalizar el ciclo comercial

---

## 20. Politica de errores y resiliencia

### 20.1 Errores esperados

- webhook duplicado;
- timeouts del orquestador;
- timeouts del modelo;
- caida parcial de Redis;
- caida parcial de Postgres;
- respuesta mal formada del orquestador;
- fallo al actualizar Chatwoot;
- reintentos que generan mensajes duplicados.

### 20.2 Reglas de resiliencia

- validacion estricta de payloads;
- idempotencia por `message_id`;
- circuit breaker simple para dependencias lentas;
- colas o reintentos para acciones secundarias;
- tiempo maximo de espera configurable;
- no perder el evento aunque falle la actualizacion secundaria.

### 20.3 Comportamiento degradado aprobado

Si el orquestador falla, el bridge debe poder:

- registrar el error;
- opcionalmente dejar nota privada tecnica;
- devolver mensaje de fallback al cliente;
- no romper la conversacion completa.

---

## 21. Seguridad aprobada

### 21.1 En el host

- acceso SSH restringido;
- llaves, no passwords;
- usuario no root para operacion diaria;
- fail2ban o equivalente si aplica;
- updates de seguridad regulares;
- puertos minimos expuestos.

### 21.2 En contenedores

- imagenes oficiales o construidas internamente;
- tags fijados;
- no usar `latest` en produccion;
- variables de entorno sensibles fuera del repo;
- volumes definidos explicitamente.

### 21.3 En integraciones

- HMAC o firma en webhooks;
- tokens en headers;
- rotacion periodica de secretos;
- TLS extremo a extremo hacia el exterior.

### 21.4 En datos personales

- principio de minima recoleccion necesaria;
- derecho de borrado;
- politica de retencion;
- acceso controlado a conversaciones y atributos;
- cifrado de disco y backups.

---

## 22. Observabilidad aprobada

### 22.1 Logs

El sistema debe producir logs estructurados al menos para:

- ingreso de webhook;
- decision de enrutamiento;
- invocacion a orquestador;
- invocacion a Chatwoot;
- actualizacion de scoring;
- handoff;
- errores.

### 22.2 Metricas minimas

- cantidad de webhooks entrantes;
- latencia por dependencia;
- ratio de errores del bridge;
- ratio de handoff;
- leads por temperatura;
- volumen diario;
- disponibilidad de servicios;
- uso de CPU, RAM, disco y swap.

### 22.3 Alertas minimas

- CPU sostenida alta;
- RAM alta;
- disco bajo;
- bridge caido;
- Postgres caido;
- Redis caido;
- error rate elevado;
- falta de backups recientes.

---

## 23. Backups y recuperacion

### 23.1 Politica aprobada

- backup diario de PostgreSQL;
- snapshot o copia de volumen segun estrategia elegida;
- backup de configuraciones Nginx y `.env` en almacenamiento seguro;
- backup cifrado hacia S3 o repositorio seguro equivalente;
- prueba de restauracion mensual.

### 23.2 Objetivo del backup

No basta con tener archivos. El objetivo es poder reconstruir la plataforma en un host nuevo con un procedimiento documentado.

### 23.3 Runbooks obligatorios

- restaurar PostgreSQL
- levantar stack desde cero
- renovar certificados
- rotar secretos
- migrar a nueva EC2

---

## 24. CI/CD aprobado

### 24.1 Fase inicial

Se acepta despliegue manual controlado, siempre que siga scripts versionados.

### 24.2 Fase recomendada

CI minima con GitHub Actions o equivalente:

- lint
- tests unitarios
- build de imagenes
- validacion de compose
- escaneo de seguridad basico

CD posterior:

- despliegue a staging
- smoke tests
- aprobacion manual
- despliegue a prod

### 24.3 Regla de oro

No se aprueba editar contenedores a mano en produccion como practica habitual. Todo cambio debe venir de codigo o configuracion versionada.

---

## 25. Roadmap de implementacion

## Fase 0 - Preparacion

- aprobar este documento
- crear repositorio
- definir naming y dominios
- definir estrategia inicial de orquestador y modelo

## Fase 1 - Infraestructura base

- aprovisionar EC2 recomendada
- instalar Docker y Compose
- montar Nginx, Postgres y Redis
- montar observabilidad basica
- configurar DNS y certificados

## Fase 2 - Chatwoot

- desplegar Chatwoot
- crear inbox del sitio web
- configurar custom attributes
- configurar Agent Bot
- validar widget embebido en miwayki.com

## Fase 3 - Bridge

- crear proyecto FastAPI
- implementar validacion HMAC
- implementar idempotencia
- implementar Chatwoot adapter
- implementar orquestador adapter
- publicar respuesta al hilo
- actualizar atributos
- soportar handoff

## Fase 4 - IA

- definir prompt base del agente
- definir esquema JSON de salida
- implementar extraccion de datos
- implementar scoring inicial
- implementar memoria resumida por lead

## Fase 5 - Hardening

- timeouts
- reintentos
- logs estructurados
- backups
- alarmas
- runbooks

## Fase 6 - Fase comercial avanzada

- notas privadas -> memoria
- follow-up logic
- modulo Mautic
- reportes y KPIs

---

## 26. Checklist de aceptacion del MVP

El MVP se considera aceptado si cumple con todo lo siguiente:

- el widget aparece y funciona en miwayki.com;
- el cliente puede iniciar una conversacion;
- la IA responde en el mismo hilo;
- el sistema captura al menos email o telefono cuando el lead coopera;
- el score y la temperatura se muestran en Chatwoot;
- el vendedor puede entrar al hilo y continuar;
- el bridge evita loops y valida firmas;
- el sistema conserva memoria minima por lead;
- existen backups y restauracion documentada;
- existe un procedimiento reproducible de despliegue.

---

## 27. Riesgos conocidos y mitigaciones

### Riesgo 1: sobrecargar una sola EC2

**Mitigacion:**

- usar tamano base correcto;
- monitorear desde el inicio;
- separar Mautic y/o orquestador si el uso sube;
- definir umbrales de re-plataformado.

### Riesgo 2: acoplarse demasiado a una herramienta de IA

**Mitigacion:**

- usar adaptadores internos;
- definir contrato JSON propio;
- no depender de tipos internos del orquestador.

### Riesgo 3: duplicidad de mensajes por reintentos

**Mitigacion:**

- idempotencia por `message_id`;
- tabla de eventos procesados.

### Riesgo 4: fuga de secretos

**Mitigacion:**

- no commitear `.env`;
- restringir permisos;
- rotacion;
- secrets manager opcional.

### Riesgo 5: que el scoring sea pobre al inicio

**Mitigacion:**

- empezar simple;
- ajustar reglas con feedback comercial;
- registrar por que un lead fue marcado como caliente.

---

## 28. Decision sobre tecnologia de modelo

### 28.1 Politica tecnica

El proyecto se diseña para funcionar con **backend de modelo intercambiable**.

### 28.2 Camino de cumplimiento estricto

Si se exige apego duro al criterio de no depender de modelo de pago, el backend aprobado es:

- modelo open source self-hosted
- servido por vLLM u Ollama
- aislado como endpoint propio

### 28.3 Camino transicional opcional

Si por time-to-market el negocio aprueba temporalmente un proveedor gestionado, este se integra solo por el `ModelProviderAdapter`.

### 28.4 Regla arquitectonica

**El dominio del sistema nunca sabra si la respuesta vino de Bedrock, vLLM, Ollama u otro backend.**

---

## 29. Politica de calidad de codigo

### 29.1 Python / FastAPI

- tipado en funciones nuevas;
- Pydantic para schemas;
- modularidad por paquetes;
- tests unitarios para scoring y adaptadores;
- logs estructurados;
- manejo claro de excepciones.

### 29.2 Docker

- imagenes livianas;
- healthchecks;
- variables de entorno documentadas;
- volumes persistentes definidos;
- no usar contenedores mascotas.

### 29.3 SQL

- migraciones versionadas;
- indices solo cuando se necesiten;
- campos estructurados para datos clave;
- JSONB donde agregue valor real, no por costumbre.

---

## 30. Normas para trabajar con Cursor

### 30.1 Uso de este documento

Este documento debe cargarse o citarse como contexto raiz en Cursor.

### 30.2 Regla de trabajo

Cada vez que se pida a Cursor crear codigo, se debe indicar:

- que respete `MASTER_SPEC.md`;
- que no rompa contratos internos;
- que use la estructura del repositorio;
- que si propone cambiar arquitectura, primero lo deje como sugerencia y no como cambio directo.

### 30.3 Cambios mayores

Si Cursor propone:

- cambiar el orquestador
- mover base de datos
- cambiar el modelo de scoring
- cambiar el flujo de handoff
- incorporar un servicio nuevo

se debe convertir esa sugerencia en un ADR antes de implementarla.

---

## 31. ADR iniciales aprobados

### ADR-001

**Tema:** Chatwoot como widget e inbox.  
**Estado:** Aprobado.

### ADR-002

**Tema:** FastAPI bridge propio como capa de integracion.  
**Estado:** Aprobado.

### ADR-003

**Tema:** EC2 fija para el core del MVP en lugar de ECS Express/Fargate.  
**Estado:** Aprobado.

### ADR-004

**Tema:** t3.large no aprobada como base productiva; baseline xlarge.  
**Estado:** Aprobado.

### ADR-005

**Tema:** Orquestador y modelo desacoplados por adaptadores.  
**Estado:** Aprobado.

### ADR-006

**Tema:** Mautic entra como modulo fase 2, no bloquea MVP.  
**Estado:** Aprobado.

---

## 32. Requisitos de capacidad y re-plataformado

### 32.1 Condiciones para seguir en una sola EC2

Se puede seguir con una sola EC2 si:

- el uso de CPU se mantiene sano la mayor parte del tiempo;
- la RAM no vive saturada;
- la latencia de respuesta es aceptable;
- el bridge no acumula retrasos;
- el equipo puede operar el host sin dolor.

### 32.2 Disparadores para separar componentes

Separar componentes si ocurre cualquiera de los siguientes:

- crecimiento sostenido de conversaciones concurrentes;
- saturacion de RAM o CPU;
- necesidad fuerte de aislar riesgos;
- Mautic consume demasiado;
- el orquestador o el modelo merecen nodo propio;
- se requiere alta disponibilidad real.

### 32.3 Orden sugerido de separacion

1. sacar Mautic del host principal
2. sacar el orquestador del host principal
3. migrar Postgres a servicio gestionado o nodo dedicado
4. mover a ECS o K8s solo cuando el beneficio supere la complejidad

---

## 33. Politica comercial y operativa

### 33.1 Que hace la IA

- atiende
- pregunta
- resume
- puntua
- recomienda handoff
- organiza contexto

### 33.2 Que no hace la IA

- no cierra operaciones que deban pasar por humano
- no reemplaza al vendedor
- no envia WhatsApp automatizado fuera del sistema
- no debe inventar politicas comerciales ni precios no aprobados

### 33.3 Rol del vendedor

- intervenir cuando el lead esta caliente o lo amerita
- dejar notas privadas de alto valor
- corregir informacion si es necesario y con criterio
- cerrar la venta por canales humanos cuando corresponda

---

## 34. Referencias tecnicas que sustentan decisiones

Estas referencias deben quedar como base para revisiones futuras. No sustituyen este documento; lo complementan.

### AWS

- EC2 On-Demand pricing: https://aws.amazon.com/ec2/pricing/on-demand/
- EC2 T3 instances: https://aws.amazon.com/ec2/instance-types/t3/
- EC2 T4g instances: https://aws.amazon.com/ec2/instance-types/t4/
- EC2 M7g instances: https://aws.amazon.com/ec2/instance-types/m7g/
- ECS pricing: https://aws.amazon.com/ecs/pricing/
- Fargate pricing: https://aws.amazon.com/fargate/pricing/
- Elastic Load Balancing pricing: https://aws.amazon.com/elasticloadbalancing/pricing/

### Chatwoot

- Self-hosted requirements: https://developers.chatwoot.com/self-hosted/deployment/requirements
- Self-hosted guide: https://developers.chatwoot.com/self-hosted
- Agent bot create API: https://developers.chatwoot.com/api-reference/account-agentbots/create-an-agent-bot
- Associate agent bot to inbox: https://developers.chatwoot.com/api-reference/inboxes/add-or-remove-agent-bot
- Update conversation custom attributes: https://developers.chatwoot.com/api-reference/conversations/update-custom-attributes
- Private notes: https://www.chatwoot.com/features/private-notes/
- Custom attributes: https://www.chatwoot.com/features/custom-attributes/

### Dify

- Self-hosted Docker Compose: https://docs.dify.ai/getting-started/install-self-hosted/docker-compose
- Model providers: https://docs.dify.ai/en/guides/model-configuration/predefined-model
- GitHub repository: https://github.com/langgenius/dify
- License file: https://github.com/langgenius/dify/blob/main/LICENSE

### Mautic

- Official site: https://mautic.org/

---

## 35. Declaracion final

Este documento reemplaza el borrador previo como especificacion maestra del proyecto.

La idea central se mantiene: **crear una plataforma propia, modular y profesional de captacion y calificacion de leads con chat web, IA y handoff humano**.

Lo que cambia es que ahora la especificacion queda alineada con una arquitectura mas sana:

- menos acoplamiento;
- mejor criterio de infraestructura;
- mejor criterio DevOps;
- mejor trazabilidad;
- mejor posibilidad de crecer sin rehacer todo.

A partir de este punto, el desarrollo debe seguir estos principios:

1. primero contrato y arquitectura;
2. luego codigo;
3. luego despliegue;
4. luego observabilidad;
5. luego optimizacion.
6. todo sera instalado localemnte primero y depsues de pruebas recien migraremos a aws, considerando eso , tiene sque saber que estoy usando macOS Tahoe 26.5 en un chip M1 Pro. Quiero usar el nuevo Containerization Framework para crear un servidor Linux (Ubuntu/Debian) que corra de forma nativa. Dame los comandos de terminal para descargar una imagen ligera de Linux y configurarla como un servicio de fondo utilizando las nuevas herramientas de virtualización del sistema, la direccion razis es donde esta este markdown 

**Este es el archivo que Cursor debe tomar como documento raiz del proyecto.**
