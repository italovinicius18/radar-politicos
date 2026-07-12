from pathlib import Path

from radar.ingest.fontes import cldf

FIXTURES = Path(__file__).parent / "fixtures"


def _pares(nome):
    return list(cldf.parse(FIXTURES / nome))


def test_transacional_gera_pares_e_politico():
    pares = _pares("cldf_transacional.xlsx")
    assert len(pares) == 6
    politico, despesa = pares[0]
    assert politico == {
        "id": "cldf-chico-vigilante",
        "nome": "Chico Vigilante",  # prefixo "Deputado " removido
        "cargo": "Deputado Distrital",
        "partido": None,
        "uf": "DF",
        "foto_url": None,
        "fonte": "cldf",
    }
    assert despesa["ano"] == 2016 and despesa["mes"] == 3
    assert despesa["data"].isoformat() == "2016-03-05"
    assert despesa["categoria"] == "Manutenção de escritório"
    assert despesa["fornecedor"] == "PAPELARIA ALFA LTDA"
    assert despesa["fornecedor_cnpj"] == "01.111.111/0001-11"
    assert despesa["valor"] == 250.0


def test_transacional_classificacao_vazia_e_cpf_prestador():
    _, despesa = _pares("cldf_transacional.xlsx")[1]
    assert despesa["categoria"] == "Não especificada"
    assert despesa["fornecedor_cnpj"] == "222.333.444-55"
    assert despesa["descricao"] == "abastecimento"


def test_pivo_emite_categorias_residuo_e_glosa():
    pares = _pares("cldf_pivo.xlsx")
    # linha 1: Imóvel 1000 + Veículos 500 + resíduo 300 = 1800
    # linha 2: Imóvel 2000 + glosa -100 (resíduo 0, não emitido) = 1900
    assert len(pares) == 5
    chico = [d for p, d in pares if p["id"] == "cldf-chico-vigilante"]
    assert round(sum(d["valor"] for d in chico), 2) == 1800.00
    residuo = [d for d in chico if d["categoria"] == cldf.CATEGORIA_RESIDUAL]
    assert len(residuo) == 1 and residuo[0]["valor"] == 300.0
    jane = [d for p, d in pares if p["id"] == "cldf-jane-klebia"]
    assert round(sum(d["valor"] for d in jane), 2) == 1900.00
    glosa = [d for d in jane if d["categoria"] == "Glosas e estornos"]
    assert len(glosa) == 1 and glosa[0]["valor"] == -100.0


def test_pivo_mes_e_campos_nulos():
    _, despesa = _pares("cldf_pivo.xlsx")[0]
    assert despesa["ano"] == 2025 and despesa["mes"] == 4  # "abr"
    assert despesa["data"] is None
    assert despesa["fornecedor"] is None and despesa["documento_url"] is None


def test_mesmo_nome_gera_mesmo_id_nos_dois_formatos():
    ids_t = {p["id"] for p, _ in _pares("cldf_transacional.xlsx")}
    ids_p = {p["id"] for p, _ in _pares("cldf_pivo.xlsx")}
    assert ids_t == ids_p == {"cldf-chico-vigilante", "cldf-jane-klebia"}


def test_pivo_normaliza_nome_maiusculo():
    nomes = {p["nome"] for p, _ in _pares("cldf_pivo.xlsx")}
    assert nomes == {"Chico Vigilante", "Jane Klebia"}


def test_transacional_linha_sem_data_e_ignorada():
    pares = _pares("cldf_transacional.xlsx")
    assert len(pares) == 6  # a 4ª linha (sem DATA_COMPROVANTE) é descartada, 3 linhas novas válidas são adicionadas
    assert all(d["fornecedor"] != "FORNECEDOR SEM DATA" for _, d in pares)


def test_transacional_valores_e_datas_string():
    pares = _pares("cldf_transacional.xlsx")
    valores = {d["valor"] for _, d in pares}
    assert 5000.0 in valores      # "R$ 5.000,00"
    assert 9900.0 in valores      # "9,900,00"
    assert 700.0 in valores       # data string "15/05/2016"


def test_transacional_ordem_de_colunas_2013():
    pares = _pares("cldf_transacional_2013.xlsx")
    assert len(pares) == 1
    _, d = pares[0]
    assert d["data"] is not None and d["valor"] > 0
