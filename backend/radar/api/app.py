import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from radar import consultas


def criar_app(db_path: str) -> FastAPI:
    app = FastAPI(title="Radar Políticos")
    app.add_middleware(
        CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"]
    )

    def con() -> duckdb.DuckDBPyConnection:
        return duckdb.connect(db_path, read_only=True)

    @app.get("/api/politicos")
    def buscar_politicos(
        busca: str = "",
        cargo: str | None = None,
        partido: str | None = None,
        uf: str | None = None,
        limite: int = Query(20, ge=1, le=100),
    ):
        with con() as c:
            return consultas.buscar_politicos(c, busca, cargo, partido, uf, limite)

    @app.get("/api/politicos/{politico_id}/resumo")
    def resumo(
        politico_id: str,
        ano_inicio: int = 0,
        ano_fim: int = 9999,
    ):
        with con() as c:
            corpo = consultas.resumo(c, politico_id, ano_inicio, ano_fim)
        if corpo is None:
            raise HTTPException(404, "Político não encontrado")
        return corpo

    @app.get("/api/politicos/{politico_id}/despesas")
    def despesas(
        politico_id: str,
        ano: int | None = None,
        categoria: str | None = None,
        fornecedor: str | None = None,
        ordenar: str = "-data",
        pagina: int = Query(1, ge=1),
        por_pagina: int = Query(50, ge=1, le=200),
    ):
        try:
            with con() as c:
                corpo = consultas.despesas_paginadas(
                    c, politico_id, ano, categoria, fornecedor, ordenar, pagina, por_pagina
                )
        except ValueError as e:
            raise HTTPException(422, str(e))
        if corpo is None:
            raise HTTPException(404, "Político não encontrado")
        return corpo

    @app.get("/api/rankings")
    def rankings(
        ano: int | None = None,
        cargo: str | None = None,
        categoria: str | None = None,
        limite: int = Query(20, ge=1, le=100),
    ):
        with con() as c:
            return consultas.rankings(c, ano, cargo, categoria, limite)

    @app.get("/api/visao-geral")
    def visao_geral(ano: int | None = None):
        with con() as c:
            return consultas.visao_geral(c, ano)

    return app


def app_padrao() -> FastAPI:
    return criar_app("../dados/radar.duckdb")
