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
