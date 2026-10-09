from tests.utils.payload_generator import DEFAULT_PASSWORD, PayloadGenerator
from tests.utils.request_generator import RequestGenerator

DUPLICATED_DOCUMENT_NUMBER = "QIT001003"
MAX_DEPOSIT = 100000000
STATEMENT_PAGE_LIMIT = 100


class ObjectGenerator:
    """Monta cenários pela API, como um cliente de verdade faria."""

    @staticmethod
    def create_client(cpf_prefix: str = None, monthly_income: int = None) -> dict:
        """Cadastra um cliente e devolve o corpo da resposta.

        O CPF com prefixo de cenário só tem 6 dígitos sorteados, e o banco
        dos testes não é zerado entre uma rodada e outra: de vez em quando
        o sorteio repete um CPF de uma rodada anterior. Quando isso
        acontece, sorteia de novo — o teste que chamou quer UM cliente
        daquele cenário, não aquele CPF.
        """
        for _attempt in range(5):
            payload = PayloadGenerator.create_client_payload(cpf_prefix=cpf_prefix, monthly_income=monthly_income)
            status, response = RequestGenerator.POST_client(payload)

            if status == 409 and response["code"] == DUPLICATED_DOCUMENT_NUMBER:
                continue

            assert status == 201, response
            return response

        raise AssertionError("Não consegui sortear um CPF livre em 5 tentativas")

    @staticmethod
    def create_account(cpf_prefix: str = None, monthly_income: int = None, password: str = DEFAULT_PASSWORD) -> dict:
        client = ObjectGenerator.create_client(cpf_prefix, monthly_income)

        status, response = RequestGenerator.POST_account(
            client["client_key"], PayloadGenerator.create_account_payload(password)
        )
        assert status == 201, response

        response["document_number"] = client["document_number"]
        response["email"] = client["email"]
        return response

    @staticmethod
    def deposit(account_key: str, amount: int) -> dict:
        status, response = RequestGenerator.POST_deposit(account_key, PayloadGenerator.create_deposit_payload(amount))
        assert status == 201, response
        return response

    @staticmethod
    def create_funded_account(balance: int, cpf_prefix: str = None, monthly_income: int = None) -> dict:
        """Uma conta aberta e com saldo, depositado em quantas vezes o teto por operação exigir."""
        account = ObjectGenerator.create_account(cpf_prefix, monthly_income)

        remaining = balance
        while remaining > 0:
            amount = min(remaining, MAX_DEPOSIT)
            ObjectGenerator.deposit(account["account_key"], amount)
            remaining = remaining - amount

        account["balance"] = balance
        return account

    @staticmethod
    def create_pix_key(account_key: str, key_type: str = "random", key_value: str = None) -> dict:
        status, response = RequestGenerator.POST_pix_key(
            account_key, PayloadGenerator.create_pix_key_payload(key_type, key_value)
        )
        assert status == 201, response
        return response

    @staticmethod
    def get_account(account_key: str) -> dict:
        status, response = RequestGenerator.GET_account(account_key)
        assert status == 200, response
        return response

    @staticmethod
    def get_balance(account_key: str) -> int:
        return ObjectGenerator.get_account(account_key)["balance"]

    @staticmethod
    def get_full_statement(account_key: str) -> list:
        """Todos os lançamentos da conta, página por página."""
        entries = []
        page = 0

        while True:
            status, response = RequestGenerator.GET_statement(
                account_key, {"limit": STATEMENT_PAGE_LIMIT, "page": page}
            )
            assert status == 200, response

            entries.extend(response["data"])

            if response["is_last_page"]:
                return entries

            page = page + 1

    @staticmethod
    def assert_balance_matches_statement(account_key: str) -> None:
        """A garantia central da RFC: o saldo é a soma dos lançamentos (RFC 1.4)."""
        entries = ObjectGenerator.get_full_statement(account_key)

        total = 0
        for entry in entries:
            total = total + entry["amount"]

        assert total == ObjectGenerator.get_balance(account_key)

        for entry in entries:
            assert entry["balance_after"] >= 0
