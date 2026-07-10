import pytest
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


def test_carregar_falha_no_meio_nao_deixa_dados_parciais(tmp_path):
    con = conectar(tmp_path / "t.duckdb")
    criar_schema(con)
    loader.carregar(con, FonteFake, 2025, tmp_path)  # carga boa inicial

    class FonteQuebrada:
        FONTE = "camara"

        @staticmethod
        def baixar(ano, pasta):
            return FIXTURE

        @staticmethod
        def parse(caminho):
            yield from camara.parse(caminho)
            raise RuntimeError("falha no meio do parse")

    with pytest.raises(RuntimeError):
        loader.carregar(con, FonteQuebrada, 2025, tmp_path)
    # rollback: os dados da carga boa continuam intactos
    assert con.execute("SELECT count(*) FROM despesas").fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM politicos").fetchone()[0] == 1
