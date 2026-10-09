from uuid import uuid4

from tests.utils.random_generator import RandomGenerator

DEFAULT_PASSWORD = "123456"

# R$ 5.000,00 de renda: a verificação de renda (2×) só alerta acima de
# R$ 10.000,00 por saída, o que deixa os testes comuns longe dela.
DEFAULT_MONTHLY_INCOME = 500000


class PayloadGenerator:
    @staticmethod
    def create_client_payload(
        name: str = None,
        email: str = None,
        document_number: str = None,
        birthdate: str = None,
        monthly_income: int = None,
        cpf_prefix: str = None,
    ) -> dict:
        """Um cadastro válido, com qualquer campo trocado a pedido.

        E-mail e CPF saem aleatórios, pra que dois cadastros seguidos não
        batam na regra de duplicidade. O `cpf_prefix` escolhe o cenário do
        mock (veja tests/utils/mock_scenario.py).
        """
        if name is None:
            name = "Maria da Silva"

        if email is None:
            email = f"maria.silva.{uuid4()}@exemplo.com.br"

        if document_number is None:
            document_number = RandomGenerator.generate_cpf(cpf_prefix)

        if birthdate is None:
            birthdate = "1990-05-17"

        if monthly_income is None:
            monthly_income = DEFAULT_MONTHLY_INCOME

        return {
            "name": name,
            "email": email,
            "document_number": document_number,
            "birthdate": birthdate,
            "monthly_income": monthly_income,
        }

    @staticmethod
    def create_account_payload(password: str = DEFAULT_PASSWORD) -> dict:
        return {"password": password}

    @staticmethod
    def create_status_payload(status: str) -> dict:
        return {"status": status}

    @staticmethod
    def create_deposit_payload(
        amount: int,
        method: str = "cash",
        transaction_key: str = None,
        source_bank_code: str = None,
        depositor_document_number: str = None,
    ) -> dict:
        if transaction_key is None:
            transaction_key = str(uuid4())

        if depositor_document_number is None:
            depositor_document_number = RandomGenerator.generate_cpf()

        payload = {
            "transaction_key": transaction_key,
            "amount": amount,
            "method": method,
            "depositor_name": "João Depositante",
            "depositor_document_number": depositor_document_number,
        }

        if source_bank_code is not None:
            payload["source_bank_code"] = source_bank_code

        return payload

    @staticmethod
    def create_transfer_payload(
        destination_account_key: str,
        amount: int,
        password: str = DEFAULT_PASSWORD,
        transaction_key: str = None,
    ) -> dict:
        if transaction_key is None:
            transaction_key = str(uuid4())

        return {
            "transaction_key": transaction_key,
            "destination_account_key": destination_account_key,
            "amount": amount,
            "password": password,
        }

    @staticmethod
    def create_pix_key_payload(key_type: str, key_value: str = None, password: str = DEFAULT_PASSWORD) -> dict:
        payload = {"key_type": key_type, "password": password}

        if key_value is not None:
            payload["key_value"] = key_value

        return payload

    @staticmethod
    def create_pix_payload(
        pix_key: str,
        amount: int,
        password: str = DEFAULT_PASSWORD,
        transaction_key: str = None,
    ) -> dict:
        if transaction_key is None:
            transaction_key = str(uuid4())

        return {
            "transaction_key": transaction_key,
            "pix_key": pix_key,
            "amount": amount,
            "password": password,
        }
