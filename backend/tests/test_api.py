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
