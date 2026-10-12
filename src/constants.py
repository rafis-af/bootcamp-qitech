import os

SERVICE_ROOT = os.path.abspath(os.path.dirname(__file__))

SCHEMA_PATH = os.path.join(SERVICE_ROOT, "schemas")

APP_ENV = os.environ.get("APP_ENV", "local")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "bootcamp-api")

DATABASE_URL = os.environ.get("DATABASE_URL")
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN")

RECEITA_API_URL = os.environ.get("RECEITA_API_URL", "http://localhost:8080/receita")
RECEITA_API_INTERNAL_TOKEN = os.environ.get("RECEITA_API_INTERNAL_TOKEN", "default_token")

SERASA_API_URL = os.environ.get("SERASA_API_URL", "http://localhost:8080/serasa")
SERASA_API_INTERNAL_TOKEN = os.environ.get("SERASA_API_INTERNAL_TOKEN", "default_token")

RECEITA_API_TIMEOUT = int(os.environ.get("RECEITA_API_TIMEOUT", "5"))
SERASA_API_TIMEOUT = int(os.environ.get("SERASA_API_TIMEOUT", "5"))

# Pool de conexões com o banco. O padrão antigo (5 + 10 extras) ficava
# abaixo das 40 threads que o uvicorn usa para rotas síncronas: com pico
# de requisições, as threads sobravam e ficavam esperando conexão.
DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "20"))
# Quanto tempo uma requisição espera por uma conexão livre antes de
# desistir com 503 (ServiceOverloaded), em vez de ficar presa.
DB_POOL_TIMEOUT = int(os.environ.get("DB_POOL_TIMEOUT", "10"))

# Limites dentro do PostgreSQL, em milissegundos:
# - lock_timeout: quanto uma operação espera a trava de uma conta que outra
#   está usando. Sem ele, uma transação presa segurava a fila para sempre.
# - statement_timeout: teto para qualquer consulta.
# - idle_in_transaction_session_timeout: derruba transação aberta e parada.
DB_LOCK_TIMEOUT_MS = int(os.environ.get("DB_LOCK_TIMEOUT_MS", "5000"))
DB_STATEMENT_TIMEOUT_MS = int(os.environ.get("DB_STATEMENT_TIMEOUT_MS", "15000"))
DB_IDLE_IN_TRANSACTION_TIMEOUT_MS = int(os.environ.get("DB_IDLE_IN_TRANSACTION_TIMEOUT_MS", "30000"))

DEFAULT_LIMIT = 10
DEFAULT_PAGE = 0

BYPASS_ENDPOINTS = [
    "/",
    "/health_check",
]

REQUIRED_VARIABLES = ["DATABASE_URL", "INTERNAL_TOKEN"]


def check_variables():
    missing = []
    for name in REQUIRED_VARIABLES:
        if not globals().get(name):
            missing.append(name)

    if missing:
        raise EnvironmentError(
            f"Faltam variáveis de ambiente: {', '.join(missing)}. "
            "Rodando com 'docker compose up' elas já vêm preenchidas. "
            "Fora do Docker, copie o .env.example para .env."
        )
