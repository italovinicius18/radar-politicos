# Fonte CLDF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar deputados distritais do DF (verbas indenizatórias da CLDF, 2013–2026) como terceira fonte, tornando o sistema genuinamente multi-fonte.

**Architecture:** Novo módulo de fonte `cldf.py` (contrato padrão `FONTE`/`baixar`/`parse`) que lê XLSX em dois formatos (transacional 2013–2024 e pivô Power BI 2025–2026, com linha residual para o total bater com o oficial). Registro central de fontes substitui os hardcodes Câmara/Senado na API (`por_casa`, `por_cargo`) e no frontend (rótulos/cores).

**Tech Stack:** openpyxl (novo), FastAPI + DuckDB, React/recharts existentes.

## Global Constraints

- Contrato de fonte existente: `FONTE = "cldf"`, `baixar(ano: int, pasta: Path) -> Path` (não re-baixa se existe), `parse(caminho) -> Iterator[tuple[dict politico, dict despesa]]` com as mesmas chaves das outras fontes.
- Dataset CKAN (verificado 2026-07-12): `https://dados.cl.df.gov.br/api/3/action/package_show?id=verbas-indenizatorias` — um recurso XLSX por ano 2013–2026; parse único via openpyxl (**sem** `read_only=True` — exports do Power BI reportam dimensões erradas nesse modo).
- Formato transacional (2013–2024): colunas `NOME_PARLAMENTAR, CPF_PARLAMENTAR, NOME_PRESTADOR, CNPJ_PRESTADOR, CPF_PRESTADOR, NR_COMPROVANTE, DATA_COMPROVANTE (datetime), VALOR_DESPESA, CLASSIFICACAO, OBSERVACOES`.
- Formato pivô (2025–2026): linhas de filtro, depois header `ano, mês, deputado, <categorias...>, Glosa, totalVerbaGeral`. **Invariante obrigatório**: a soma das despesas emitidas por linha (categorias + glosa negativa + resíduo "Outras (não detalhado no dado oficial)") é exatamente `totalVerbaGeral`.
- Político: `id = cldf-{slug(nome sem prefixo "Deputado(a) ")}`, `cargo = "Deputado Distrital"`, `uf = "DF"`, `partido = None`, `foto_url = None`.
- API: `camara_senado` → `por_casa` (`[{fonte, rotulo, total, parlamentares}]`); `kpis.deputados/senadores` → `kpis.por_cargo` (`[{cargo, quantidade}]`); breaking interno aceito (frontend é o único consumidor, atualizado no mesmo plano).
- Cores de gráfico validadas (dataviz, todas PASS sobre `#f5f5f2`): camara `#1d7a4d`, senado `#0369a1`, cldf `#a07d10`. Fonte desconhecida → cinza `#475569` com rótulo = código da fonte.
- UI pt-BR; convenções existentes (SQL parametrizado, floats no JSON, flag `ativo` em efeitos React).

## File Structure

```
backend/radar/ingest/fontes/cldf.py       # nova fonte (baixar CKAN + parse 2 formatos)
backend/radar/fontes_registro.py          # registro central {fonte: rotulo, cargo}
backend/radar/ingest/normalizacao.py      # + 4 regras de categoria (IMOVEL, MAQUINA, MATERIA, GLOSA)
backend/radar/ingest/__main__.py          # + cldf no dict FONTES
backend/radar/api/app.py                  # visao_geral: por_casa + por_cargo
backend/tests/fixtures/gerar_cldf.py      # gera as fixtures XLSX
backend/tests/fixtures/cldf_transacional.xlsx / cldf_pivo.xlsx
backend/tests/test_cldf.py                # testes da fonte
backend/tests/test_api.py                 # testes de visao_geral atualizados
frontend/src/lib/fontes.ts                # registro de rótulo/cor por fonte
frontend/src/lib/api.ts                   # tipos VisaoGeral atualizados
frontend/src/paginas/Panorama.tsx         # tile por_cargo + barra "Por casa" N fatias
frontend/src/paginas/Rankings.tsx         # opção "Deputado Distrital"
```

---

### Task 1: Fonte CLDF (parse dos dois formatos + download CKAN)

**Files:**
- Create: `backend/radar/ingest/fontes/cldf.py`, `backend/tests/fixtures/gerar_cldf.py`, `backend/tests/test_cldf.py`
- Modify: `backend/radar/ingest/normalizacao.py` (4 regras novas), `backend/tests/test_normalizacao.py`
- Test: `backend/tests/test_cldf.py`

**Interfaces:**
- Consumes: `normalizacao.normalizar_categoria/slug`; contrato de fonte.
- Produces: módulo `cldf` com `FONTE = "cldf"`, `baixar(ano, pasta) -> Path`, `parse(caminho) -> Iterator[tuple[dict, dict]]`; constante `CATEGORIA_RESIDUAL = "Outras (não detalhado no dado oficial)"`.

- [ ] **Step 1: Adicionar openpyxl e gerar fixtures**

```bash
cd backend && uv add openpyxl
```

`backend/tests/fixtures/gerar_cldf.py`:
```python
"""Gera as fixtures XLSX da CLDF (rodar uma vez: uv run python tests/fixtures/gerar_cldf.py)."""
from datetime import datetime
from pathlib import Path

import openpyxl

PASTA = Path(__file__).parent

wb = openpyxl.Workbook()
ws = wb.active
ws.append([
    "NOME_PARLAMENTAR", "CPF_PARLAMENTAR", "NOME_PRESTADOR", "CNPJ_PRESTADOR",
    "CPF_PRESTADOR", "NR_COMPROVANTE", "DATA_COMPROVANTE", "VALOR_DESPESA",
    "CLASSIFICACAO", "OBSERVACOES",
])
ws.append(["Deputado Chico Vigilante", "111", "PAPELARIA ALFA LTDA",
           "01.111.111/0001-11", None, "10", datetime(2016, 3, 5), 250.0,
           "MATERIAL DE ESCRITÓRIO", None])
ws.append(["Deputado Chico Vigilante", "111", "POSTO BETA", None,
           "222.333.444-55", "11", datetime(2016, 3, 20), 100.0, None,
           "abastecimento"])
ws.append(["Deputada Jane Klebia", "222", "IMOBILIÁRIA GAMA",
           "02.222.222/0002-22", None, "12", datetime(2016, 4, 1), 3000.0,
           "Locação de imóvel", None])
wb.save(PASTA / "cldf_transacional.xlsx")

wb = openpyxl.Workbook()
ws = wb.active
ws.append(["Filtros aplicados:\nAno é 2025"] + [None] * 6)
ws.append([None] * 7)
ws.append(["ano", "mês", "deputado", "Imóvel", "Veículos", "Glosa", "totalVerbaGeral"])
ws.append([2025, "abr", "CHICO VIGILANTE", 1000, 500, 0, 1800])
ws.append([2025, "mai", "JANE KLEBIA", 2000, None, 100, 1900])
wb.save(PASTA / "cldf_pivo.xlsx")
print("fixtures geradas")
```

Run: `cd backend && uv run python tests/fixtures/gerar_cldf.py`
Expected: `fixtures geradas` e os dois `.xlsx` criados.

- [ ] **Step 2: Regras novas de categoria (TDD)**

Acrescentar a `backend/tests/test_normalizacao.py`:
```python
def test_normalizar_categoria_cldf():
    assert normalizar_categoria("Imóvel") == "Manutenção de escritório"
    assert normalizar_categoria("Locação de imóvel") == "Manutenção de escritório"
    assert normalizar_categoria("Maquina Equipamento") == "Manutenção de escritório"
    assert normalizar_categoria("Aquisição Materias") == "Manutenção de escritório"
    assert normalizar_categoria("Glosa") == "Glosas e estornos"
```

Run: `cd backend && uv run pytest tests/test_normalizacao.py -v` → o novo FAIL.

Em `backend/radar/ingest/normalizacao.py`, acrescentar a `_REGRAS_CATEGORIA` (logo após a regra `("MATERIAL DE CONSUMO", "Manutenção de escritório")`):
```python
    ("IMOVEL", "Manutenção de escritório"),
    ("MAQUINA", "Manutenção de escritório"),
    ("MATERIA", "Manutenção de escritório"),
    ("GLOSA", "Glosas e estornos"),
```

Run de novo → PASS (todos).

- [ ] **Step 3: Testes da fonte que falham**

`backend/tests/test_cldf.py`:
```python
from pathlib import Path

from radar.ingest.fontes import cldf

FIXTURES = Path(__file__).parent / "fixtures"


def _pares(nome):
    return list(cldf.parse(FIXTURES / nome))


def test_transacional_gera_pares_e_politico():
    pares = _pares("cldf_transacional.xlsx")
    assert len(pares) == 3
    politico, despesa = pares[0]
    assert politico == {
        "id": "cldf-chico-vigilante",
        "nome": "Chico Vigilante",  # prefixo "Deputado " removido
        "cargo": "Deputado Distrital",
        "partido": None,
        "uf": "DF",
        "foto_url": None,
        "fonte": "cldf",
    }
    assert despesa["ano"] == 2016 and despesa["mes"] == 3
    assert despesa["data"].isoformat() == "2016-03-05"
    assert despesa["categoria"] == "Manutenção de escritório"
    assert despesa["fornecedor"] == "PAPELARIA ALFA LTDA"
    assert despesa["fornecedor_cnpj"] == "01.111.111/0001-11"
    assert despesa["valor"] == 250.0


def test_transacional_classificacao_vazia_e_cpf_prestador():
    _, despesa = _pares("cldf_transacional.xlsx")[1]
    assert despesa["categoria"] == "Não especificada"
    assert despesa["fornecedor_cnpj"] == "222.333.444-55"
    assert despesa["descricao"] == "abastecimento"


def test_pivo_emite_categorias_residuo_e_glosa():
    pares = _pares("cldf_pivo.xlsx")
    # linha 1: Imóvel 1000 + Veículos 500 + resíduo 300 = 1800
    # linha 2: Imóvel 2000 + glosa -100 (resíduo 0, não emitido) = 1900
    assert len(pares) == 5
    chico = [d for p, d in pares if p["id"] == "cldf-chico-vigilante"]
    assert round(sum(d["valor"] for d in chico), 2) == 1800.00
    residuo = [d for d in chico if d["categoria"] == cldf.CATEGORIA_RESIDUAL]
    assert len(residuo) == 1 and residuo[0]["valor"] == 300.0
    jane = [d for p, d in pares if p["id"] == "cldf-jane-klebia"]
    assert round(sum(d["valor"] for d in jane), 2) == 1900.00
    glosa = [d for d in jane if d["categoria"] == "Glosas e estornos"]
    assert len(glosa) == 1 and glosa[0]["valor"] == -100.0


def test_pivo_mes_e_campos_nulos():
    _, despesa = _pares("cldf_pivo.xlsx")[0]
    assert despesa["ano"] == 2025 and despesa["mes"] == 4  # "abr"
    assert despesa["data"] is None
    assert despesa["fornecedor"] is None and despesa["documento_url"] is None


def test_mesmo_nome_gera_mesmo_id_nos_dois_formatos():
    ids_t = {p["id"] for p, _ in _pares("cldf_transacional.xlsx")}
    ids_p = {p["id"] for p, _ in _pares("cldf_pivo.xlsx")}
    assert ids_t == ids_p == {"cldf-chico-vigilante", "cldf-jane-klebia"}
```

Run: `cd backend && uv run pytest tests/test_cldf.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 4: Implementar a fonte**

`backend/radar/ingest/fontes/cldf.py`:
```python
import re
from collections.abc import Iterator
from pathlib import Path

import httpx
import openpyxl

from radar.ingest.normalizacao import normalizar_categoria, slug

FONTE = "cldf"
CARGO = "Deputado Distrital"
URL_DATASET = "https://dados.cl.df.gov.br/api/3/action/package_show?id=verbas-indenizatorias"
CATEGORIA_RESIDUAL = "Outras (não detalhado no dado oficial)"
_MES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}


def baixar(ano: int, pasta: Path) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"cldf-{ano}.xlsx"
    if destino.exists():
        return destino
    resposta = httpx.get(URL_DATASET, timeout=60, follow_redirects=True)
    resposta.raise_for_status()
    recursos = resposta.json()["result"]["resources"]
    candidatos = [
        r for r in recursos
        if r["format"].upper() == "XLSX" and str(ano) in r["name"]
    ]
    if not candidatos:
        raise ValueError(f"CLDF: nenhum recurso XLSX para {ano}")
    with httpx.stream("GET", candidatos[0]["url"], timeout=300, follow_redirects=True) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for pedaco in r.iter_bytes():
                f.write(pedaco)
    return destino


def parse(caminho: Path) -> Iterator[tuple[dict, dict]]:
    # read_only=False de propósito: exports do Power BI trazem dimensões erradas
    wb = openpyxl.load_workbook(caminho)
    linhas = wb.active.iter_rows(values_only=True)
    primeira = next(linhas, None)
    if primeira is None:
        return
    if str(primeira[0] or "").strip() == "NOME_PARLAMENTAR":
        yield from _parse_transacional(linhas)
    else:
        yield from _parse_pivo(linhas)
    wb.close()


def _politico(nome_bruto: str) -> dict:
    nome = re.sub(r"^deputad[oa]\s+", "", str(nome_bruto).strip(), flags=re.IGNORECASE)
    return {
        "id": f"cldf-{slug(nome)}",
        "nome": nome,
        "cargo": CARGO,
        "partido": None,
        "uf": "DF",
        "foto_url": None,
        "fonte": FONTE,
    }


def _parse_transacional(linhas) -> Iterator[tuple[dict, dict]]:
    for linha in linhas:
        if not linha or not linha[0] or linha[6] is None:
            continue
        politico = _politico(linha[0])
        data = linha[6].date()
        classificacao = str(linha[8]).strip() if linha[8] else ""
        despesa = {
            "politico_id": politico["id"],
            "ano": data.year,
            "mes": data.month,
            "data": data,
            "categoria": normalizar_categoria(classificacao),
            "categoria_original": classificacao,
            "descricao": str(linha[9]).strip() if linha[9] else None,
            "fornecedor": str(linha[2]).strip() if linha[2] else None,
            "fornecedor_cnpj": str(linha[3] or linha[4] or "").strip() or None,
            "valor": float(linha[7] or 0),
            "documento_url": None,
            "fonte": FONTE,
        }
        yield politico, despesa


def _despesa_pivo(politico, ano, mes, categoria_original, valor, residual=False):
    return {
        "politico_id": politico["id"],
        "ano": ano,
        "mes": mes,
        "data": None,
        "categoria": CATEGORIA_RESIDUAL if residual else normalizar_categoria(categoria_original),
        "categoria_original": categoria_original,
        "descricao": None,
        "fornecedor": None,
        "fornecedor_cnpj": None,
        "valor": valor,
        "documento_url": None,
        "fonte": FONTE,
    }


def _parse_pivo(linhas) -> Iterator[tuple[dict, dict]]:
    cabecalho = None
    for linha in linhas:
        if linha and str(linha[0] or "").strip().lower() == "ano":
            cabecalho = [str(c or "").strip() for c in linha]
            break
    if cabecalho is None:
        raise ValueError("CLDF: cabeçalho do formato pivô não encontrado")
    idx_glosa = cabecalho.index("Glosa")
    idx_total = cabecalho.index("totalVerbaGeral")
    categorias = cabecalho[3:idx_glosa]
    for linha in linhas:
        if not linha or not linha[2] or linha[idx_total] is None:
            continue
        politico = _politico(linha[2])
        ano = int(linha[0])
        mes = _MES.get(str(linha[1] or "").strip().lower()[:3])
        total = float(linha[idx_total])
        soma = 0.0
        for i, categoria in enumerate(categorias, start=3):
            valor = float(linha[i] or 0)
            if valor == 0:
                continue
            soma += valor
            yield politico, _despesa_pivo(politico, ano, mes, categoria, valor)
        glosa = float(linha[idx_glosa] or 0)
        if glosa != 0:
            yield politico, _despesa_pivo(politico, ano, mes, "Glosa", -glosa)
        # invariante: soma das despesas emitidas == totalVerbaGeral
        residuo = round(total - soma + glosa, 2)
        if residuo != 0:
            yield politico, _despesa_pivo(politico, ano, mes, CATEGORIA_RESIDUAL, residuo, residual=True)
```

- [ ] **Step 5: Rodar e ver passar**

Run: `cd backend && uv run pytest -q`
Expected: 44 passed (38 + 5 de cldf + 1 de normalização)

- [ ] **Step 6: Commit**

```bash
git add backend
git commit -m "feat: fonte CLDF (deputados distritais) com formatos transacional e pivô"
```

---

### Task 2: Registro de fontes + API `por_casa`/`por_cargo` + CLI

**Files:**
- Create: `backend/radar/fontes_registro.py`
- Modify: `backend/radar/api/app.py` (endpoint `visao_geral`), `backend/radar/ingest/__main__.py`, `backend/tests/test_api.py`

**Interfaces:**
- Consumes: endpoint `visao_geral` existente; fonte `cldf` (Task 1).
- Produces: `fontes_registro.FONTES: dict[str, dict]` com chaves `rotulo` e `cargo`; payload novo de `/api/visao-geral`: `kpis.por_cargo: [{cargo, quantidade}]` (substitui `deputados`/`senadores`), `por_casa: [{fonte, rotulo, total, parlamentares}]` (substitui `camara_senado`). CLI aceita `--fontes camara,senado,cldf`.

- [ ] **Step 1: Atualizar testes de API (falham)**

Em `backend/tests/test_api.py`, no teste `test_visao_geral_2024`, substituir a linha
`assert k["deputados"] == 2 and k["senadores"] == 1 and k["parlamentares"] == 3` por:
```python
    assert k["parlamentares"] == 3
    assert {"cargo": "Deputado Federal", "quantidade": 2} in k["por_cargo"]
    assert {"cargo": "Senador", "quantidade": 1} in k["por_cargo"]
```
e substituir a asserção de `camara_senado` por:
```python
    assert {"fonte": "camara", "rotulo": "Câmara", "total": 6300.00, "parlamentares": 2} in corpo["por_casa"]
```

Run: `cd backend && uv run pytest tests/test_api.py -v -k visao` → test_visao_geral_2024 FAIL.

- [ ] **Step 2: Implementar registro e API**

`backend/radar/fontes_registro.py`:
```python
FONTES = {
    "camara": {"rotulo": "Câmara", "cargo": "Deputado Federal"},
    "senado": {"rotulo": "Senado", "cargo": "Senador"},
    "cldf": {"rotulo": "CLDF", "cargo": "Deputado Distrital"},
}


def rotulo(fonte: str) -> str:
    return FONTES.get(fonte, {}).get("rotulo", fonte)
```

Em `backend/radar/api/app.py`: importar `from radar.fontes_registro import rotulo` no topo. No `visao_geral`:
- substituir o bloco `deputados = ... / senadores = ... / parlamentares = ...` por:
```python
            por_cargo = [
                {"cargo": cargo, "quantidade": qtd}
                for cargo, qtd in sorted(cargos.items())
            ]
            parlamentares = sum(cargos.values())
```
- no dict de retorno, dentro de `kpis`, remover `"deputados"`/`"senadores"` e acrescentar `"por_cargo": por_cargo`;
- substituir a chave `"camara_senado"` por:
```python
            "por_casa": [
                {"fonte": f, "rotulo": rotulo(f), "total": float(t), "parlamentares": q}
                for f, t, q in camara_senado
            ],
```
(o nome da variável local `camara_senado` pode ser renomeado para `por_casa_linhas` na mesma edição).

Em `backend/radar/ingest/__main__.py`: trocar o import para `from radar.ingest.fontes import camara, cldf, senado` e o dict para `FONTES = {"camara": camara, "senado": senado, "cldf": cldf}` (default `--fontes` continua `"camara,senado"` — a carga da CLDF usa `--fontes cldf --anos 2013-2026`).

- [ ] **Step 3: Rodar e ver passar**

Run: `cd backend && uv run pytest -q`
Expected: 44 passed

- [ ] **Step 4: Commit**

```bash
git add backend
git commit -m "feat: registro de fontes e visão geral multi-casa (por_casa/por_cargo)"
```

---

### Task 3: Frontend multi-fonte

**Files:**
- Create: `frontend/src/lib/fontes.ts`
- Modify: `frontend/src/lib/api.ts`, `frontend/src/paginas/Panorama.tsx`, `frontend/src/paginas/Rankings.tsx`

**Interfaces:**
- Consumes: payload novo da Task 2; `infoFonte(fonte)` definido aqui.
- Produces: UI mostrando N casas/cargos dinamicamente.

- [ ] **Step 1: Registro de fontes no frontend**

`frontend/src/lib/fontes.ts`:
```ts
// Cores validadas pelo verificador do dataviz (par a par sobre #f5f5f2)
export const FONTES: Record<string, { rotulo: string; cor: string }> = {
  camara: { rotulo: 'Câmara', cor: '#1d7a4d' },
  senado: { rotulo: 'Senado', cor: '#0369a1' },
  cldf: { rotulo: 'CLDF', cor: '#a07d10' },
}

export function infoFonte(fonte: string): { rotulo: string; cor: string } {
  return FONTES[fonte] ?? { rotulo: fonte, cor: '#475569' }
}
```

- [ ] **Step 2: Tipos em api.ts**

Em `frontend/src/lib/api.ts`, na interface `VisaoGeral`:
- em `kpis`, remover `deputados: number` e `senadores: number`; acrescentar `por_cargo: { cargo: string; quantidade: number }[]`;
- substituir `camara_senado: { fonte: string; total: number; parlamentares: number }[]` por `por_casa: { fonte: string; rotulo: string; total: number; parlamentares: number }[]`.

- [ ] **Step 3: Panorama.tsx**

- Remover as constantes `COR_SENADO` (manter `COR_MARCA` para colunas/minibars) e importar `infoFonte` de `../lib/fontes`.
- `const totalCS = dados.camara_senado...` → `const totalCasas = dados.por_casa.reduce((s, x) => s + x.total, 0)`.
- Tile "Parlamentares com gastos": substituir `<small>{kpis.deputados} deputados · {kpis.senadores} senadores</small>` por:
```tsx
          <small>{kpis.por_cargo.map((c) => `${c.cargo}: ${c.quantidade}`).join(' · ')}</small>
```
- Cartão "Câmara × Senado" vira "Por casa": título `<h3>Por casa</h3>`; o split e a legenda iteram `dados.por_casa` usando `infoFonte(x.fonte).cor` e `x.rotulo`:
```tsx
          <div className="split-bar">
            {dados.por_casa.map((x) => (
              <div
                key={x.fonte}
                className="split-parte"
                style={{
                  width: totalCasas ? `${(x.total / totalCasas) * 100}%` : `${100 / dados.por_casa.length}%`,
                  background: infoFonte(x.fonte).cor,
                }}
              />
            ))}
          </div>
          {dados.por_casa.map((x) => (
            <div key={x.fonte} className="split-legenda">
              <span className="pino" style={{ background: infoFonte(x.fonte).cor }} />
              {x.rotulo}: {formatarBRLCompacto(x.total)}
              {' '}({x.parlamentares} parlamentares{totalCasas ? `, ${((x.total / totalCasas) * 100).toFixed(0)}%` : ''})
            </div>
          ))}
```

- [ ] **Step 4: Rankings.tsx**

No select de cargo, acrescentar após a opção Senadores:
```tsx
          <option value="Deputado Distrital">Deputados Distritais</option>
```

- [ ] **Step 5: Build + testes**

Run: `cd frontend && npm run build && npm test`
Expected: build sem erros TS; 5 testes passam.

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "feat: frontend multi-fonte (por casa, cargos dinâmicos, filtro distrital)"
```

---

### Task 4: Ingestão CLDF 2013–2026 + validação

**Files:**
- Modify: `README.md` (linha da ingestão CLDF)
- Create: `docs/superpowers/validacao-cldf-2026-07-12.md`

- [ ] **Step 1: Ingestão real**

Run: `cd backend && uv run python -m radar.ingest --anos 2013-2026 --fontes cldf --db ../dados/radar.duckdb --pasta ../dados`
Expected: 14 cargas ✔ (2013–2026), dezenas de milhares de despesas no total; enriquecimento do senado roda sem efeito (0 novos). Exit 0.

- [ ] **Step 2: Sanidade**

```bash
cd backend && uv run python -c "
from radar.db import conectar
con = conectar('../dados/radar.duckdb', somente_leitura=True)
print('cldf por ano:', con.execute(\"SELECT ano, count(*), round(sum(valor)) FROM despesas WHERE fonte='cldf' GROUP BY ano ORDER BY ano\").fetchall())
print('distritais:', con.execute(\"SELECT count(*) FROM politicos WHERE fonte='cldf'\").fetchone())
print('órfãs:', con.execute('SELECT count(*) FROM despesas d LEFT JOIN politicos p ON p.id=d.politico_id WHERE p.id IS NULL').fetchone())
print('categorias cldf:', con.execute(\"SELECT categoria, count(*) FROM despesas WHERE fonte='cldf' GROUP BY 1 ORDER BY 2 DESC LIMIT 12\").fetchall())
"
```
Expected: todos os anos 2013–2026 presentes; políticos na casa de dezenas (mandatos acumulados); 0 órfãs; categorias coerentes.

- [ ] **Step 3: Validação independente**

Re-soma direto dos XLSX baixados (sem passar pelo parse do projeto), comparando com `/api/politicos/{id}/resumo`:
- 1 distrital num ano transacional (ex.: 2016): somar `VALOR_DESPESA` das linhas do deputado no arquivo `dados/cldf/cldf-2016.xlsx` e comparar com o total do ano no resumo (tolerância 0,01).
- 1 distrital num ano pivô (2025): somar `totalVerbaGeral` das linhas do deputado e comparar com o resumo do ano (deve bater exato — é o invariante).
- Conferir que o panorama (`/api/visao-geral?ano=2025`) tem `por_casa` com 3 fontes e `por_cargo` com 3 cargos.
(API precisa ser reiniciada após o deploy do código novo.)

- [ ] **Step 4: README + relatório de validação + commit**

No `README.md`, após a linha da ingestão existente, acrescentar:
```bash
# CLDF (deputados distritais) cobre 2013-2026:
cd backend && uv run python -m radar.ingest --anos 2013-2026 --fontes cldf --db ../dados/radar.duckdb --pasta ../dados
```
Criar `docs/superpowers/validacao-cldf-2026-07-12.md` com a tabela: distrital, ano, total sistema, total re-somado, diferença, veredicto + observação sobre o formato pivô (sem fornecedor/data em 2025+, resíduo "Outras"). Commit:
```bash
git add README.md docs backend
git commit -m "feat: ingestão CLDF 2013-2026 validada"
```

## Self-Review (feito na escrita)

- **Cobertura do spec:** fonte 2 formatos ✔ (Task 1), invariante do pivô testado ✔, registro backend+frontend ✔ (Tasks 2–3), por_casa/por_cargo ✔, cores validadas ✔, regras de categoria novas ✔, CLI ✔, ingestão+validação ✔ (Task 4). Fora de escopo respeitado.
- **Placeholders:** nenhum.
- **Consistência:** chaves de `por_casa`/`por_cargo` idênticas entre Task 2 (payload), testes e Task 3 (tipos TS); `CATEGORIA_RESIDUAL` usado em Task 1 e citado na validação; contagem de testes 38→44 conferida (5 cldf + 1 normalização).
