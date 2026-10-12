from contextvars import ContextVar
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from constants import (
    DATABASE_URL,
    DB_IDLE_IN_TRANSACTION_TIMEOUT_MS,
    DB_LOCK_TIMEOUT_MS,
    DB_MAX_OVERFLOW,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
    DB_STATEMENT_TIMEOUT_MS,
)

SERVER_SETTINGS = (
    f"-c lock_timeout={DB_LOCK_TIMEOUT_MS} "
    f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS} "
    f"-c idle_in_transaction_session_timeout={DB_IDLE_IN_TRANSACTION_TIMEOUT_MS}"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=600,
    pool_pre_ping=True,
    # Sem isto, todo erro do banco ia para o log com os parâmetros da
    # consulta: CPF, e-mail, nome e até o hash da senha.
    hide_parameters=True,
    connect_args={"options": SERVER_SETTINGS},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Context:
    def __init__(self) -> None:
        self.db_session: Optional[Session] = None

    def get_or_create_session(self) -> Session:
        if self.db_session is None:
            self.db_session = SessionLocal()

        return self.db_session


_context: ContextVar[Optional[Context]] = ContextVar("context", default=None)


def open_context() -> Context:
    context = Context()
    _context.set(context)

    return context


def clear_context() -> None:
    _context.set(None)


def get_context() -> Context:
    context = _context.get()

    if context is None:
        raise Exception(
            "Nao existe contexto neste trabalho. "
            + "Quem prepara o contexto de cada requisicao e o middleware "
            + "src/middlewares/session_manager.py. Se voce chegou aqui, ele nao rodou."
        )

    return context
