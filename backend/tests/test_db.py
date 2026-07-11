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
