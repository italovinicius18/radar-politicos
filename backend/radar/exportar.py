"""Exporta o DuckDB para os JSONs estáticos consumidos pelo site pré-compilado."""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from radar import consultas
from radar.db import conectar
from radar.fontes_registro import FONTES


def _gravar(caminho: Path, corpo) -> int:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(corpo, ensure_ascii=False, separators=(",", ":"))
    caminho.write_text(texto, encoding="utf-8")
    return len(texto.encode("utf-8"))


def exportar(db: str, saida: Path) -> dict:
    saida = Path(saida)
    staging = saida.with_name(saida.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    con = conectar(db, somente_leitura=True)
    arquivos = 0
    total_bytes = 0

    def grava(rel: str, corpo):
        nonlocal arquivos, total_bytes
        total_bytes += _gravar(staging / rel, corpo)
        arquivos += 1

    anos = consultas.anos_com_dados(con)
    politicos = consultas.buscar_politicos(con, limite=100_000)
    grava("politicos.json", politicos)
    for ano in anos:
        grava(f"visao-geral/{ano}.json", consultas.visao_geral(con, ano))
        por_cargo = {}
        for fonte in FONTES.values():
            cargo = fonte["cargo"]
            lista = consultas.rankings(con, ano=ano, cargo=cargo, limite=50)
            if lista:
                por_cargo[cargo] = lista
        grava(f"rankings/{ano}.json", {
            "geral": consultas.rankings(con, ano=ano, limite=100),
            "por_cargo": por_cargo,
        })
    for p in politicos:
        pid = p["id"]
        grava(f"perfil/{pid}.json", consultas.resumo(con, pid))
        grava(f"despesas/{pid}.json", consultas.despesas_compactas(con, pid))
    grava("meta.json", {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "anos": anos,
        "ano_max": max(anos) if anos else None,
        "total_politicos": len(politicos),
        "total_despesas": con.execute("SELECT count(*) FROM despesas").fetchone()[0],
    })
    con.close()

    if saida.exists():
        shutil.rmtree(saida)
    staging.replace(saida)
    return {"arquivos": arquivos, "bytes": total_bytes}


def main() -> int:
    p = argparse.ArgumentParser(description="Exporta JSONs estáticos do Radar Políticos")
    p.add_argument("--db", default="../dados/radar.duckdb")
    p.add_argument("--saida", default="../frontend/public/dados")
    args = p.parse_args()
    r = exportar(args.db, Path(args.saida))
    print(f"✔ {r['arquivos']:,} arquivos · {r['bytes'] / 1e6:,.1f} MB".replace(",", "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
