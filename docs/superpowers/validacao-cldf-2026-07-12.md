# Validação da fonte CLDF — 2026-07-12

Ingestão real: **14/14 cargas OK (2013–2026), 21.358 despesas, 82 deputados distritais, 0 despesas órfãs.**

## Re-soma independente (lógica de parse própria, direto nos XLSX oficiais)

| Distrital | Ano | Formato | Sistema | Re-soma oficial | Dif. | Veredicto |
|---|---|---|---|---:|---:|---|
| Chico Vigilante | 2016 | transacional | 277.531,79 | 277.531,79 | 0,00 | ✅ |
| Chico Vigilante | 2025 | pivô (Σ totalVerbaGeral) | 180.803,47 | 180.803,47 | 0,00 | ✅ |

O invariante do formato pivô (categorias + glosa negativa + resíduo "Outras (não detalhado no dado oficial)" = totalVerbaGeral) segurou nos dados reais.

## Multi-fonte na API e na UI

- `/api/visao-geral?ano=2025`: `por_casa` com 3 casas (Câmara R$ 241,1 mi/562, CLDF R$ 3,4 mi/20, Senado R$ 37,2 mi/82) e `por_cargo` com 3 cargos. ✅
- Home: barra "Por casa" com 3 fatias (cores validadas), tile de parlamentares dinâmico, busca "chico vigilante" → perfil do distrital com gráficos. Zero erros de console. ✅

## O que a ingestão real ensinou (corrigido durante a execução)

1. **2013 tem colunas trocadas** (DATA antes de NR_COMPROVANTE) → parse passou a mapear colunas pelo nome do cabeçalho.
2. **Valores como string BR** em 8.554 células ("198,84", "9,900,00", "R$ 5.000,00" com NBSP) → parser tolerante; verificado empiricamente que em todos os 14 arquivos nenhuma string usa ponto como decimal (0 casos ambíguos).
3. **Datas como string** em anos antigos → conversor tolerante (datetime/date/ISO/DD/MM/AAAA); linhas sem data ou sem valor são descartadas (sem competência/valor não há despesa) — comportamento documentado por teste.
4. **Regras de categoria** ajustadas para singular/plural reais ("Locação e manutenção de imóveis", "Locação De Veículo").

## Inconsistências do dado oficial (documentadas, ingeridas fielmente)

- O arquivo de 2018 traz uma **linha duplicada com valor errado na origem**: o comprovante 89524 (Auto Posto, Cláudio Abrantes, jan/2018) aparece como `248.998` (float — R$ 249, plausível para combustível) e de novo como `248998` (inteiro — R$ 248.998,00, absurdo). Ingerimos o que o arquivo oficial publica; o perfil do deputado reflete a soma oficial.
- 2024 transacional tem só ~330 linhas na origem (arquivo oficial visivelmente incompleto); 2025+ não publica fornecedor/data (export pivô do Power BI) — na UI esses campos aparecem como "—" e a data cai no fallback mês/ano.
- ~13.500 despesas antigas vêm sem CLASSIFICACAO na origem → "Não especificada".

## Veredicto

Fonte CLDF validada: números idênticos aos arquivos oficiais nas re-somas independentes (0,00 de diferença nos dois formatos), sistema multi-fonte funcionando de ponta a ponta. Limitações herdadas do dado oficial documentadas acima.
