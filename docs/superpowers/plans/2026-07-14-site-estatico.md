# Site Estático Pré-compilado Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publicação 100% estática: exportador lê o DuckDB e gera JSONs; Next.js 15 (`output: 'export'`) pré-compila 1.547 perfis + home + rankings com meta/OG por página; deploy vira upload de arquivos.

**Architecture:** As consultas SQL saem de `app.py` para `radar/consultas.py` (API e exportador chamam as mesmas funções — paridade garantida). O exportador grava `frontend*/public/dados/**`. O app Next é construído em `frontend-next/` ao lado do Vite atual e o swap acontece na última tarefa.

**Tech Stack:** Python/DuckDB existentes; Next.js 15 App Router + TypeScript + recharts + fontsource (Archivo/Plex Mono); vitest; Playwright para verificação.

## Global Constraints

- **Paridade**: os payloads de `perfil/{id}.json`, `visao-geral/{ano}.json` e `rankings/{ano}.json` são EXATAMENTE os das rotas da API atual (mesmas chaves) — garantido por `consultas.py` compartilhado. Os 53 testes de backend existentes continuam passando sem alteração de asserções na Task 1.
- **Formato compacto de despesas**: `{"colunas": ["data","categoria","categoria_original","descricao","fornecedor","cnpj","valor","doc"], "linhas": [[...], ...]}`, ordenado por data desc (nulls por último), `data` ISO ou null, `valor` float.
- Rotas preservadas: `/`, `/politico/{id}/`, `/rankings/` (`trailingSlash: true`).
- `generateMetadata` por perfil: title `Gastos de {nome} ({partido}/{uf}) — Radar Políticos` (partido/uf omitidos se null), description com total formatado e período, `og:image` = `foto_url` ou `/og-padrao.png`.
- Seletores de ano SEMPRE derivados de `meta.json`/dados (nunca hardcode de intervalo).
- Tema Painel de Brasília intocado: mesmo CSS/tokens/paletas validadas; recharts em client components.
- UI pt-BR; `frontend*/public/dados/` e `frontend*/out/` no `.gitignore` (150–250 MB gerados).
- Exportador atômico: escreve em staging e `os.replace` no final; relatório com nº de arquivos e bytes.
- Node 20; `images: { unoptimized: true }` (export estático não otimiza imagem).

## File Structure

```
backend/radar/consultas.py        # TODAS as consultas (API e exportador consomem)
backend/radar/api/app.py          # endpoints viram cascas finas sobre consultas.py
backend/radar/exportar.py         # gerador dos JSONs (CLI python -m radar.exportar)
backend/tests/test_consultas.py   # paridade/refactor
backend/tests/test_exportar.py
frontend-next/                    # app Next (vira frontend/ na última task)
  next.config.ts, package.json, tsconfig.json, vitest.config.ts
  src/app/layout.tsx              # header/status/rodapé + metadata base
  src/app/page.tsx                # home (server) → <PaginaInicial> (client)
  src/app/politico/[id]/page.tsx  # generateStaticParams + generateMetadata
  src/app/rankings/page.tsx
  src/app/sitemap.ts, src/app/robots.ts
  src/app/globals.css             # portado do tema atual
  src/lib/{formato,fontes,tipos,busca}.ts + formato.test.ts + busca.test.ts
  src/lib/dados-build.ts          # leitores fs (só server/build)
  src/componentes/{PaginaInicial,Panorama,Perfil,TabelaDespesas,Rankings}.tsx
```

---

### Task 1: Extrair `consultas.py` (refactor com rede de testes)

**Files:**
- Create: `backend/radar/consultas.py`, `backend/tests/test_consultas.py`
- Modify: `backend/radar/api/app.py`

**Interfaces:**
- Produces (assinaturas exatas — todas recebem uma conexão DuckDB aberta):
```python
COLUNAS_POLITICO: tuple[str, ...]           # movido de app.py
def politico_dict(linha) -> dict            # ex-_politico_dict
def politico_por_id(con, politico_id: str) -> dict | None
def buscar_politicos(con, busca="", cargo=None, partido=None, uf=None, limite=20) -> list[dict]
def resumo(con, politico_id: str, ano_inicio=0, ano_fim=9999) -> dict | None   # None se não existe
def despesas_paginadas(con, politico_id, ano=None, categoria=None, fornecedor=None,
                       ordenar="-data", pagina=1, por_pagina=50) -> dict | None
ORDENACOES: dict[str, str]                  # movido de app.py (whitelist)
def rankings(con, ano=None, cargo=None, categoria=None, limite=20) -> list[dict]
def visao_geral(con, ano: int | None = None) -> dict
def anos_com_dados(con) -> list[int]        # NOVO: SELECT DISTINCT ano ORDER BY ano
def anos_do_politico(con, politico_id) -> list[int]  # NOVO
def despesas_compactas(con, politico_id, ano) -> dict  # NOVO: formato {"colunas", "linhas"}
```

- [ ] **Step 1: Testes novos que falham** (`backend/tests/test_consultas.py`)

```python
import duckdb
import pytest

from radar import consultas
from radar.db import conectar, criar_schema


@pytest.fixture
def con(db_amostra):
    c = conectar(db_amostra, somente_leitura=True)
    yield c
    c.close()


def test_paridade_resumo_com_api(con, cliente):
    via_api = cliente.get("/api/politicos/camara-1/resumo").json()
    via_consulta = consultas.resumo(con, "camara-1")
    assert via_consulta == via_api


def test_paridade_visao_geral(con, cliente):
    assert consultas.visao_geral(con, 2024) == cliente.get(
        "/api/visao-geral", params={"ano": 2024}
    ).json()


def test_paridade_rankings(con, cliente):
    assert consultas.rankings(con, ano=2024) == cliente.get(
        "/api/rankings", params={"ano": 2024}
    ).json()


def test_resumo_inexistente_retorna_none(con):
    assert consultas.resumo(con, "nao-existe") is None


def test_anos_com_dados(con):
    assert consultas.anos_com_dados(con) == [2024, 2025]


def test_anos_do_politico(con):
    assert consultas.anos_do_politico(con, "camara-1") == [2024, 2025]
    assert consultas.anos_do_politico(con, "senado-joao-neto") == [2024]


def test_despesas_compactas(con):
    d = consultas.despesas_compactas(con, "camara-1", 2024)
    assert d["colunas"] == [
        "data", "categoria", "categoria_original", "descricao",
        "fornecedor", "cnpj", "valor", "doc",
    ]
    assert len(d["linhas"]) == 2
    # ordenado por data desc: fev antes de jan
    assert d["linhas"][0][0] == "2024-02-05" and d["linhas"][0][6] == 300.0
    assert d["linhas"][1][4] == "TAM" and d["linhas"][1][7] == "http://doc/1.pdf"
```

(O `conftest.py` já expõe `db_amostra` e `cliente`.)

Run: `cd backend && uv run pytest tests/test_consultas.py -v` → FAIL (ModuleNotFoundError).

- [ ] **Step 2: Criar `consultas.py` MOVENDO os corpos de `app.py`**

Regra do refactor: os corpos das consultas saem de `backend/radar/api/app.py` **sem alterar nenhum SQL nem nenhuma montagem de dict** — apenas trocando o acesso à conexão (parâmetro `con` em vez do helper local) e removendo o que é HTTP (`HTTPException`, `Query`). Mapeamento:

| Endpoint em app.py | Função em consultas.py | Diferença |
|---|---|---|
| corpo de `buscar_politicos` | `buscar_politicos(con, ...)` | idêntico |
| `_buscar_politico` | `politico_por_id(con, id)` | retorna `None` em vez de levantar 404 |
| corpo de `resumo` | `resumo(con, id, ano_inicio, ano_fim)` | começa com `politico = politico_por_id(...)`; `if politico is None: return None` |
| corpo de `despesas` | `despesas_paginadas(con, ...)` | valida `ordenar` com `if ordenar not in ORDENACOES: raise ValueError(...)`; político inexistente → `None` |
| corpo de `rankings` | `rankings(con, ...)` | idêntico |
| corpo de `visao_geral` | `visao_geral(con, ano=None)` | idêntico (incluindo TODO o bloco de estatísticas) |

Novas funções (código completo):

```python
def anos_com_dados(con) -> list[int]:
    return [a for (a,) in con.execute(
        "SELECT DISTINCT ano FROM despesas ORDER BY ano"
    ).fetchall()]


def anos_do_politico(con, politico_id: str) -> list[int]:
    return [a for (a,) in con.execute(
        "SELECT DISTINCT ano FROM despesas WHERE politico_id = ? ORDER BY ano",
        (politico_id,),
    ).fetchall()]


COLUNAS_COMPACTAS = [
    "data", "categoria", "categoria_original", "descricao",
    "fornecedor", "cnpj", "valor", "doc",
]


def despesas_compactas(con, politico_id: str, ano: int) -> dict:
    linhas = con.execute(
        """SELECT data, categoria, categoria_original, descricao,
                  fornecedor, fornecedor_cnpj, valor, documento_url
           FROM despesas WHERE politico_id = ? AND ano = ?
           ORDER BY data DESC NULLS LAST""",
        (politico_id, ano),
    ).fetchall()
    return {
        "colunas": COLUNAS_COMPACTAS,
        "linhas": [
            [d.isoformat() if d else None, cat, cat_o, desc, forn, cnpj, float(v), doc]
            for d, cat, cat_o, desc, forn, cnpj, v, doc in linhas
        ],
    }
```

- [ ] **Step 3: Emagrecer `app.py`**

Cada endpoint vira casca: abre `con()`, chama a função de `consultas`, traduz `None`→`HTTPException(404)` e `ValueError`→`HTTPException(422)`. Exemplo do padrão (aplicar a todos):

```python
    @app.get("/api/politicos/{politico_id}/resumo")
    def resumo(politico_id: str, ano_inicio: int = 0, ano_fim: int = 9999):
        with con() as c:
            corpo = consultas.resumo(c, politico_id, ano_inicio, ano_fim)
        if corpo is None:
            raise HTTPException(404, "Político não encontrado")
        return corpo
```

As validações `Query(ge=1, le=...)` dos parâmetros permanecem nos endpoints (são HTTP). `app.py` não deve mais conter nenhum `c.execute(` (checar com grep).

- [ ] **Step 4: Rodar TODA a suíte**

Run: `cd backend && uv run pytest -q`
Expected: 60 passed (53 antigos SEM MUDANÇA DE ASSERÇÃO + 7 novos). `grep -c "execute(" radar/api/app.py` → 0.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "refactor: consultas compartilhadas em radar/consultas.py"
```

---

### Task 2: Exportador de JSONs estáticos

**Files:**
- Create: `backend/radar/exportar.py`
- Test: `backend/tests/test_exportar.py`

**Interfaces:**
- Consumes: `consultas.*` (Task 1).
- Produces: CLI `python -m radar.exportar --db ../dados/radar.duckdb --saida ../frontend-next/public/dados`; função `exportar(db: str, saida: Path) -> dict` (relatório `{"arquivos": n, "bytes": n}`). Estrutura gerada: `meta.json`, `politicos.json`, `visao-geral/{ano}.json`, `rankings/{ano}.json`, `perfil/{id}.json`, `despesas/{id}/{ano}.json`.

- [ ] **Step 1: Testes que falham** (`backend/tests/test_exportar.py`)

```python
import json
from pathlib import Path

from radar import consultas, exportar
from radar.db import conectar


def _exportado(db_amostra, tmp_path) -> Path:
    saida = tmp_path / "dados"
    relatorio = exportar.exportar(db_amostra, saida)
    assert relatorio["arquivos"] > 0 and relatorio["bytes"] > 0
    return saida


def test_estrutura_gerada(db_amostra, tmp_path):
    saida = _exportado(db_amostra, tmp_path)
    assert (saida / "meta.json").exists()
    assert (saida / "politicos.json").exists()
    assert (saida / "visao-geral" / "2024.json").exists()
    assert (saida / "visao-geral" / "2025.json").exists()
    assert (saida / "rankings" / "2024.json").exists()
    assert (saida / "perfil" / "camara-1.json").exists()
    assert (saida / "despesas" / "camara-1" / "2024.json").exists()
    # senado-joao-neto só tem 2024: não deve existir chunk de 2025
    assert not (saida / "despesas" / "senado-joao-neto" / "2025.json").exists()


def test_meta(db_amostra, tmp_path):
    saida = _exportado(db_amostra, tmp_path)
    meta = json.loads((saida / "meta.json").read_text())
    assert meta["anos"] == [2024, 2025]
    assert meta["ano_max"] == 2025
    assert meta["total_politicos"] == 3
    assert meta["total_despesas"] == 5
    assert "gerado_em" in meta


def test_paridade_com_consultas(db_amostra, tmp_path):
    saida = _exportado(db_amostra, tmp_path)
    con = conectar(db_amostra, somente_leitura=True)
    assert json.loads((saida / "perfil" / "camara-1.json").read_text()) == consultas.resumo(con, "camara-1")
    assert json.loads((saida / "visao-geral" / "2024.json").read_text()) == consultas.visao_geral(con, 2024)
    assert json.loads((saida / "despesas" / "camara-1" / "2024.json").read_text()) == (
        consultas.despesas_compactas(con, "camara-1", 2024)
    )
    con.close()


def test_reexecucao_e_atomica(db_amostra, tmp_path):
    saida = _exportado(db_amostra, tmp_path)
    (saida / "lixo.json").write_text("{}")
    _exportado(db_amostra, tmp_path)  # segunda execução substitui o diretório inteiro
    assert not (saida / "lixo.json").exists()
    assert (saida / "meta.json").exists()
```

Run: `cd backend && uv run pytest tests/test_exportar.py -v` → FAIL.

- [ ] **Step 2: Implementar** (`backend/radar/exportar.py`)

```python
"""Exporta o DuckDB para os JSONs estáticos consumidos pelo site pré-compilado."""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from radar import consultas
from radar.db import conectar


def _gravar(caminho: Path, corpo) -> int:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(corpo, ensure_ascii=False, separators=(",", ":"))
    caminho.write_text(texto, encoding="utf-8")
    return len(texto.encode("utf-8"))


def exportar(db: str, saida: Path) -> dict:
    saida = Path(saida)
    staging = saida.with_name(saida.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    con = conectar(db, somente_leitura=True)
    arquivos = 0
    total_bytes = 0

    def grava(rel: str, corpo):
        nonlocal arquivos, total_bytes
        total_bytes += _gravar(staging / rel, corpo)
        arquivos += 1

    anos = consultas.anos_com_dados(con)
    politicos = consultas.buscar_politicos(con, limite=100_000)
    grava("politicos.json", politicos)
    for ano in anos:
        grava(f"visao-geral/{ano}.json", consultas.visao_geral(con, ano))
        grava(f"rankings/{ano}.json", consultas.rankings(con, ano=ano, limite=100))
    for p in politicos:
        pid = p["id"]
        grava(f"perfil/{pid}.json", consultas.resumo(con, pid))
        for ano in consultas.anos_do_politico(con, pid):
            grava(f"despesas/{pid}/{ano}.json", consultas.despesas_compactas(con, pid, ano))
    grava("meta.json", {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "anos": anos,
        "ano_max": max(anos) if anos else None,
        "total_politicos": len(politicos),
        "total_despesas": con.execute("SELECT count(*) FROM despesas").fetchone()[0],
    })
    con.close()

    if saida.exists():
        shutil.rmtree(saida)
    staging.replace(saida)
    return {"arquivos": arquivos, "bytes": total_bytes}


def main() -> int:
    p = argparse.ArgumentParser(description="Exporta JSONs estáticos do Radar Políticos")
    p.add_argument("--db", default="../dados/radar.duckdb")
    p.add_argument("--saida", default="../frontend-next/public/dados")
    args = p.parse_args()
    r = exportar(args.db, Path(args.saida))
    print(f"✔ {r['arquivos']:,} arquivos · {r['bytes'] / 1e6:,.1f} MB".replace(",", "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Nota: `buscar_politicos` precisa aceitar `limite` alto — se a assinatura da Task 1 tiver `Query`-limits, eles vivem só no endpoint; a função aceita qualquer int.

- [ ] **Step 3: Rodar e ver passar**

Run: `cd backend && uv run pytest -q` → 64 passed.

- [ ] **Step 4: Commit**

```bash
git add backend
git commit -m "feat: exportador de JSONs estáticos (perfis, panoramas, despesas compactas)"
```

---

### Task 3: Scaffold Next.js + tema + libs

**Files:**
- Create: `frontend-next/` (scaffold), `src/app/globals.css`, `src/app/layout.tsx`, `src/lib/{tipos,formato,fontes,busca,dados-build}.ts`, `src/lib/formato.test.ts`, `src/lib/busca.test.ts`, `vitest.config.ts`
- Modify: `.gitignore` (raiz)

**Interfaces:**
- Produces: `dados-build.ts` com `lerMeta()`, `lerPoliticos()`, `lerPerfil(id)`, `lerVisaoGeral(ano)` (fs, só em build); `busca.ts` com `semAcento(t: string): string` e `filtrarPoliticos(lista, termo, limite=20)`; `tipos.ts` re-exporta as interfaces `Politico`, `Resumo`, `Despesa`(objeto expandido), `VisaoGeral`, `ItemRanking`, `Meta`, `DespesasCompactas` copiadas do Vite atual (`frontend/src/lib/api.ts`) + novas; `formato.ts`/`fontes.ts` copiados sem mudança.

- [ ] **Step 1: Scaffold**

```bash
cd /home/italo/radar-politicos
npx create-next-app@latest frontend-next --ts --app --no-eslint --no-tailwind --src-dir --use-npm --turbopack --import-alias "@/*" --yes
cd frontend-next
npm i recharts @fontsource-variable/archivo @fontsource/ibm-plex-mono --no-fund --no-audit
npm i -D vitest --no-fund --no-audit
```

`next.config.ts`:
```ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  images: { unoptimized: true },
}

export default nextConfig
```

Em `package.json`, scripts: `"test": "vitest run"`. `vitest.config.ts`:
```ts
import { defineConfig } from 'vitest/config'
export default defineConfig({ test: { include: ['src/**/*.test.ts'] } })
```

No `.gitignore` da RAIZ acrescentar:
```
frontend-next/public/dados/
frontend-next/out/
frontend/public/dados/
frontend/out/
```

- [ ] **Step 2: Portar tema e utilitários (TDD nos novos)**

- `src/app/globals.css` = cópia integral de `frontend/src/index.css` (tema Painel de Brasília, incluindo `.rodape`).
- `src/lib/formato.ts` + `src/lib/formato.test.ts` = cópias de `frontend/src/lib/formato*.ts` (ajustar import no teste).
- `src/lib/fontes.ts` = cópia de `frontend/src/lib/fontes.ts`.
- `src/lib/tipos.ts`: copiar as interfaces de `frontend/src/lib/api.ts` (sem as funções `obter*`), acrescentando:
```ts
export interface Meta {
  gerado_em: string
  anos: number[]
  ano_max: number | null
  total_politicos: number
  total_despesas: number
}

export interface DespesasCompactas {
  colunas: string[]
  linhas: (string | number | null)[][]
}
```
- `src/lib/busca.test.ts` (falha primeiro):
```ts
import { describe, expect, it } from 'vitest'
import { filtrarPoliticos, semAcento } from './busca'

const LISTA = [
  { id: 'a', nome: 'José Ávila', cargo: 'Deputado Federal', partido: 'PT', uf: 'SP', foto_url: null, fonte: 'camara' },
  { id: 'b', nome: 'JOÃO NETO', cargo: 'Senador', partido: null, uf: null, foto_url: null, fonte: 'senado' },
]

describe('semAcento', () => {
  it('remove acentos e baixa caixa', () => {
    expect(semAcento('José ÁVILA')).toBe('jose avila')
  })
})

describe('filtrarPoliticos', () => {
  it('acha por trecho sem acento', () => {
    expect(filtrarPoliticos(LISTA, 'jose av').map((p) => p.id)).toEqual(['a'])
    expect(filtrarPoliticos(LISTA, 'joao').map((p) => p.id)).toEqual(['b'])
  })
  it('vazio com menos de 3 letras', () => {
    expect(filtrarPoliticos(LISTA, 'jo')).toEqual([])
  })
})
```
- `src/lib/busca.ts`:
```ts
import type { Politico } from './tipos'

export function semAcento(texto: string): string {
  return texto.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

export function filtrarPoliticos(lista: Politico[], termo: string, limite = 20): Politico[] {
  const chave = semAcento(termo)
  if (chave.length < 3) return []
  return lista.filter((p) => semAcento(p.nome).includes(chave)).slice(0, limite)
}
```
- `src/lib/dados-build.ts` (fs, usado só em server components/build):
```ts
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import type { Meta, Politico, Resumo, VisaoGeral } from './tipos'

const RAIZ = join(process.cwd(), 'public', 'dados')

function ler<T>(rel: string): T {
  return JSON.parse(readFileSync(join(RAIZ, rel), 'utf-8')) as T
}

export const lerMeta = () => ler<Meta>('meta.json')
export const lerPoliticos = () => ler<Politico[]>('politicos.json')
export const lerPerfil = (id: string) => ler<Resumo>(`perfil/${id}.json`)
export const lerVisaoGeral = (ano: number) => ler<VisaoGeral>(`visao-geral/${ano}.json`)
```

- [ ] **Step 3: Layout** (`src/app/layout.tsx` — porta o App.tsx atual: header com wordmark ⦿ + status + rodapé institucional):

```tsx
import type { Metadata } from 'next'
import Link from 'next/link'
import '@fontsource-variable/archivo/index.css'
import '@fontsource/ibm-plex-mono/500.css'
import '@fontsource/ibm-plex-mono/600.css'
import './globals.css'
import { lerMeta } from '@/lib/dados-build'
import { formatarData } from '@/lib/formato'

export const metadata: Metadata = {
  title: 'Radar Políticos — gastos parlamentares abertos',
  description:
    'Gastos de deputados federais, senadores e deputados distritais (2013–2026), direto das bases abertas oficiais: o quê, com quem, quanto e a nota fiscal.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const meta = lerMeta()
  return (
    <html lang="pt-BR">
      <body>
        <header className="cabecalho">
          <div className="container">
            <Link href="/" className="wordmark"><span>⦿</span>Radar Políticos</Link>
            <nav>
              <Link href="/rankings">Rankings</Link>
            </nav>
            <span className="status-base">
              base: <b>3 casas</b> · {meta.total_despesas.toLocaleString('pt-BR')} despesas ·{' '}
              <b>{meta.anos[0]}–{meta.ano_max}</b>
            </span>
          </div>
        </header>
        <main className="container">{children}</main>
        <footer className="rodape">
          <div className="container">
            <strong>O Radar Políticos não tem vínculo nem viés político-partidário.</strong>{' '}
            Todos os dados vêm das bases abertas oficiais — Câmara dos Deputados (CEAP), Senado
            Federal (CEAPS) e Câmara Legislativa do DF — e são apresentados como publicados, sem
            edição. O objetivo é dar ao cidadão acesso claro à informação que já é pública. Dados
            atualizados em {formatarData(meta.gerado_em.slice(0, 10))}.
          </div>
        </footer>
      </body>
    </html>
  )
}
```

(Bônus real da arquitetura: a barra de status agora mostra a contagem VIVA de despesas, que antes era estática.)

- [ ] **Step 4: Gate**

Para o build ter dados, gerar o dataset da fixture:
```bash
cd backend && uv run python - <<'EOF'
from pathlib import Path
from tests.conftest import *  # noqa
# usa o gerador da fixture manualmente
import duckdb, pytest
EOF
```
— NÃO: mais simples e real, exportar do banco REAL (existe em dados/radar.duckdb):
```bash
cd backend && uv run python -m radar.exportar --db ../dados/radar.duckdb --saida ../frontend-next/public/dados
cd ../frontend-next && npm test && npm run build
```
Expected: exportação ~13 mil arquivos; vitest 7 passed (5 formato + 2 busca); `next build` compila (ainda só layout + página padrão do scaffold).

- [ ] **Step 5: Commit**

```bash
git add .gitignore frontend-next
git commit -m "feat: scaffold Next.js estático com tema e utilitários portados"
```

---

### Task 4: Home — busca client-side + Panorama estático

**Files:**
- Create: `src/componentes/PaginaInicial.tsx`, `src/componentes/Panorama.tsx`
- Modify: `src/app/page.tsx`

**Interfaces:**
- Consumes: `lerMeta/lerVisaoGeral` (build), `filtrarPoliticos`, tipos, `infoFonte`, formatadores.
- Produces: `<Panorama inicial={VisaoGeral} anos={number[]} />` (client; troca de ano via `fetch('/dados/visao-geral/{ano}.json')`); `<PaginaInicial politicosUrl="/dados/politicos.json" ...>`.

- [ ] **Step 1: `src/app/page.tsx`** (server):

```tsx
import { PaginaInicial } from '@/componentes/PaginaInicial'
import { lerMeta, lerVisaoGeral } from '@/lib/dados-build'

export default function Home() {
  const meta = lerMeta()
  const inicial = lerVisaoGeral(meta.ano_max!)
  return <PaginaInicial inicial={inicial} anos={meta.anos} />
}
```

- [ ] **Step 2: `PaginaInicial.tsx`** (client) — porta `Busca.tsx` atual trocando a chamada de API por índice local:

```tsx
'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { filtrarPoliticos } from '@/lib/busca'
import type { Politico, VisaoGeral } from '@/lib/tipos'
import { Panorama } from './Panorama'

export function PaginaInicial({ inicial, anos }: { inicial: VisaoGeral; anos: number[] }) {
  const [indice, setIndice] = useState<Politico[] | null>(null)
  const [busca, setBusca] = useState('')
  const [erro, setErro] = useState('')

  useEffect(() => {
    let ativo = true
    fetch('/dados/politicos.json')
      .then((r) => { if (!r.ok) throw new Error(`Erro ${r.status} ao carregar o índice`); return r.json() })
      .then((lista) => { if (ativo) setIndice(lista) })
      .catch((e) => { if (ativo) setErro(e.message) })
    return () => { ativo = false }
  }, [])

  const ativa = busca.trim().length >= 3
  const resultados = ativa && indice ? filtrarPoliticos(indice, busca) : []

  return (
    <div>
      <h1>Buscar político</h1>
      <input
        className="busca-input"
        placeholder="Digite o nome (mín. 3 letras) — ex: Nikolas, Alan Rick..."
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
        autoFocus
      />
      {erro && <p className="cartao">⚠️ {erro}</p>}
      {ativa && !indice && !erro && <p>Carregando índice...</p>}
      {resultados.map((p) => (
        <Link key={p.id} href={`/politico/${p.id}`}>
          <div className="cartao resultado">
            {p.foto_url ? <img src={p.foto_url} alt="" /> : <div style={{ width: 48 }} />}
            <div>
              <strong>{p.nome}</strong>
              <div>
                {p.cargo}
                {p.partido ? ` · ${p.partido}` : ''}
                {p.uf ? ` · ${p.uf}` : ''}
              </div>
            </div>
          </div>
        </Link>
      ))}
      {ativa && indice && resultados.length === 0 && <p>Nenhum político encontrado.</p>}
      {!ativa && <Panorama inicial={inicial} anos={anos} />}
    </div>
  )
}
```

- [ ] **Step 3: `Panorama.tsx`** — porta o componente atual (`frontend/src/paginas/Panorama.tsx`) com três mudanças mecânicas: (1) primeira linha vira `'use client'`; (2) props `{ inicial, anos }` — estado começa `useState<VisaoGeral>(inicial)` e o efeito de troca de ano faz `fetch(\`/dados/visao-geral/${ano}.json\`)` (com flag `ativo`), sem buscar no mount (`if (ano === undefined) { setDados(inicial); return }`); (3) `ANOS` hardcoded → prop `anos`; `Link` de `next/link` com `href`. TODO o JSX (tiles, split "Por casa", tops, estatísticas, cartões de partido/UF/casa) permanece idêntico ao atual.

- [ ] **Step 4: Gate + commit**

```bash
cd frontend-next && npm run build && npx serve out -l 3999 &
curl -s http://localhost:3999/ | grep -c "Panorama"   # >= 1 (conteúdo no HTML puro)
```
Expected: build OK; HTML da home contém o panorama renderizado.
```bash
git add frontend-next && git commit -m "feat: home estática com busca client-side e panorama"
```

---

### Task 5: Perfil estático + Rankings + sitemap/robots

**Files:**
- Create: `src/app/politico/[id]/page.tsx`, `src/componentes/Perfil.tsx`, `src/componentes/TabelaDespesas.tsx`, `src/app/rankings/page.tsx`, `src/componentes/Rankings.tsx`, `src/app/sitemap.ts`, `src/app/robots.ts`, `public/og-padrao.png` (gerar: quadrado 1200×630 com wordmark — pode ser um PNG simples criado com script/canvas ou copiado do favicon ampliado)

**Interfaces:**
- Consumes: `lerPoliticos/lerPerfil/lerMeta`, tipos, `CORES_ROSCA` (portar de Perfil atual), formatadores.

- [ ] **Step 1: `src/app/politico/[id]/page.tsx`**

```tsx
import type { Metadata } from 'next'
import { Perfil } from '@/componentes/Perfil'
import { lerPerfil, lerPoliticos } from '@/lib/dados-build'
import { formatarBRLCompacto } from '@/lib/formato'

export function generateStaticParams() {
  return lerPoliticos().map((p) => ({ id: p.id }))
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params
  const resumo = lerPerfil(decodeURIComponent(id))
  const p = resumo.politico
  const filiacao = [p.partido, p.uf].filter(Boolean).join('/')
  const anos = resumo.por_ano.map((a) => a.ano)
  const periodo = anos.length ? `${Math.min(...anos)}–${Math.max(...anos)}` : ''
  return {
    title: `Gastos de ${p.nome}${filiacao ? ` (${filiacao})` : ''} — Radar Políticos`,
    description: `${p.cargo} ${p.nome}: ${formatarBRLCompacto(resumo.total)} em verbas públicas (${periodo}). Veja categorias, fornecedores e notas fiscais.`,
    openGraph: { images: [p.foto_url ?? '/og-padrao.png'] },
  }
}

export default async function Pagina({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const resumo = lerPerfil(decodeURIComponent(id))
  return <Perfil resumo={resumo} />
}
```

- [ ] **Step 2: `Perfil.tsx`** (client) — porta `frontend/src/paginas/Perfil.tsx`: recebe `{ resumo }` como prop (sem fetch de resumo, sem useParams, sem estados de erro/loading do resumo); mantém cabeçalho, gráficos (mesmas cores `CORES_ROSCA` dark validadas, `MAX_FATIAS`, paddingAngle, Legend formatter) e top fornecedores idênticos; a seção de despesas vira `<TabelaDespesas politicoId={resumo.politico.id} anos={resumo.por_ano.map((a) => a.ano)} categorias={resumo.por_categoria.map((c) => c.categoria)} />`.

- [ ] **Step 3: `TabelaDespesas.tsx`** (client, novo — substitui a paginação server-side):

```tsx
'use client'
import { useEffect, useMemo, useState } from 'react'
import type { DespesasCompactas } from '@/lib/tipos'
import { formatarBRL, formatarData } from '@/lib/formato'

const POR_PAGINA = 50

interface Linha {
  data: string | null; categoria: string; categoria_original: string
  descricao: string | null; fornecedor: string | null; cnpj: string | null
  valor: number; doc: string | null
}

export function TabelaDespesas({ politicoId, anos, categorias }:
  { politicoId: string; anos: number[]; categorias: string[] }) {
  const [ano, setAno] = useState(Math.max(...anos))
  const [linhas, setLinhas] = useState<Linha[] | null>(null)
  const [categoria, setCategoria] = useState('')
  const [ordenar, setOrdenar] = useState<'-data' | '-valor'>('-data')
  const [pagina, setPagina] = useState(1)
  const [erro, setErro] = useState('')

  useEffect(() => {
    let ativo = true
    setLinhas(null)
    fetch(`/dados/despesas/${politicoId}/${ano}.json`)
      .then((r) => { if (!r.ok) throw new Error(`Erro ${r.status}`); return r.json() })
      .then((d: DespesasCompactas) => {
        if (!ativo) return
        setLinhas(d.linhas.map((l) => ({
          data: l[0] as string | null, categoria: l[1] as string,
          categoria_original: l[2] as string, descricao: l[3] as string | null,
          fornecedor: l[4] as string | null, cnpj: l[5] as string | null,
          valor: l[6] as number, doc: l[7] as string | null,
        })))
        setErro('')
      })
      .catch((e) => { if (ativo) setErro(e.message) })
    return () => { ativo = false }
  }, [politicoId, ano])

  const filtradas = useMemo(() => {
    let base = linhas ?? []
    if (categoria) base = base.filter((l) => l.categoria === categoria)
    if (ordenar === '-valor') base = [...base].sort((a, b) => b.valor - a.valor)
    return base
  }, [linhas, categoria, ordenar])

  const totalPaginas = Math.max(1, Math.ceil(filtradas.length / POR_PAGINA))
  const visiveis = filtradas.slice((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA)

  return (
    <div className="cartao">
      <h3>Despesas</h3>
      <div className="filtros">
        <select value={ano} onChange={(e) => { setPagina(1); setAno(Number(e.target.value)) }}>
          {[...anos].sort((a, b) => b - a).map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <select value={categoria} onChange={(e) => { setPagina(1); setCategoria(e.target.value) }}>
          <option value="">Todas as categorias</option>
          {categorias.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={ordenar} onChange={(e) => { setPagina(1); setOrdenar(e.target.value as '-data' | '-valor') }}>
          <option value="-data">Mais recentes</option>
          <option value="-valor">Maior valor</option>
        </select>
      </div>
      {erro && <p>⚠️ {erro}</p>}
      {!linhas && !erro && <p>Carregando despesas...</p>}
      <table>
        <thead>
          <tr>
            <th>Data</th><th>Categoria</th><th>Fornecedor</th><th>Detalhe</th>
            <th className="valor">Valor</th><th>Nota</th>
          </tr>
        </thead>
        <tbody>
          {visiveis.map((d, i) => (
            <tr key={i}>
              <td>{d.data ? formatarData(d.data) : '—'}</td>
              <td title={d.categoria_original}>{d.categoria}</td>
              <td>{d.fornecedor ?? '—'}</td>
              <td>{d.descricao ?? '—'}</td>
              <td className="valor">{formatarBRL(d.valor)}</td>
              <td>{d.doc ? <a href={d.doc} target="_blank" rel="noreferrer">📄</a> : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="paginacao">
        <button disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>← Anterior</button>
        <span>Página {pagina} de {totalPaginas} ({filtradas.length} despesas em {ano})</span>
        <button disabled={pagina >= totalPaginas} onClick={() => setPagina(pagina + 1)}>Próxima →</button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Rankings** — `src/app/rankings/page.tsx` (server: `lerMeta`, passa `anos` e o ranking do `ano_max` embutido) + `src/componentes/Rankings.tsx` (porta o atual: client, troca de ano via `fetch('/dados/rankings/{ano}.json')` com flag `ativo`, filtro de cargo client-side `itens.filter(i => !cargo || i.politico.cargo === cargo)`, `Link` next).

- [ ] **Step 5: sitemap + robots** (`src/app/sitemap.ts`, `src/app/robots.ts`):

```ts
import type { MetadataRoute } from 'next'
import { lerPoliticos } from '@/lib/dados-build'

export const dynamic = 'force-static'
const BASE = 'https://radarpoliticos.com.br' // ajustar quando o domínio existir

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: `${BASE}/`, changeFrequency: 'daily', priority: 1 },
    { url: `${BASE}/rankings/`, changeFrequency: 'daily', priority: 0.8 },
    ...lerPoliticos().map((p) => ({
      url: `${BASE}/politico/${p.id}/`,
      changeFrequency: 'weekly' as const,
      priority: 0.7,
    })),
  ]
}
```

```ts
import type { MetadataRoute } from 'next'

export const dynamic = 'force-static'

export default function robots(): MetadataRoute.Robots {
  return { rules: { userAgent: '*', allow: '/' }, sitemap: 'https://radarpoliticos.com.br/sitemap.xml' }
}
```

`public/og-padrao.png`: gerar com o script `frontend-next/scripts/gerar-og.mjs` (canvas 1200×630, fundo `#0b1712`, texto "⦿ RADAR POLÍTICOS" em verde `#4ade80` — usar `playwright` do scratchpad ou `sharp`; alternativa aceitável: screenshot 1200×630 da home). O arquivo é commitado.

- [ ] **Step 6: Gate + commit**

```bash
cd frontend-next && npm run build
ls out/politico | wc -l      # ~1.547
grep -o '<title>[^<]*' out/politico/camara-160541/index.html   # "Gastos de Arthur Lira (PP/AL)..."
test -f out/sitemap.xml && echo sitemap ok
git add frontend-next && git commit -m "feat: perfis estáticos com SEO, rankings e sitemap"
```

---

### Task 6: Swap final, README e verificação de escala (controller)

**Files:**
- Delete: `frontend/` (Vite) · Rename: `frontend-next/` → `frontend/` · Modify: `README.md`

- [ ] **Step 1: Swap**

```bash
cd /home/italo/radar-politicos
git rm -r frontend && mv frontend-next frontend
# ajustar .gitignore: remover linhas frontend-next/, manter frontend/public/dados e frontend/out
cd backend && uv run python -m radar.exportar --db ../dados/radar.duckdb --saida ../frontend/public/dados
cd ../frontend && npm run build
```

- [ ] **Step 2: README** — seção "Como rodar" vira:

```bash
# 1. Ingestão (local): idem hoje
# 2. Exportar dados estáticos
cd backend && uv run python -m radar.exportar --db ../dados/radar.duckdb --saida ../frontend/public/dados
# 3. Build do site (gera frontend/out/ pronto para qualquer hosting estático)
cd frontend && npm run build
# 4. Ver localmente
npx serve frontend/out
# (a API FastAPI continua disponível para desenvolvimento: uvicorn ... --port 8010)
```
Mais uma linha em "Publicar": `npx wrangler pages deploy frontend/out` (Cloudflare Pages) ou GitHub Pages.

- [ ] **Step 3: Verificação de escala e e2e (controller)** — `du -sh frontend/out`, `find frontend/out -type f | wc -l` (esperado < 20.000... ATENÇÃO: são ~13 mil JSONs + ~1.550 HTMLs + assets ≈ 16–17 mil — se passar de 20 mil, agrupar despesas por político em UM json por político em vez de por ano é o plano B, decidir com evidência); servir `out/` e rodar Playwright: home (busca "arthur lira" → navegar), perfil com meta tag no HTML cru, troca de ano no panorama e na tabela, rankings, rodapé com "atualizados em". Testes: `cd backend && uv run pytest -q` (64) e `cd frontend && npm test` (7).

- [ ] **Step 4: Commit final**

```bash
git add -A && git commit -m "feat: publicação estática substitui SPA+API (frontend Next exportado)"
```

## Self-Review (feito na escrita)

- **Cobertura do spec:** consultas compartilhadas ✔ (T1, com testes de paridade); exportador atômico+relatório+meta ✔ (T2); Next export/trailingSlash/rotas ✔ (T3–5); metadata/OG por perfil ✔ (T5); seletores de ano via meta.json ✔ (T4–5, paga o débito); sitemap/robots ✔; tabela de despesas por chunk anual com filtros client ✔; README + swap + verificação de escala ✔ (T6). Fora de escopo respeitado (sem deploy real).
- **Placeholders:** nenhum — passos de porte referenciam arquivos-fonte existentes no repo com as mudanças mecânicas enumeradas.
- **Consistência:** nomes de `consultas.py` idênticos entre T1/T2; `DespesasCompactas`/colunas idênticos entre T1, T2 e `TabelaDespesas`; leitores de `dados-build.ts` cobrem exatamente os arquivos que o exportador gera; contagens de teste 53→60→64 conferidas.
