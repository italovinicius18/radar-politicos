# Radar Políticos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sistema local para consultar gastos de deputados federais e senadores (2016–2026): o quê, por quê (categoria), com quem (fornecedor), quanto, quando, com link da nota fiscal.

**Architecture:** ETL em Python baixa CSVs públicos (CEAP/Câmara e CEAPS/Senado), normaliza para um modelo único e carrega num DuckDB local. FastAPI expõe consultas agregadas; frontend React/Vite consome via proxy `/api`.

**Tech Stack:** Python 3.12 + uv, DuckDB, FastAPI, httpx, pytest; Node 20, Vite + React + TypeScript, react-router-dom, recharts, vitest.

## Global Constraints

- Backend em `backend/`, frontend em `frontend/`, dados baixados em `dados/` (gitignorado, junto com `*.duckdb`).
- Gerenciador Python: `uv` (já instalado, 0.9.21). Rodar comandos backend com `uv run` a partir de `backend/`.
- Toda a interface e mensagens em pt-BR; valores em R$ com formatação brasileira (`Intl.NumberFormat('pt-BR')`).
- IDs de político: `camara-{ideCadastro}` e `senado-{slug-do-nome}`.
- Valor usado da Câmara: `vlrLiquido` (líquido pós-glosa — é o que o site oficial soma). Estornos (valores negativos) entram no banco e são somados normalmente.
- Linhas da CEAP sem `ideCadastro` (lideranças partidárias, ex. "LID.GOV-CD") são ignoradas — não são políticos individuais.
- Agrupamento por ano usa o ano de competência (`numAno` / `ANO`), não a data de emissão — é assim que os sites oficiais agrupam.
- Fontes de dados (verificadas em 2026-07-10):
  - Câmara: `https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip` — UTF-8 com BOM, `;`, aspas, decimal com ponto, datas `2025-02-07T00:00:00`.
  - Senado: `https://www.senado.leg.br/transparencia/LAI/verba/despesa_ceaps_{ano}.csv` — latin-1, `;`, primeira linha é "ULTIMA ATUALIZACAO" (pular), decimal com vírgula, datas `DD/MM/YYYY`.
  - Lista de senadores: `https://legis.senado.leg.br/dadosabertos/senador/lista/legislatura/55/57.json` — campos `UfParlamentar`/`SiglaPartidoParlamentar` podem faltar (usar `.get`).
  - Foto deputado: `https://www.camara.leg.br/internet/deputado/bandep/{ideCadastro}.jpg`; foto senador: `https://www.senado.leg.br/senadores/img/fotos-oficiais/senador{CodigoParlamentar}.jpg`.

## File Structure

```
backend/
  pyproject.toml
  radar/
    __init__.py
    db.py                    # conexão + schema DuckDB
    ingest/
      __init__.py
      __main__.py            # CLI: python -m radar.ingest --anos 2016-2026
      normalizacao.py        # parse_valor, parse_data, normalizar_categoria, slug
      loader.py              # carga idempotente no DuckDB + relatório
      fontes/
        __init__.py
        camara.py            # baixar() + parse() da CEAP
        senado.py            # baixar() + parse() da CEAPS + enriquecer()
    api/
      __init__.py
      app.py                 # criar_app(db_path) com os 4 endpoints
  tests/
    conftest.py              # banco de amostra
    test_db.py
    test_normalizacao.py
    test_camara.py
    test_senado.py
    test_loader.py
    test_api.py
    fixtures/
      ceap_amostra.csv
      ceaps_amostra.csv
      senadores_amostra.json
frontend/
  (Vite React TS: src/lib/api.ts, src/lib/formato.ts, src/paginas/{Busca,Perfil,Rankings}.tsx, src/App.tsx)
dados/                       # downloads + radar.duckdb (gitignorado)
```

---

### Task 1: Scaffold do backend + schema DuckDB

**Files:**
- Create: `.gitignore`, `backend/pyproject.toml`, `backend/radar/__init__.py`, `backend/radar/db.py`
- Test: `backend/tests/test_db.py`

**Interfaces:**
- Produces: `radar.db.conectar(caminho: str | Path, somente_leitura: bool = False) -> duckdb.DuckDBPyConnection` e `radar.db.criar_schema(con) -> None`. Tabelas `politicos` e `despesas` conforme DDL abaixo.

- [ ] **Step 1: Criar .gitignore e projeto uv**

```bash
cd /home/italo/radar-politicos
cat > .gitignore <<'EOF'
dados/
*.duckdb
*.duckdb.wal
__pycache__/
.venv/
node_modules/
frontend/dist/
.pytest_cache/
EOF
mkdir -p backend/radar backend/tests
cd backend
uv init --bare --name radar
uv add duckdb httpx "fastapi[standard]"
uv add --dev pytest
```

- [ ] **Step 2: Escrever teste que falha**

`backend/tests/test_db.py`:
```python
from radar.db import conectar, criar_schema


def test_criar_schema_cria_tabelas(tmp_path):
    con = conectar(tmp_path / "t.duckdb")
    criar_schema(con)
    tabelas = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    assert {"politicos", "despesas"} <= tabelas


def test_criar_schema_e_idempotente(tmp_path):
    con = conectar(tmp_path / "t.duckdb")
    criar_schema(con)
    criar_schema(con)  # não deve lançar erro
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `cd backend && uv run pytest tests/test_db.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'radar'` ou import error)

- [ ] **Step 4: Implementar**

`backend/radar/__init__.py`: vazio.

`backend/radar/db.py`:
```python
from pathlib import Path

import duckdb

DDL = """
CREATE TABLE IF NOT EXISTS politicos (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    cargo TEXT NOT NULL,
    partido TEXT,
    uf TEXT,
    foto_url TEXT,
    fonte TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS despesas (
    politico_id TEXT NOT NULL,
    ano INTEGER NOT NULL,
    mes INTEGER,
    data DATE,
    categoria TEXT NOT NULL,
    categoria_original TEXT NOT NULL,
    descricao TEXT,
    fornecedor TEXT,
    fornecedor_cnpj TEXT,
    valor DECIMAL(14, 2) NOT NULL,
    documento_url TEXT,
    fonte TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_despesas_politico ON despesas (politico_id);
CREATE INDEX IF NOT EXISTS idx_despesas_ano ON despesas (ano);
"""


def conectar(caminho: str | Path, somente_leitura: bool = False) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(caminho), read_only=somente_leitura)


def criar_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(DDL)
```

Para o pytest achar o pacote, adicionar ao `backend/pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.uv]
package = true

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["radar"]
```
(Manter as seções `[project]` geradas pelo `uv init`; rodar `uv sync` após editar.)

- [ ] **Step 5: Rodar e ver passar**

Run: `cd backend && uv sync && uv run pytest tests/test_db.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add .gitignore backend
git commit -m "feat: scaffold do backend com schema DuckDB"
```

---

### Task 2: Normalização compartilhada (valores, datas, categorias, slug)

**Files:**
- Create: `backend/radar/ingest/__init__.py`, `backend/radar/ingest/normalizacao.py`
- Test: `backend/tests/test_normalizacao.py`

**Interfaces:**
- Produces:
  - `parse_valor(texto: str) -> float` — aceita `"1467"`, `"-238.27"`, `"399,44"`, `"1.234,56"`, `""` → `0.0`.
  - `parse_data(texto: str) -> datetime.date | None` — aceita ISO (`2025-02-07T00:00:00`, `2025-02-07`) e `DD/MM/YYYY`; inválido/vazio → `None`.
  - `normalizar_categoria(original: str) -> str` — mapeia texto da fonte para categoria comum.
  - `slug(texto: str) -> str` — `"João da Silva"` → `"joao-da-silva"`.
  - `sem_acento(texto: str) -> str` — minúsculas sem acentos (para busca).

- [ ] **Step 1: Escrever testes que falham**

`backend/tests/test_normalizacao.py`:
```python
from datetime import date

from radar.ingest.normalizacao import (
    normalizar_categoria,
    parse_data,
    parse_valor,
    sem_acento,
    slug,
)


def test_parse_valor():
    assert parse_valor("1467") == 1467.0
    assert parse_valor("-238.27") == -238.27
    assert parse_valor("399,44") == 399.44
    assert parse_valor("1.234,56") == 1234.56
    assert parse_valor("") == 0.0


def test_parse_data():
    assert parse_data("2025-02-07T00:00:00") == date(2025, 2, 7)
    assert parse_data("2025-02-07") == date(2025, 2, 7)
    assert parse_data("18/01/2025") == date(2025, 1, 18)
    assert parse_data("") is None
    assert parse_data("data inválida") is None


def test_normalizar_categoria_camara():
    assert normalizar_categoria("PASSAGEM AÉREA - SIGEPA") == "Passagens"
    assert normalizar_categoria("COMBUSTÍVEIS E LUBRIFICANTES.") == "Combustíveis"
    assert normalizar_categoria("DIVULGAÇÃO DA ATIVIDADE PARLAMENTAR.") == "Divulgação"
    assert (
        normalizar_categoria("MANUTENÇÃO DE ESCRITÓRIO DE APOIO À ATIVIDADE PARLAMENTAR")
        == "Manutenção de escritório"
    )
    assert normalizar_categoria("CONSULTORIAS, PESQUISAS E TRABALHOS TÉCNICOS.") == (
        "Consultorias e trabalhos técnicos"
    )


def test_normalizar_categoria_senado():
    assert (
        normalizar_categoria(
            "Locomoção, hospedagem, alimentação, combustíveis e lubrificantes"
        )
        == "Locomoção, hospedagem e alimentação"
    )
    assert (
        normalizar_categoria(
            "Aluguel de imóveis para escritório político, compreendendo despesas concernentes a eles."
        )
        == "Manutenção de escritório"
    )
    assert normalizar_categoria("Divulgação da atividade parlamentar") == "Divulgação"


def test_normalizar_categoria_desconhecida_vira_titulo():
    assert normalizar_categoria("CATEGORIA NOVA QUALQUER") == "Categoria Nova Qualquer"


def test_slug_e_sem_acento():
    assert slug("João da Silva") == "joao-da-silva"
    assert sem_acento("José ÁVILA") == "jose avila"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && uv run pytest tests/test_normalizacao.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implementar**

`backend/radar/ingest/__init__.py`: vazio.

`backend/radar/ingest/normalizacao.py`:
```python
import unicodedata
from datetime import date, datetime


def sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def slug(texto: str) -> str:
    return "-".join(sem_acento(texto).split())


def parse_valor(texto: str) -> float:
    texto = (texto or "").strip()
    if not texto:
        return 0.0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return float(texto)


_FORMATOS_DATA = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y")


def parse_data(texto: str) -> date | None:
    texto = (texto or "").strip()
    for formato in _FORMATOS_DATA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


# Ordem importa: a categoria combinada do Senado ("Locomoção, hospedagem,
# alimentação, combustíveis...") precisa casar antes de COMBUST/ALIMENTA.
_REGRAS_CATEGORIA = [
    ("LOCOMOCAO", "Locomoção, hospedagem e alimentação"),
    ("PASSAGE", "Passagens"),
    ("COMBUST", "Combustíveis"),
    ("DIVULGA", "Divulgação"),
    ("CONSULTOR", "Consultorias e trabalhos técnicos"),
    ("ESCRITORIO", "Manutenção de escritório"),
    ("MATERIAL DE CONSUMO", "Manutenção de escritório"),
    ("TELEFON", "Telefonia"),
    ("POSTA", "Serviços postais"),
    ("ALIMENTA", "Alimentação"),
    ("HOSPEDAGEM", "Hospedagem"),
    ("SEGURANCA", "Segurança"),
    ("TAXI", "Táxi, pedágio e estacionamento"),
    ("VEICULOS", "Locação de veículos"),
    ("AERONAVES", "Locação de aeronaves"),
    ("EMBARCA", "Locação de embarcações"),
    ("CURSO", "Cursos e eventos"),
    ("ASSINATURA", "Publicações"),
    ("TOKENS", "Certificados digitais"),
]


def normalizar_categoria(original: str) -> str:
    chave = sem_acento(original).upper()
    for padrao, categoria in _REGRAS_CATEGORIA:
        if padrao in chave:
            return categoria
    return original.strip().title()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && uv run pytest tests/test_normalizacao.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: normalização de valores, datas, categorias e slugs"
```

---

### Task 3: Fonte Câmara (CEAP)

**Files:**
- Create: `backend/radar/ingest/fontes/__init__.py`, `backend/radar/ingest/fontes/camara.py`, `backend/tests/fixtures/ceap_amostra.csv`
- Test: `backend/tests/test_camara.py`

**Interfaces:**
- Consumes: `normalizacao.parse_valor/parse_data/normalizar_categoria`.
- Produces (contrato de toda fonte, usado pelo loader na Task 5):
  - `FONTE = "camara"`
  - `baixar(ano: int, pasta: Path) -> Path` — baixa e extrai; retorna caminho do CSV. Se o arquivo já existe na pasta, não baixa de novo.
  - `parse(caminho: Path) -> Iterator[tuple[dict, dict]]` — pares `(politico, despesa)`. `politico`: chaves `id, nome, cargo, partido, uf, foto_url, fonte`. `despesa`: chaves `politico_id, ano, mes, data, categoria, categoria_original, descricao, fornecedor, fornecedor_cnpj, valor, documento_url, fonte`.

- [ ] **Step 1: Criar fixture com dados reais (incluindo linha de liderança e estorno)**

`backend/tests/fixtures/ceap_amostra.csv` (UTF-8 com BOM, uma linha de cabeçalho real da CEAP; a primeira linha de dados é liderança sem ideCadastro e deve ser ignorada; a terceira é estorno negativo):
```csv
"txNomeParlamentar";"cpf";"ideCadastro";"nuCarteiraParlamentar";"nuLegislatura";"sgUF";"sgPartido";"codLegislatura";"numSubCota";"txtDescricao";"numEspecificacaoSubCota";"txtDescricaoEspecificacao";"txtFornecedor";"txtCNPJCPF";"txtNumero";"indTipoDocumento";"datEmissao";"vlrDocumento";"vlrGlosa";"vlrLiquido";"numMes";"numAno";"numParcela";"txtPassageiro";"txtTrecho";"numLote";"numRessarcimento";"datPagamentoRestituicao";"vlrRestituicao";"nuDeputadoId";"ideDocumento";"urlDocumento"
"LID.GOV-CD";"";"";"";"2023";"NA";"";"57";"1";"MANUTENÇÃO DE ESCRITÓRIO DE APOIO À ATIVIDADE PARLAMENTAR";"0";"";"AMORETTO CAFES EXPRESSO LTDA";"085.324.290/0013-1";"1984";"0";"2025-02-07T00:00:00";"1467";"0";"1467";"2";"2025";"0";"";"";"2115566";"";"";"";"2812";"7877589";"https://www.camara.leg.br/cota-parlamentar/documentos/publ/2812/2025/7877589.pdf"
"Gervásio Maia";"88623327420";"204394";"133";"2023";"PB";"PCdoB";"57";"999";"PASSAGEM AÉREA - RPA";"0";"";"TAM";"02.012.862/0001-60";"957";"0";"2025-02-15T00:00:00";"1500.50";"0";"1500.50";"2";"2025";"0";"GERVASIO MAIA";"BSB/JPA";"0";"0";"";"";"3401";"314240";"https://www.camara.leg.br/cota-parlamentar/nota-fiscal-eletronica?ideDocumentoFiscal=314240"
"Gervásio Maia";"88623327420";"204394";"133";"2023";"PB";"PCdoB";"57";"998";"PASSAGEM AÉREA - SIGEPA";"0";"";"TAM";"";"9572222045926";"0";"2025-03-02T12:00:00";"-238.27";"0";"-238.27";"3";"2025";"0";"GERVASIO AGRIPINO MAIA";"BSB /JPA";"0";"0";"";"";"3401";"314239";""
```

- [ ] **Step 2: Escrever testes que falham**

`backend/tests/test_camara.py`:
```python
from datetime import date
from pathlib import Path

from radar.ingest.fontes import camara

FIXTURE = Path(__file__).parent / "fixtures" / "ceap_amostra.csv"


def test_parse_ignora_liderancas_e_gera_pares():
    pares = list(camara.parse(FIXTURE))
    assert len(pares) == 2  # linha de liderança (sem ideCadastro) ignorada


def test_parse_politico():
    politico, _ = list(camara.parse(FIXTURE))[0]
    assert politico == {
        "id": "camara-204394",
        "nome": "Gervásio Maia",
        "cargo": "Deputado Federal",
        "partido": "PCdoB",
        "uf": "PB",
        "foto_url": "https://www.camara.leg.br/internet/deputado/bandep/204394.jpg",
        "fonte": "camara",
    }


def test_parse_despesa():
    _, despesa = list(camara.parse(FIXTURE))[0]
    assert despesa["politico_id"] == "camara-204394"
    assert despesa["ano"] == 2025
    assert despesa["mes"] == 2
    assert despesa["data"] == date(2025, 2, 15)
    assert despesa["categoria"] == "Passagens"
    assert despesa["categoria_original"] == "PASSAGEM AÉREA - RPA"
    assert despesa["descricao"] == "BSB/JPA"
    assert despesa["fornecedor"] == "TAM"
    assert despesa["fornecedor_cnpj"] == "02.012.862/0001-60"
    assert despesa["valor"] == 1500.50
    assert despesa["documento_url"].startswith("https://www.camara.leg.br/")
    assert despesa["fonte"] == "camara"


def test_parse_estorno_negativo_e_url_vazia():
    _, estorno = list(camara.parse(FIXTURE))[1]
    assert estorno["valor"] == -238.27
    assert estorno["documento_url"] is None
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `cd backend && uv run pytest tests/test_camara.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 4: Implementar**

`backend/radar/ingest/fontes/__init__.py`: vazio.

`backend/radar/ingest/fontes/camara.py`:
```python
import csv
import zipfile
from collections.abc import Iterator
from pathlib import Path

import httpx

from radar.ingest.normalizacao import normalizar_categoria, parse_data, parse_valor

FONTE = "camara"
URL = "https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip"
FOTO = "https://www.camara.leg.br/internet/deputado/bandep/{id}.jpg"


def baixar(ano: int, pasta: Path) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    csv_destino = pasta / f"Ano-{ano}.csv"
    if csv_destino.exists():
        return csv_destino
    zip_destino = pasta / f"Ano-{ano}.csv.zip"
    with httpx.stream("GET", URL.format(ano=ano), timeout=300, follow_redirects=True) as r:
        r.raise_for_status()
        with open(zip_destino, "wb") as f:
            for pedaco in r.iter_bytes():
                f.write(pedaco)
    with zipfile.ZipFile(zip_destino) as z:
        z.extract(f"Ano-{ano}.csv", pasta)
    zip_destino.unlink()
    return csv_destino


def parse(caminho: Path) -> Iterator[tuple[dict, dict]]:
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        for linha in csv.DictReader(f, delimiter=";"):
            ide = (linha["ideCadastro"] or "").strip()
            if not ide:
                continue  # linhas de liderança partidária, não são políticos
            uf = (linha["sgUF"] or "").strip()
            politico = {
                "id": f"camara-{ide}",
                "nome": linha["txNomeParlamentar"].strip(),
                "cargo": "Deputado Federal",
                "partido": (linha["sgPartido"] or "").strip() or None,
                "uf": uf if uf and uf != "NA" else None,
                "foto_url": FOTO.format(id=ide),
                "fonte": FONTE,
            }
            descricao = (linha["txtDescricaoEspecificacao"] or "").strip() or (
                linha["txtTrecho"] or ""
            ).strip() or None
            despesa = {
                "politico_id": politico["id"],
                "ano": int(linha["numAno"]),
                "mes": int(linha["numMes"]) if linha["numMes"] else None,
                "data": parse_data(linha["datEmissao"]),
                "categoria": normalizar_categoria(linha["txtDescricao"]),
                "categoria_original": linha["txtDescricao"].strip(),
                "descricao": descricao,
                "fornecedor": (linha["txtFornecedor"] or "").strip() or None,
                "fornecedor_cnpj": (linha["txtCNPJCPF"] or "").strip() or None,
                "valor": parse_valor(linha["vlrLiquido"]),
                "documento_url": (linha["urlDocumento"] or "").strip() or None,
                "fonte": FONTE,
            }
            yield politico, despesa
```

- [ ] **Step 5: Rodar e ver passar**

Run: `cd backend && uv run pytest tests/test_camara.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add backend
git commit -m "feat: fonte Câmara (CEAP) com download e parse"
```

---

### Task 4: Fonte Senado (CEAPS) + enriquecimento de senadores

**Files:**
- Create: `backend/radar/ingest/fontes/senado.py`, `backend/tests/fixtures/ceaps_amostra.csv`, `backend/tests/fixtures/senadores_amostra.json`
- Test: `backend/tests/test_senado.py`

**Interfaces:**
- Consumes: `normalizacao.*`.
- Produces: mesmo contrato de fonte da Task 3 (`FONTE = "senado"`, `baixar(ano, pasta) -> Path`, `parse(caminho) -> Iterator[tuple[dict, dict]]`), mais:
  - `enriquecer(con) -> int` — busca a lista de senadores (legislaturas 55–57), casa por nome normalizado e atualiza `partido`, `uf`, `foto_url` dos políticos `senado-*`; retorna quantos atualizou. Aceita parâmetro opcional `dados` (dict já carregado) para testes.

- [ ] **Step 1: Criar fixtures**

`backend/tests/fixtures/ceaps_amostra.csv` (salvar em **latin-1**; primeira linha é a de atualização, que o parse pula):
```csv
"ULTIMA ATUALIZACAO";"10/07/2026 02:02"
"ANO";"MES";"SENADOR";"TIPO_DESPESA";"CNPJ_CPF";"FORNECEDOR";"DOCUMENTO";"DATA";"DETALHAMENTO";"VALOR_REEMBOLSADO";"COD_DOCUMENTO"
"2025";"1";"ALAN RICK";"Aluguel de imóveis para escritório político, compreendendo despesas concernentes a eles.";"66.970.229/0132-26";"CLARO NXT TELECOMUNICAÇÕES S.A";"693736";"18/01/2025";"";"399,44";"2248419"
"2025";"1";"ALAN RICK";"Locomoção, hospedagem, alimentação, combustíveis e lubrificantes";"00.529.581/0001-53";"AUTO POSTO AMAPÁ LTDA";"2108920";"08/02/2025";"Abastecimento veículo oficial";"150";"2249041"
```
Gerar com Python para garantir a codificação:
```bash
cd backend && uv run python -c "
conteudo = '''\"ULTIMA ATUALIZACAO\";\"10/07/2026 02:02\"
\"ANO\";\"MES\";\"SENADOR\";\"TIPO_DESPESA\";\"CNPJ_CPF\";\"FORNECEDOR\";\"DOCUMENTO\";\"DATA\";\"DETALHAMENTO\";\"VALOR_REEMBOLSADO\";\"COD_DOCUMENTO\"
\"2025\";\"1\";\"ALAN RICK\";\"Aluguel de imóveis para escritório político, compreendendo despesas concernentes a eles.\";\"66.970.229/0132-26\";\"CLARO NXT TELECOMUNICAÇÕES S.A\";\"693736\";\"18/01/2025\";\"\";\"399,44\";\"2248419\"
\"2025\";\"1\";\"ALAN RICK\";\"Locomoção, hospedagem, alimentação, combustíveis e lubrificantes\";\"00.529.581/0001-53\";\"AUTO POSTO AMAPÁ LTDA\";\"2108920\";\"08/02/2025\";\"Abastecimento veículo oficial\";\"150\";\"2249041\"
'''
open('tests/fixtures/ceaps_amostra.csv', 'w', encoding='latin-1').write(conteudo)
"
```

`backend/tests/fixtures/senadores_amostra.json`:
```json
{
  "ListaParlamentarLegislatura": {
    "Parlamentares": {
      "Parlamentar": [
        {
          "IdentificacaoParlamentar": {
            "CodigoParlamentar": "6335",
            "NomeParlamentar": "Alan Rick",
            "SiglaPartidoParlamentar": "UNIÃO",
            "UfParlamentar": "AC"
          }
        },
        {
          "IdentificacaoParlamentar": {
            "CodigoParlamentar": "5573",
            "NomeParlamentar": "Abel Rebouças",
            "SiglaPartidoParlamentar": "PDT"
          }
        }
      ]
    }
  }
}
```

- [ ] **Step 2: Escrever testes que falham**

`backend/tests/test_senado.py`:
```python
import json
from datetime import date
from pathlib import Path

from radar.db import conectar, criar_schema
from radar.ingest.fontes import senado

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_pula_linha_de_atualizacao():
    pares = list(senado.parse(FIXTURES / "ceaps_amostra.csv"))
    assert len(pares) == 2


def test_parse_politico_e_despesa():
    politico, despesa = list(senado.parse(FIXTURES / "ceaps_amostra.csv"))[0]
    assert politico["id"] == "senado-alan-rick"
    assert politico["nome"] == "ALAN RICK"
    assert politico["cargo"] == "Senador"
    assert politico["fonte"] == "senado"
    assert despesa["ano"] == 2025
    assert despesa["mes"] == 1
    assert despesa["data"] == date(2025, 1, 18)
    assert despesa["categoria"] == "Manutenção de escritório"
    assert despesa["valor"] == 399.44
    assert despesa["fornecedor_cnpj"] == "66.970.229/0132-26"
    assert despesa["documento_url"] is None


def test_parse_valor_sem_decimal_e_detalhamento():
    _, despesa = list(senado.parse(FIXTURES / "ceaps_amostra.csv"))[1]
    assert despesa["valor"] == 150.0
    assert despesa["descricao"] == "Abastecimento veículo oficial"
    assert despesa["categoria"] == "Locomoção, hospedagem e alimentação"


def test_enriquecer_atualiza_partido_uf_foto(tmp_path):
    con = conectar(tmp_path / "t.duckdb")
    criar_schema(con)
    con.execute(
        "INSERT INTO politicos VALUES ('senado-alan-rick', 'ALAN RICK', 'Senador', NULL, NULL, NULL, 'senado')"
    )
    dados = json.loads((FIXTURES / "senadores_amostra.json").read_text())
    atualizados = senado.enriquecer(con, dados=dados)
    assert atualizados == 1
    linha = con.execute(
        "SELECT partido, uf, foto_url FROM politicos WHERE id = 'senado-alan-rick'"
    ).fetchone()
    assert linha == (
        "UNIÃO",
        "AC",
        "https://www.senado.leg.br/senadores/img/fotos-oficiais/senador6335.jpg",
    )
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `cd backend && uv run pytest tests/test_senado.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 4: Implementar**

`backend/radar/ingest/fontes/senado.py`:
```python
import csv
from collections.abc import Iterator
from pathlib import Path

import httpx

from radar.ingest.normalizacao import (
    normalizar_categoria,
    parse_data,
    parse_valor,
    sem_acento,
    slug,
)

FONTE = "senado"
URL = "https://www.senado.leg.br/transparencia/LAI/verba/despesa_ceaps_{ano}.csv"
URL_SENADORES = "https://legis.senado.leg.br/dadosabertos/senador/lista/legislatura/55/57.json"
FOTO = "https://www.senado.leg.br/senadores/img/fotos-oficiais/senador{codigo}.jpg"


def baixar(ano: int, pasta: Path) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"despesa_ceaps_{ano}.csv"
    if destino.exists():
        return destino
    with httpx.stream("GET", URL.format(ano=ano), timeout=300, follow_redirects=True) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for pedaco in r.iter_bytes():
                f.write(pedaco)
    return destino


def parse(caminho: Path) -> Iterator[tuple[dict, dict]]:
    with open(caminho, encoding="latin-1", newline="") as f:
        f.readline()  # primeira linha: "ULTIMA ATUALIZACAO";...
        for linha in csv.DictReader(f, delimiter=";"):
            nome = linha["SENADOR"].strip()
            politico = {
                "id": f"senado-{slug(nome)}",
                "nome": nome,
                "cargo": "Senador",
                "partido": None,
                "uf": None,
                "foto_url": None,
                "fonte": FONTE,
            }
            despesa = {
                "politico_id": politico["id"],
                "ano": int(linha["ANO"]),
                "mes": int(linha["MES"]) if linha["MES"] else None,
                "data": parse_data(linha["DATA"]),
                "categoria": normalizar_categoria(linha["TIPO_DESPESA"]),
                "categoria_original": linha["TIPO_DESPESA"].strip(),
                "descricao": (linha["DETALHAMENTO"] or "").strip() or None,
                "fornecedor": (linha["FORNECEDOR"] or "").strip() or None,
                "fornecedor_cnpj": (linha["CNPJ_CPF"] or "").strip() or None,
                "valor": parse_valor(linha["VALOR_REEMBOLSADO"]),
                "documento_url": None,  # CEAPS não publica URL de documento
                "fonte": FONTE,
            }
            yield politico, despesa


def enriquecer(con, dados: dict | None = None) -> int:
    """Preenche partido/uf/foto dos senadores casando por nome normalizado."""
    if dados is None:
        dados = httpx.get(URL_SENADORES, timeout=60, follow_redirects=True).json()
    parlamentares = dados["ListaParlamentarLegislatura"]["Parlamentares"]["Parlamentar"]
    atualizados = 0
    existentes = {
        sem_acento(nome): pid
        for pid, nome in con.execute(
            "SELECT id, nome FROM politicos WHERE fonte = 'senado'"
        ).fetchall()
    }
    for p in parlamentares:
        ident = p["IdentificacaoParlamentar"]
        pid = existentes.get(sem_acento(ident["NomeParlamentar"]))
        if not pid:
            continue
        con.execute(
            "UPDATE politicos SET partido = ?, uf = ?, foto_url = ? WHERE id = ?",
            (
                ident.get("SiglaPartidoParlamentar"),
                ident.get("UfParlamentar"),
                FOTO.format(codigo=ident["CodigoParlamentar"]),
                pid,
            ),
        )
        atualizados += 1
    return atualizados
```

- [ ] **Step 5: Rodar e ver passar**

Run: `cd backend && uv run pytest tests/test_senado.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add backend
git commit -m "feat: fonte Senado (CEAPS) com parse e enriquecimento de senadores"
```

---

### Task 5: Loader idempotente + CLI de ingestão

**Files:**
- Create: `backend/radar/ingest/loader.py`, `backend/radar/ingest/__main__.py`
- Test: `backend/tests/test_loader.py`

**Interfaces:**
- Consumes: contrato de fonte (Tasks 3–4), `db.conectar/criar_schema`.
- Produces:
  - `loader.carregar(con, fonte_modulo, ano: int, pasta: Path) -> int` — baixa (se preciso), apaga despesas daquele (fonte, ano) e insere de novo; upsert de políticos; retorna nº de despesas inseridas.
  - CLI `python -m radar.ingest --anos 2016-2026 --fontes camara,senado --db ../dados/radar.duckdb --pasta ../dados` com relatório final e resiliência a falhas por (fonte, ano).

- [ ] **Step 1: Escrever teste que falha**

`backend/tests/test_loader.py`:
```python
from pathlib import Path

from radar.db import conectar, criar_schema
from radar.ingest import loader
from radar.ingest.fontes import camara

FIXTURE = Path(__file__).parent / "fixtures" / "ceap_amostra.csv"


class FonteFake:
    """Fonte que 'baixa' devolvendo a fixture da CEAP."""

    FONTE = "camara"
    parse = staticmethod(camara.parse)

    @staticmethod
    def baixar(ano, pasta):
        return FIXTURE


def test_carregar_insere_despesas_e_politicos(tmp_path):
    con = conectar(tmp_path / "t.duckdb")
    criar_schema(con)
    n = loader.carregar(con, FonteFake, 2025, tmp_path)
    assert n == 2
    assert con.execute("SELECT count(*) FROM despesas").fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM politicos").fetchone()[0] == 1


def test_carregar_e_idempotente(tmp_path):
    con = conectar(tmp_path / "t.duckdb")
    criar_schema(con)
    loader.carregar(con, FonteFake, 2025, tmp_path)
    loader.carregar(con, FonteFake, 2025, tmp_path)  # segunda carga não duplica
    assert con.execute("SELECT count(*) FROM despesas").fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM politicos").fetchone()[0] == 1
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && uv run pytest tests/test_loader.py -v`
Expected: FAIL (ModuleNotFoundError ou AttributeError)

- [ ] **Step 3: Implementar loader**

`backend/radar/ingest/loader.py`:
```python
from pathlib import Path

_COLUNAS_DESPESA = (
    "politico_id", "ano", "mes", "data", "categoria", "categoria_original",
    "descricao", "fornecedor", "fornecedor_cnpj", "valor", "documento_url", "fonte",
)
_SQL_DESPESA = (
    f"INSERT INTO despesas ({', '.join(_COLUNAS_DESPESA)}) "
    f"VALUES ({', '.join('?' * len(_COLUNAS_DESPESA))})"
)
_SQL_POLITICO = (
    "INSERT OR REPLACE INTO politicos (id, nome, cargo, partido, uf, foto_url, fonte) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)"
)
_TAMANHO_LOTE = 50_000


def carregar(con, fonte_modulo, ano: int, pasta: Path) -> int:
    caminho = fonte_modulo.baixar(ano, pasta)
    con.execute(
        "DELETE FROM despesas WHERE fonte = ? AND ano = ?", (fonte_modulo.FONTE, ano)
    )
    politicos: dict[str, tuple] = {}
    lote: list[tuple] = []
    total = 0
    for politico, despesa in fonte_modulo.parse(caminho):
        # Só carrega despesas do ano pedido (o CSV anual pode conter competências vizinhas)
        if despesa["ano"] != ano:
            continue
        politicos[politico["id"]] = (
            politico["id"], politico["nome"], politico["cargo"],
            politico["partido"], politico["uf"], politico["foto_url"], politico["fonte"],
        )
        lote.append(tuple(despesa[c] for c in _COLUNAS_DESPESA))
        if len(lote) >= _TAMANHO_LOTE:
            con.executemany(_SQL_DESPESA, lote)
            total += len(lote)
            lote = []
    if lote:
        con.executemany(_SQL_DESPESA, lote)
        total += len(lote)
    if politicos:
        con.executemany(_SQL_POLITICO, list(politicos.values()))
    return total
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && uv run pytest tests/test_loader.py -v`
Expected: 2 passed

- [ ] **Step 5: Implementar CLI**

`backend/radar/ingest/__main__.py`:
```python
import argparse
import sys
from pathlib import Path

from radar.db import conectar, criar_schema
from radar.ingest import loader
from radar.ingest.fontes import camara, senado

FONTES = {"camara": camara, "senado": senado}


def parse_anos(texto: str) -> list[int]:
    if "-" in texto:
        inicio, fim = texto.split("-")
        return list(range(int(inicio), int(fim) + 1))
    return [int(a) for a in texto.split(",")]


def main() -> int:
    p = argparse.ArgumentParser(description="Ingestão de gastos parlamentares")
    p.add_argument("--anos", required=True, help="ex: 2016-2026 ou 2024,2025")
    p.add_argument("--fontes", default="camara,senado")
    p.add_argument("--db", default="../dados/radar.duckdb")
    p.add_argument("--pasta", default="../dados")
    args = p.parse_args()

    anos = parse_anos(args.anos)
    fontes = [FONTES[f.strip()] for f in args.fontes.split(",")]
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    con = conectar(args.db)
    criar_schema(con)

    sucesso, falhas = [], []
    for fonte in fontes:
        for ano in anos:
            try:
                n = loader.carregar(con, fonte, ano, Path(args.pasta) / fonte.FONTE)
                sucesso.append((fonte.FONTE, ano, n))
                print(f"✔ {fonte.FONTE} {ano}: {n:,} despesas".replace(",", "."))
            except Exception as e:  # resiliente: falha em um ano não para o resto
                falhas.append((fonte.FONTE, ano, str(e)))
                print(f"✖ {fonte.FONTE} {ano}: {e}", file=sys.stderr)

    try:
        atualizados = senado.enriquecer(con)
        print(f"✔ senadores enriquecidos (partido/uf/foto): {atualizados}")
    except Exception as e:
        print(f"✖ enriquecimento de senadores: {e}", file=sys.stderr)

    total = sum(n for _, _, n in sucesso)
    print(f"\nRelatório: {len(sucesso)} cargas OK, {len(falhas)} falhas, "
          f"{total:,} despesas no total".replace(",", "."))
    for fonte, ano, erro in falhas:
        print(f"  FALTOU {fonte} {ano}: {erro}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Fumaça manual com um ano pequeno do Senado**

Run: `cd backend && uv run python -m radar.ingest --anos 2025 --fontes senado --db ../dados/radar-teste.duckdb --pasta ../dados`
Expected: `✔ senado 2025: N despesas` (N na casa dos milhares), enriquecimento > 70, exit 0. Depois: `rm ../dados/radar-teste.duckdb`.

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "feat: loader idempotente e CLI de ingestão com relatório"
```

---

### Task 6: API — busca e resumo

**Files:**
- Create: `backend/radar/api/__init__.py`, `backend/radar/api/app.py`
- Test: `backend/tests/conftest.py`, `backend/tests/test_api.py`

**Interfaces:**
- Consumes: tabelas do DuckDB.
- Produces: `criar_app(db_path: str) -> FastAPI` com:
  - `GET /api/politicos?busca=&cargo=&partido=&uf=&limite=20` → `[{id, nome, cargo, partido, uf, foto_url, fonte}]` (busca parcial sem acento).
  - `GET /api/politicos/{id}/resumo?ano_inicio=&ano_fim=` → `{politico, total, por_ano: [{ano, total}], por_categoria: [{categoria, total}], top_fornecedores: [{fornecedor, cnpj, total, quantidade}]}`; 404 se político não existe.

- [ ] **Step 1: Escrever conftest e testes que falham**

`backend/tests/conftest.py`:
```python
import pytest
from fastapi.testclient import TestClient

from radar.db import conectar, criar_schema


@pytest.fixture
def db_amostra(tmp_path):
    caminho = tmp_path / "amostra.duckdb"
    con = conectar(caminho)
    criar_schema(con)
    con.execute("""
        INSERT INTO politicos VALUES
        ('camara-1', 'José Ávila', 'Deputado Federal', 'PT', 'SP', 'http://foto/1.jpg', 'camara'),
        ('camara-2', 'Maria Souza', 'Deputado Federal', 'PL', 'MG', 'http://foto/2.jpg', 'camara'),
        ('senado-joao-neto', 'JOÃO NETO', 'Senador', 'MDB', 'GO', NULL, 'senado')
    """)
    con.execute("""
        INSERT INTO despesas VALUES
        ('camara-1', 2024, 1, '2024-01-10', 'Passagens', 'PASSAGEM AÉREA - SIGEPA', 'BSB/GRU',
         'TAM', '02.012.862/0001-60', 1000.00, 'http://doc/1.pdf', 'camara'),
        ('camara-1', 2024, 2, '2024-02-05', 'Combustíveis', 'COMBUSTÍVEIS E LUBRIFICANTES.', NULL,
         'POSTO X', '11.111.111/0001-11', 300.00, NULL, 'camara'),
        ('camara-1', 2025, 1, '2025-01-15', 'Passagens', 'PASSAGEM AÉREA - SIGEPA', NULL,
         'TAM', '02.012.862/0001-60', -200.00, NULL, 'camara'),
        ('camara-2', 2024, 3, '2024-03-01', 'Divulgação', 'DIVULGAÇÃO DA ATIVIDADE PARLAMENTAR.', NULL,
         'GRÁFICA Y', '22.222.222/0001-22', 5000.00, 'http://doc/2.pdf', 'camara'),
        ('senado-joao-neto', 2024, 1, '2024-01-20', 'Manutenção de escritório',
         'Aluguel de imóveis para escritório político', NULL,
         'IMOBILIÁRIA Z', '33.333.333/0001-33', 2000.00, NULL, 'senado')
    """)
    con.close()
    return str(caminho)


@pytest.fixture
def cliente(db_amostra):
    from radar.api.app import criar_app

    return TestClient(criar_app(db_amostra))
```

`backend/tests/test_api.py` (parte 1):
```python
def test_busca_sem_acento(cliente):
    r = cliente.get("/api/politicos", params={"busca": "jose avila"})
    assert r.status_code == 200
    assert [p["id"] for p in r.json()] == ["camara-1"]


def test_busca_com_filtros(cliente):
    r = cliente.get("/api/politicos", params={"cargo": "Senador"})
    assert [p["id"] for p in r.json()] == ["senado-joao-neto"]


def test_resumo_totais(cliente):
    r = cliente.get("/api/politicos/camara-1/resumo")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["politico"]["nome"] == "José Ávila"
    assert corpo["total"] == 1100.00  # 1000 + 300 - 200 (estorno subtrai)
    assert {"ano": 2024, "total": 1300.00} in corpo["por_ano"]
    assert {"ano": 2025, "total": -200.00} in corpo["por_ano"]
    categorias = {c["categoria"]: c["total"] for c in corpo["por_categoria"]}
    assert categorias["Passagens"] == 800.00
    assert corpo["top_fornecedores"][0]["fornecedor"] == "TAM"


def test_resumo_filtro_ano(cliente):
    r = cliente.get("/api/politicos/camara-1/resumo", params={"ano_inicio": 2025})
    assert r.json()["total"] == -200.00


def test_resumo_politico_inexistente_404(cliente):
    assert cliente.get("/api/politicos/nao-existe/resumo").status_code == 404
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && uv run pytest tests/test_api.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implementar**

`backend/radar/api/__init__.py`: vazio.

`backend/radar/api/app.py`:
```python
import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

COLUNAS_POLITICO = ("id", "nome", "cargo", "partido", "uf", "foto_url", "fonte")


def _politico_dict(linha) -> dict:
    return dict(zip(COLUNAS_POLITICO, linha))


def criar_app(db_path: str) -> FastAPI:
    app = FastAPI(title="Radar Políticos")
    app.add_middleware(
        CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"]
    )

    def con() -> duckdb.DuckDBPyConnection:
        return duckdb.connect(db_path, read_only=True)

    @app.get("/api/politicos")
    def buscar_politicos(
        busca: str = "",
        cargo: str | None = None,
        partido: str | None = None,
        uf: str | None = None,
        limite: int = Query(20, le=100),
    ):
        sql = f"SELECT {', '.join(COLUNAS_POLITICO)} FROM politicos WHERE 1=1"
        parametros: list = []
        if busca:
            sql += " AND strip_accents(lower(nome)) LIKE '%' || strip_accents(lower(?)) || '%'"
            parametros.append(busca)
        for coluna, valor in (("cargo", cargo), ("partido", partido), ("uf", uf)):
            if valor:
                sql += f" AND {coluna} = ?"
                parametros.append(valor)
        sql += " ORDER BY nome LIMIT ?"
        parametros.append(limite)
        with con() as c:
            return [_politico_dict(l) for l in c.execute(sql, parametros).fetchall()]

    def _buscar_politico(c, politico_id: str) -> dict:
        linha = c.execute(
            f"SELECT {', '.join(COLUNAS_POLITICO)} FROM politicos WHERE id = ?",
            (politico_id,),
        ).fetchone()
        if not linha:
            raise HTTPException(404, "Político não encontrado")
        return _politico_dict(linha)

    @app.get("/api/politicos/{politico_id}/resumo")
    def resumo(
        politico_id: str,
        ano_inicio: int = 0,
        ano_fim: int = 9999,
    ):
        with con() as c:
            politico = _buscar_politico(c, politico_id)
            filtro = "politico_id = ? AND ano BETWEEN ? AND ?"
            parametros = (politico_id, ano_inicio, ano_fim)
            total = c.execute(
                f"SELECT coalesce(sum(valor), 0) FROM despesas WHERE {filtro}", parametros
            ).fetchone()[0]
            por_ano = c.execute(
                f"SELECT ano, sum(valor) FROM despesas WHERE {filtro} GROUP BY ano ORDER BY ano",
                parametros,
            ).fetchall()
            por_categoria = c.execute(
                f"""SELECT categoria, sum(valor) AS t FROM despesas WHERE {filtro}
                    GROUP BY categoria ORDER BY t DESC""",
                parametros,
            ).fetchall()
            fornecedores = c.execute(
                f"""SELECT fornecedor, coalesce(fornecedor_cnpj, '') AS cnpj,
                           sum(valor) AS t, count(*) AS q
                    FROM despesas WHERE {filtro} AND fornecedor IS NOT NULL
                    GROUP BY fornecedor, cnpj ORDER BY t DESC LIMIT 10""",
                parametros,
            ).fetchall()
        return {
            "politico": politico,
            "total": float(total),
            "por_ano": [{"ano": a, "total": float(t)} for a, t in por_ano],
            "por_categoria": [{"categoria": cat, "total": float(t)} for cat, t in por_categoria],
            "top_fornecedores": [
                {"fornecedor": f, "cnpj": cnpj, "total": float(t), "quantidade": q}
                for f, cnpj, t, q in fornecedores
            ],
        }

    return app
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && uv run pytest tests/test_api.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: API de busca de políticos e resumo de gastos"
```

---

### Task 7: API — despesas paginadas e rankings

**Files:**
- Modify: `backend/radar/api/app.py` (adicionar dois endpoints dentro de `criar_app`, antes do `return app`)
- Test: `backend/tests/test_api.py` (acrescentar)

**Interfaces:**
- Produces:
  - `GET /api/politicos/{id}/despesas?ano=&categoria=&fornecedor=&ordenar=data|-data|valor|-valor&pagina=1&por_pagina=50` → `{total_itens, pagina, por_pagina, itens: [{ano, mes, data, categoria, categoria_original, descricao, fornecedor, fornecedor_cnpj, valor, documento_url, fonte}]}`.
  - `GET /api/rankings?ano=&cargo=&categoria=&limite=20` → `[{politico: {...}, total}]` ordenado do maior para o menor.

- [ ] **Step 1: Acrescentar testes que falham**

Acrescentar ao `backend/tests/test_api.py`:
```python
def test_despesas_paginadas_e_ordenadas(cliente):
    r = cliente.get(
        "/api/politicos/camara-1/despesas",
        params={"ordenar": "-valor", "por_pagina": 2, "pagina": 1},
    )
    corpo = r.json()
    assert corpo["total_itens"] == 3
    assert len(corpo["itens"]) == 2
    assert corpo["itens"][0]["valor"] == 1000.00


def test_despesas_filtro_categoria(cliente):
    r = cliente.get(
        "/api/politicos/camara-1/despesas", params={"categoria": "Passagens"}
    )
    assert r.json()["total_itens"] == 2


def test_despesas_filtro_fornecedor(cliente):
    r = cliente.get("/api/politicos/camara-1/despesas", params={"fornecedor": "tam"})
    assert r.json()["total_itens"] == 2


def test_despesas_ordenar_invalido_422(cliente):
    r = cliente.get(
        "/api/politicos/camara-1/despesas", params={"ordenar": "1; DROP TABLE"}
    )
    assert r.status_code == 422


def test_rankings(cliente):
    r = cliente.get("/api/rankings", params={"ano": 2024})
    corpo = r.json()
    assert corpo[0]["politico"]["id"] == "camara-2"  # 5000 > 2000 > 1300
    assert corpo[0]["total"] == 5000.00
    assert len(corpo) == 3


def test_rankings_filtro_cargo_e_categoria(cliente):
    r = cliente.get("/api/rankings", params={"cargo": "Senador"})
    assert [x["politico"]["id"] for x in r.json()] == ["senado-joao-neto"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && uv run pytest tests/test_api.py -v`
Expected: os 6 novos FAIL (404), os 5 antigos PASS

- [ ] **Step 3: Implementar**

Dentro de `criar_app`, antes do `return app`, acrescentar:
```python
    ORDENACOES = {
        "data": "data ASC NULLS LAST",
        "-data": "data DESC NULLS LAST",
        "valor": "valor ASC",
        "-valor": "valor DESC",
    }
    COLUNAS_DESPESA = (
        "ano", "mes", "data", "categoria", "categoria_original", "descricao",
        "fornecedor", "fornecedor_cnpj", "valor", "documento_url", "fonte",
    )

    @app.get("/api/politicos/{politico_id}/despesas")
    def despesas(
        politico_id: str,
        ano: int | None = None,
        categoria: str | None = None,
        fornecedor: str | None = None,
        ordenar: str = "-data",
        pagina: int = Query(1, ge=1),
        por_pagina: int = Query(50, le=200),
    ):
        if ordenar not in ORDENACOES:
            raise HTTPException(422, f"ordenar deve ser um de: {sorted(ORDENACOES)}")
        filtro = "politico_id = ?"
        parametros: list = [politico_id]
        if ano is not None:
            filtro += " AND ano = ?"
            parametros.append(ano)
        if categoria:
            filtro += " AND categoria = ?"
            parametros.append(categoria)
        if fornecedor:
            filtro += " AND strip_accents(lower(fornecedor)) LIKE '%' || strip_accents(lower(?)) || '%'"
            parametros.append(fornecedor)
        with con() as c:
            _buscar_politico(c, politico_id)
            total_itens = c.execute(
                f"SELECT count(*) FROM despesas WHERE {filtro}", parametros
            ).fetchone()[0]
            linhas = c.execute(
                f"""SELECT {', '.join(COLUNAS_DESPESA)} FROM despesas WHERE {filtro}
                    ORDER BY {ORDENACOES[ordenar]} LIMIT ? OFFSET ?""",
                parametros + [por_pagina, (pagina - 1) * por_pagina],
            ).fetchall()
        return {
            "total_itens": total_itens,
            "pagina": pagina,
            "por_pagina": por_pagina,
            "itens": [
                {
                    **dict(zip(COLUNAS_DESPESA, l)),
                    "data": l[2].isoformat() if l[2] else None,
                    "valor": float(l[8]),
                }
                for l in linhas
            ],
        }

    @app.get("/api/rankings")
    def rankings(
        ano: int | None = None,
        cargo: str | None = None,
        categoria: str | None = None,
        limite: int = Query(20, le=100),
    ):
        filtro = "1=1"
        parametros: list = []
        if ano is not None:
            filtro += " AND d.ano = ?"
            parametros.append(ano)
        if cargo:
            filtro += " AND p.cargo = ?"
            parametros.append(cargo)
        if categoria:
            filtro += " AND d.categoria = ?"
            parametros.append(categoria)
        with con() as c:
            linhas = c.execute(
                f"""SELECT {', '.join('p.' + col for col in COLUNAS_POLITICO)},
                           sum(d.valor) AS total
                    FROM despesas d JOIN politicos p ON p.id = d.politico_id
                    WHERE {filtro}
                    GROUP BY {', '.join('p.' + col for col in COLUNAS_POLITICO)}
                    ORDER BY total DESC LIMIT ?""",
                parametros + [limite],
            ).fetchall()
        return [
            {"politico": _politico_dict(l[:-1]), "total": float(l[-1])} for l in linhas
        ]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && uv run pytest -v`
Expected: todos os testes do backend passed

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: endpoints de despesas paginadas e rankings"
```

---

### Task 8: Frontend — scaffold, API client e página de busca

**Files:**
- Create: `frontend/` (Vite React TS), `frontend/src/lib/api.ts`, `frontend/src/lib/formato.ts`, `frontend/src/lib/formato.test.ts`, `frontend/src/paginas/Busca.tsx`, `frontend/src/App.tsx` (substituir), `frontend/src/index.css` (substituir)
- Modify: `frontend/vite.config.ts` (proxy `/api`)

**Interfaces:**
- Consumes: endpoints `/api/*` da Task 6–7.
- Produces:
  - `api.ts`: tipos `Politico`, `Resumo`, `PaginaDespesas`, `ItemRanking` e funções `buscarPoliticos(busca)`, `obterResumo(id, anoInicio?, anoFim?)`, `obterDespesas(id, filtros)`, `obterRankings(filtros)`.
  - `formato.ts`: `formatarBRL(v: number): string` (ex.: `1234.5` → `"R$ 1.234,50"`), `formatarData(iso: string | null): string` (`"2025-02-07"` → `"07/02/2025"`, null → `"—"`).
  - Rotas: `/` (Busca), `/politico/:id` (Perfil, Task 9), `/rankings` (Task 10).

- [ ] **Step 1: Scaffold**

```bash
cd /home/italo/radar-politicos
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom recharts
npm install -D vitest
```
Adicionar a `frontend/package.json` em `"scripts"`: `"test": "vitest run"`.

Substituir `frontend/vite.config.ts`:
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://localhost:8000' },
  },
})
```

- [ ] **Step 2: Teste de formatação que falha**

`frontend/src/lib/formato.test.ts`:
```ts
import { describe, expect, it } from 'vitest'
import { formatarBRL, formatarData } from './formato'

describe('formatarBRL', () => {
  it('formata em pt-BR', () => {
    expect(formatarBRL(1234.5).replace(/ /g, ' ')).toBe('R$ 1.234,50')
    expect(formatarBRL(-200).replace(/ /g, ' ')).toBe('-R$ 200,00')
  })
})

describe('formatarData', () => {
  it('converte ISO para DD/MM/YYYY', () => {
    expect(formatarData('2025-02-07')).toBe('07/02/2025')
    expect(formatarData(null)).toBe('—')
  })
})
```

Run: `cd frontend && npm test`
Expected: FAIL (arquivo formato.ts não existe)

- [ ] **Step 3: Implementar formato.ts e api.ts**

`frontend/src/lib/formato.ts`:
```ts
const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

export function formatarBRL(valor: number): string {
  return brl.format(valor)
}

export function formatarData(iso: string | null): string {
  if (!iso) return '—'
  const [ano, mes, dia] = iso.split('-')
  return `${dia}/${mes}/${ano}`
}
```

`frontend/src/lib/api.ts`:
```ts
export interface Politico {
  id: string
  nome: string
  cargo: string
  partido: string | null
  uf: string | null
  foto_url: string | null
  fonte: string
}

export interface Resumo {
  politico: Politico
  total: number
  por_ano: { ano: number; total: number }[]
  por_categoria: { categoria: string; total: number }[]
  top_fornecedores: { fornecedor: string; cnpj: string; total: number; quantidade: number }[]
}

export interface Despesa {
  ano: number
  mes: number | null
  data: string | null
  categoria: string
  categoria_original: string
  descricao: string | null
  fornecedor: string | null
  fornecedor_cnpj: string | null
  valor: number
  documento_url: string | null
  fonte: string
}

export interface PaginaDespesas {
  total_itens: number
  pagina: number
  por_pagina: number
  itens: Despesa[]
}

export interface ItemRanking {
  politico: Politico
  total: number
}

async function obter<T>(caminho: string, parametros: Record<string, string | number | undefined>): Promise<T> {
  const query = new URLSearchParams()
  for (const [chave, valor] of Object.entries(parametros)) {
    if (valor !== undefined && valor !== '') query.set(chave, String(valor))
  }
  const resposta = await fetch(`${caminho}?${query}`)
  if (!resposta.ok) throw new Error(`Erro ${resposta.status} ao consultar a API`)
  return resposta.json()
}

export const buscarPoliticos = (busca: string) =>
  obter<Politico[]>('/api/politicos', { busca })

export const obterResumo = (id: string, anoInicio?: number, anoFim?: number) =>
  obter<Resumo>(`/api/politicos/${id}/resumo`, { ano_inicio: anoInicio, ano_fim: anoFim })

export const obterDespesas = (
  id: string,
  filtros: { ano?: number; categoria?: string; ordenar?: string; pagina?: number },
) => obter<PaginaDespesas>(`/api/politicos/${id}/despesas`, filtros)

export const obterRankings = (filtros: { ano?: number; cargo?: string; categoria?: string }) =>
  obter<ItemRanking[]>('/api/rankings', filtros)
```

Run: `cd frontend && npm test`
Expected: 2 passed

- [ ] **Step 4: App com rotas + página de busca**

Substituir `frontend/src/index.css`:
```css
:root {
  font-family: system-ui, -apple-system, sans-serif;
  color: #1a1a1a;
  background: #f5f5f2;
}
* { box-sizing: border-box; }
body { margin: 0; }
a { color: #0a5c36; text-decoration: none; }
a:hover { text-decoration: underline; }
.container { max-width: 1000px; margin: 0 auto; padding: 1rem; }
.cabecalho { background: #0a5c36; color: #fff; padding: 0.8rem 0; }
.cabecalho .container { display: flex; gap: 1.5rem; align-items: center; padding-top: 0; padding-bottom: 0; }
.cabecalho a { color: #fff; font-weight: 600; }
.cartao { background: #fff; border-radius: 8px; padding: 1rem; margin: 0.8rem 0; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.busca-input { width: 100%; padding: 0.7rem 1rem; font-size: 1.1rem; border: 1px solid #ccc; border-radius: 8px; }
.resultado { display: flex; align-items: center; gap: 1rem; }
.resultado img { width: 48px; height: 60px; object-fit: cover; border-radius: 4px; background: #ddd; }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid #eee; }
td.valor, th.valor { text-align: right; white-space: nowrap; }
.filtros { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 0.8rem; }
.filtros select, .filtros input { padding: 0.4rem; border: 1px solid #ccc; border-radius: 6px; }
.paginacao { display: flex; gap: 0.6rem; align-items: center; margin-top: 0.8rem; }
button { padding: 0.4rem 0.9rem; border: 1px solid #0a5c36; background: #fff; color: #0a5c36; border-radius: 6px; cursor: pointer; }
button:disabled { opacity: 0.4; cursor: default; }
.total-destaque { font-size: 1.6rem; font-weight: 700; color: #0a5c36; }
.graficos { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 800px) { .graficos { grid-template-columns: 1fr; } }
```

Substituir `frontend/src/App.tsx`:
```tsx
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Busca from './paginas/Busca'
import Perfil from './paginas/Perfil'
import Rankings from './paginas/Rankings'

export default function App() {
  return (
    <BrowserRouter>
      <header className="cabecalho">
        <div className="container">
          <Link to="/">📡 Radar Políticos</Link>
          <Link to="/rankings">Rankings</Link>
        </div>
      </header>
      <main className="container">
        <Routes>
          <Route path="/" element={<Busca />} />
          <Route path="/politico/:id" element={<Perfil />} />
          <Route path="/rankings" element={<Rankings />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
```
Apagar `frontend/src/App.css` e remover seu import se existir. Nesta task, criar `Perfil.tsx` e `Rankings.tsx` como placeholders (substituídos nas Tasks 9–10):
```tsx
export default function Perfil() { return <p>Em construção</p> }
```
```tsx
export default function Rankings() { return <p>Em construção</p> }
```

`frontend/src/paginas/Busca.tsx`:
```tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { buscarPoliticos, type Politico } from '../lib/api'

export default function Busca() {
  const [busca, setBusca] = useState('')
  const [resultados, setResultados] = useState<Politico[]>([])
  const [erro, setErro] = useState('')

  useEffect(() => {
    if (busca.trim().length < 3) { setResultados([]); return }
    const timer = setTimeout(() => {
      buscarPoliticos(busca).then(setResultados).catch((e) => setErro(e.message))
    }, 300)
    return () => clearTimeout(timer)
  }, [busca])

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
      {resultados.map((p) => (
        <Link key={p.id} to={`/politico/${p.id}`}>
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
      {busca.trim().length >= 3 && resultados.length === 0 && !erro && (
        <p>Nenhum político encontrado.</p>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Verificar build e fumaça manual**

Run: `cd frontend && npm run build`
Expected: build OK sem erros de TypeScript.

Fumaça (com o banco de teste da Task 5 ou o real): terminal 1 `cd backend && uv run uvicorn --factory "radar.api.app:criar_app" ...` — como `criar_app` recebe argumento, criar atalho: adicionar em `backend/radar/api/app.py` ao final:
```python
def app_padrao() -> FastAPI:
    return criar_app("../dados/radar.duckdb")
```
Rodar: `cd backend && uv run uvicorn radar.api.app:app_padrao --factory --port 8000`; terminal 2 `cd frontend && npm run dev`. Abrir http://localhost:5173, buscar um nome e ver resultados.

- [ ] **Step 6: Commit**

```bash
git add frontend backend
git commit -m "feat: frontend com busca de políticos"
```

---

### Task 9: Frontend — página de perfil do político

**Files:**
- Create (substituir placeholder): `frontend/src/paginas/Perfil.tsx`

**Interfaces:**
- Consumes: `obterResumo`, `obterDespesas`, `formatarBRL`, `formatarData`.

- [ ] **Step 1: Implementar**

`frontend/src/paginas/Perfil.tsx`:
```tsx
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  Bar, BarChart, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { obterDespesas, obterResumo, type PaginaDespesas, type Resumo } from '../lib/api'
import { formatarBRL, formatarData } from '../lib/formato'

const CORES = ['#0a5c36', '#1d7a4d', '#3e9e6b', '#6ec293', '#a3ddbd', '#c9a227',
  '#d97706', '#b91c1c', '#6d28d9', '#0369a1', '#475569', '#94a3b8']

export default function Perfil() {
  const { id } = useParams<{ id: string }>()
  const [resumo, setResumo] = useState<Resumo | null>(null)
  const [despesas, setDespesas] = useState<PaginaDespesas | null>(null)
  const [ano, setAno] = useState<number | undefined>()
  const [categoria, setCategoria] = useState('')
  const [pagina, setPagina] = useState(1)
  const [erro, setErro] = useState('')

  useEffect(() => {
    if (id) obterResumo(id).then(setResumo).catch((e) => setErro(e.message))
  }, [id])

  useEffect(() => {
    if (id)
      obterDespesas(id, { ano, categoria: categoria || undefined, pagina, ordenar: '-data' })
        .then(setDespesas)
        .catch((e) => setErro(e.message))
  }, [id, ano, categoria, pagina])

  if (erro) return <p className="cartao">⚠️ {erro}</p>
  if (!resumo) return <p>Carregando...</p>

  const { politico } = resumo
  const totalPaginas = despesas ? Math.ceil(despesas.total_itens / despesas.por_pagina) : 1

  return (
    <div>
      <div className="cartao resultado">
        {politico.foto_url && <img src={politico.foto_url} alt="" style={{ width: 72, height: 90 }} />}
        <div>
          <h1 style={{ margin: 0 }}>{politico.nome}</h1>
          <div>
            {politico.cargo}
            {politico.partido ? ` · ${politico.partido}` : ''}
            {politico.uf ? ` · ${politico.uf}` : ''}
          </div>
          <div className="total-destaque">{formatarBRL(resumo.total)}</div>
          <small>total no período disponível (estornos já descontados)</small>
        </div>
      </div>

      <div className="graficos">
        <div className="cartao">
          <h3>Gasto por ano</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={resumo.por_ano}>
              <XAxis dataKey="ano" />
              <YAxis tickFormatter={(v) => `${Math.round(v / 1000)}k`} width={50} />
              <Tooltip formatter={(v) => formatarBRL(Number(v))} />
              <Bar dataKey="total" fill="#0a5c36" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="cartao">
          <h3>Por categoria (o porquê)</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={resumo.por_categoria.filter((c) => c.total > 0)}
                dataKey="total"
                nameKey="categoria"
                innerRadius={50}
                outerRadius={90}
              >
                {resumo.por_categoria.map((c, i) => (
                  <Cell key={c.categoria} fill={CORES[i % CORES.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => formatarBRL(Number(v))} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="cartao">
        <h3>Top fornecedores (para quem foi o dinheiro)</h3>
        <table>
          <thead>
            <tr><th>Fornecedor</th><th>CNPJ/CPF</th><th>Notas</th><th className="valor">Total</th></tr>
          </thead>
          <tbody>
            {resumo.top_fornecedores.map((f) => (
              <tr key={f.fornecedor + f.cnpj}>
                <td>{f.fornecedor}</td>
                <td>{f.cnpj || '—'}</td>
                <td>{f.quantidade}</td>
                <td className="valor">{formatarBRL(f.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="cartao">
        <h3>Despesas</h3>
        <div className="filtros">
          <select value={ano ?? ''} onChange={(e) => { setPagina(1); setAno(e.target.value ? Number(e.target.value) : undefined) }}>
            <option value="">Todos os anos</option>
            {resumo.por_ano.map((a) => <option key={a.ano} value={a.ano}>{a.ano}</option>)}
          </select>
          <select value={categoria} onChange={(e) => { setPagina(1); setCategoria(e.target.value) }}>
            <option value="">Todas as categorias</option>
            {resumo.por_categoria.map((c) => (
              <option key={c.categoria} value={c.categoria}>{c.categoria}</option>
            ))}
          </select>
        </div>
        <table>
          <thead>
            <tr>
              <th>Data</th><th>Categoria</th><th>Fornecedor</th><th>Detalhe</th>
              <th className="valor">Valor</th><th>Nota</th>
            </tr>
          </thead>
          <tbody>
            {despesas?.itens.map((d, i) => (
              <tr key={i}>
                <td>{d.data ? formatarData(d.data) : `${d.mes ?? '—'}/${d.ano}`}</td>
                <td title={d.categoria_original}>{d.categoria}</td>
                <td>{d.fornecedor ?? '—'}</td>
                <td>{d.descricao ?? '—'}</td>
                <td className="valor">{formatarBRL(d.valor)}</td>
                <td>
                  {d.documento_url
                    ? <a href={d.documento_url} target="_blank" rel="noreferrer">📄</a>
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="paginacao">
          <button disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>← Anterior</button>
          <span>Página {pagina} de {totalPaginas} ({despesas?.total_itens ?? 0} despesas)</span>
          <button disabled={pagina >= totalPaginas} onClick={() => setPagina(pagina + 1)}>Próxima →</button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verificar build e fumaça manual**

Run: `cd frontend && npm run build`
Expected: OK. Com API + dev server rodando, abrir um político pela busca e conferir: total, gráfico por ano, rosca de categorias, fornecedores, tabela com filtros/paginação e link 📄 abrindo o PDF.

- [ ] **Step 3: Commit**

```bash
git add frontend
git commit -m "feat: página de perfil com gráficos e tabela de despesas"
```

---

### Task 10: Frontend — página de rankings

**Files:**
- Create (substituir placeholder): `frontend/src/paginas/Rankings.tsx`

**Interfaces:**
- Consumes: `obterRankings`, `formatarBRL`.

- [ ] **Step 1: Implementar**

`frontend/src/paginas/Rankings.tsx`:
```tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { obterRankings, type ItemRanking } from '../lib/api'
import { formatarBRL } from '../lib/formato'

const ANOS = Array.from({ length: 11 }, (_, i) => 2016 + i)

export default function Rankings() {
  const [ano, setAno] = useState<number | undefined>(2026)
  const [cargo, setCargo] = useState('')
  const [itens, setItens] = useState<ItemRanking[]>([])
  const [erro, setErro] = useState('')

  useEffect(() => {
    obterRankings({ ano, cargo: cargo || undefined })
      .then(setItens)
      .catch((e) => setErro(e.message))
  }, [ano, cargo])

  return (
    <div>
      <h1>Rankings — quem mais gastou</h1>
      <div className="filtros">
        <select value={ano ?? ''} onChange={(e) => setAno(e.target.value ? Number(e.target.value) : undefined)}>
          <option value="">Todos os anos</option>
          {ANOS.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <select value={cargo} onChange={(e) => setCargo(e.target.value)}>
          <option value="">Todos os cargos</option>
          <option value="Deputado Federal">Deputados Federais</option>
          <option value="Senador">Senadores</option>
        </select>
      </div>
      {erro && <p className="cartao">⚠️ {erro}</p>}
      <div className="cartao">
        <table>
          <thead>
            <tr><th>#</th><th>Político</th><th>Cargo</th><th>Partido/UF</th><th className="valor">Total</th></tr>
          </thead>
          <tbody>
            {itens.map((item, i) => (
              <tr key={item.politico.id}>
                <td>{i + 1}º</td>
                <td><Link to={`/politico/${item.politico.id}`}>{item.politico.nome}</Link></td>
                <td>{item.politico.cargo}</td>
                <td>{[item.politico.partido, item.politico.uf].filter(Boolean).join('/') || '—'}</td>
                <td className="valor">{formatarBRL(item.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verificar build e fumaça manual**

Run: `cd frontend && npm run build`
Expected: OK. No navegador, /rankings lista políticos ordenados; clicar num nome abre o perfil.

- [ ] **Step 3: Commit**

```bash
git add frontend
git commit -m "feat: página de rankings de gastos"
```

---

### Task 11: Ingestão completa 2016–2026

**Files:**
- Nenhum código novo; execução da CLI.

- [ ] **Step 1: Rodar ingestão completa**

Run: `cd backend && uv run python -m radar.ingest --anos 2016-2026 --db ../dados/radar.duckdb --pasta ../dados`
Expected: 22 cargas (2 fontes × 11 anos) com ✔; alguma falha pontual de rede pode ser re-rodada (idempotente). Total esperado: ~2 milhões de despesas da Câmara + ~250 mil do Senado. Duração: minutos (download é o gargalo).

- [ ] **Step 2: Sanidade dos dados**

```bash
cd backend && uv run python -c "
from radar.db import conectar
con = conectar('../dados/radar.duckdb', somente_leitura=True)
print(con.execute('SELECT fonte, count(*), round(sum(valor)/1e6, 1) FROM despesas GROUP BY fonte').fetchall())
print(con.execute('SELECT ano, count(*) FROM despesas GROUP BY ano ORDER BY ano').fetchall())
print(con.execute('SELECT count(*) FROM politicos').fetchall())
print(con.execute('SELECT categoria, count(*) FROM despesas GROUP BY categoria ORDER BY 2 DESC LIMIT 25').fetchall())
"
```
Expected: todos os anos 2016–2026 presentes; políticos > 1000; categorias normalizadas coerentes (sem explosão de categorias-fallback — se houver muitas, ajustar `_REGRAS_CATEGORIA` e re-rodar só a normalização via nova ingestão).

- [ ] **Step 3: Commit (se houve ajuste de regras)**

```bash
git add backend && git commit -m "chore: ingestão completa 2016-2026 e ajustes de categorias" || echo "nada a commitar"
```

---

### Task 12: Validação com políticos reais

**Files:**
- Create: `docs/superpowers/validacao-2026-07-10.md` (relatório)

Executar com API e frontend rodando e o banco completo da Task 11.

- [ ] **Step 1: Escolher 4 políticos variados**

1 deputado de alto gasto (ex.: 1º do ranking 2025), 1 deputado de baixo gasto, 1 senador (ex.: Alan Rick), 1 político reeleito com histórico longo (com dados desde 2016).

- [ ] **Step 2: Comparar com as fontes oficiais**

Para cada um:
- Deputados: comparar o total anual do sistema com a API oficial `https://dadosabertos.camara.leg.br/api/v2/deputados/{ideCadastro}/despesas?ano=YYYY` (somar `valorLiquido` de todas as páginas) ou com a página `https://www.camara.leg.br/deputados/{ideCadastro}` (seção "Gastos"). Tolerância: diferença < 1% (o portal consolida glosas com pequeno atraso).
- Senadores: comparar com o CSV oficial re-somado de forma independente (`awk`/pandas direto no arquivo baixado) e, por amostragem, com a página de transparência do senador no site do Senado.
- Conferir também: gráfico por ano bate com os totais; categorias somam o total; link de nota fiscal abre PDF válido (amostrar 2–3 notas).

- [ ] **Step 3: Registrar relatório**

Criar `docs/superpowers/validacao-2026-07-10.md` com tabela: político, ano, total no sistema, total oficial, diferença %, veredicto. Qualquer divergência > 1% vira investigação (categoria de valor: glosa? estorno? linha de liderança?) antes de dar por concluído.

- [ ] **Step 4: Commit final**

```bash
git add docs && git commit -m "docs: relatório de validação com políticos reais"
```

---

## Self-Review (feito na escrita do plano)

- **Cobertura do spec:** modelo único ✔ (Tasks 2–4), ingestão idempotente + relatório ✔ (Task 5), 4 endpoints ✔ (Tasks 6–7), 3 telas ✔ (Tasks 8–10), estornos ✔ (testes nas Tasks 3 e 6), categorias normalizadas ✔ (Task 2), validação com políticos reais ✔ (Task 12).
- **Placeholders:** nenhum; todo step tem código ou comando completo.
- **Consistência de tipos:** contrato de fonte (`FONTE`, `baixar`, `parse`) idêntico nas Tasks 3, 4 e 5; colunas de `despesas` idênticas no DDL (Task 1), nos dicts das fontes (Tasks 3–4), no loader (Task 5) e na API (Tasks 6–7); tipos de `api.ts` espelham as respostas JSON das Tasks 6–7.
