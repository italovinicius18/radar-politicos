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


def test_normalizar_categoria_vazia():
    assert normalizar_categoria("") == "Não especificada"
    assert normalizar_categoria("   ") == "Não especificada"


def test_slug_e_sem_acento():
    assert slug("João da Silva") == "joao-da-silva"
    assert sem_acento("José ÁVILA") == "jose avila"


def test_normalizar_categoria_cldf():
    assert normalizar_categoria("Imóvel") == "Manutenção de escritório"
    assert normalizar_categoria("Locação de imóvel") == "Manutenção de escritório"
    assert normalizar_categoria("Maquina Equipamento") == "Manutenção de escritório"
    assert normalizar_categoria("Aquisição Materias") == "Manutenção de escritório"
    assert normalizar_categoria("Glosa") == "Glosas e estornos"
