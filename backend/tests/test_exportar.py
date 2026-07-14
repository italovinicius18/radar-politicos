import json
from pathlib import Path

from radar import consultas, exportar
from radar.db import conectar


def _exportado(db_amostra, tmp_path) -> Path:
    saida = tmp_path / "dados"
    relatorio = exportar.exportar(db_amostra, saida)
    assert relatorio["arquivos"] > 0 and relatorio["bytes"] > 0
    return saida


def test_estrutura_gerada(db_amostra, tmp_path):
    saida = _exportado(db_amostra, tmp_path)
    assert (saida / "meta.json").exists()
    assert (saida / "politicos.json").exists()
    assert (saida / "visao-geral" / "2024.json").exists()
    assert (saida / "visao-geral" / "2025.json").exists()
    assert (saida / "rankings" / "2024.json").exists()
    assert (saida / "perfil" / "camara-1.json").exists()
    assert (saida / "despesas" / "camara-1" / "2024.json").exists()
    # senado-joao-neto só tem 2024: não deve existir chunk de 2025
    assert not (saida / "despesas" / "senado-joao-neto" / "2025.json").exists()


def test_meta(db_amostra, tmp_path):
    saida = _exportado(db_amostra, tmp_path)
    meta = json.loads((saida / "meta.json").read_text())
    assert meta["anos"] == [2024, 2025]
    assert meta["ano_max"] == 2025
    assert meta["total_politicos"] == 3
    assert meta["total_despesas"] == 5
    assert "gerado_em" in meta


def test_paridade_com_consultas(db_amostra, tmp_path):
    saida = _exportado(db_amostra, tmp_path)
    con = conectar(db_amostra, somente_leitura=True)
    assert json.loads((saida / "perfil" / "camara-1.json").read_text()) == consultas.resumo(con, "camara-1")
    assert json.loads((saida / "visao-geral" / "2024.json").read_text()) == consultas.visao_geral(con, 2024)
    assert json.loads((saida / "despesas" / "camara-1" / "2024.json").read_text()) == (
        consultas.despesas_compactas(con, "camara-1", 2024)
    )
    con.close()


def test_reexecucao_e_atomica(db_amostra, tmp_path):
    saida = _exportado(db_amostra, tmp_path)
    (saida / "lixo.json").write_text("{}")
    _exportado(db_amostra, tmp_path)  # segunda execução substitui o diretório inteiro
    assert not (saida / "lixo.json").exists()
    assert (saida / "meta.json").exists()
