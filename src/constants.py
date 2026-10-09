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
