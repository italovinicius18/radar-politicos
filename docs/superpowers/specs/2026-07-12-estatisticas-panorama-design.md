# Estatísticas do ano no Panorama — Design

**Data:** 2026-07-12
**Status:** Aprovado

## Objetivo

Ampliar o Panorama da home com estatísticas derivadas dos dados já coletados: média/mediana por partido, média por estado, média/mediana por casa, e quatro indicadores do ano (efeito fim de ano, transparência documental, concentração de fornecedores, fornecedores quase-exclusivos). Tudo respeita o seletor de ano existente.

## Definições estatísticas (fonte de verdade)

Base comum: **total do ano por parlamentar** (CTE `totais`: soma de `despesas.valor` por `politico_id` no ano, com partido/uf/fonte do político). Média e mediana são sempre **sobre os totais por parlamentar**, nunca por despesa individual.

- **Por partido**: `partido NULL → "Sem partido informado"` (82 distritais + 6 senadores); colunas partido, parlamentares, media, mediana; ordenado por média desc; lista completa.
- **Média por UF**: `uf NULL → "Não informado"`; uf, parlamentares, media; ordenado por média desc.
- **Por casa**: o bloco `por_casa` existente ganha `media` e `mediana` (por parlamentar da casa). Comparação justa entre regimes de cota diferentes — nota de rodapé na UI explicando que os tetos diferem por casa.
- **Efeito fim de ano**: dezembro vs média mensal. Se o ano selecionado tem `mes = 12` com dados, `ano_ref = ano`; senão `ano_ref` = maior ano ≤ selecionado com dezembro. `variacao_pct = (dezembro − media_mensal) / media_mensal × 100`, onde `media_mensal` = média das somas mensais de `ano_ref`. `null` se não houver referência.
- **Transparência documental**: % de despesas do ano com `documento_url` preenchido — geral e por fonte (`por_fonte` com rótulo do registro). Só a Câmara publica link; a UI diz isso.
- **Concentração de fornecedores**: soma dos 10 maiores fornecedores do ano (group by fornecedor+cnpj, `fornecedor IS NOT NULL`) ÷ total do ano × 100. `null` se total ≤ 0.
- **Fornecedores quase-exclusivos** (sinal Serenata de Amor): fornecedores com `total ≥ R$ 50.000` no ano e `≥ 90%` desse total vindo de um único parlamentar. Payload: `quantidade` + `maior` (o de maior total: fornecedor, cnpj, total, pct_um_parlamentar, politico {id, nome}) ou `null`.

## API — extensão de `GET /api/visao-geral`

Novos campos no payload (breaking interno aceito; frontend atualizado junto):

```json
{
  "por_casa": [{ "fonte": "...", "rotulo": "...", "total": 0, "parlamentares": 0, "media": 0, "mediana": 0 }],
  "por_partido": [{ "partido": "PT", "parlamentares": 70, "media": 0, "mediana": 0 }],
  "media_por_uf": [{ "uf": "SP", "parlamentares": 74, "media": 0 }],
  "estatisticas": {
    "fim_de_ano": { "ano_ref": 2025, "dezembro": 0, "media_mensal": 0, "variacao_pct": 0 },
    "transparencia": { "pct_com_documento": 0, "por_fonte": [{ "fonte": "camara", "rotulo": "Câmara", "pct": 0 }] },
    "concentracao_top10_pct": 0,
    "quase_exclusivos": { "quantidade": 0, "maior": { "fornecedor": "...", "cnpj": "...", "total": 0, "pct_um_parlamentar": 0, "politico": { "id": "...", "nome": "..." } } }
  }
}
```

`fim_de_ano` e `quase_exclusivos.maior` podem ser `null`; `concentracao_top10_pct` pode ser `null`. Ano sem dados → blocos vazios/null, HTTP 200.

## Frontend (Panorama)

1. **Segunda linha de tiles** (mesma grade `.tiles`): Efeito fim de ano ("dez/{ano_ref}: +38% vs média mensal"); Transparência ("34% com nota anexada" + subtexto por fonte); Concentração ("Top 10 fornecedores = 18% do gasto"); Quase-exclusivos ("N fornecedores ≥90% de 1 parlamentar" + maior caso no subtexto com link para o perfil).
2. **Cartão "Gasto por partido"**: tabela compacta (partido · parl. · mediana · média) com `max-height` + scroll interno.
3. **Cartão "Média por estado"**: mini-barras (padrão visual existente, verde único) das UFs, com scroll.
4. **Cartão "Por casa"**: 3 linhas (rótulo, parlamentares, mediana, média) + rodapé sobre tetos de cota diferentes.

Sem cores novas (verde de marca já validado; texto em cor de texto). Tiles sem valor (null) mostram "—" com subtexto explicativo.

## Testes

- pytest: cada agregação com valores conferíveis à mão — incluindo mediana ≠ média (partido com 2+ parlamentares, banco construído no teste), NULL → rótulos de fallback, thresholds do quase-exclusivo (49k não conta; 50k/91% conta; 50k/89% não), fim_de_ano com dezembro ausente no ano selecionado (usa ano anterior), transparência 0% em fonte sem documento_url.
- Frontend: build TS + vitest existentes; verificação visual no navegador ao final.

## Fora de escopo

Comparação vs ano anterior por parlamentar (pareamento de mandatos), índice de Gini, normalização por teto de cota, página dedicada de estatísticas.
