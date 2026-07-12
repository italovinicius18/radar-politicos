import re
from collections.abc import Iterator
from pathlib import Path

import httpx
import openpyxl

from radar.ingest.normalizacao import normalizar_categoria, slug

FONTE = "cldf"
CARGO = "Deputado Distrital"
URL_DATASET = "https://dados.cl.df.gov.br/api/3/action/package_show?id=verbas-indenizatorias"
CATEGORIA_RESIDUAL = "Outras (não detalhado no dado oficial)"
_MES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}


def baixar(ano: int, pasta: Path) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"cldf-{ano}.xlsx"
    if destino.exists():
        return destino
    resposta = httpx.get(URL_DATASET, timeout=60, follow_redirects=True)
    resposta.raise_for_status()
    recursos = resposta.json()["result"]["resources"]
    candidatos = [
        r for r in recursos
        if r["format"].upper() == "XLSX" and str(ano) in r["name"]
    ]
    if not candidatos:
        raise ValueError(f"CLDF: nenhum recurso XLSX para {ano}")
    with httpx.stream("GET", candidatos[0]["url"], timeout=300, follow_redirects=True) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for pedaco in r.iter_bytes():
                f.write(pedaco)
    return destino


def parse(caminho: Path) -> Iterator[tuple[dict, dict]]:
    # read_only=False de propósito: exports do Power BI trazem dimensões erradas
    wb = openpyxl.load_workbook(caminho)
    try:
        linhas = wb.active.iter_rows(values_only=True)
        primeira = next(linhas, None)
        if primeira is None:
            return
        if str(primeira[0] or "").strip() == "NOME_PARLAMENTAR":
            yield from _parse_transacional(linhas)
        else:
            yield from _parse_pivo(linhas)
    finally:
        wb.close()


def _politico(nome_bruto: str) -> dict:
    nome = re.sub(r"^deputad[oa]\s+", "", str(nome_bruto).strip(), flags=re.IGNORECASE)
    # normalizar nomes em CAIXA ALTA (formato pivô)
    if nome.isupper():
        nome = nome.title()
    return {
        "id": f"cldf-{slug(nome)}",
        "nome": nome,
        "cargo": CARGO,
        "partido": None,
        "uf": "DF",
        "foto_url": None,
        "fonte": FONTE,
    }


def _parse_transacional(linhas) -> Iterator[tuple[dict, dict]]:
    for linha in linhas:
        if not linha or not linha[0] or linha[6] is None:
            # sem data não há competência (ano/mês) para a despesa
            continue
        politico = _politico(linha[0])
        data = linha[6].date()
        classificacao = str(linha[8]).strip() if linha[8] else ""
        despesa = {
            "politico_id": politico["id"],
            "ano": data.year,
            "mes": data.month,
            "data": data,
            "categoria": normalizar_categoria(classificacao),
            "categoria_original": classificacao,
            "descricao": str(linha[9]).strip() if linha[9] else None,
            "fornecedor": str(linha[2]).strip() if linha[2] else None,
            "fornecedor_cnpj": str(linha[3] or linha[4] or "").strip() or None,
            "valor": float(linha[7] or 0),
            "documento_url": None,
            "fonte": FONTE,
        }
        yield politico, despesa


def _despesa_pivo(politico, ano, mes, categoria_original, valor, residual=False):
    return {
        "politico_id": politico["id"],
        "ano": ano,
        "mes": mes,
        "data": None,
        "categoria": CATEGORIA_RESIDUAL if residual else normalizar_categoria(categoria_original),
        "categoria_original": categoria_original,
        "descricao": None,
        "fornecedor": None,
        "fornecedor_cnpj": None,
        "valor": valor,
        "documento_url": None,
        "fonte": FONTE,
    }


def _parse_pivo(linhas) -> Iterator[tuple[dict, dict]]:
    cabecalho = None
    for linha in linhas:
        if linha and str(linha[0] or "").strip().lower() == "ano":
            cabecalho = [str(c or "").strip() for c in linha]
            break
    if cabecalho is None:
        raise ValueError("CLDF: cabeçalho do formato pivô não encontrado")
    idx_glosa = cabecalho.index("Glosa")
    idx_total = cabecalho.index("totalVerbaGeral")
    categorias = cabecalho[3:idx_glosa]
    for linha in linhas:
        if not linha or not linha[2] or linha[idx_total] is None:
            continue
        politico = _politico(linha[2])
        ano = int(linha[0])
        mes = _MES.get(str(linha[1] or "").strip().lower()[:3])
        total = float(linha[idx_total])
        soma = 0.0
        for i, categoria in enumerate(categorias, start=3):
            valor = float(linha[i] or 0)
            if valor == 0:
                continue
            soma += valor
            yield politico, _despesa_pivo(politico, ano, mes, categoria, valor)
        glosa = float(linha[idx_glosa] or 0)
        if glosa != 0:
            yield politico, _despesa_pivo(politico, ano, mes, "Glosa", -glosa)
        # invariante: soma das despesas emitidas == totalVerbaGeral
        residuo = round(total - soma + glosa, 2)
        if residuo != 0:
            yield politico, _despesa_pivo(politico, ano, mes, CATEGORIA_RESIDUAL, residuo, residual=True)
