import pytest
from fastapi.testclient import TestClient

from radar.db import conectar, criar_schema


@pytest.fixture
def db_amostra(tmp_path):
    caminho = tmp_path / "amostra.duckdb"
    con = conectar(caminho)
    criar_schema(con)
    con.execute("""
        INSERT INTO politicos VALUES
        ('camara-1', 'José Ávila', 'Deputado Federal', 'PT', 'SP', 'http://foto/1.jpg', 'camara'),
        ('camara-2', 'Maria Souza', 'Deputado Federal', 'PL', 'MG', 'http://foto/2.jpg', 'camara'),
        ('senado-joao-neto', 'JOÃO NETO', 'Senador', 'MDB', 'GO', NULL, 'senado')
    """)
    con.execute("""
        INSERT INTO despesas VALUES
        ('camara-1', 2024, 1, '2024-01-10', 'Passagens', 'PASSAGEM AÉREA - SIGEPA', 'BSB/GRU',
         'TAM', '02.012.862/0001-60', 1000.00, 'http://doc/1.pdf', 'camara'),
        ('camara-1', 2024, 2, '2024-02-05', 'Combustíveis', 'COMBUSTÍVEIS E LUBRIFICANTES.', NULL,
         'POSTO X', '11.111.111/0001-11', 300.00, NULL, 'camara'),
        ('camara-1', 2025, 1, '2025-01-15', 'Passagens', 'PASSAGEM AÉREA - SIGEPA', NULL,
         'TAM', '02.012.862/0001-60', -200.00, NULL, 'camara'),
        ('camara-2', 2024, 3, '2024-03-01', 'Divulgação', 'DIVULGAÇÃO DA ATIVIDADE PARLAMENTAR.', NULL,
         'GRÁFICA Y', '22.222.222/0001-22', 5000.00, 'http://doc/2.pdf', 'camara'),
        ('senado-joao-neto', 2024, 1, '2024-01-20', 'Manutenção de escritório',
         'Aluguel de imóveis para escritório político', NULL,
         'IMOBILIÁRIA Z', '33.333.333/0001-33', 2000.00, NULL, 'senado')
    """)
    con.close()
    return str(caminho)


@pytest.fixture
def cliente(db_amostra):
    from radar.api.app import criar_app

    return TestClient(criar_app(db_amostra))
