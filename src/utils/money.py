def format_brl(cents: int) -> str:
    """Centavos em reais, do jeito que o cliente lê: 123456 vira "R$ 1.234,56".

    Só serve para MENSAGEM. Dinheiro continua inteiro, em centavos, em
    todo o resto da API.
    """
    sign = "-" if cents < 0 else ""
    reais, centavos = divmod(abs(int(cents)), 100)
    reais_com_ponto = f"{reais:,}".replace(",", ".")

    return f"{sign}R$ {reais_com_ponto},{centavos:02d}"
