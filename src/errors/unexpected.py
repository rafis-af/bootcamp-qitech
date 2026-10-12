"""Traduz o erro que ninguém levantou de propósito num erro com nome.

O controller só levanta QIException. Tudo o que chega aqui veio de baixo:
do banco, do pool de conexões ou de um bug. Antes, tudo virava o mesmo
500 "erro interno"; agora o banco fora do ar, a conta travada por outra
operação e o pool esgotado têm cada um a sua resposta, e só o que é bug
de verdade continua sendo 500.
"""
from sqlalchemy import exc as sa_exc

from errors.base_error import (
    DataConflict,
    DataOutOfRange,
    DatabaseUnavailable,
    InternalError,
    OperationTimeout,
    QIException,
    ResourceBusy,
    ServiceOverloaded,
)

# Códigos do PostgreSQL (SQLSTATE) que têm resposta própria.
LOCK_NOT_AVAILABLE = "55P03"       # lock_timeout: outra transação segurou a linha tempo demais
DEADLOCK_DETECTED = "40P01"
SERIALIZATION_FAILURE = "40001"
QUERY_CANCELED = "57014"           # statement_timeout
UNIQUE_VIOLATION = "23505"         # o único IntegrityError que é "já existe"; CHECK, FK e NOT NULL são bug

BUSY_CODES = {LOCK_NOT_AVAILABLE, DEADLOCK_DETECTED, SERIALIZATION_FAILURE}


def postgres_code(error: Exception):
    return getattr(getattr(error, "orig", None), "pgcode", None)


def map_unexpected_exception(error: Exception, request_id: str = None) -> QIException:
    if isinstance(error, QIException):
        return error

    # O pool não tinha conexão livre dentro do pool_timeout.
    if isinstance(error, sa_exc.TimeoutError):
        return ServiceOverloaded()

    code = postgres_code(error)

    if code in BUSY_CODES:
        return ResourceBusy()

    if code == QUERY_CANCELED:
        return OperationTimeout()

    if isinstance(error, sa_exc.IntegrityError):
        if code == UNIQUE_VIOLATION:
            return DataConflict()
        return InternalError(request_id)

    if isinstance(error, sa_exc.DataError):
        return DataOutOfRange()

    # Conexão recusada, caiu no meio, servidor reiniciando...
    if isinstance(error, (sa_exc.OperationalError, sa_exc.InterfaceError, sa_exc.DisconnectionError)):
        return DatabaseUnavailable()

    return InternalError(request_id)


def is_bug(mapped: QIException) -> bool:
    """InternalError é bug; DataOutOfRange também merece o traceback, porque
    o schema deveria ter barrado o valor antes. O resto é infraestrutura."""
    return isinstance(mapped, (InternalError, DataOutOfRange))
