#!/usr/bin/env bash
# Publica o Radar Políticos: ingestão -> export -> testes -> build -> deploy.
# As fontes oficiais (Câmara/Senado) bloqueiam IPs estrangeiros, então a
# ingestão precisa rodar de um IP brasileiro — por isso este script é local.
set -euo pipefail
cd "$(dirname "$0")"
ano=$(date +%Y)

echo "== Ingestão das fontes oficiais =="
(cd backend && uv run python -m radar.ingest --anos "2016-${ano}" --db ../dados/radar.duckdb --pasta ../dados)
(cd backend && uv run python -m radar.ingest --anos "2013-${ano}" --fontes cldf --db ../dados/radar.duckdb --pasta ../dados)

echo "== Export dos JSONs estáticos =="
(cd backend && uv run python -m radar.exportar --db ../dados/radar.duckdb --saida ../frontend/public/dados)

echo "== Testes =="
(cd backend && uv run pytest -q)
(cd frontend && npm test)

echo "== Build =="
(cd frontend && npm run build)

echo "== Deploy no Cloudflare Pages =="
npx wrangler pages deploy frontend/out --project-name radar-politicos --commit-dirty=true

echo "✔ publicado: https://radar-politicos.pages.dev"
