import csv
import zipfile
from collections.abc import Iterator
from pathlib import Path

import httpx

from radar.ingest.normalizacao import normalizar_categoria, parse_data, parse_valor

FONTE = "camara"
URL = "https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip"
FOTO = "https://www.camara.leg.br/internet/deputado/bandep/{id}.jpg"


def baixar(ano: int, pasta: Path) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    csv_destino = pasta / f"Ano-{ano}.csv"
    if csv_destino.exists():
        return csv_destino
    zip_destino = pasta / f"Ano-{ano}.csv.zip"
    with httpx.stream("GET", URL.format(ano=ano), timeout=300, follow_redirects=True) as r:
        r.raise_for_status()
        with open(zip_destino, "wb") as f:
            for pedaco in r.iter_bytes():
                f.write(pedaco)
    with zipfile.ZipFile(zip_destino) as z:
        z.extract(f"Ano-{ano}.csv", pasta)
    zip_destino.unlink()
    return csv_destino


def parse(caminho: Path) -> Iterator[tuple[dict, dict]]:
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        for linha in csv.DictReader(f, delimiter=";"):
            ide = (linha["ideCadastro"] or "").strip()
            if not ide:
                continue  # linhas de liderança partidária, não são políticos
            uf = (linha["sgUF"] or "").strip()
            politico = {
                "id": f"camara-{ide}",
                "nome": linha["txNomeParlamentar"].strip(),
                "cargo": "Deputado Federal",
                "partido": (linha["sgPartido"] or "").strip() or None,
                "uf": uf if uf and uf != "NA" else None,
                "foto_url": FOTO.format(id=ide),
                "fonte": FONTE,
            }
            descricao = (linha["txtDescricaoEspecificacao"] or "").strip() or (
                linha["txtTrecho"] or ""
            ).strip() or None
            despesa = {
                "politico_id": politico["id"],
                "ano": int(linha["numAno"]),
                "mes": int(linha["numMes"]) if linha["numMes"] else None,
                "data": parse_data(linha["datEmissao"]),
                "categoria": normalizar_categoria(linha["txtDescricao"]),
                "categoria_original": linha["txtDescricao"].strip(),
                "descricao": descricao,
                "fornecedor": (linha["txtFornecedor"] or "").strip() or None,
                "fornecedor_cnpj": (linha["txtCNPJCPF"] or "").strip() or None,
                "valor": parse_valor(linha["vlrLiquido"]),
                "documento_url": (linha["urlDocumento"] or "").strip() or None,
                "fonte": FONTE,
            }
            yield politico, despesa
