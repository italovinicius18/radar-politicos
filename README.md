# Radar Políticos

Gastos parlamentares abertos — Câmara (CEAP, 2016–2026), Senado (CEAPS, 2016–2026) e CLDF (deputados distritais do DF, 2013–2026): o que gastaram, por quê, com quem, quanto e quando — com link da nota fiscal quando a fonte publica. **Site 100% estático**: nenhum servidor em produção.

## Como gerar o site

```bash
# 1. Ingestão dos dados (re-executável/idempotente)
cd backend && uv run python -m radar.ingest --anos 2016-2026 --db ../dados/radar.duckdb --pasta ../dados
# CLDF (deputados distritais) cobre 2013-2026:
cd backend && uv run python -m radar.ingest --anos 2013-2026 --fontes cldf --db ../dados/radar.duckdb --pasta ../dados

# 2. Exportar os JSONs estáticos
cd backend && uv run python -m radar.exportar --db ../dados/radar.duckdb --saida ../frontend/public/dados

# 3. Build do site (gera frontend/out/ — 1.547 perfis + home + rankings, ~17 mil arquivos / ~660 MB)
cd frontend && npm install && npm run build

# 4. Ver localmente
npx serve frontend/out
```

## Publicar

Qualquer hosting estático serve `frontend/out/`:
- Cloudflare Pages: `npx wrangler pages deploy frontend/out` (limite de 20 mil arquivos — hoje usamos ~17 mil; se apertar, desligar o segment-prefetch do Next ou trocar de hosting)
- GitHub Pages / Netlify: upload do diretório

Atualizar o site = repetir os passos 1–3 e publicar de novo.

## Desenvolvimento

```bash
cd backend && uv run pytest                     # 64 testes
cd frontend && npm test                         # 8 testes (formatação e busca)
cd frontend && npm run dev                      # dev server Next (usa public/dados)
# API local para debug (opcional, não é usada pelo site):
cd backend && uv run uvicorn radar.api.app:app_padrao --factory --port 8010
```

Documentação: `docs/superpowers/specs/` (designs), `docs/superpowers/plans/` (planos) e `docs/superpowers/validacao-*.md` (validações contra as fontes oficiais).
