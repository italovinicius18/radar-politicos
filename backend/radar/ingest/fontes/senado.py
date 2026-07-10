import csv
from collections.abc import Iterator
from pathlib import Path

import httpx

from radar.ingest.normalizacao import (
    normalizar_categoria,
    parse_data,
    parse_valor,
    sem_acento,
    slug,
)

FONTE = "senado"
URL = "https://www.senado.leg.br/transparencia/LAI/verba/despesa_ceaps_{ano}.csv"
URL_SENADORES = "https://legis.senado.leg.br/dadosabertos/senador/lista/legislatura/55/57.json"
FOTO = "https://www.senado.leg.br/senadores/img/fotos-oficiais/senador{codigo}.jpg"


def baixar(ano: int, pasta: Path) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"despesa_ceaps_{ano}.csv"
    if destino.exists():
        return destino
    with httpx.stream("GET", URL.format(ano=ano), timeout=300, follow_redirects=True) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for pedaco in r.iter_bytes():
                f.write(pedaco)
    return destino


def parse(caminho: Path) -> Iterator[tuple[dict, dict]]:
    with open(caminho, encoding="latin-1", newline="") as f:
        f.readline()  # primeira linha: "ULTIMA ATUALIZACAO";...
        for linha in csv.DictReader(f, delimiter=";"):
            nome = linha["SENADOR"].strip()
            politico = {
                "id": f"senado-{slug(nome)}",
                "nome": nome,
                "cargo": "Senador",
                "partido": None,
                "uf": None,
                "foto_url": None,
                "fonte": FONTE,
            }
            despesa = {
                "politico_id": politico["id"],
                "ano": int(linha["ANO"]),
                "mes": int(linha["MES"]) if linha["MES"] else None,
                "data": parse_data(linha["DATA"]),
                "categoria": normalizar_categoria(linha["TIPO_DESPESA"]),
                "categoria_original": linha["TIPO_DESPESA"].strip(),
                "descricao": (linha["DETALHAMENTO"] or "").strip() or None,
                "fornecedor": (linha["FORNECEDOR"] or "").strip() or None,
                "fornecedor_cnpj": (linha["CNPJ_CPF"] or "").strip() or None,
                "valor": parse_valor(linha["VALOR_REEMBOLSADO"]),
                "documento_url": None,  # CEAPS não publica URL de documento
                "fonte": FONTE,
            }
            yield politico, despesa


def enriquecer(con, dados: dict | None = None) -> int:
    """Preenche partido/uf/foto dos senadores casando por nome normalizado."""
    if dados is None:
        dados = httpx.get(URL_SENADORES, timeout=60, follow_redirects=True).json()
    parlamentares = dados["ListaParlamentarLegislatura"]["Parlamentares"]["Parlamentar"]
    atualizados = 0
    existentes = {
        sem_acento(nome): pid
        for pid, nome in con.execute(
            "SELECT id, nome FROM politicos WHERE fonte = 'senado'"
        ).fetchall()
    }
    for p in parlamentares:
        ident = p["IdentificacaoParlamentar"]
        pid = existentes.get(sem_acento(ident["NomeParlamentar"]))
        if not pid:
            continue
        con.execute(
            "UPDATE politicos SET partido = ?, uf = ?, foto_url = ? WHERE id = ?",
            (
                ident.get("SiglaPartidoParlamentar"),
                ident.get("UfParlamentar"),
                FOTO.format(codigo=ident["CodigoParlamentar"]),
                pid,
            ),
        )
        atualizados += 1
    return atualizados
