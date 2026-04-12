# MiWayki Project Context

## Project identity
MiWayki is a lead capture, qualification, and sales handoff platform for miwayki.com.

## Source of truth
The primary source of truth is `miwayki_master_spec_updated.md`.
The operational continuity log is `historial_chat.md`.

## Approved architecture
- Chatwoot is the web widget and human inbox.
- FastAPI Bridge is the integration and business-rules layer.
- Dify is the initial AI orchestrator, but the codebase must remain adapter-based.
- PostgreSQL is the main database.
- Redis is used for cache and light queueing.
- Mautic is phase 2, not part of the required basic phase delivery.

## Non-negotiable engineering rules
- Do not replace the approved architecture with a CLI-only architecture.
- Do not couple business logic directly to Dify-specific payloads.
- Preserve or improve modularity.
- Prefer small, reversible changes.
- Always propose a plan before editing.
- For code changes, validate with tests or at least with explicit verification commands.
- Never invent environment variables, endpoints, or file paths; inspect first.
- Never commit secrets.
- Keep `.env` secrets out of git.
- Treat `miwayki_master_spec_updated.md` as binding architecture.
- Treat `historial_chat.md` as operational memory.

## Current local reality
- Local environment is macOS + Lima VM + Docker Compose.
- Chatwoot and the local stack were already validated end-to-end.
- Dify is already running locally and the bridge must call Dify internally through `http://api:5001/v1` from the bridge container, not `127.0.0.1`.
- There is already a Dify Chatflow called `Prueba Gemini` used as local proof of life.

## What “basic phase” means here
The local basic phase is now **Functionally Closed** (2026-04-11).
This includes:
- [x] 1. Stable local stack.
- [x] 2. Chatwoot webhook to Bridge.
- [x] 3. Bridge to Dify integration.
- [x] 4. Controlled reply back into Chatwoot.
- [x] 5. Minimal lead scoring and attributes.
- [x] 6. E2E validation.
- [x] 7. Updated docs/runbooks (See `docs/RUNBOOKS/local_operations.md`).

## Next Phase: Cloud Transition
The next step is the migration to AWS (EC2/Docker Compose) following the roadmap in `miwayki_master_spec_updated.md` (§25.5).

## Working style
Use spec-driven engineering, not vibe coding.
Before each implementation block:
1. inspect
2. map affected files
3. propose changes
4. apply smallest safe diff
5. validate
6. document outcome