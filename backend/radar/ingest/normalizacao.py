import unicodedata
from datetime import date, datetime


def sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def slug(texto: str) -> str:
    return "-".join(sem_acento(texto).split())


def parse_valor(texto: str) -> float:
    texto = (texto or "").strip()
    if not texto:
        return 0.0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return float(texto)


_FORMATOS_DATA = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y")


def parse_data(texto: str) -> date | None:
    texto = (texto or "").strip()
    for formato in _FORMATOS_DATA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


# Ordem importa: a categoria combinada do Senado ("Locomoção, hospedagem,
# alimentação, combustíveis...") precisa casar antes de COMBUST/ALIMENTA.
_REGRAS_CATEGORIA = [
    ("LOCOMOCAO", "Locomoção, hospedagem e alimentação"),
    ("PASSAGE", "Passagens"),
    ("COMBUST", "Combustíveis"),
    ("DIVULGA", "Divulgação"),
    ("CONSULTOR", "Consultorias e trabalhos técnicos"),
    ("ESCRITORIO", "Manutenção de escritório"),
    ("MATERIAL DE CONSUMO", "Manutenção de escritório"),
    ("IMOVE", "Manutenção de escritório"),
    ("MAQUINA", "Manutenção de escritório"),
    ("MATERIA", "Manutenção de escritório"),
    ("GLOSA", "Glosas e estornos"),
    ("TELEFON", "Telefonia"),
    ("POSTA", "Serviços postais"),
    ("ALIMENTA", "Alimentação"),
    ("HOSPEDAGEM", "Hospedagem"),
    ("SEGURANCA", "Segurança"),
    ("TAXI", "Táxi, pedágio e estacionamento"),
    ("VEICULO", "Locação de veículos"),
    ("AERONAVES", "Locação de aeronaves"),
    ("EMBARCA", "Locação de embarcações"),
    ("CURSO", "Cursos e eventos"),
    ("ASSINATURA", "Publicações"),
    ("TOKENS", "Certificados digitais"),
]


def normalizar_categoria(original: str) -> str:
    original = (original or "").strip()
    if not original:
        return "Não especificada"
    chave = sem_acento(original).upper()
    for padrao, categoria in _REGRAS_CATEGORIA:
        if padrao in chave:
            return categoria
    return original.title()
