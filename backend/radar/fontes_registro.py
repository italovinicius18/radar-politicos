FONTES = {
    "camara": {"rotulo": "Câmara", "cargo": "Deputado Federal"},
    "senado": {"rotulo": "Senado", "cargo": "Senador"},
    "cldf": {"rotulo": "CLDF", "cargo": "Deputado Distrital"},
}


def rotulo(fonte: str) -> str:
    return FONTES.get(fonte, {}).get("rotulo", fonte)
