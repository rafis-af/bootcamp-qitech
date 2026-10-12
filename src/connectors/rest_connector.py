import json
import time
from abc import ABCMeta

import requests

from errors import ExternalServiceUnavailable, ExternalServiceUnreachable
from utils.logger import get_logger


class RestConnector(metaclass=ABCMeta):
    def __init__(self, class_name: str, service_name: str, base_url: str, timeout: int, internal_token: str) -> None:
        self.logger = get_logger(class_name)
        self.service_name = service_name
        self.base_url = base_url
        self.timeout = timeout
        self.internal_token = internal_token

    def send(self, endpoint: str, method: str, payload: dict = None, headers: dict = None):
        if headers is None:
            headers = {}

        headers["INTERNAL-TOKEN"] = self.internal_token

        url = f"{self.base_url}{endpoint}"

        self.logger.info(f"OUTGOING REQUEST {method} {url}")
        started_at = time.perf_counter()

        try:
            response = requests.request(
                method.upper(),
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as error:
            # Conectou (ou tentou) e o serviço não respondeu dentro do timeout.
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            self.logger.error(f"TIMEOUT {method} {url} - {elapsed_ms:.1f} ms - {type(error).__name__}")
            raise ExternalServiceUnavailable(self.service_name, self.timeout)
        except requests.exceptions.RequestException as error:
            # Nem conectou: serviço fora do ar, porta fechada, nome que não
            # resolve ou URL mal configurada. Responde na hora, sem esperar
            # o timeout, e a mensagem não finge que foi demora.
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            self.logger.error(f"NO CONNECTION {method} {url} - {elapsed_ms:.1f} ms - {type(error).__name__}: {error}")
            raise ExternalServiceUnreachable(self.service_name)

        elapsed_ms = (time.perf_counter() - started_at) * 1000
        self.logger.info(f"INCOMING RESPONSE {response.status_code} {method} {url} - {elapsed_ms:.1f} ms")

        return BaseConnectorResponse(endpoint, method, response)


class BaseConnectorResponse:
    def __init__(self, endpoint: str, method: str, response: requests.Response) -> None:
        self.endpoint = endpoint
        self.method = method
        self.status = response.status_code

        self.json = None
        try:
            self.json = json.loads(response.content)
        except ValueError:
            pass
