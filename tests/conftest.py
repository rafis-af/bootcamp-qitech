import tempfile
from pathlib import Path
from os import path, environ

import pytest

try:
    import fcntl
except ImportError:
    fcntl = None

root = Path(__file__).resolve().parents[1]

if not environ.get("APP_ENV") or environ.get("APP_ENV") == "local":
    from dotenv import load_dotenv

    load_dotenv(path.join(str(root), ".env"))

    # "localhost" e nao "0.0.0.0": no Windows, 0.0.0.0 nao aceita conexao.
    if environ.get("SERVER_LOCALHOST") is None:
        environ["SERVER_LOCALHOST"] = "localhost"


LOCK_DIRECTORY = Path(tempfile.gettempdir())
GATE_FILE = LOCK_DIRECTORY / "bootcamp-api-tests.gate"
RUNNING_FILE = LOCK_DIRECTORY / "bootcamp-api-tests.running"


@pytest.fixture(autouse=True)
def run_exclusive_tests_alone(request):
    """Os testes rodam em paralelo (pytest-xdist, veja o pytest.ini). Quase
    todos podem, porque cada um cria e olha só os próprios dados.

    A exceção é quem muda um dado que TODOS enxergam — a tarifa, por
    exemplo: enquanto o teste de tarifa roda, uma transferência de outro
    teste pagaria a tarifa errada. Esse teste leva a marca `exclusive`, e
    esta trava faz ele rodar sozinho:

    • teste comum: entra junto com os outros (trava compartilhada);
    • teste `exclusive`: fecha a porta para quem ainda vai começar, espera
      os que já estão rodando terminarem, roda, e abre a porta de novo.

    A trava é um arquivo, porque cada worker do xdist é um processo
    separado. No Windows não existe `fcntl`; lá a trava não faz nada, e é
    preciso rodar sem paralelismo (pytest -n 0).
    """
    if fcntl is None:
        yield
        return

    exclusive = request.node.get_closest_marker("exclusive") is not None

    with open(GATE_FILE, "a") as gate, open(RUNNING_FILE, "a") as running:
        fcntl.flock(gate, fcntl.LOCK_EX)

        if exclusive:
            fcntl.flock(running, fcntl.LOCK_EX)
        else:
            fcntl.flock(gate, fcntl.LOCK_UN)
            fcntl.flock(running, fcntl.LOCK_SH)

        try:
            yield
        finally:
            fcntl.flock(running, fcntl.LOCK_UN)
            fcntl.flock(gate, fcntl.LOCK_UN)
