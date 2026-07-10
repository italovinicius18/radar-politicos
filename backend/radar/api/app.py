import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

COLUNAS_POLITICO = ("id", "nome", "cargo", "partido", "uf", "foto_url", "fonte")


def _politico_dict(linha) -> dict:
    return dict(zip(COLUNAS_POLITICO, linha))


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
        limite: int = Query(20, le=100),
    ):
        sql = f"SELECT {', '.join(COLUNAS_POLITICO)} FROM politicos WHERE 1=1"
        parametros: list = []
        if busca:
            sql += " AND strip_accents(lower(nome)) LIKE '%' || strip_accents(lower(?)) || '%'"
            parametros.append(busca)
        for coluna, valor in (("cargo", cargo), ("partido", partido), ("uf", uf)):
            if valor:
                sql += f" AND {coluna} = ?"
                parametros.append(valor)
        sql += " ORDER BY nome LIMIT ?"
        parametros.append(limite)
        with con() as c:
            return [_politico_dict(l) for l in c.execute(sql, parametros).fetchall()]

    def _buscar_politico(c, politico_id: str) -> dict:
        linha = c.execute(
            f"SELECT {', '.join(COLUNAS_POLITICO)} FROM politicos WHERE id = ?",
            (politico_id,),
        ).fetchone()
        if not linha:
            raise HTTPException(404, "Político não encontrado")
        return _politico_dict(linha)

    @app.get("/api/politicos/{politico_id}/resumo")
    def resumo(
        politico_id: str,
        ano_inicio: int = 0,
        ano_fim: int = 9999,
    ):
        with con() as c:
            politico = _buscar_politico(c, politico_id)
            filtro = "politico_id = ? AND ano BETWEEN ? AND ?"
            parametros = (politico_id, ano_inicio, ano_fim)
            total = c.execute(
                f"SELECT coalesce(sum(valor), 0) FROM despesas WHERE {filtro}", parametros
            ).fetchone()[0]
            por_ano = c.execute(
                f"SELECT ano, sum(valor) FROM despesas WHERE {filtro} GROUP BY ano ORDER BY ano",
                parametros,
            ).fetchall()
            por_categoria = c.execute(
                f"""SELECT categoria, sum(valor) AS t FROM despesas WHERE {filtro}
                    GROUP BY categoria ORDER BY t DESC""",
                parametros,
            ).fetchall()
            fornecedores = c.execute(
                f"""SELECT fornecedor, coalesce(fornecedor_cnpj, '') AS cnpj,
                           sum(valor) AS t, count(*) AS q
                    FROM despesas WHERE {filtro} AND fornecedor IS NOT NULL
                    GROUP BY fornecedor, cnpj ORDER BY t DESC LIMIT 10""",
                parametros,
            ).fetchall()
        return {
            "politico": politico,
            "total": float(total),
            "por_ano": [{"ano": a, "total": float(t)} for a, t in por_ano],
            "por_categoria": [{"categoria": cat, "total": float(t)} for cat, t in por_categoria],
            "top_fornecedores": [
                {"fornecedor": f, "cnpj": cnpj, "total": float(t), "quantidade": q}
                for f, cnpj, t, q in fornecedores
            ],
        }

    return app
