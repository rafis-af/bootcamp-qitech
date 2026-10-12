import pytest

from connectors import ReceitaConnector
from errors import ExternalServiceUnreachable

NOTHING_LISTENS_HERE = "http://127.0.0.1:1/receita"


def test_service_that_cannot_be_connected_is_1040_and_answers_at_once():
    """Porta fechada: não é demora (1009), é conexão recusada. A resposta sai na hora."""
    connector = ReceitaConnector()
    connector.base_url = NOTHING_LISTENS_HERE

    with pytest.raises(ExternalServiceUnreachable) as caught:
        connector.get_document_situation("52998224725")

    error = caught.value
    assert error.code == "QIT001040"
    assert error.http_status == 503
    assert "Receita" in error.translation
    assert "Nada foi gravado" in error.translation
