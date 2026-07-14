import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from radar.fontes_registro import rotulo

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

    @app.get("/api/visao-geral")
    def visao_geral(ano: int | None = None):
        with con() as c:
            if ano is None:
                ano = c.execute("SELECT coalesce(max(ano), 0) FROM despesas").fetchone()[0]
            total, num_despesas, meses = c.execute(
                "SELECT coalesce(sum(valor), 0), count(*), coalesce(max(mes), 0) "
                "FROM despesas WHERE ano = ?",
                (ano,),
            ).fetchone()
            anterior = c.execute(
                "SELECT coalesce(sum(valor), 0) FROM despesas WHERE ano = ? AND mes <= ?",
                (ano - 1, meses),
            ).fetchone()[0]
            cargos = dict(
                c.execute(
                    """SELECT p.cargo, count(DISTINCT d.politico_id)
                       FROM despesas d JOIN politicos p ON p.id = d.politico_id
                       WHERE d.ano = ? GROUP BY p.cargo""",
                    (ano,),
                ).fetchall()
            )
            por_cargo = [
                {"cargo": cargo, "quantidade": qtd}
                for cargo, qtd in sorted(cargos.items())
            ]
            parlamentares = sum(cargos.values())
            nota = c.execute(
                f"""SELECT d.valor, d.categoria, d.fornecedor, d.data,
                           {', '.join('p.' + col for col in COLUNAS_POLITICO)}
                    FROM despesas d JOIN politicos p ON p.id = d.politico_id
                    WHERE d.ano = ? ORDER BY d.valor DESC LIMIT 1""",
                (ano,),
            ).fetchone()
            por_mes = c.execute(
                "SELECT mes, sum(valor) FROM despesas WHERE ano = ? AND mes IS NOT NULL "
                "GROUP BY mes ORDER BY mes",
                (ano,),
            ).fetchall()
            gastadores = c.execute(
                f"""SELECT {', '.join('p.' + col for col in COLUNAS_POLITICO)},
                           sum(d.valor) AS total
                    FROM despesas d JOIN politicos p ON p.id = d.politico_id
                    WHERE d.ano = ?
                    GROUP BY {', '.join('p.' + col for col in COLUNAS_POLITICO)}
                    ORDER BY total DESC LIMIT 5""",
                (ano,),
            ).fetchall()
            categorias = c.execute(
                "SELECT categoria, sum(valor) AS t FROM despesas WHERE ano = ? "
                "GROUP BY categoria ORDER BY t DESC LIMIT 5",
                (ano,),
            ).fetchall()
            fornecedores = c.execute(
                """SELECT fornecedor, coalesce(fornecedor_cnpj, '') AS cnpj,
                          sum(valor) AS t, count(*) AS q
                   FROM despesas WHERE ano = ? AND fornecedor IS NOT NULL
                   GROUP BY fornecedor, cnpj ORDER BY t DESC LIMIT 5""",
                (ano,),
            ).fetchall()

            SQL_TOTAIS = """
                SELECT p.id, p.partido, p.uf, p.fonte, sum(d.valor) AS total
                FROM despesas d JOIN politicos p ON p.id = d.politico_id
                WHERE d.ano = ? GROUP BY p.id, p.partido, p.uf, p.fonte
            """
            por_partido = c.execute(
                f"""WITH totais AS ({SQL_TOTAIS})
                    SELECT coalesce(partido, 'Sem partido informado') AS pt,
                           count(*), avg(total), median(total)
                    FROM totais GROUP BY pt ORDER BY 3 DESC""",
                (ano,),
            ).fetchall()
            media_por_uf = c.execute(
                f"""WITH totais AS ({SQL_TOTAIS})
                    SELECT coalesce(uf, 'Não informado') AS u, count(*), avg(total)
                    FROM totais GROUP BY u ORDER BY 3 DESC""",
                (ano,),
            ).fetchall()
            por_casa_linhas = c.execute(
                f"""WITH totais AS ({SQL_TOTAIS})
                    SELECT fonte, sum(total), count(*), avg(total), median(total)
                    FROM totais GROUP BY fonte ORDER BY fonte""",
                (ano,),
            ).fetchall()

            ano_ref = c.execute(
                "SELECT max(ano) FROM despesas WHERE mes = 12 AND ano <= ?", (ano,)
            ).fetchone()[0]
            fim_de_ano = None
            if ano_ref is not None:
                meses_ref = c.execute(
                    "SELECT mes, sum(valor) FROM despesas WHERE ano = ? AND mes IS NOT NULL GROUP BY mes",
                    (ano_ref,),
                ).fetchall()
                dezembro = next((float(t) for m, t in meses_ref if m == 12), 0.0)
                media_mensal = sum(float(t) for _, t in meses_ref) / len(meses_ref)
                if media_mensal:
                    fim_de_ano = {
                        "ano_ref": ano_ref,
                        "dezembro": dezembro,
                        "media_mensal": media_mensal,
                        "variacao_pct": (dezembro - media_mensal) / media_mensal * 100,
                    }

            linhas_doc = c.execute(
                "SELECT fonte, count(*), count(documento_url) FROM despesas "
                "WHERE ano = ? GROUP BY fonte ORDER BY fonte",
                (ano,),
            ).fetchall()
            transparencia = None
            if linhas_doc:
                total_n = sum(n for _, n, _ in linhas_doc)
                total_com = sum(cd for _, _, cd in linhas_doc)
                transparencia = {
                    "pct_com_documento": total_com * 100.0 / total_n,
                    "por_fonte": [
                        {"fonte": f, "rotulo": rotulo(f), "pct": cd * 100.0 / n}
                        for f, n, cd in linhas_doc
                    ],
                }

            top10, total_ano = c.execute(
                """WITH forn AS (
                       SELECT sum(valor) AS t FROM despesas
                       WHERE ano = ? AND fornecedor IS NOT NULL
                       GROUP BY fornecedor, coalesce(fornecedor_cnpj, '')
                       ORDER BY t DESC LIMIT 10)
                   SELECT (SELECT sum(t) FROM forn),
                          (SELECT sum(valor) FROM despesas WHERE ano = ?)""",
                (ano, ano),
            ).fetchone()
            concentracao_pct = (
                float(top10) * 100.0 / float(total_ano)
                if top10 is not None and total_ano is not None and float(total_ano) > 0
                else None
            )

            exclusivos = c.execute(
                """WITH por_parl AS (
                       SELECT fornecedor, coalesce(fornecedor_cnpj, '') AS cnpj,
                              politico_id, sum(valor) AS v
                       FROM despesas WHERE ano = ? AND fornecedor IS NOT NULL
                       GROUP BY 1, 2, 3),
                   agg AS (
                       SELECT fornecedor, cnpj, sum(v) AS total, max(v) AS maior_v,
                              arg_max(politico_id, v) AS pid
                       FROM por_parl GROUP BY 1, 2)
                   SELECT a.fornecedor, a.cnpj, a.total,
                          a.maior_v * 100.0 / a.total, p.id, p.nome
                   FROM agg a JOIN politicos p ON p.id = a.pid
                   WHERE a.total >= 50000 AND a.maior_v >= a.total * 0.9
                   ORDER BY a.total DESC""",
                (ano,),
            ).fetchall()
        total = float(total)
        anterior = float(anterior)
        return {
            "ano": ano,
            "kpis": {
                "total": total,
                "total_mesmo_periodo_anterior": anterior,
                "variacao_pct": ((total - anterior) / anterior * 100) if anterior else None,
                "meses_com_dados": meses,
                "parlamentares": parlamentares,
                "por_cargo": por_cargo,
                "media_por_parlamentar": total / parlamentares if parlamentares else 0.0,
                "num_despesas": num_despesas,
                "nota_mais_cara": {
                    "valor": float(nota[0]),
                    "categoria": nota[1],
                    "fornecedor": nota[2],
                    "data": nota[3].isoformat() if nota[3] else None,
                    "politico": _politico_dict(nota[4:]),
                }
                if nota
                else None,
            },
            "por_mes": [{"mes": m, "total": float(t)} for m, t in por_mes],
            "por_casa": [
                {"fonte": f, "rotulo": rotulo(f), "total": float(t), "parlamentares": q,
                 "media": float(m), "mediana": float(md)}
                for f, t, q, m, md in por_casa_linhas
            ],
            "por_partido": [
                {"partido": pt, "parlamentares": q, "media": float(m), "mediana": float(md)}
                for pt, q, m, md in por_partido
            ],
            "media_por_uf": [
                {"uf": u, "parlamentares": q, "media": float(m)}
                for u, q, m in media_por_uf
            ],
            "estatisticas": {
                "fim_de_ano": fim_de_ano,
                "transparencia": transparencia,
                "concentracao_top10_pct": concentracao_pct,
                "quase_exclusivos": {
                    "quantidade": len(exclusivos),
                    "maior": {
                        "fornecedor": exclusivos[0][0],
                        "cnpj": exclusivos[0][1],
                        "total": float(exclusivos[0][2]),
                        "pct_um_parlamentar": float(exclusivos[0][3]),
                        "politico": {"id": exclusivos[0][4], "nome": exclusivos[0][5]},
                    }
                    if exclusivos
                    else None,
                },
            },
            "top_gastadores": [
                {"politico": _politico_dict(l[:-1]), "total": float(l[-1])}
                for l in gastadores
            ],
            "top_categorias": [{"categoria": cat, "total": float(t)} for cat, t in categorias],
            "top_fornecedores": [
                {"fornecedor": f, "cnpj": cnpj, "total": float(t), "quantidade": q}
                for f, cnpj, t, q in fornecedores
            ],
        }

    return app


def app_padrao() -> FastAPI:
    return criar_app("../dados/radar.duckdb")
