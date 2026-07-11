# Panorama na Home — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tela inicial ganha um "Panorama" do ano abaixo da busca: KPIs, evolução mensal, Câmara×Senado e top 5s, servidos por um único endpoint agregador.

**Architecture:** Novo endpoint `GET /api/visao-geral?ano=` em `backend/radar/api/app.py` (6 consultas agregadas DuckDB num payload). Novo componente `frontend/src/paginas/Panorama.tsx` renderizado pela `Busca.tsx` quando não há busca ativa.

**Tech Stack:** FastAPI + DuckDB (existentes), React + recharts (existentes), vitest/pytest.

## Global Constraints

- Convenções existentes do `app.py`: SQL 100% parametrizado, conexão read-only por request via `con()`, números como `float` no JSON, reuso de `COLUNAS_POLITICO`/`_politico_dict`.
- **Variação honesta**: `meses_com_dados = max(mes)` do ano selecionado; `total_mesmo_periodo_anterior` soma o ano anterior só até esse mês; `variacao_pct = null` se o período anterior for 0.
- Ano sem dados → HTTP 200 com blocos zerados (`total: 0`, listas vazias, `nota_mais_cara: null`), nunca erro. `ano` omitido → `max(ano)` da tabela.
- **Cores de gráfico validadas (dataviz)**: marcas verdes `#1d7a4d`, senado azul `#0369a1` (par passou o validador: ΔE CVD 55, contraste ≥3:1 sobre `#f5f5f2`). O verde escuro `#0a5c36` NÃO entra em marcas de gráfico (falha banda de luminosidade e croma) — só em texto/header.
- Regras dataviz: colunas mensais = 1 série verde sem legenda (título nomeia); Câmara×Senado = barra 100% empilhada horizontal em HTML com rótulos diretos e vão de 2px (nunca pizza de 2 fatias); top 5 categorias = mini-barras HTML todas na MESMA cor (identidade fica no rótulo); variação do KPI = texto neutro com seta ▲/▼ (sem verde/vermelho de status); texto sempre em cor de texto, nunca na cor da série; cantos das colunas arredondados só no topo (4px).
- UI pt-BR; valores grandes com `formatarBRLCompacto` ("R$ 89,2 mi"); meses abreviados pt-BR ("jan"…"dez").
- Fluxo async React: flag `ativo` no cleanup (padrão de `Busca.tsx`); erro do Panorama isolado num cartão (não afeta a busca).

## File Structure

```
backend/radar/api/app.py        # + endpoint visao_geral dentro de criar_app (antes do return)
backend/tests/test_api.py       # + testes do endpoint (fixture existente de conftest.py)
frontend/src/lib/formato.ts     # + formatarBRLCompacto, MESES_ABREV
frontend/src/lib/formato.test.ts# + testes
frontend/src/lib/api.ts         # + tipos VisaoGeral etc. + obterVisaoGeral
frontend/src/paginas/Panorama.tsx  # novo componente (tiles, gráficos, tops)
frontend/src/paginas/Busca.tsx  # renderiza <Panorama /> quando busca inativa
frontend/src/index.css          # + classes do panorama
```

---

### Task 1: Endpoint `GET /api/visao-geral`

**Files:**
- Modify: `backend/radar/api/app.py` (dentro de `criar_app`, antes do `return app`)
- Test: `backend/tests/test_api.py` (acrescentar)

**Interfaces:**
- Consumes: fixture `cliente`/`db_amostra` de `conftest.py` (dados 2024: camara-1 1000+300, camara-2 5000, senado-joao-neto 2000; 2025: camara-1 −200 em jan).
- Produces: `GET /api/visao-geral?ano=` → `{ano, kpis:{total, total_mesmo_periodo_anterior, variacao_pct, meses_com_dados, parlamentares, deputados, senadores, media_por_parlamentar, num_despesas, nota_mais_cara}, por_mes:[{mes,total}], camara_senado:[{fonte,total,parlamentares}], top_gastadores:[{politico,total}], top_categorias:[{categoria,total}], top_fornecedores:[{fornecedor,cnpj,total,quantidade}]}` — tops limitados a 5.

- [ ] **Step 1: Acrescentar testes que falham**

Ao final de `backend/tests/test_api.py`:
```python
def test_visao_geral_2024(cliente):
    corpo = cliente.get("/api/visao-geral", params={"ano": 2024}).json()
    assert corpo["ano"] == 2024
    k = corpo["kpis"]
    assert k["total"] == 8300.00
    assert k["num_despesas"] == 4
    assert k["meses_com_dados"] == 3
    assert k["deputados"] == 2 and k["senadores"] == 1 and k["parlamentares"] == 3
    assert round(k["media_por_parlamentar"], 2) == round(8300 / 3, 2)
    assert k["nota_mais_cara"]["valor"] == 5000.00
    assert k["nota_mais_cara"]["politico"]["id"] == "camara-2"
    assert corpo["por_mes"] == [
        {"mes": 1, "total": 3000.00},
        {"mes": 2, "total": 300.00},
        {"mes": 3, "total": 5000.00},
    ]
    assert {"fonte": "camara", "total": 6300.00, "parlamentares": 2} in corpo["camara_senado"]
    assert corpo["top_gastadores"][0]["politico"]["id"] == "camara-2"
    assert corpo["top_categorias"][0] == {"categoria": "Divulgação", "total": 5000.00}
    assert corpo["top_fornecedores"][0]["fornecedor"] == "GRÁFICA Y"


def test_visao_geral_variacao_mesmo_periodo(cliente):
    # 2025 tem dados só até mes=1; período anterior = 2024 até mes=1 (3000)
    k = cliente.get("/api/visao-geral", params={"ano": 2025}).json()["kpis"]
    assert k["total"] == -200.00
    assert k["meses_com_dados"] == 1
    assert k["total_mesmo_periodo_anterior"] == 3000.00
    assert round(k["variacao_pct"], 2) == round((-200 - 3000) / 3000 * 100, 2)


def test_visao_geral_ano_padrao_e_o_maximo(cliente):
    assert cliente.get("/api/visao-geral").json()["ano"] == 2025


def test_visao_geral_ano_sem_dados(cliente):
    corpo = cliente.get("/api/visao-geral", params={"ano": 1999}).json()
    assert corpo["kpis"]["total"] == 0
    assert corpo["kpis"]["nota_mais_cara"] is None
    assert corpo["kpis"]["variacao_pct"] is None
    assert corpo["por_mes"] == [] and corpo["top_gastadores"] == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && uv run pytest tests/test_api.py -v -k visao`
Expected: 4 FAIL (404)

- [ ] **Step 3: Implementar**

Em `backend/radar/api/app.py`, dentro de `criar_app` antes do `return app`:
```python
    @app.get("/api/visao-geral")
    def visao_geral(ano: int | None = None):
        with con() as c:
            if ano is None:
                ano = c.execute("SELECT coalesce(max(ano), 0) FROM despesas").fetchone()[0]
            total, num_despesas, meses = c.execute(
                "SELECT coalesce(sum(valor), 0), count(*), coalesce(max(mes), 0) "
                "FROM despesas WHERE ano = ?",
                (ano,),
            ).fetchone()
            anterior = c.execute(
                "SELECT coalesce(sum(valor), 0) FROM despesas WHERE ano = ? AND mes <= ?",
                (ano - 1, meses),
            ).fetchone()[0]
            cargos = dict(
                c.execute(
                    """SELECT p.cargo, count(DISTINCT d.politico_id)
                       FROM despesas d JOIN politicos p ON p.id = d.politico_id
                       WHERE d.ano = ? GROUP BY p.cargo""",
                    (ano,),
                ).fetchall()
            )
            deputados = cargos.get("Deputado Federal", 0)
            senadores = cargos.get("Senador", 0)
            parlamentares = deputados + senadores
            nota = c.execute(
                f"""SELECT d.valor, d.categoria, d.fornecedor, d.data,
                           {', '.join('p.' + col for col in COLUNAS_POLITICO)}
                    FROM despesas d JOIN politicos p ON p.id = d.politico_id
                    WHERE d.ano = ? ORDER BY d.valor DESC LIMIT 1""",
                (ano,),
            ).fetchone()
            por_mes = c.execute(
                "SELECT mes, sum(valor) FROM despesas WHERE ano = ? AND mes IS NOT NULL "
                "GROUP BY mes ORDER BY mes",
                (ano,),
            ).fetchall()
            camara_senado = c.execute(
                "SELECT fonte, sum(valor), count(DISTINCT politico_id) "
                "FROM despesas WHERE ano = ? GROUP BY fonte ORDER BY fonte",
                (ano,),
            ).fetchall()
            gastadores = c.execute(
                f"""SELECT {', '.join('p.' + col for col in COLUNAS_POLITICO)},
                           sum(d.valor) AS total
                    FROM despesas d JOIN politicos p ON p.id = d.politico_id
                    WHERE d.ano = ?
                    GROUP BY {', '.join('p.' + col for col in COLUNAS_POLITICO)}
                    ORDER BY total DESC LIMIT 5""",
                (ano,),
            ).fetchall()
            categorias = c.execute(
                "SELECT categoria, sum(valor) AS t FROM despesas WHERE ano = ? "
                "GROUP BY categoria ORDER BY t DESC LIMIT 5",
                (ano,),
            ).fetchall()
            fornecedores = c.execute(
                """SELECT fornecedor, coalesce(fornecedor_cnpj, '') AS cnpj,
                          sum(valor) AS t, count(*) AS q
                   FROM despesas WHERE ano = ? AND fornecedor IS NOT NULL
                   GROUP BY fornecedor, cnpj ORDER BY t DESC LIMIT 5""",
                (ano,),
            ).fetchall()
        total = float(total)
        anterior = float(anterior)
        return {
            "ano": ano,
            "kpis": {
                "total": total,
                "total_mesmo_periodo_anterior": anterior,
                "variacao_pct": ((total - anterior) / anterior * 100) if anterior else None,
                "meses_com_dados": meses,
                "parlamentares": parlamentares,
                "deputados": deputados,
                "senadores": senadores,
                "media_por_parlamentar": total / parlamentares if parlamentares else 0.0,
                "num_despesas": num_despesas,
                "nota_mais_cara": {
                    "valor": float(nota[0]),
                    "categoria": nota[1],
                    "fornecedor": nota[2],
                    "data": nota[3].isoformat() if nota[3] else None,
                    "politico": _politico_dict(nota[4:]),
                }
                if nota
                else None,
            },
            "por_mes": [{"mes": m, "total": float(t)} for m, t in por_mes],
            "camara_senado": [
                {"fonte": f, "total": float(t), "parlamentares": q}
                for f, t, q in camara_senado
            ],
            "top_gastadores": [
                {"politico": _politico_dict(l[:-1]), "total": float(l[-1])}
                for l in gastadores
            ],
            "top_categorias": [{"categoria": cat, "total": float(t)} for cat, t in categorias],
            "top_fornecedores": [
                {"fornecedor": f, "cnpj": cnpj, "total": float(t), "quantidade": q}
                for f, cnpj, t, q in fornecedores
            ],
        }
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && uv run pytest -q`
Expected: 38 passed (34 antigos + 4 novos)

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: endpoint /api/visao-geral com KPIs e tops do ano"
```

---

### Task 2: `formatarBRLCompacto` e meses pt-BR

**Files:**
- Modify: `frontend/src/lib/formato.ts`
- Test: `frontend/src/lib/formato.test.ts` (acrescentar)

**Interfaces:**
- Produces: `formatarBRLCompacto(v: number): string` (≥1 mi → "R$ 89,2 mi"; ≥1 mil → "R$ 151,7 mil"; abaixo → `formatarBRL`); `MESES_ABREV: string[]` (12 itens, "jan"…"dez").

- [ ] **Step 1: Acrescentar testes que falham**

Em `frontend/src/lib/formato.test.ts`:
```ts
import { formatarBRL, formatarBRLCompacto, formatarData, MESES_ABREV } from './formato'

describe('formatarBRLCompacto', () => {
  it('abrevia milhões e milhares em pt-BR', () => {
    expect(formatarBRLCompacto(89_200_000)).toBe('R$ 89,2 mi')
    expect(formatarBRLCompacto(151_700)).toBe('R$ 151,7 mil')
    expect(formatarBRLCompacto(2_000_000)).toBe('R$ 2 mi')
  })
  it('mantém valores pequenos e negativos legíveis', () => {
    expect(formatarBRLCompacto(42.5).replace(/\s/g, ' ')).toBe('R$ 42,50')
    expect(formatarBRLCompacto(-1_500_000)).toBe('R$ -1,5 mi')
  })
})

describe('MESES_ABREV', () => {
  it('tem 12 meses pt-BR', () => {
    expect(MESES_ABREV).toHaveLength(12)
    expect(MESES_ABREV[0]).toBe('jan')
    expect(MESES_ABREV[11]).toBe('dez')
  })
})
```
(Ajustar o import existente no topo do arquivo para incluir os novos nomes.)

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd frontend && npm test`
Expected: FAIL (formatarBRLCompacto não exportado)

- [ ] **Step 3: Implementar**

Acrescentar a `frontend/src/lib/formato.ts`:
```ts
const compacto = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

export function formatarBRLCompacto(valor: number): string {
  const abs = Math.abs(valor)
  if (abs >= 1_000_000) return `R$ ${compacto.format(valor / 1_000_000)} mi`
  if (abs >= 1_000) return `R$ ${compacto.format(valor / 1_000)} mil`
  return formatarBRL(valor)
}

export const MESES_ABREV = [
  'jan', 'fev', 'mar', 'abr', 'mai', 'jun',
  'jul', 'ago', 'set', 'out', 'nov', 'dez',
]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd frontend && npm test`
Expected: todos passam (5 testes)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib
git commit -m "feat: formatador compacto de reais e meses abreviados"
```

---

### Task 3: Componente Panorama + integração na Busca

**Files:**
- Modify: `frontend/src/lib/api.ts` (tipos + `obterVisaoGeral`)
- Create: `frontend/src/paginas/Panorama.tsx`
- Modify: `frontend/src/paginas/Busca.tsx`, `frontend/src/index.css`

**Interfaces:**
- Consumes: Task 1 (payload), Task 2 (`formatarBRLCompacto`, `MESES_ABREV`), `formatarBRL`, tipos `Politico`/`ItemRanking` de `api.ts`.

- [ ] **Step 1: Tipos e client em `api.ts`**

Acrescentar:
```ts
export interface NotaMaisCara {
  valor: number
  categoria: string
  fornecedor: string | null
  data: string | null
  politico: Politico
}

export interface VisaoGeral {
  ano: number
  kpis: {
    total: number
    total_mesmo_periodo_anterior: number
    variacao_pct: number | null
    meses_com_dados: number
    parlamentares: number
    deputados: number
    senadores: number
    media_por_parlamentar: number
    num_despesas: number
    nota_mais_cara: NotaMaisCara | null
  }
  por_mes: { mes: number; total: number }[]
  camara_senado: { fonte: string; total: number; parlamentares: number }[]
  top_gastadores: ItemRanking[]
  top_categorias: { categoria: string; total: number }[]
  top_fornecedores: { fornecedor: string; cnpj: string; total: number; quantidade: number }[]
}

export const obterVisaoGeral = (ano?: number) =>
  obter<VisaoGeral>('/api/visao-geral', { ano })
```

- [ ] **Step 2: Criar `frontend/src/paginas/Panorama.tsx`**

```tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { obterVisaoGeral, type VisaoGeral } from '../lib/api'
import { formatarBRL, formatarBRLCompacto, MESES_ABREV } from '../lib/formato'

const ANOS = Array.from({ length: 11 }, (_, i) => 2016 + i)
// Cores validadas (dataviz): verde de marca de gráfico e azul do Senado
const COR_MARCA = '#1d7a4d'
const COR_SENADO = '#0369a1'

export default function Panorama() {
  const [dados, setDados] = useState<VisaoGeral | null>(null)
  const [ano, setAno] = useState<number | undefined>()
  const [erro, setErro] = useState('')

  useEffect(() => {
    let ativo = true
    obterVisaoGeral(ano)
      .then((d) => { if (ativo) { setDados(d); setErro('') } })
      .catch((e) => { if (ativo) setErro(e.message) })
    return () => { ativo = false }
  }, [ano])

  if (erro) return <p className="cartao">⚠️ Panorama indisponível: {erro}</p>
  if (!dados) return <p>Carregando panorama...</p>

  const { kpis } = dados
  const nota = kpis.nota_mais_cara
  const totalCS = dados.camara_senado.reduce((s, x) => s + x.total, 0)
  const serieMensal = dados.por_mes.map((m) => ({ nome: MESES_ABREV[m.mes - 1], total: m.total }))
  const maxCategoria = dados.top_categorias[0]?.total ?? 0

  return (
    <section>
      <div className="panorama-titulo">
        <h2>Panorama</h2>
        <select value={dados.ano} onChange={(e) => setAno(Number(e.target.value))}>
          {ANOS.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
      </div>

      <div className="tiles">
        <div className="cartao tile">
          <small>Total gasto em {dados.ano}</small>
          <div className="tile-valor">{formatarBRLCompacto(kpis.total)}</div>
          {kpis.variacao_pct !== null && (
            <small>
              {kpis.variacao_pct >= 0 ? '▲' : '▼'} {Math.abs(kpis.variacao_pct).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%
              {' '}vs jan–{MESES_ABREV[kpis.meses_com_dados - 1]}/{dados.ano - 1}
            </small>
          )}
        </div>
        <div className="cartao tile">
          <small>Parlamentares com gastos</small>
          <div className="tile-valor">{kpis.parlamentares}</div>
          <small>{kpis.deputados} deputados · {kpis.senadores} senadores</small>
        </div>
        <div className="cartao tile">
          <small>Média por parlamentar</small>
          <div className="tile-valor">{formatarBRLCompacto(kpis.media_por_parlamentar)}</div>
          <small>{kpis.num_despesas.toLocaleString('pt-BR')} despesas no ano</small>
        </div>
        <div className="cartao tile">
          <small>Nota mais cara do ano</small>
          <div className="tile-valor">{nota ? formatarBRLCompacto(nota.valor) : '—'}</div>
          {nota && (
            <small>
              <Link to={`/politico/${nota.politico.id}`}>{nota.politico.nome}</Link> · {nota.categoria}
            </small>
          )}
        </div>
      </div>

      <div className="graficos">
        <div className="cartao">
          <h3>Gasto mês a mês</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={serieMensal}>
              <XAxis dataKey="nome" tickLine={false} axisLine={false} />
              <YAxis tickFormatter={(v) => formatarBRLCompacto(Number(v))} width={80}
                     tickLine={false} axisLine={false} />
              <Tooltip formatter={(v) => formatarBRL(Number(v))} />
              <Bar dataKey="total" name="Total" fill={COR_MARCA} radius={[4, 4, 0, 0]} maxBarSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="cartao">
          <h3>Câmara × Senado</h3>
          <div className="split-bar">
            {dados.camara_senado.map((x) => (
              <div
                key={x.fonte}
                className="split-parte"
                style={{
                  width: totalCS ? `${(x.total / totalCS) * 100}%` : '50%',
                  background: x.fonte === 'camara' ? COR_MARCA : COR_SENADO,
                }}
              />
            ))}
          </div>
          {dados.camara_senado.map((x) => (
            <div key={x.fonte} className="split-legenda">
              <span className="pino" style={{ background: x.fonte === 'camara' ? COR_MARCA : COR_SENADO }} />
              {x.fonte === 'camara' ? 'Câmara' : 'Senado'}: {formatarBRLCompacto(x.total)}
              {' '}({x.parlamentares} parlamentares{totalCS ? `, ${((x.total / totalCS) * 100).toFixed(0)}%` : ''})
            </div>
          ))}
        </div>
      </div>

      <div className="tops">
        <div className="cartao">
          <h3>Top 5 gastadores</h3>
          {dados.top_gastadores.map((g, i) => (
            <Link key={g.politico.id} to={`/politico/${g.politico.id}`}>
              <div className="top-linha">
                <span className="top-posicao">{i + 1}º</span>
                {g.politico.foto_url && <img src={g.politico.foto_url} alt="" />}
                <span className="top-nome">
                  {g.politico.nome}
                  <small>{[g.politico.partido, g.politico.uf].filter(Boolean).join('/')}</small>
                </span>
                <span className="top-valor">{formatarBRLCompacto(g.total)}</span>
              </div>
            </Link>
          ))}
        </div>
        <div className="cartao">
          <h3>Top 5 categorias</h3>
          {dados.top_categorias.map((c) => (
            <div key={c.categoria} className="minibar-linha">
              <div className="minibar-rotulo">
                <span>{c.categoria}</span>
                <span className="top-valor">{formatarBRLCompacto(c.total)}</span>
              </div>
              <div className="minibar-trilha">
                <div className="minibar" style={{ width: maxCategoria ? `${(c.total / maxCategoria) * 100}%` : 0 }} />
              </div>
            </div>
          ))}
        </div>
        <div className="cartao">
          <h3>Top 5 fornecedores</h3>
          {dados.top_fornecedores.map((f) => (
            <div key={f.fornecedor + f.cnpj} className="top-linha">
              <span className="top-nome">
                {f.fornecedor}
                <small>{f.cnpj || '—'} · {f.quantidade} notas</small>
              </span>
              <span className="top-valor">{formatarBRLCompacto(f.total)}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Step 3: Integrar na Busca e CSS**

Em `frontend/src/paginas/Busca.tsx`: importar `Panorama` e, após o bloco de resultados/mensagens (antes do `</div>` final do componente), acrescentar:
```tsx
      {busca.trim().length < 3 && <Panorama />}
```

Acrescentar a `frontend/src/index.css`:
```css
.panorama-titulo { display: flex; align-items: center; gap: 0.8rem; margin-top: 1.6rem; }
.panorama-titulo h2 { margin: 0; }
.panorama-titulo select { padding: 0.3rem 0.5rem; border: 1px solid #ccc; border-radius: 6px; }
.tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
@media (max-width: 800px) { .tiles { grid-template-columns: 1fr 1fr; } }
.tile small { color: #666; display: block; }
.tile-valor { font-size: 1.5rem; font-weight: 700; color: #0a5c36; margin: 0.2rem 0; }
.split-bar { display: flex; gap: 2px; height: 28px; border-radius: 6px; overflow: hidden; margin: 0.8rem 0; }
.split-parte { min-width: 4px; }
.split-legenda { display: flex; align-items: center; gap: 0.5rem; margin: 0.3rem 0; font-size: 0.9rem; }
.pino { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
.tops { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
@media (max-width: 900px) { .tops { grid-template-columns: 1fr; } }
.top-linha { display: flex; align-items: center; gap: 0.6rem; padding: 0.45rem 0; border-bottom: 1px solid #eee; color: #1a1a1a; }
.top-linha:last-child { border-bottom: none; }
.top-linha img { width: 34px; height: 42px; object-fit: cover; border-radius: 4px; background: #ddd; }
.top-posicao { color: #666; width: 1.6rem; }
.top-nome { flex: 1; min-width: 0; }
.top-nome small { display: block; color: #666; }
.top-valor { font-weight: 600; white-space: nowrap; }
.minibar-linha { margin: 0.5rem 0; }
.minibar-rotulo { display: flex; justify-content: space-between; font-size: 0.9rem; gap: 0.5rem; }
.minibar-trilha { background: #eee; border-radius: 4px; height: 8px; margin-top: 0.25rem; }
.minibar { background: #1d7a4d; height: 8px; border-radius: 4px; min-width: 2px; }
```

- [ ] **Step 4: Build + testes**

Run: `cd frontend && npm run build && npm test`
Expected: build sem erros TS; testes passam.

- [ ] **Step 5: Verificação visual (obrigatória — dataviz passo 7)**

Com API (porta 8010) e `npm run dev` rodando, dirigir com Playwright (instalado no scratchpad da sessão) ou abrir no navegador: home mostra busca + panorama (tiles com números reais, colunas mensais, barra Câmara×Senado com rótulos, três tops); trocar o ano no seletor atualiza tudo; digitar 3+ letras esconde o panorama e mostra resultados; screenshot para inspeção de colisões/overflow.

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "feat: panorama com KPIs, evolução mensal e top 5s na home"
```

## Self-Review (feito na escrita)

- **Cobertura do spec:** endpoint+regras (Task 1), formatadores (Task 2), componente/integração/CSS/verificação visual (Task 3). Variação honesta testada; ano vazio testado; cores validadas pelo script do dataviz.
- **Placeholders:** nenhum.
- **Consistência de tipos:** payload do Task 1 ↔ interface `VisaoGeral` do Task 3 conferidos campo a campo; `ItemRanking` reusado para gastadores (mesmo shape do /api/rankings); `formatarBRLCompacto`/`MESES_ABREV` idênticos entre Tasks 2 e 3.
