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
