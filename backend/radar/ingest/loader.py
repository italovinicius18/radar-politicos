from pathlib import Path

_COLUNAS_DESPESA = (
    "politico_id", "ano", "mes", "data", "categoria", "categoria_original",
    "descricao", "fornecedor", "fornecedor_cnpj", "valor", "documento_url", "fonte",
)
_SQL_DESPESA = (
    f"INSERT INTO despesas ({', '.join(_COLUNAS_DESPESA)}) "
    f"VALUES ({', '.join('?' * len(_COLUNAS_DESPESA))})"
)
_SQL_POLITICO = (
    "INSERT OR REPLACE INTO politicos (id, nome, cargo, partido, uf, foto_url, fonte) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)"
)
_TAMANHO_LOTE = 50_000


def carregar(con, fonte_modulo, ano: int, pasta: Path) -> int:
    caminho = fonte_modulo.baixar(ano, pasta)  # download FORA da transação
    con.begin()
    try:
        con.execute(
            "DELETE FROM despesas WHERE fonte = ? AND ano = ?", (fonte_modulo.FONTE, ano)
        )
        politicos: dict[str, tuple] = {}
        lote: list[tuple] = []
        total = 0
        for politico, despesa in fonte_modulo.parse(caminho):
            # Só carrega despesas do ano pedido (o CSV anual pode conter competências vizinhas)
            if despesa["ano"] != ano:
                continue
            politicos[politico["id"]] = (
                politico["id"], politico["nome"], politico["cargo"],
                politico["partido"], politico["uf"], politico["foto_url"], politico["fonte"],
            )
            lote.append(tuple(despesa[c] for c in _COLUNAS_DESPESA))
            if len(lote) >= _TAMANHO_LOTE:
                con.executemany(_SQL_DESPESA, lote)
                total += len(lote)
                lote = []
        if lote:
            con.executemany(_SQL_DESPESA, lote)
            total += len(lote)
        if politicos:
            con.executemany(_SQL_POLITICO, list(politicos.values()))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return total
