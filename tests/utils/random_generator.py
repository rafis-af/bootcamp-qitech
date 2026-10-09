import random
from typing import Optional

CPF_BASE_LENGTH = 9


class RandomGenerator:
    @staticmethod
    def generate_cpf(prefix: Optional[str] = None) -> str:
        """Um CPF válido — os dois dígitos verificadores batem com a conta.

        O `prefix` escolhe o cenário do mock da Receita e da Serasa: os três
        primeiros dígitos decidem a resposta (a tabela está em mocks/app.py
        e em tests/utils/mock_scenario.py). O resto é sorteado.

        Sem prefixo, o primeiro dígito vai de 0 a 8, nunca 9: os começos
        9xx são os cenários especiais do mock, e um cadastro "comum" não
        pode cair num deles por sorte.
        """
        if prefix is None:
            cpf = [random.randrange(9)]
        else:
            cpf = [int(digit) for digit in prefix]

        while len(cpf) < CPF_BASE_LENGTH:
            cpf.append(random.randrange(10))

        for _ in range(2):
            value = sum([(len(cpf) + 1 - i) * v for i, v in enumerate(cpf)]) % 11
            cpf.append(11 - value if value > 1 else 0)

        cpf_number = "".join(str(x) for x in cpf)
        cpf_number = f"{cpf_number[0:3]}.{cpf_number[3:6]}.{cpf_number[6:9]}-{cpf_number[9:11]}"
        return cpf_number

    @staticmethod
    def generate_phone() -> str:
        """Um celular no formato da chave Pix: +55, DDD e 9 dígitos."""
        return "+55119" + "".join(str(random.randrange(10)) for _ in range(8))
