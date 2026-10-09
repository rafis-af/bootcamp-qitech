class MockScenario:
    """Os três primeiros dígitos do CPF que escolhem a resposta do mock.

    É a mesma tabela de mocks/app.py, escrita aqui à mão pelo mesmo motivo
    de sempre: os testes não importam nada de fora deles. Se o mock mudar,
    os testes que dependem do cenário ficam vermelhos — e é esse o aviso.

    Sem prefixo nenhum, o cliente sai "limpo": Receita REGULAR, Serasa sem
    restrição e score 800 — ou seja, Ouro.
    """

    RECEITA_SUSPENDED = "900"
    RECEITA_CANCELED = "901"
    RECEITA_SLOW = "910"

    SERASA_RESTRICTION = "920"
    SERASA_HIGH_FRAUD_RISK = "921"
    SERASA_SCORE_599 = "922"
    SERASA_SCORE_600 = "923"
    SERASA_NO_SCORE = "924"
    SERASA_LATE_PAYMENTS = "925"
    SERASA_SLOW = "930"

    # Atalho: quando o teste só precisa de um cliente Prata, este é o cenário.
    SILVER = SERASA_SCORE_599
