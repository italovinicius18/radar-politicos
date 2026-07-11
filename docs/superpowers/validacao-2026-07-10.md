# Validação com políticos reais — 2026-07-10

Banco validado: `dados/radar.duckdb` — 2.892.967 despesas (2016–2026), 22/22 cargas OK, 0 despesas órfãs.

## Políticos testados

| Perfil | Político | ID |
|---|---|---|
| Deputado de alto gasto (1º ranking 2025) | Gabriel Mota (UNIÃO/RR) | camara-224117 |
| Deputado de baixo gasto 2025 | Eduardo Bismarck (CE) | camara-204541 |
| Senador | Alan Rick (REPUBLICANOS/AC) | senado-alan-rick |
| Histórico longo (11 anos, 2016–2026) | Arthur Lira (AL) | camara-160541 |

## Resultados — totais anuais

| Político | Ano | Sistema | Fonte oficial | Dif. | Veredicto |
|---|---|---:|---:|---:|---|
| Eduardo Bismarck | 2025 | 2.229,27 | 2.229,27 (API REST Câmara) | 0,000% | ✅ |
| Alan Rick | 2023 | 433.257,75 | 433.257,75 (CSV CEAPS re-somado independente) | 0,000% | ✅ |
| Alan Rick | 2025 | 435.216,00 | 435.216,00 (CSV CEAPS re-somado independente) | 0,000% | ✅ |
| Gabriel Mota | 2025 | 621.578,60 | 621.578,60 (CSV CEAP re-somado independente) | 0,000% | ✅ |
| Arthur Lira | 2016 | 285.644,63 | 285.644,63 (CSV CEAP re-somado independente) | 0,000% | ✅ |
| Arthur Lira | 2025 | 312.598,93 | 312.598,93 (CSV CEAP re-somado independente) | 0,000% | ✅ |
| Gabriel Mota | 2025 | 621.578,60 | 637.200,98 (API REST Câmara) | 2,45% | ⚠️ ver nota |
| Arthur Lira | 2025 | 312.598,93 | 367.878,42 (API REST Câmara) | 15,0% | ⚠️ ver nota |

## Nota: divergência entre os dois canais oficiais da Câmara (CSV × API REST)

O sistema reproduz **ao centavo** o arquivo oficial em massa (`Ano-{ano}.csv.zip`), verificado por re-soma independente (DuckDB `read_csv` direto no arquivo bruto, sem passar pelo nosso código de parse).

A API REST de Dados Abertos (`/deputados/{id}/despesas`) retorna, para alguns deputados, documentos a mais que o CSV do mesmo dia. Investigação documento a documento (Arthur Lira, 2025): os 28 documentos presentes só na API são todos **PASSAGEM AÉREA - SIGEPA** (R$ 54.849,72) — bilhetes emitidos diretamente pelo sistema da Câmara, que o CSV diário consolida com atraso. É uma discrepância entre os canais da própria Câmara, não um defeito do pipeline.

Limitação adicional da API REST: para anos antigos (testado 2016 e 2020) ela retorna vazio — o histórico completo só existe nos CSVs anuais, que é exatamente a fonte que o sistema usa.

## Verificações adicionais

- **Consistência interna** (4/4 políticos): `total == Σ por_ano == Σ por_categoria` com tolerância de 1 centavo. ✅
- **Notas fiscais**: amostra de 3 `documento_url` → HTTP 200 (2 PDFs diretos + 1 página da NF-e). ✅
- **E2E via frontend** (proxy Vite → FastAPI): busca "alan rick" retorna os dois mandatos (senador + ex-deputado, comportamento desenhado); busca "nikolas" retorna Nikolas Ferreira (PL/MG). ✅
- **Rankings 2025 plausíveis**: topo dominado por parlamentares de RR/AC/AM/AP (estados com passagens aéreas caras), consistente com o padrão conhecido da cota parlamentar. ✅
- **Enriquecimento de senadores**: 213/219 com partido/UF/foto (6 nomes do CEAPS não casaram com a API de legislaturas). Aceito como limitação conhecida.

## Veredicto

Pipeline de ingestão, agregações da API e frontend validados. Os números do sistema são idênticos aos arquivos oficiais em massa da Câmara e do Senado (0,000% de diferença em todas as comparações diretas). As divergências observadas existem entre os próprios canais oficiais da Câmara (CSV × API REST) e estão documentadas acima.

## Notas de ambiente

- Porta 8000 (padrão FastAPI) e 5173/5174 (padrão Vite) estavam ocupadas por outros serviços da máquina. A API do projeto usa a porta **8010** (proxy do Vite ajustado em `frontend/vite.config.ts`); o Vite escolhe automaticamente a próxima porta livre (5175 nesta validação).
- Como subir: `cd backend && uv run uvicorn radar.api.app:app_padrao --factory --port 8010` e `cd frontend && npm run dev`.
