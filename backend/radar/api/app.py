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
        limite: int = Query(20, ge=1, le=100),
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

    ORDENACOES = {
        "data": "data ASC NULLS LAST",
        "-data": "data DESC NULLS LAST",
        "valor": "valor ASC",
        "-valor": "valor DESC",
    }
    COLUNAS_DESPESA = (
        "ano", "mes", "data", "categoria", "categoria_original", "descricao",
        "fornecedor", "fornecedor_cnpj", "valor", "documento_url", "fonte",
    )

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
        if ordenar not in ORDENACOES:
            raise HTTPException(422, f"ordenar deve ser um de: {sorted(ORDENACOES)}")
        filtro = "politico_id = ?"
        parametros: list = [politico_id]
        if ano is not None:
            filtro += " AND ano = ?"
            parametros.append(ano)
        if categoria:
            filtro += " AND categoria = ?"
            parametros.append(categoria)
        if fornecedor:
            filtro += " AND strip_accents(lower(fornecedor)) LIKE '%' || strip_accents(lower(?)) || '%'"
            parametros.append(fornecedor)
        with con() as c:
            _buscar_politico(c, politico_id)
            total_itens = c.execute(
                f"SELECT count(*) FROM despesas WHERE {filtro}", parametros
            ).fetchone()[0]
            linhas = c.execute(
                f"""SELECT {', '.join(COLUNAS_DESPESA)} FROM despesas WHERE {filtro}
                    ORDER BY {ORDENACOES[ordenar]} LIMIT ? OFFSET ?""",
                parametros + [por_pagina, (pagina - 1) * por_pagina],
            ).fetchall()
        return {
            "total_itens": total_itens,
            "pagina": pagina,
            "por_pagina": por_pagina,
            "itens": [
                {
                    **dict(zip(COLUNAS_DESPESA, l)),
                    "data": l[2].isoformat() if l[2] else None,
                    "valor": float(l[8]),
                }
                for l in linhas
            ],
        }

    @app.get("/api/rankings")
    def rankings(
        ano: int | None = None,
        cargo: str | None = None,
        categoria: str | None = None,
        limite: int = Query(20, ge=1, le=100),
    ):
        filtro = "1=1"
        parametros: list = []
        if ano is not None:
            filtro += " AND d.ano = ?"
            parametros.append(ano)
        if cargo:
            filtro += " AND p.cargo = ?"
            parametros.append(cargo)
        if categoria:
            filtro += " AND d.categoria = ?"
            parametros.append(categoria)
        with con() as c:
            linhas = c.execute(
                f"""SELECT {', '.join('p.' + col for col in COLUNAS_POLITICO)},
                           sum(d.valor) AS total
                    FROM despesas d JOIN politicos p ON p.id = d.politico_id
                    WHERE {filtro}
                    GROUP BY {', '.join('p.' + col for col in COLUNAS_POLITICO)}
                    ORDER BY total DESC LIMIT ?""",
                parametros + [limite],
            ).fetchall()
        return [
            {"politico": _politico_dict(l[:-1]), "total": float(l[-1])} for l in linhas
        ]

    return app


def app_padrao() -> FastAPI:
    return criar_app("../dados/radar.duckdb")
