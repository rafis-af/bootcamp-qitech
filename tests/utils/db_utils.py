from os import environ
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


RESET_QUERIES = [
    "DROP SCHEMA public CASCADE;",
    "CREATE SCHEMA public;",
    "GRANT ALL ON SCHEMA public TO CURRENT_USER;",
    "GRANT ALL ON SCHEMA public TO public;",
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_FILE = PROJECT_ROOT / "database" / "database.sql"

DEFAULT_DATABASE_URL = "postgresql+psycopg2://bootcamp:bootcamp@localhost:5432/bootcamp"

DATABASE_OFFLINE = (
    "Não consegui falar com o banco em {host}:{port}.\n"
    "Ele precisa estar de pé pros testes rodarem. Suba com:  docker compose up\n"
    "Se ele já está de pé, confira a porta na DATABASE_URL do seu .env."
)

EVENTS_OF_ACCOUNT_QUERY = text(
    """
    SELECT event.event_type, event.severity, event.detail, event.request_id
    FROM event
    JOIN account ON account.id = event.account_id
    WHERE account.account_key = :account_key
    ORDER BY event.id
    """
)

EVENTS_OF_CLIENT_QUERY = text(
    """
    SELECT event.event_type, event.severity, event.detail, event.request_id
    FROM event
    JOIN client ON client.id = event.client_id
    WHERE client.client_key = :client_key
    ORDER BY event.id
    """
)

CLOSE_CURRENT_FEE_QUERY = text(
    """
    UPDATE fee SET ends_at = NOW()
    WHERE ends_at IS NULL
      AND level_id = (SELECT id FROM level WHERE enumerator = :level)
      AND transaction_type_id = (SELECT id FROM transaction_type WHERE enumerator = :transaction_type)
    """
)

OPEN_NEW_FEE_QUERY = text(
    """
    INSERT INTO fee (level_id, transaction_type_id, amount)
    SELECT level.id, transaction_type.id, :amount
    FROM level, transaction_type
    WHERE level.enumerator = :level AND transaction_type.enumerator = :transaction_type
    """
)


class DbUtils:
    """O acesso direto ao banco que os testes têm — e o porquê de cada um.

    A regra deste projeto é que os testes falam com a API por HTTP, como
    um cliente de verdade. As três exceções abaixo existem porque a API
    não tem (e não deve ter) uma rota para o que elas fazem:

    • `rollback` zera o banco. Não monta cenário nenhum.
    • `events_of_*` LÊ a tabela de eventos. A RFC promete que recusas,
      alertas e bloqueios viram evento (RFC 2.3), e nenhuma rota da v1
      devolve eventos — sem esta leitura, essa promessa não teria teste.
    • `change_fee` troca a tarifa do jeito que a RFC 2.1 descreve: fechar
      a vigente e abrir outra, por dado, sem deploy. Na vida real isso é
      um comando do back-office no banco; aqui, é este método.
    """

    @staticmethod
    def database_url() -> str:
        return environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

    @staticmethod
    def rollback() -> None:
        """Apaga o banco inteiro e o recria do zero com o database/database.sql.

        Quem precisa chamar: o teste cuja asserção depende de QUANTAS
        linhas existem no banco (contar, listar, paginar). Um teste que
        só olha o que ele mesmo criou não precisa.
        """
        # Lê o schema ANTES de apagar qualquer coisa: se o arquivo não
        # estiver lá, o erro acontece com o banco ainda intacto, e não
        # depois que o schema já foi embora.
        # utf-8 explícito: o arquivo tem acento ("Depósito"), e o padrão
        # do Windows não é utf-8.
        schema = SCHEMA_FILE.read_text(encoding="utf-8")

        engine = create_engine(DbUtils.database_url(), isolation_level="AUTOCOMMIT")

        try:
            with engine.connect() as connection:
                for query in RESET_QUERIES:
                    connection.exec_driver_sql(query)

                connection.exec_driver_sql(schema)
        except OperationalError:
            message = DATABASE_OFFLINE.format(host=engine.url.host, port=engine.url.port)
            raise RuntimeError(message) from None
        finally:
            engine.dispose()

    @staticmethod
    def events_of_account(account_key: str) -> list:
        return DbUtils._fetch_all(EVENTS_OF_ACCOUNT_QUERY, {"account_key": account_key})

    @staticmethod
    def events_of_client(client_key: str) -> list:
        return DbUtils._fetch_all(EVENTS_OF_CLIENT_QUERY, {"client_key": client_key})

    @staticmethod
    def change_fee(level: str, transaction_type: str, amount: int) -> None:
        """Fecha a tarifa vigente e abre outra, na MESMA transação (RFC 2.1)."""
        engine = create_engine(DbUtils.database_url())

        try:
            with engine.begin() as connection:
                params = {"level": level, "transaction_type": transaction_type, "amount": amount}
                connection.execute(CLOSE_CURRENT_FEE_QUERY, params)
                connection.execute(OPEN_NEW_FEE_QUERY, params)
        finally:
            engine.dispose()

    @staticmethod
    def _fetch_all(query, params: dict) -> list:
        engine = create_engine(DbUtils.database_url())

        try:
            with engine.connect() as connection:
                rows = connection.execute(query, params).mappings().all()
                return [dict(row) for row in rows]
        finally:
            engine.dispose()
