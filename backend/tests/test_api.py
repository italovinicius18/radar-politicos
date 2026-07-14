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


def test_por_pagina_negativo_422(cliente):
    r = cliente.get("/api/politicos/camara-1/despesas", params={"por_pagina": -5})
    assert r.status_code == 422


def test_rankings_limite_negativo_422(cliente):
    assert cliente.get("/api/rankings", params={"limite": -1}).status_code == 422


def test_visao_geral_2024(cliente):
    corpo = cliente.get("/api/visao-geral", params={"ano": 2024}).json()
    assert corpo["ano"] == 2024
    k = corpo["kpis"]
    assert k["total"] == 8300.00
    assert k["num_despesas"] == 4
    assert k["meses_com_dados"] == 3
    assert k["parlamentares"] == 3
    assert {"cargo": "Deputado Federal", "quantidade": 2} in k["por_cargo"]
    assert {"cargo": "Senador", "quantidade": 1} in k["por_cargo"]
    assert round(k["media_por_parlamentar"], 2) == round(8300 / 3, 2)
    assert k["nota_mais_cara"]["valor"] == 5000.00
    assert k["nota_mais_cara"]["politico"]["id"] == "camara-2"
    assert corpo["por_mes"] == [
        {"mes": 1, "total": 3000.00},
        {"mes": 2, "total": 300.00},
        {"mes": 3, "total": 5000.00},
    ]
    casa_camara = next(x for x in corpo["por_casa"] if x["fonte"] == "camara")
    assert casa_camara["rotulo"] == "Câmara" and casa_camara["total"] == 6300.00 and casa_camara["parlamentares"] == 2
    assert corpo["top_gastadores"][0]["politico"]["id"] == "camara-2"
    assert corpo["top_categorias"][0] == {"categoria": "Divulgação", "total": 5000.00}
    assert corpo["top_fornecedores"][0]["fornecedor"] == "GRÁFICA Y"


def test_visao_geral_variacao_mesmo_periodo(cliente):
    # 2025 tem dados só até mes=1; período anterior = 2024 até mes=1 (3000)
    k = cliente.get("/api/visao-geral", params={"ano": 2025}).json()["kpis"]
    assert k["total"] == -200.00
    assert k["meses_com_dados"] == 1
    assert k["total_mesmo_periodo_anterior"] == 3000.00
    assert round(k["variacao_pct"], 2) == round((-200 - 3000) / 3000 * 100, 2)


def test_visao_geral_ano_padrao_e_o_maximo(cliente):
    assert cliente.get("/api/visao-geral").json()["ano"] == 2025


def test_visao_geral_ano_sem_dados(cliente):
    corpo = cliente.get("/api/visao-geral", params={"ano": 1999}).json()
    assert corpo["kpis"]["total"] == 0
    assert corpo["kpis"]["nota_mais_cara"] is None
    assert corpo["kpis"]["variacao_pct"] is None
    assert corpo["por_mes"] == [] and corpo["top_gastadores"] == []


def test_visao_geral_por_partido_uf_casa(cliente):
    corpo = cliente.get("/api/visao-geral", params={"ano": 2024}).json()
    # partidos: 1 parlamentar cada -> media == mediana == total
    assert corpo["por_partido"][0] == {
        "partido": "PL", "parlamentares": 1, "media": 5000.0, "mediana": 5000.0
    }
    assert {"partido": "PT", "parlamentares": 1, "media": 1300.0, "mediana": 1300.0} in corpo["por_partido"]
    assert corpo["media_por_uf"][0] == {"uf": "MG", "parlamentares": 1, "media": 5000.0}
    casa_camara = next(x for x in corpo["por_casa"] if x["fonte"] == "camara")
    assert casa_camara["media"] == 3150.0 and casa_camara["mediana"] == 3150.0
    assert casa_camara["total"] == 6300.0 and casa_camara["parlamentares"] == 2


def test_visao_geral_estatisticas_fixture(cliente):
    e = cliente.get("/api/visao-geral", params={"ano": 2024}).json()["estatisticas"]
    # fixture não tem mês 12 em nenhum ano -> sem referência
    assert e["fim_de_ano"] is None
    # camara: 3 despesas, 2 com documento; senado: 1 sem -> geral 50%
    assert round(e["transparencia"]["pct_com_documento"], 2) == 50.0
    por_fonte = {x["fonte"]: x for x in e["transparencia"]["por_fonte"]}
    assert round(por_fonte["camara"]["pct"], 2) == 66.67
    assert por_fonte["senado"]["pct"] == 0.0
    assert por_fonte["camara"]["rotulo"] == "Câmara"
    # 4 fornecedores no ano, todos no top10 -> 100%
    assert round(e["concentracao_top10_pct"], 2) == 100.0
    # nenhum fornecedor >= 50k
    assert e["quase_exclusivos"] == {"quantidade": 0, "maior": None}


def test_visao_geral_estatisticas_ano_vazio(cliente):
    corpo = cliente.get("/api/visao-geral", params={"ano": 1999}).json()
    assert corpo["por_partido"] == [] and corpo["media_por_uf"] == []
    e = corpo["estatisticas"]
    assert e["fim_de_ano"] is None and e["transparencia"] is None
    assert e["concentracao_top10_pct"] is None
    assert e["quase_exclusivos"] == {"quantidade": 0, "maior": None}


def test_mediana_e_quase_exclusivos_banco_dedicado(tmp_path):
    from fastapi.testclient import TestClient

    from radar.api.app import criar_app
    from radar.db import conectar, criar_schema

    caminho = tmp_path / "est.duckdb"
    con = conectar(caminho)
    criar_schema(con)
    con.execute("""
        INSERT INTO politicos VALUES
        ('camara-10', 'Ana',   'Deputado Federal', 'XX', 'SP', NULL, 'camara'),
        ('camara-11', 'Bruno', 'Deputado Federal', 'XX', 'SP', NULL, 'camara'),
        ('camara-12', 'Carla', 'Deputado Federal', 'XX', 'SP', NULL, 'camara')
    """)
    # ano 2030: totais 100/200/900 -> media 400, mediana 200
    con.execute("""
        INSERT INTO despesas VALUES
        ('camara-10', 2030, 1, '2030-01-10', 'X', 'X', NULL, 'F1', '1', 100, NULL, 'camara'),
        ('camara-11', 2030, 1, '2030-01-11', 'X', 'X', NULL, 'F1', '1', 200, NULL, 'camara'),
        ('camara-12', 2030, 1, '2030-01-12', 'X', 'X', NULL, 'F1', '1', 900, NULL, 'camara')
    """)
    # ano 2031, limiares de quase-exclusivo:
    #  EXC91: 50.000 com 91% da Ana -> CONTA (maior)
    #  EXC89: 50.000 com 89% da Ana -> não conta (< 90%)
    #  PEQ:   49.000 com 100% da Ana -> não conta (< 50k)
    con.execute("""
        INSERT INTO despesas VALUES
        ('camara-10', 2031, 1, '2031-01-10', 'X', 'X', NULL, 'EXC91', '9', 45500, NULL, 'camara'),
        ('camara-11', 2031, 1, '2031-01-11', 'X', 'X', NULL, 'EXC91', '9',  4500, NULL, 'camara'),
        ('camara-10', 2031, 2, '2031-02-10', 'X', 'X', NULL, 'EXC89', '8', 44500, NULL, 'camara'),
        ('camara-11', 2031, 2, '2031-02-11', 'X', 'X', NULL, 'EXC89', '8',  5500, NULL, 'camara'),
        ('camara-10', 2031, 3, '2031-03-10', 'X', 'X', NULL, 'PEQ',   '7', 49000, NULL, 'camara')
    """)
    con.close()
    cliente = TestClient(criar_app(str(caminho)))

    corpo = cliente.get("/api/visao-geral", params={"ano": 2030}).json()
    assert corpo["por_partido"] == [
        {"partido": "XX", "parlamentares": 3, "media": 400.0, "mediana": 200.0}
    ]
    assert corpo["media_por_uf"] == [{"uf": "SP", "parlamentares": 3, "media": 400.0}]

    qe = cliente.get("/api/visao-geral", params={"ano": 2031}).json()["estatisticas"]["quase_exclusivos"]
    assert qe["quantidade"] == 1
    assert qe["maior"]["fornecedor"] == "EXC91"
    assert round(qe["maior"]["pct_um_parlamentar"], 1) == 91.0
    assert qe["maior"]["total"] == 50000.0
    assert qe["maior"]["politico"] == {"id": "camara-10", "nome": "Ana"}


def test_fim_de_ano_usa_ultimo_ano_com_dezembro(tmp_path):
    from fastapi.testclient import TestClient

    from radar.api.app import criar_app
    from radar.db import conectar, criar_schema

    caminho = tmp_path / "dez.duckdb"
    con = conectar(caminho)
    criar_schema(con)
    con.execute(
        "INSERT INTO politicos VALUES ('camara-20', 'Davi', 'Deputado Federal', 'YY', 'RJ', NULL, 'camara')"
    )
    # 2040: jan 100, fev 100, dez 400 -> media mensal 200, dez +100%
    # 2041: só jan (sem dezembro) -> deve referenciar 2040
    con.execute("""
        INSERT INTO despesas VALUES
        ('camara-20', 2040,  1, '2040-01-10', 'X', 'X', NULL, 'F', '1', 100, NULL, 'camara'),
        ('camara-20', 2040,  2, '2040-02-10', 'X', 'X', NULL, 'F', '1', 100, NULL, 'camara'),
        ('camara-20', 2040, 12, '2040-12-10', 'X', 'X', NULL, 'F', '1', 400, NULL, 'camara'),
        ('camara-20', 2041,  1, '2041-01-10', 'X', 'X', NULL, 'F', '1', 150, NULL, 'camara')
    """)
    con.close()
    cliente = TestClient(criar_app(str(caminho)))

    fe = cliente.get("/api/visao-geral", params={"ano": 2041}).json()["estatisticas"]["fim_de_ano"]
    assert fe["ano_ref"] == 2040
    assert fe["dezembro"] == 400.0 and fe["media_mensal"] == 200.0
    assert round(fe["variacao_pct"], 1) == 100.0
