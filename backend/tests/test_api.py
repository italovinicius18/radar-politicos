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
    assert k["deputados"] == 2 and k["senadores"] == 1 and k["parlamentares"] == 3
    assert round(k["media_por_parlamentar"], 2) == round(8300 / 3, 2)
    assert k["nota_mais_cara"]["valor"] == 5000.00
    assert k["nota_mais_cara"]["politico"]["id"] == "camara-2"
    assert corpo["por_mes"] == [
        {"mes": 1, "total": 3000.00},
        {"mes": 2, "total": 300.00},
        {"mes": 3, "total": 5000.00},
    ]
    assert {"fonte": "camara", "total": 6300.00, "parlamentares": 2} in corpo["camara_senado"]
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
