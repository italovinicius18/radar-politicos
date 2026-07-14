# Estatísticas do Panorama Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Panorama ganha média/mediana por partido, média por UF, média/mediana por casa e quatro indicadores do ano (fim de ano, transparência documental, concentração e quase-exclusivos de fornecedores).

**Architecture:** Extensão do endpoint `/api/visao-geral` (CTE de totais por parlamentar + agregações `avg`/`median` do DuckDB + consultas de fornecedores) e do componente `Panorama.tsx` (segunda linha de tiles + três cartões). Sem dependências novas.

**Tech Stack:** DuckDB (`median`, `arg_max`, `count(col)`), FastAPI, React existentes.

## Global Constraints

- Média/mediana SEMPRE sobre os **totais do ano por parlamentar** (CTE `totais`), nunca por despesa.
- Fallbacks: partido NULL → "Sem partido informado"; uf NULL → "Não informado".
- Quase-exclusivos: `total ≥ 50000` E `max(por parlamentar) ≥ total × 0.9`; ordenado por total desc; payload `{quantidade, maior|null}`.
- Fim de ano: `ano_ref = max(ano) com mes=12 e ano ≤ selecionado`; `variacao_pct = (dezembro − media_mensal)/media_mensal × 100`; bloco `null` sem referência.
- Transparência: `count(documento_url)/count(*)` por fonte (rótulos do `fontes_registro`) + geral ponderado.
- Concentração: soma dos 10 maiores fornecedores ÷ total do ano × 100; `null` se total ≤ 0.
- Convenções: SQL parametrizado, floats no JSON, UI pt-BR, sem cores novas (verde `#1d7a4d` p/ mini-barras, texto em cor de texto), valores com `formatarBRLCompacto`.
- Payload conforme spec (breaking interno aceito; frontend atualizado no mesmo plano).

## File Structure

```
backend/radar/api/app.py       # visao_geral: SQL_TOTAIS + 6 consultas novas + payload
backend/tests/test_api.py      # testes com fixture existente + banco dedicado p/ mediana/limiares
frontend/src/lib/api.ts        # tipos novos
frontend/src/paginas/Panorama.tsx  # 2ª linha de tiles + 3 cartões
frontend/src/index.css         # .tabela-rolavel, .tabela-compacta, .rodape-nota
```

---

### Task 1: Backend — agregações e indicadores no visão-geral

**Files:**
- Modify: `backend/radar/api/app.py` (dentro de `visao_geral`)
- Test: `backend/tests/test_api.py` (acrescentar)

**Interfaces:**
- Consumes: fixture `cliente` (2024: camara-1/PT/SP total 1300, camara-2/PL/MG total 5000, senado-joao-neto/MDB/GO total 2000; docs: 2 de 3 despesas da camara com documento_url, senado sem; nenhum mês 12 em ano algum).
- Produces: payload novo — `por_casa[i]` ganha `media`/`mediana`; novos `por_partido: [{partido, parlamentares, media, mediana}]`, `media_por_uf: [{uf, parlamentares, media}]`, `estatisticas: {fim_de_ano|null, transparencia|null, concentracao_top10_pct|null, quase_exclusivos: {quantidade, maior|null}}`.

- [ ] **Step 1: Testes que falham**

Acrescentar ao final de `backend/tests/test_api.py`:
```python
def test_visao_geral_por_partido_uf_casa(cliente):
    corpo = cliente.get("/api/visao-geral", params={"ano": 2024}).json()
    # partidos: 1 parlamentar cada -> media == mediana == total
    assert corpo["por_partido"][0] == {
        "partido": "PL", "parlamentares": 1, "media": 5000.0, "mediana": 5000.0
    }
    assert {"partido": "PT", "parlamentares": 1, "media": 1300.0, "mediana": 1300.0} in corpo["por_partido"]
    assert corpo["media_por_uf"][0] == {"uf": "MG", "parlamentares": 1, "media": 5000.0}
    casa_camara = next(x for x in corpo["por_casa"] if x["fonte"] == "camara")
    assert casa_camara["media"] == 3150.0 and casa_camara["mediana"] == 3150.0
    assert casa_camara["total"] == 6300.0 and casa_camara["parlamentares"] == 2


def test_visao_geral_estatisticas_fixture(cliente):
    e = cliente.get("/api/visao-geral", params={"ano": 2024}).json()["estatisticas"]
    # fixture não tem mês 12 em nenhum ano -> sem referência
    assert e["fim_de_ano"] is None
    # camara: 3 despesas, 2 com documento; senado: 1 sem -> geral 50%
    assert round(e["transparencia"]["pct_com_documento"], 2) == 50.0
    por_fonte = {x["fonte"]: x for x in e["transparencia"]["por_fonte"]}
    assert round(por_fonte["camara"]["pct"], 2) == 66.67
    assert por_fonte["senado"]["pct"] == 0.0
    assert por_fonte["camara"]["rotulo"] == "Câmara"
    # 4 fornecedores no ano, todos no top10 -> 100%
    assert round(e["concentracao_top10_pct"], 2) == 100.0
    # nenhum fornecedor >= 50k
    assert e["quase_exclusivos"] == {"quantidade": 0, "maior": None}


def test_visao_geral_estatisticas_ano_vazio(cliente):
    corpo = cliente.get("/api/visao-geral", params={"ano": 1999}).json()
    assert corpo["por_partido"] == [] and corpo["media_por_uf"] == []
    e = corpo["estatisticas"]
    assert e["fim_de_ano"] is None and e["transparencia"] is None
    assert e["concentracao_top10_pct"] is None
    assert e["quase_exclusivos"] == {"quantidade": 0, "maior": None}


def test_mediana_e_quase_exclusivos_banco_dedicado(tmp_path):
    from fastapi.testclient import TestClient

    from radar.api.app import criar_app
    from radar.db import conectar, criar_schema

    caminho = tmp_path / "est.duckdb"
    con = conectar(caminho)
    criar_schema(con)
    con.execute("""
        INSERT INTO politicos VALUES
        ('camara-10', 'Ana',   'Deputado Federal', 'XX', 'SP', NULL, 'camara'),
        ('camara-11', 'Bruno', 'Deputado Federal', 'XX', 'SP', NULL, 'camara'),
        ('camara-12', 'Carla', 'Deputado Federal', 'XX', 'SP', NULL, 'camara')
    """)
    # ano 2030: totais 100/200/900 -> media 400, mediana 200
    con.execute("""
        INSERT INTO despesas VALUES
        ('camara-10', 2030, 1, '2030-01-10', 'X', 'X', NULL, 'F1', '1', 100, NULL, 'camara'),
        ('camara-11', 2030, 1, '2030-01-11', 'X', 'X', NULL, 'F1', '1', 200, NULL, 'camara'),
        ('camara-12', 2030, 1, '2030-01-12', 'X', 'X', NULL, 'F1', '1', 900, NULL, 'camara')
    """)
    # ano 2031, limiares de quase-exclusivo:
    #  EXC91: 50.000 com 91% da Ana -> CONTA (maior)
    #  EXC89: 50.000 com 89% da Ana -> não conta (< 90%)
    #  PEQ:   49.000 com 100% da Ana -> não conta (< 50k)
    con.execute("""
        INSERT INTO despesas VALUES
        ('camara-10', 2031, 1, '2031-01-10', 'X', 'X', NULL, 'EXC91', '9', 45500, NULL, 'camara'),
        ('camara-11', 2031, 1, '2031-01-11', 'X', 'X', NULL, 'EXC91', '9',  4500, NULL, 'camara'),
        ('camara-10', 2031, 2, '2031-02-10', 'X', 'X', NULL, 'EXC89', '8', 44500, NULL, 'camara'),
        ('camara-11', 2031, 2, '2031-02-11', 'X', 'X', NULL, 'EXC89', '8',  5500, NULL, 'camara'),
        ('camara-10', 2031, 3, '2031-03-10', 'X', 'X', NULL, 'PEQ',   '7', 49000, NULL, 'camara')
    """)
    con.close()
    cliente = TestClient(criar_app(str(caminho)))

    corpo = cliente.get("/api/visao-geral", params={"ano": 2030}).json()
    assert corpo["por_partido"] == [
        {"partido": "XX", "parlamentares": 3, "media": 400.0, "mediana": 200.0}
    ]
    assert corpo["media_por_uf"] == [{"uf": "SP", "parlamentares": 3, "media": 400.0}]

    qe = cliente.get("/api/visao-geral", params={"ano": 2031}).json()["estatisticas"]["quase_exclusivos"]
    assert qe["quantidade"] == 1
    assert qe["maior"]["fornecedor"] == "EXC91"
    assert round(qe["maior"]["pct_um_parlamentar"], 1) == 91.0
    assert qe["maior"]["total"] == 50000.0
    assert qe["maior"]["politico"] == {"id": "camara-10", "nome": "Ana"}


def test_fim_de_ano_usa_ultimo_ano_com_dezembro(tmp_path):
    from fastapi.testclient import TestClient

    from radar.api.app import criar_app
    from radar.db import conectar, criar_schema

    caminho = tmp_path / "dez.duckdb"
    con = conectar(caminho)
    criar_schema(con)
    con.execute(
        "INSERT INTO politicos VALUES ('camara-20', 'Davi', 'Deputado Federal', 'YY', 'RJ', NULL, 'camara')"
    )
    # 2040: jan 100, fev 100, dez 400 -> media mensal 200, dez +100%
    # 2041: só jan (sem dezembro) -> deve referenciar 2040
    con.execute("""
        INSERT INTO despesas VALUES
        ('camara-20', 2040,  1, '2040-01-10', 'X', 'X', NULL, 'F', '1', 100, NULL, 'camara'),
        ('camara-20', 2040,  2, '2040-02-10', 'X', 'X', NULL, 'F', '1', 100, NULL, 'camara'),
        ('camara-20', 2040, 12, '2040-12-10', 'X', 'X', NULL, 'F', '1', 400, NULL, 'camara'),
        ('camara-20', 2041,  1, '2041-01-10', 'X', 'X', NULL, 'F', '1', 150, NULL, 'camara')
    """)
    con.close()
    cliente = TestClient(criar_app(str(caminho)))

    fe = cliente.get("/api/visao-geral", params={"ano": 2041}).json()["estatisticas"]["fim_de_ano"]
    assert fe["ano_ref"] == 2040
    assert fe["dezembro"] == 400.0 and fe["media_mensal"] == 200.0
    assert round(fe["variacao_pct"], 1) == 100.0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && uv run pytest tests/test_api.py -v -k "partido or estatisticas or mediana or fim_de_ano"`
Expected: 5 FAIL (KeyError `por_partido`/`estatisticas`)

- [ ] **Step 3: Implementar**

Em `backend/radar/api/app.py`, dentro de `visao_geral`, após a consulta de `fornecedores` (ainda dentro do `with con() as c:`), acrescentar:

```python
            SQL_TOTAIS = """
                SELECT p.id, p.partido, p.uf, p.fonte, sum(d.valor) AS total
                FROM despesas d JOIN politicos p ON p.id = d.politico_id
                WHERE d.ano = ? GROUP BY p.id, p.partido, p.uf, p.fonte
            """
            por_partido = c.execute(
                f"""WITH totais AS ({SQL_TOTAIS})
                    SELECT coalesce(partido, 'Sem partido informado') AS pt,
                           count(*), avg(total), median(total)
                    FROM totais GROUP BY pt ORDER BY 3 DESC""",
                (ano,),
            ).fetchall()
            media_por_uf = c.execute(
                f"""WITH totais AS ({SQL_TOTAIS})
                    SELECT coalesce(uf, 'Não informado') AS u, count(*), avg(total)
                    FROM totais GROUP BY u ORDER BY 3 DESC""",
                (ano,),
            ).fetchall()
            por_casa_linhas = c.execute(
                f"""WITH totais AS ({SQL_TOTAIS})
                    SELECT fonte, sum(total), count(*), avg(total), median(total)
                    FROM totais GROUP BY fonte ORDER BY fonte""",
                (ano,),
            ).fetchall()

            ano_ref = c.execute(
                "SELECT max(ano) FROM despesas WHERE mes = 12 AND ano <= ?", (ano,)
            ).fetchone()[0]
            fim_de_ano = None
            if ano_ref is not None:
                meses_ref = c.execute(
                    "SELECT mes, sum(valor) FROM despesas WHERE ano = ? AND mes IS NOT NULL GROUP BY mes",
                    (ano_ref,),
                ).fetchall()
                dezembro = next((float(t) for m, t in meses_ref if m == 12), 0.0)
                media_mensal = sum(float(t) for _, t in meses_ref) / len(meses_ref)
                if media_mensal:
                    fim_de_ano = {
                        "ano_ref": ano_ref,
                        "dezembro": dezembro,
                        "media_mensal": media_mensal,
                        "variacao_pct": (dezembro - media_mensal) / media_mensal * 100,
                    }

            linhas_doc = c.execute(
                "SELECT fonte, count(*), count(documento_url) FROM despesas "
                "WHERE ano = ? GROUP BY fonte ORDER BY fonte",
                (ano,),
            ).fetchall()
            transparencia = None
            if linhas_doc:
                total_n = sum(n for _, n, _ in linhas_doc)
                total_com = sum(cd for _, _, cd in linhas_doc)
                transparencia = {
                    "pct_com_documento": total_com * 100.0 / total_n,
                    "por_fonte": [
                        {"fonte": f, "rotulo": rotulo(f), "pct": cd * 100.0 / n}
                        for f, n, cd in linhas_doc
                    ],
                }

            top10, total_ano = c.execute(
                """WITH forn AS (
                       SELECT sum(valor) AS t FROM despesas
                       WHERE ano = ? AND fornecedor IS NOT NULL
                       GROUP BY fornecedor, coalesce(fornecedor_cnpj, '')
                       ORDER BY t DESC LIMIT 10)
                   SELECT (SELECT sum(t) FROM forn),
                          (SELECT sum(valor) FROM despesas WHERE ano = ?)""",
                (ano, ano),
            ).fetchone()
            concentracao_pct = (
                float(top10) * 100.0 / float(total_ano)
                if top10 is not None and total_ano is not None and float(total_ano) > 0
                else None
            )

            exclusivos = c.execute(
                """WITH por_parl AS (
                       SELECT fornecedor, coalesce(fornecedor_cnpj, '') AS cnpj,
                              politico_id, sum(valor) AS v
                       FROM despesas WHERE ano = ? AND fornecedor IS NOT NULL
                       GROUP BY 1, 2, 3),
                   agg AS (
                       SELECT fornecedor, cnpj, sum(v) AS total, max(v) AS maior_v,
                              arg_max(politico_id, v) AS pid
                       FROM por_parl GROUP BY 1, 2)
                   SELECT a.fornecedor, a.cnpj, a.total,
                          a.maior_v * 100.0 / a.total, p.id, p.nome
                   FROM agg a JOIN politicos p ON p.id = a.pid
                   WHERE a.total >= 50000 AND a.maior_v >= a.total * 0.9
                   ORDER BY a.total DESC""",
                (ano,),
            ).fetchall()
```

No dict de retorno:
- substituir o bloco `"por_casa": [...]` para usar `por_casa_linhas`:
```python
            "por_casa": [
                {"fonte": f, "rotulo": rotulo(f), "total": float(t), "parlamentares": q,
                 "media": float(m), "mediana": float(md)}
                for f, t, q, m, md in por_casa_linhas
            ],
```
(e remover a consulta antiga `camara_senado`, que ficou redundante — a soma por fonte agora vem da CTE)
- acrescentar:
```python
            "por_partido": [
                {"partido": pt, "parlamentares": q, "media": float(m), "mediana": float(md)}
                for pt, q, m, md in por_partido
            ],
            "media_por_uf": [
                {"uf": u, "parlamentares": q, "media": float(m)}
                for u, q, m in media_por_uf
            ],
            "estatisticas": {
                "fim_de_ano": fim_de_ano,
                "transparencia": transparencia,
                "concentracao_top10_pct": concentracao_pct,
                "quase_exclusivos": {
                    "quantidade": len(exclusivos),
                    "maior": {
                        "fornecedor": exclusivos[0][0],
                        "cnpj": exclusivos[0][1],
                        "total": float(exclusivos[0][2]),
                        "pct_um_parlamentar": float(exclusivos[0][3]),
                        "politico": {"id": exclusivos[0][4], "nome": exclusivos[0][5]},
                    }
                    if exclusivos
                    else None,
                },
            },
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && uv run pytest -q`
Expected: 53 passed (48 + 5 novos)

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: estatísticas por partido, UF, casa e indicadores do ano na visão geral"
```

---

### Task 2: Frontend — tiles de indicadores e cartões de partido/UF/casa

**Files:**
- Modify: `frontend/src/lib/api.ts`, `frontend/src/paginas/Panorama.tsx`, `frontend/src/index.css`

**Interfaces:**
- Consumes: payload da Task 1; `formatarBRL`, `formatarBRLCompacto`, `MESES_ABREV` existentes.

- [ ] **Step 1: Tipos em api.ts**

Na interface `VisaoGeral`: itens de `por_casa` ganham `media: number` e `mediana: number`; acrescentar após `por_casa`:
```ts
  por_partido: { partido: string; parlamentares: number; media: number; mediana: number }[]
  media_por_uf: { uf: string; parlamentares: number; media: number }[]
  estatisticas: {
    fim_de_ano: { ano_ref: number; dezembro: number; media_mensal: number; variacao_pct: number } | null
    transparencia: { pct_com_documento: number; por_fonte: { fonte: string; rotulo: string; pct: number }[] } | null
    concentracao_top10_pct: number | null
    quase_exclusivos: {
      quantidade: number
      maior: {
        fornecedor: string
        cnpj: string
        total: number
        pct_um_parlamentar: number
        politico: { id: string; nome: string }
      } | null
    }
  }
```

- [ ] **Step 2: Panorama.tsx — segunda linha de tiles**

Logo após o `</div>` da `.tiles` existente, acrescentar (usando `const e = dados.estatisticas` declarado junto de `totalCasas`):
```tsx
      <div className="tiles">
        <div className="cartao tile">
          <small>Efeito fim de ano</small>
          <div className="tile-valor">
            {e.fim_de_ano
              ? `${e.fim_de_ano.variacao_pct >= 0 ? '+' : ''}${e.fim_de_ano.variacao_pct.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`
              : '—'}
          </div>
          <small>
            {e.fim_de_ano
              ? `dez/${e.fim_de_ano.ano_ref} vs média mensal (${formatarBRLCompacto(e.fim_de_ano.media_mensal)})`
              : 'sem dezembro na base'}
          </small>
        </div>
        <div className="cartao tile">
          <small>Despesas com nota anexada</small>
          <div className="tile-valor">
            {e.transparencia
              ? `${e.transparencia.pct_com_documento.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`
              : '—'}
          </div>
          <small>
            {e.transparencia
              ? e.transparencia.por_fonte.map((f) => `${f.rotulo}: ${f.pct.toFixed(0)}%`).join(' · ')
              : 'sem dados no ano'}
          </small>
        </div>
        <div className="cartao tile">
          <small>Concentração de fornecedores</small>
          <div className="tile-valor">
            {e.concentracao_top10_pct !== null
              ? `${e.concentracao_top10_pct.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`
              : '—'}
          </div>
          <small>do gasto do ano vai para os 10 maiores fornecedores</small>
        </div>
        <div className="cartao tile">
          <small>Fornecedores quase-exclusivos</small>
          <div className="tile-valor">{e.quase_exclusivos.quantidade}</div>
          <small>
            ≥ R$ 50 mil no ano com ≥ 90% de um só parlamentar
            {e.quase_exclusivos.maior && (
              <>
                {' — maior: '}{e.quase_exclusivos.maior.fornecedor} ({formatarBRLCompacto(e.quase_exclusivos.maior.total)},{' '}
                {e.quase_exclusivos.maior.pct_um_parlamentar.toFixed(0)}% de{' '}
                <Link to={`/politico/${e.quase_exclusivos.maior.politico.id}`}>{e.quase_exclusivos.maior.politico.nome}</Link>)
              </>
            )}
          </small>
        </div>
      </div>
```

- [ ] **Step 3: Panorama.tsx — três cartões**

Após o `</div>` da `.tops`, acrescentar (com `const maxUf = dados.media_por_uf[0]?.media ?? 0`):
```tsx
      <div className="graficos">
        <div className="cartao">
          <h3>Gasto por partido (por parlamentar)</h3>
          <div className="tabela-rolavel">
            <table className="tabela-compacta">
              <thead>
                <tr><th>Partido</th><th>Parl.</th><th className="valor">Mediana</th><th className="valor">Média</th></tr>
              </thead>
              <tbody>
                {dados.por_partido.map((p) => (
                  <tr key={p.partido}>
                    <td>{p.partido}</td>
                    <td>{p.parlamentares}</td>
                    <td className="valor">{formatarBRLCompacto(p.mediana)}</td>
                    <td className="valor">{formatarBRLCompacto(p.media)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <small className="rodape-nota">Média longe da mediana indica gastador extremo puxando o partido para cima.</small>
        </div>
        <div className="cartao">
          <h3>Média por estado (por parlamentar)</h3>
          <div className="tabela-rolavel">
            {dados.media_por_uf.map((u) => (
              <div key={u.uf} className="minibar-linha">
                <div className="minibar-rotulo">
                  <span>{u.uf} <small>({u.parlamentares})</small></span>
                  <span className="top-valor">{formatarBRLCompacto(u.media)}</span>
                </div>
                <div className="minibar-trilha">
                  <div className="minibar" style={{ width: maxUf ? `${(u.media / maxUf) * 100}%` : 0 }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="cartao">
        <h3>Por casa (média e mediana por parlamentar)</h3>
        <table className="tabela-compacta">
          <thead>
            <tr><th>Casa</th><th>Parlamentares</th><th className="valor">Mediana</th><th className="valor">Média</th></tr>
          </thead>
          <tbody>
            {dados.por_casa.map((x) => (
              <tr key={x.fonte}>
                <td>{x.rotulo}</td>
                <td>{x.parlamentares}</td>
                <td className="valor">{formatarBRLCompacto(x.mediana)}</td>
                <td className="valor">{formatarBRLCompacto(x.media)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <small className="rodape-nota">Os tetos de cota diferem por casa — compare parlamentares dentro da mesma casa.</small>
      </div>
```

- [ ] **Step 4: CSS**

Acrescentar a `frontend/src/index.css`:
```css
.tabela-rolavel { max-height: 320px; overflow-y: auto; }
.tabela-compacta { font-size: 0.85rem; }
.tabela-compacta th { position: sticky; top: 0; background: #fff; }
.rodape-nota { color: #666; display: block; margin-top: 0.5rem; }
```

- [ ] **Step 5: Build + testes**

Run: `cd frontend && npm run build && npm test`
Expected: build sem erros TS; 5 testes passam.

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "feat: tiles de indicadores e estatísticas por partido/UF/casa no panorama"
```

---

### Task 3: Verificação com dados reais (controller)

**Files:** nenhum código; execução.

- [ ] **Step 1:** Reiniciar a API (`pkill -f uvicorn` fora do comando que sobe; `cd backend && uv run uvicorn radar.api.app:app_padrao --factory --port 8010`).
- [ ] **Step 2:** Sanidade com dados reais via `curl /api/visao-geral?ano=2025`: mediana ≤ média nos partidos grandes; UFs plausíveis (RR/AC/AM no topo); transparência coerente (Câmara > 0%, Senado/CLDF 0%); fim_de_ano com ano_ref 2025; conferir 1 quase-exclusivo manualmente no banco (SQL direto validando total/pct do maior).
- [ ] **Step 3:** Verificação visual (Playwright): home com as duas linhas de tiles + 3 cartões novos, scroll da tabela de partidos, troca de ano; screenshot inspecionado; 0 erros de console.

## Self-Review (feito na escrita)

- **Cobertura do spec:** CTE por parlamentar ✔; partido/UF/casa ✔ (Task 1); 4 indicadores ✔; fallbacks NULL ✔; thresholds testados nos dois lados ✔; fim_de_ano com ano de referência testado ✔; ano vazio ✔; tiles + 3 cartões + rodapés ✔ (Task 2); verificação real ✔ (Task 3).
- **Placeholders:** nenhum.
- **Consistência:** nomes de campos idênticos entre payload (Task 1), testes e tipos TS (Task 2); consulta antiga `camara_senado` explicitamente removida ao ser substituída por `por_casa_linhas`.
