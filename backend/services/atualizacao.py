from datetime import date


def aplicar_campos(objeto, campos):
    for nome, valor in campos.items():
        if valor is not None:
            setattr(objeto, nome, valor)


def converter_data(valor, descricao):
    if valor in (None, ""):
        return None
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except ValueError as erro:
        raise ValueError(f"{descricao} deve estar no formato AAAA-MM-DD.") from erro
