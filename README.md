# Miwayki AWS Phase 1 Pilot

End-to-end AWS pilot:
fake site -> Chatwoot widget -> Chatwoot -> bridge -> Dify -> reply in widget.

## Public URLs
- Fake site: http://34.207.15.203:8080
- Chatwoot: http://34.207.15.203:3000

## Services
- EC2 (Docker)
- Chatwoot + Sidekiq
- Bridge (FastAPI)
- Dify
- Fake site (nginx)

## Quick smoke test
```bash
/opt/miwayki-platform/Final_Project/scripts/smoke_test_piloto.sh
```
