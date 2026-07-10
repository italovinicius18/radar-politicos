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
