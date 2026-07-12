import argparse
import sys
from pathlib import Path

from radar.db import conectar, criar_schema
from radar.ingest import loader
from radar.ingest.fontes import camara, cldf, senado

FONTES = {"camara": camara, "senado": senado, "cldf": cldf}


def parse_anos(texto: str) -> list[int]:
    if "-" in texto:
        inicio, fim = texto.split("-")
        return list(range(int(inicio), int(fim) + 1))
    return [int(a) for a in texto.split(",")]


def main() -> int:
    p = argparse.ArgumentParser(description="Ingestão de gastos parlamentares")
    p.add_argument("--anos", required=True, help="ex: 2016-2026 ou 2024,2025")
    p.add_argument("--fontes", default="camara,senado")
    p.add_argument("--db", default="../dados/radar.duckdb")
    p.add_argument("--pasta", default="../dados")
    args = p.parse_args()

    anos = parse_anos(args.anos)
    fontes = [FONTES[f.strip()] for f in args.fontes.split(",")]
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    con = conectar(args.db)
    criar_schema(con)

    sucesso, falhas = [], []
    for fonte in fontes:
        for ano in anos:
            try:
                n = loader.carregar(con, fonte, ano, Path(args.pasta) / fonte.FONTE)
                sucesso.append((fonte.FONTE, ano, n))
                print(f"✔ {fonte.FONTE} {ano}: {n:,} despesas".replace(",", "."))
            except Exception as e:  # resiliente: falha em um ano não para o resto
                falhas.append((fonte.FONTE, ano, str(e)))
                print(f"✖ {fonte.FONTE} {ano}: {e}", file=sys.stderr)

    try:
        atualizados = senado.enriquecer(con)
        print(f"✔ senadores enriquecidos (partido/uf/foto): {atualizados}")
    except Exception as e:
        falhas.append(("senado", "enriquecimento", str(e)))
        print(f"✖ enriquecimento de senadores: {e}", file=sys.stderr)

    total = sum(n for _, _, n in sucesso)
    print(f"\nRelatório: {len(sucesso)} cargas OK, {len(falhas)} falhas, "
          f"{total:,} despesas no total".replace(",", "."))
    for fonte, ano, erro in falhas:
        print(f"  FALTOU {fonte} {ano}: {erro}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
