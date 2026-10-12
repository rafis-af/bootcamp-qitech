"""Erro que ninguém levantou de propósito vira um erro com nome (src/errors/unexpected.py).

Cada caso abaixo é um erro que a API só mostra quando a infraestrutura falha:
banco fora do ar, pool cheio, consulta cancelada pelo tempo. Nenhuma rota
consegue provocar isso de forma confiável, então o teste chama o mapeamento
direto, com o erro que o SQLAlchemy levantaria.
"""
import pytest
import sqlalchemy.exc as sa_exc

from errors import (
    DataConflict,
    DataOutOfRange,
    DatabaseUnavailable,
    InternalError,
    OperationTimeout,
    ServiceOverloaded,
)
from errors.unexpected import map_unexpected_exception


class FakePostgresError(Exception):
    """O que o driver do PostgreSQL anexa ao erro: o SQLSTATE em `pgcode`."""

    def __init__(self, pgcode: str) -> None:
        super().__init__(f"postgres error {pgcode}")
        self.pgcode = pgcode


def database_error(error_class, pgcode: str):
    return error_class("SELECT 1", {}, FakePostgresError(pgcode))


def test_no_free_connection_in_the_pool_is_503_overloaded():
    mapped = map_unexpected_exception(sa_exc.TimeoutError("QueuePool limit of size 10 overflow 20 reached"))

    assert isinstance(mapped, ServiceOverloaded)
    assert mapped.code == "QIT000429"
    assert mapped.http_status == 503
    assert "Nada foi gravado" in mapped.translation


def test_database_out_of_reach_is_503_database_unavailable():
    mapped = map_unexpected_exception(sa_exc.OperationalError("SELECT 1", {}, ConnectionRefusedError("refused")))

    assert isinstance(mapped, DatabaseUnavailable)
    assert mapped.code == "QIT000503"
    assert mapped.http_status == 503
    assert "pode ter sido gravada" in mapped.translation


def test_query_cancelled_by_statement_timeout_is_504_operation_timeout():
    mapped = map_unexpected_exception(database_error(sa_exc.OperationalError, "57014"))

    assert isinstance(mapped, OperationTimeout)
    assert mapped.code == "QIT000504"
    assert mapped.http_status == 503


def test_unique_violation_nobody_handled_is_409_data_conflict():
    mapped = map_unexpected_exception(database_error(sa_exc.IntegrityError, "23505"))

    assert isinstance(mapped, DataConflict)
    assert mapped.code == "QIT000012"
    assert mapped.http_status == 409


def test_value_the_column_cannot_hold_is_422_data_out_of_range():
    mapped = map_unexpected_exception(database_error(sa_exc.DataError, "22003"))

    assert isinstance(mapped, DataOutOfRange)
    assert mapped.code == "QIT000013"
    assert mapped.http_status == 422
    assert "Nada foi gravado" in mapped.translation


def test_check_violation_is_a_bug_not_a_data_error():
    """CHECK, FK e NOT NULL querem dizer que o código deixou passar algo: é 500."""
    mapped = map_unexpected_exception(database_error(sa_exc.IntegrityError, "23514"), "req-123")

    assert isinstance(mapped, InternalError)
    assert mapped.code == "QIT000500"
    assert mapped.http_status == 500
    assert "req-123" in mapped.description


def test_unknown_error_is_500_with_the_request_id_to_search_the_log():
    mapped = map_unexpected_exception(ValueError("bug"), "req-456")

    assert isinstance(mapped, InternalError)
    assert mapped.code == "QIT000500"
    assert mapped.http_status == 500
    assert "req-456" in mapped.translation


@pytest.mark.parametrize("pgcode", ["55P03", "40P01", "40001"])
def test_busy_database_codes_are_409_resource_busy(pgcode):
    from errors import ResourceBusy

    mapped = map_unexpected_exception(database_error(sa_exc.OperationalError, pgcode))

    assert isinstance(mapped, ResourceBusy)
    assert mapped.code == "QIT000011"
    assert mapped.http_status == 409
