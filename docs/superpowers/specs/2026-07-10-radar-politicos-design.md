# Radar Políticos — Design

**Data:** 2026-07-10
**Status:** Aprovado

## Objetivo

Sistema local para consultar gastos de políticos brasileiros: **o que** gastaram, **por que** (categoria), **com quem** (fornecedor), **quanto** e **quando**, com comprovação (link da nota fiscal) quando disponível.

## Escopo

- **Fase 1 (este projeto):** deputados federais (CEAP/Câmara) e senadores (CEAPS/Senado), últimos 10 anos (2016–2026).
- **Futuro (fora deste plano):** assembleias estaduais e câmaras municipais. A arquitetura já prevê múltiplas fontes: adicionar um estado = escrever um novo módulo de fonte, sem tocar em API ou frontend.
- Roda localmente (localhost); publicação na internet é passo separado, futuro.

## Arquitetura

```
INGESTÃO (Python)                 API (FastAPI)              FRONTEND (React/Vite)
fontes/camara.py  ─┐              /politicos?busca=          Busca
fontes/senado.py  ─┼→ DuckDB  →   /politicos/{id}/resumo  →  Perfil do político
(futuro: estados) ─┘ radar.duckdb /politicos/{id}/despesas   Rankings
                                  /rankings
```

- **Ingestão:** comando `python -m ingest --anos 2016-2026`. Baixa os CSVs anuais públicos da Câmara (CEAP) e do Senado (CEAPS), normaliza para o modelo único de despesa e carrega no DuckDB. Reexecutável e idempotente (não duplica dados).
- **Banco:** DuckDB local (`radar.duckdb`), analítico — agregações sobre ~5 milhões de linhas em milissegundos.
- **API:** FastAPI em localhost:8000.
- **Frontend:** React + Vite em localhost:5173, tudo em português, valores em R$ com formatação brasileira.

## Modelo de dados

### Tabela `politicos` — uma linha por político por fonte

| campo | exemplo |
|---|---|
| id | `camara-204554` |
| nome | Nikolas Ferreira |
| cargo | Deputado Federal |
| partido | PL |
| uf | MG |
| foto_url | URL da API da Câmara |
| fonte | `camara` |

### Tabela `despesas` — uma linha por gasto

| campo | responde | observação |
|---|---|---|
| politico_id | quem | FK para `politicos` |
| data | quando | |
| categoria_original | por quê | texto original da fonte |
| categoria | por quê (comparável) | categoria normalizada comum às fontes |
| descricao | detalhe | texto livre da fonte, quando houver |
| fornecedor | com quem | |
| fornecedor_cnpj | com quem (verificável) | CNPJ/CPF quando disponível |
| valor | quanto | negativos = estornos/ressarcimentos |
| documento_url | comprovação | link do PDF da nota fiscal, quando houver |
| fonte | origem do dado | `camara` / `senado` |

### Decisões

- **Categorias:** a CEAP tem ~18 tipos; o Senado usa nomes diferentes. Mantemos o texto original em `categoria_original` e mapeamos para uma `categoria` normalizada comum, permitindo comparar deputado com senador.
- **Estornos:** valores negativos (ex.: bilhete aéreo não voado) entram no banco e são subtraídos dos totais — mesmo comportamento do site oficial.
- **Identidade entre fontes:** quem foi deputado e depois senador aparece como dois registros; a busca por nome mostra ambos. Unificação por CPF fica para o futuro.
- **Índices:** por `politico_id` e por `data`.

## API

1. `GET /politicos?busca=<nome>` — busca parcial, sem acento; filtros opcionais de cargo/partido/UF.
2. `GET /politicos/{id}/resumo` — total gasto, por ano, por categoria, top 10 fornecedores.
3. `GET /politicos/{id}/despesas` — lista paginada; filtros por ano, categoria, fornecedor; ordenável por data ou valor.
4. `GET /rankings?ano=&cargo=&categoria=` — maiores gastadores no período.

## Dashboard

1. **Busca** — campo de busca; resultados com foto, nome, partido/UF, cargo.
2. **Perfil do político** — tela principal:
   - Cabeçalho: foto, nome, partido, total gasto no período selecionado
   - Gráfico de barras: gasto por ano
   - Gráfico por categoria (o porquê)
   - Top fornecedores (para quem foi o dinheiro)
   - Tabela de despesas com filtros (ano, categoria) e link da nota fiscal por linha
3. **Rankings** — maiores gastadores por ano/categoria, clicável para o perfil.

## Tratamento de erros

- Ingestão resiliente: falha em um ano/fonte → loga e continua; relatório final lista o que entrou e o que faltou.
- API valida parâmetros e retorna 404 para político inexistente.

## Testes e validação

- **Unitários:** normalização de cada fonte (parsing de CSV, mapeamento de categorias, estornos).
- **API:** testes com banco pequeno de amostra.
- **Validação com políticos reais:** consultar no sistema políticos variados — deputado de alto gasto, senador, deputado de baixo gasto, político reeleito (histórico longo) — e comparar os totais com os sites oficiais da Câmara e do Senado.

## Fontes de dados

- **Câmara (CEAP):** CSVs anuais em `https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip` + API de Dados Abertos (`https://dadosabertos.camara.leg.br/api/v2`) para dados cadastrais/fotos dos deputados.
- **Senado (CEAPS):** CSVs anuais em `https://www.senado.gov.br/transparencia/LAI/verba/despesa_ceaps_{ano}.csv`.
- URLs exatas serão confirmadas na implementação; se algum formato tiver mudado, o módulo da fonte é o único ponto de ajuste.
