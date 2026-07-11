# Panorama na tela inicial — Design

**Data:** 2026-07-11
**Status:** Aprovado

## Objetivo

A tela inicial hoje só tem a busca. Adicionar abaixo dela um "Panorama" do ano: KPIs, evolução mensal, comparativo Câmara × Senado e top 5s — dando visão imediata dos gastos sem precisar buscar alguém.

## Backend — `GET /api/visao-geral?ano=`

Novo endpoint no `backend/radar/api/app.py` (mesmas convenções: SQL parametrizado, conexão read-only por request, floats no JSON). `ano` opcional; padrão = maior ano com dados (`SELECT max(ano) FROM despesas`).

Payload:

```json
{
  "ano": 2026,
  "kpis": {
    "total": 89200000.0,
    "total_mesmo_periodo_anterior": 92100000.0,
    "variacao_pct": -3.2,
    "meses_com_dados": 7,
    "parlamentares": 588,
    "deputados": 513,
    "senadores": 75,
    "media_por_parlamentar": 151700.0,
    "num_despesas": 89229,
    "nota_mais_cara": {
      "valor": 62000.0, "categoria": "Divulgação", "fornecedor": "…",
      "data": "2026-03-10", "politico": { "id": "…", "nome": "…", "partido": "…", "uf": "…", "foto_url": "…", "cargo": "…", "fonte": "…" }
    }
  },
  "por_mes": [{ "mes": 1, "total": 12000000.0 }],
  "camara_senado": [{ "fonte": "camara", "total": 80000000.0, "parlamentares": 513 }],
  "top_gastadores": [{ "politico": { "…": "…" }, "total": 364132.97 }],
  "top_categorias": [{ "categoria": "Passagens", "total": 30000000.0 }],
  "top_fornecedores": [{ "fornecedor": "…", "cnpj": "…", "total": 500000.0, "quantidade": 120 }]
}
```

Regras:

- **Variação honesta**: `meses_com_dados` = maior mês com despesa no ano selecionado. `total_mesmo_periodo_anterior` = soma do ano anterior **limitada aos mesmos meses** (1..meses_com_dados). `variacao_pct` = null se o período anterior for 0/inexistente.
- Tops limitados a 5; `nota_mais_cara` = despesa de maior valor no ano (com política associada).
- Ano sem dados → 200 com blocos zerados/vazios (`total: 0`, listas vazias, `nota_mais_cara: null`), nunca erro.
- `parlamentares` = quem tem despesa no ano (não o total da tabela politicos).

## Frontend

- **`frontend/src/paginas/Panorama.tsx`** (novo componente): consome `obterVisaoGeral(ano?)` (novo em `api.ts` com tipo `VisaoGeral`); seletor de ano (lista fixa 2016..2026, mesmo padrão da página Rankings); estados de erro/loading isolados (falha no panorama não afeta a busca); flag `ativo` contra respostas fora de ordem.
- **`Busca.tsx`**: renderiza `<Panorama />` abaixo do campo quando **não** há busca ativa (menos de 3 letras digitadas); com busca ativa, mostra só resultados.
- **Layout** (classes novas em `index.css`, seguindo o tema existente):
  1. Linha de 4 stat tiles: Total gasto (+ variação % com seta e rótulo "vs jan–{mês}/{ano-1}"), Parlamentares (com quebra dep/sen), Média por parlamentar, Nota mais cara (valor + nome clicável).
  2. Gráfico de área/barras da evolução mensal + rosca Câmara × Senado.
  3. Três colunas top 5: gastadores (foto, nome → perfil, total), categorias (mini-barras horizontais proporcionais), fornecedores (nome, CNPJ, total).
- **`formatarBRLCompacto`** em `formato.ts`: R$ ≥ 1 mi → "R$ 89,2 mi"; ≥ 1 mil → "R$ 151,7 mil"; abaixo → formatarBRL normal. Meses em pt-BR abreviados ("jan", "fev"…).
- Consultar o skill `dataviz` antes de escrever os gráficos (cores, formas, acessibilidade).

## Testes

- pytest (`tests/test_api.py`): payload completo com fixture existente (totais, tops, por_mes), variação com período parcial, ano sem dados (zerado), `nota_mais_cara` correta.
- vitest: `formatarBRLCompacto` (mi/mil/pequeno, negativo).
- Gate frontend: `npm run build` sem erros TS + navegação manual/Playwright na home.

## Fora de escopo

Filtros extras na home, drill-down de categorias/fornecedores, cache no backend.
