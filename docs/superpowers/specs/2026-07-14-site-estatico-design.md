# Site estático pré-compilado — Design

**Data:** 2026-07-14
**Status:** Aprovado

## Objetivo

Trocar a arquitetura de publicação: em vez de subir API + frontend, **pré-compilar o site inteiro** a partir do DuckDB local. O fluxo passa a ser: ingestão local → exportação de JSONs → build estático (1.547 páginas de perfil + home + rankings) → deploy de arquivos. Zero servidor em produção, custo de hospedagem zero, SEO máximo (HTML completo por político, com meta/OG únicos). A API FastAPI continua existindo só como ferramenta local de desenvolvimento.

## Arquitetura

```
ingestão (local/CI) → dados/radar.duckdb
       ↓
python -m radar.exportar --db dados/radar.duckdb --saida frontend/public/dados
       ↓  (JSONs estáticos)
next build (output: export) → frontend/out/  → deploy estático (Cloudflare/GH Pages)
```

## Exportador (`backend/radar/exportar.py`, CLI `python -m radar.exportar`)

Lê o DuckDB direto (sem HTTP) e grava em `frontend/public/dados/`:

| Arquivo | Conteúdo | Uso |
|---|---|---|
| `meta.json` | anos com dados (min/max e lista), contagens por fonte, `gerado_em` (ISO) | seletores de ano; rodapé "atualizado em" |
| `politicos.json` | lista completa `{id, nome, cargo, partido, uf, foto_url, fonte}` | índice de busca client-side (~150 KB) |
| `visao-geral/{ano}.json` | payload idêntico ao endpoint `/api/visao-geral` | Panorama (embutido no build p/ ano mais recente; fetch na troca de ano) |
| `rankings/{ano}.json` | itens `{politico, total}` do ano (limite 100) | página Rankings (filtro de cargo client-side) |
| `perfil/{id}.json` | payload idêntico ao `/api/politicos/{id}/resumo` | embutido no HTML do perfil no build |
| `despesas/{id}/{ano}.json` | **formato compacto**: `{"colunas": ["data","categoria","categoria_original","descricao","fornecedor","cnpj","valor","doc"], "linhas": [[…], …]}`, ordenado por data desc | tabela de despesas (fetch por ano, filtros/ordenação no navegador) |

Regras: reusa as MESMAS consultas SQL da API (extraídas para módulo compartilhado `backend/radar/consultas.py` — a API e o exportador chamam as mesmas funções, garantindo paridade); floats; escreve atômico (staging + rename); relatório final (nº de arquivos, tamanho total). Escala esperada: ~1.550 perfis + ~12 mil chunks de despesas ≈ 150–250 MB brutos (compactos), dentro dos limites do Cloudflare Pages (20 mil arquivos) e GitHub Pages.

## Frontend: migração Vite SPA → Next.js 15 (App Router, `output: 'export'`)

- **Rotas preservadas**: `/` (busca + panorama), `/politico/[id]`, `/rankings`. `trailingSlash: true` (gera `pasta/index.html`, amigável a hosting estático).
- **`/politico/[id]`**: `generateStaticParams` a partir de `politicos.json`; resumo lido de `perfil/{id}.json` no build (fs) e embutido no HTML; `generateMetadata` por político — `title` "Gastos de {nome} ({partido}/{uf}) — Radar Políticos", description com total e período, `og:image` = foto oficial (ou padrão do site). Tabela de despesas: client component que busca `/dados/despesas/{id}/{ano}.json` (ano padrão = mais recente com dados do político, derivado do resumo), pagina/filtra/ordena no navegador.
- **Home**: visão-geral do ano mais recente embutida no build; troca de ano busca o JSON estático; busca client-side sobre `politicos.json` com normalização de acentos (equivalente TS do `sem_acento`). Anos dos seletores vêm de `meta.json` — **paga o débito do hardcode 2013–2026**.
- **Rankings**: shell estático + fetch do JSON do ano; filtro de cargo client-side.
- **`sitemap.xml` e `robots.txt`** gerados no build com todas as rotas.
- Componentes/gráficos/CSS do tema Painel de Brasília portados como client components (recharts exige); paleta validada intocada. `formato.ts` e testes vitest mantidos.
- O diretório `frontend/` é substituído in-place (o Vite SPA fica no histórico do git).

## O que muda de comportamento (aceito)

- Ordenação/filtragem de despesas vale dentro do ano carregado (não mais sobre todo o período de uma vez).
- Frescor = data do último build (rodapé mostra "dados atualizados em {gerado_em}").
- A API local continua para debug/desenvolvimento, mas não é mais pré-requisito do site.

## Testes e verificação

- Exportador: pytest com o banco-fixture (arquivos gerados, formato compacto correto, paridade com payloads da API via `consultas.py` compartilhado, meta.json, atomicidade básica).
- Frontend: vitest (formato + normalização de busca); `next build` como gate de tipos; verificação final servindo `out/` (ex.: `npx serve`) com Playwright — busca, perfil (meta tags presentes no HTML puro!), troca de ano, rankings, rodapé.
- Sanidade de escala: build completo com o banco real; conferir nº de páginas/arquivos e tamanho do `out/`.

## Fora de escopo

Publicação efetiva (precisa de conta/credenciais — passo separado com o usuário); automação GitHub Actions (evolução futura); OG images customizadas geradas por build; PWA/offline.
