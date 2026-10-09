from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from tests.utils import ObjectGenerator, PayloadGenerator, RequestGenerator

FEE = 150


def run_at_the_same_time(requests: list) -> list:
    """Dispara todos os pedidos juntos, cada um na sua thread, e devolve (status, corpo) de cada."""
    with ThreadPoolExecutor(max_workers=len(requests)) as executor:
        futures = [executor.submit(function, *arguments) for function, *arguments in requests]
        return [future.result() for future in futures]


class TestConcurrency:
    """Pedidos simultâneos (RFC 2.4): a trava faz o segundo esperar e ler o saldo já atualizado."""

    def test_simultaneous_outflows_never_overdraw(self):
        """Dez saídas ao mesmo tempo, saldo para seis: exatamente seis passam.

        Sem a trava, as dez leriam o mesmo saldo de R$ 1.000,00, as dez
        achariam que cabe, e a conta ficaria negativa — ou a CHECK do banco
        viraria 500 em algumas. Com a trava, cada uma lê o saldo deixado
        pela anterior.
        """
        origin = ObjectGenerator.create_funded_account(100000)
        destination = ObjectGenerator.create_account()

        requests = []
        for _request in range(10):
            payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 15000)
            requests.append((RequestGenerator.POST_transfer, origin["account_key"], payload))

        results = run_at_the_same_time(requests)
        statuses = [status for status, _response in results]

        # Cada saída custa 15.000 + 150 = 15.150. Seis custam 90.900; sete, 106.050.
        assert statuses.count(201) == 6
        assert statuses.count(422) == 4

        assert ObjectGenerator.get_balance(origin["account_key"]) == 100000 - 6 * (15000 + FEE)
        assert ObjectGenerator.get_balance(destination["account_key"]) == 6 * 15000

        ObjectGenerator.assert_balance_matches_statement(origin["account_key"])
        ObjectGenerator.assert_balance_matches_statement(destination["account_key"])

    def test_same_key_at_the_same_time_moves_once(self):
        """Cinco cópias do mesmo pedido juntas: uma move (201), as outras devolvem a mesma (200)."""
        origin = ObjectGenerator.create_funded_account(100000)
        destination = ObjectGenerator.create_account()
        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 10000)

        results = run_at_the_same_time(
            [(RequestGenerator.POST_transfer, origin["account_key"], payload) for _copy in range(5)]
        )

        statuses = sorted(status for status, _response in results)
        assert statuses == [200, 200, 200, 200, 201]

        transaction_keys = {response["transaction_key"] for _status, response in results}
        assert transaction_keys == {payload["transaction_key"]}

        assert ObjectGenerator.get_balance(origin["account_key"]) == 100000 - 10000 - FEE

    def test_same_key_on_different_accounts_at_the_same_time(self):
        """Mesmo ID em contas diferentes: as travas não se cruzam, e quem barra é o UNIQUE.

        Origens E destinos diferentes, de propósito: se os dois pedidos
        dividissem uma conta, um esperaria o outro na trava e quem pegaria
        o conflito seria a segunda procura pelo ID — não o banco.
        """
        pairs = [
            (ObjectGenerator.create_funded_account(100000), ObjectGenerator.create_account()),
            (ObjectGenerator.create_funded_account(100000), ObjectGenerator.create_account()),
        ]
        transaction_key = str(uuid4())

        requests = []
        for origin, destination in pairs:
            payload = PayloadGenerator.create_transfer_payload(
                destination["account_key"], 10000, transaction_key=transaction_key
            )
            requests.append((RequestGenerator.POST_transfer, origin["account_key"], payload))

        results = run_at_the_same_time(requests)

        statuses = sorted(status for status, _response in results)
        assert statuses == [201, 409]

        origin_balances = sorted(ObjectGenerator.get_balance(origin["account_key"]) for origin, _destination in pairs)
        assert origin_balances == [100000 - 10000 - FEE, 100000]

        destination_balances = sorted(ObjectGenerator.get_balance(destination["account_key"]) for _origin, destination in pairs)
        assert destination_balances == [0, 10000]

    def test_crossed_transfers_do_not_deadlock(self):
        """A→B e B→A ao mesmo tempo, várias vezes: ninguém fica preso.

        É a ordem da trava (sempre do menor id pro maior) que garante isto.
        Travando na ordem "origem, depois destino", A→B e B→A esperariam
        uma pela outra, e o PostgreSQL mataria uma delas — um 500 aqui.
        """
        first = ObjectGenerator.create_funded_account(100000)
        second = ObjectGenerator.create_funded_account(100000)

        requests = []
        for _round in range(5):
            to_second = PayloadGenerator.create_transfer_payload(second["account_key"], 1000)
            to_first = PayloadGenerator.create_transfer_payload(first["account_key"], 1000)
            requests.append((RequestGenerator.POST_transfer, first["account_key"], to_second))
            requests.append((RequestGenerator.POST_transfer, second["account_key"], to_first))

        results = run_at_the_same_time(requests)

        assert [status for status, _response in results] == [201] * 10

        # Cada um mandou e recebeu cinco vezes 1.000: só a tarifa saiu.
        assert ObjectGenerator.get_balance(first["account_key"]) == 100000 - 5 * FEE
        assert ObjectGenerator.get_balance(second["account_key"]) == 100000 - 5 * FEE

        ObjectGenerator.assert_balance_matches_statement(first["account_key"])
        ObjectGenerator.assert_balance_matches_statement(second["account_key"])
