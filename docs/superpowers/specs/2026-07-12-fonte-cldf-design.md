# Fonte CLDF (deputados distritais) — Design

**Data:** 2026-07-12
**Status:** Aprovado

## Objetivo

Adicionar os deputados distritais do DF ao Radar Políticos, via verbas indenizatórias da Câmara Legislativa do DF (CLDF), cobrindo 2013–2026. Primeira fonte além do Congresso — força o sistema a ficar genuinamente multi-fonte (rótulos, cores e contagens deixam de assumir só Câmara/Senado).

## Contexto do levantamento (2026-07-11)

Pesquisa em 26 câmaras municipais de capitais + 27 estados (gabinetes de governadores): **apenas a CLDF tem dado estruturado completo verificado** (portal CKAN `dados.cl.df.gov.br`, dataset `verbas-indenizatorias`). Quase-viáveis documentados para o futuro: Porto Alegre (API JSON com WAF), Teresina (form JSF com export Excel desde 1993), São Paulo (bulk 2007–2017 + webservice SisGV), ES (CSV de cartão do gabinete do governador — fora de escopo por decisão do usuário), PI (seção de cartão corporativo não verificada). Governadores e vereadores estão fora desta fase.

## Fonte de dados (verificada)

- Descoberta de recursos via API CKAN: `https://dados.cl.df.gov.br/api/3/action/package_show?id=verbas-indenizatorias` — um recurso XLSX por ano, 2013–2026 (nomes variam; alguns anos também têm CSV, mas 2025/2026 só XLSX → caminho único de parse: XLSX via `openpyxl`).
- **2013–2024 (formato transacional)**: colunas `NOME_PARLAMENTAR, CPF_PARLAMENTAR, NOME_PRESTADOR, CNPJ_PRESTADOR, CPF_PRESTADOR, NR_COMPROVANTE, DATA_COMPROVANTE (datetime), VALOR_DESPESA, CLASSIFICACAO, OBSERVACOES`.
- **2025–2026 (formato pivô, export Power BI)**: 2 linhas de cabeçalho de filtro, depois header `ano, mês, deputado, <categorias em colunas...>, Glosa, totalVerbaGeral`; uma linha por deputado/mês; **sem fornecedor nem data**; a soma das colunas de categoria não fecha com `totalVerbaGeral` (o export omite categorias).

## Regras de ingestão

Novo módulo `backend/radar/ingest/fontes/cldf.py` com o contrato padrão (`FONTE = "cldf"`, `baixar(ano, pasta)`, `parse(caminho)`), mais `openpyxl` como dependência.

- `baixar(ano, pasta)`: consulta o `package_show` do CKAN, escolhe o recurso XLSX cujo nome contém o ano (se houver mais de um, o de nome mais recente/corrigido), baixa para `dados/cldf/`. Não re-baixa se o arquivo já existe.
- `parse(caminho)`: detecta o formato pela primeira linha (header `NOME_PARLAMENTAR` → transacional; célula "Filtros aplicados" → pivô).
  - **Transacional**: uma despesa por linha. `fornecedor = NOME_PRESTADOR`, `fornecedor_cnpj = CNPJ_PRESTADOR ou CPF_PRESTADOR`, `data = DATA_COMPROVANTE` (date), `ano/mes` derivados da data, `valor = VALOR_DESPESA`, `categoria_original = CLASSIFICACAO` (vazio → "Não especificada" via normalização), `descricao = OBSERVACOES`.
  - **Pivô**: por linha (deputado/mês), uma despesa por coluna de categoria com valor > 0 (`fornecedor/data = None`, `mes` do nome do mês pt-BR abreviado da coluna `mês`); mais uma despesa residual `categoria = "Outras (não detalhado no dado oficial)"` com `valor = totalVerbaGeral − Σ(categorias) − Glosa` quando esse resíduo for ≠ 0, para o total do deputado/mês bater com o oficial. Glosa entra como despesa negativa quando ≠ 0 (mesma semântica de estorno das outras fontes).
- **Político**: `id = cldf-{slug(nome)}`, nome sem prefixo "Deputado "/"Deputada ", `cargo = "Deputado Distrital"`, `uf = "DF"`, `partido = None`, `foto_url = None` (CLDF não publica URL previsível). Mesmo nome nos dois formatos → mesmo id (verificar na validação).
- Categorias do pivô mapeadas pela normalização existente (ex.: "Combustível Lubrificante" → Combustíveis, "Veículos" → Locação de veículos, "Imóvel" → Manutenção de escritório, "Consultoria..." → Consultorias e trabalhos técnicos); adicionar regras que faltarem.

## Sistema multi-fonte (paga hardcodes atuais)

Novo registro central de fontes:

- **Backend** `backend/radar/fontes_registro.py`: `FONTES = {"camara": {"rotulo": "Câmara", "casa": "Câmara dos Deputados", "cargo": "Deputado Federal"}, "senado": {...}, "cldf": {"rotulo": "CLDF", "casa": "Câmara Legislativa do DF", "cargo": "Deputado Distrital"}}`.
- `/api/visao-geral`: `camara_senado` renomeado para `por_casa` (lista por fonte, mesma estrutura + `rotulo`); contagem de deputados/senadores substituída por contagem por fonte (`kpis.por_cargo: [{cargo, quantidade}]` derivado do registro). **Breaking change interno** aceito: o frontend é o único consumidor.
- **Frontend**: espelho do registro em `src/lib/fontes.ts` (rótulo + cor de gráfico por fonte); Panorama: tile de parlamentares lista os cargos dinamicamente; barra "Câmara × Senado" vira "**Por casa**" com N fatias (cores: paleta de 3 validada pelo verificador do dataviz — verde `#1d7a4d`, azul `#0369a1`, terceira cor a validar no plano); Rankings: opção "Deputado Distrital" no filtro de cargo.

## Testes e validação

- Unitários da fonte: fixtures XLSX pequenas geradas por script (formato transacional e pivô — incluindo linha com resíduo e glosa), parse de ambos, strip do prefixo "Deputado", detecção de formato.
- Testes de API atualizados para `por_casa`/`por_cargo`.
- Validação final: ingestão real 2013–2026; re-soma independente dos XLSX oficiais (2 distritais, 1 ano transacional + 1 ano pivô); conferir que o total do ano pivô bate com Σ totalVerbaGeral; navegação real (busca distrital → perfil → panorama "Por casa" com 3 fatias).

## Fora de escopo

Governadores (ES etc.), vereadores, fotos/partidos dos distritais, unificação de identidade entre casas (quem foi distrital e virou federal segue como registros separados).
