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
    d = consultas.despesas_compactas(con, "camara-1")
    assert d["colunas"] == [
        "ano", "data", "categoria", "categoria_original", "descricao",
        "fornecedor", "cnpj", "valor", "doc",
    ]
    # camara-1 tem 3 despesas no total (2x2024 + 1x2025)
    assert len(d["linhas"]) == 3
    # ordenado por ano desc: 2025 primeiro
    assert d["linhas"][0][0] == 2025
    # dentro de 2024: fev antes de jan
    assert d["linhas"][1][0] == 2024 and d["linhas"][1][1] == "2024-02-05"
    assert d["linhas"][1][7] == 300.0
    assert d["linhas"][2][0] == 2024 and d["linhas"][2][1] == "2024-01-10"
    assert d["linhas"][2][5] == "TAM" and d["linhas"][2][8] == "http://doc/1.pdf"
