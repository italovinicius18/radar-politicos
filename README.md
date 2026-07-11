# Radar Políticos

Consulta local de gastos parlamentares (Câmara/CEAP e Senado/CEAPS, 2016–2026): o que gastaram, por quê, com quem, quanto e quando — com link da nota fiscal.

## Como rodar

```bash
# 1. Ingestão dos dados (uma vez; re-executável/idempotente)
cd backend && uv run python -m radar.ingest --anos 2016-2026 --db ../dados/radar.duckdb --pasta ../dados

# 2. API (porta 8010 — 8000 costuma estar ocupada por Docker)
cd backend && uv run uvicorn radar.api.app:app_padrao --factory --port 8010

# 3. Frontend (abre em http://localhost:5175 ou próxima porta livre)
cd frontend && npm install && npm run dev
```

## Testes

```bash
cd backend && uv run pytest      # 34 testes
cd frontend && npm test          # utilitários de formatação
```

Documentação: `docs/superpowers/specs/` (design), `docs/superpowers/plans/` (plano) e `docs/superpowers/validacao-2026-07-10.md` (validação contra fontes oficiais).
