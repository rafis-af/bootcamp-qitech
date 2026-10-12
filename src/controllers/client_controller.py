from datetime import date

from sqlalchemy.exc import IntegrityError

from connectors import ReceitaConnector, SerasaConnector
from controllers.base_controller import BaseController
from dtos import ClientDTO
from errors import (
    BirthdateInFuture,
    DocumentNotFoundAtReceita,
    DuplicatedDocumentNumber,
    DuplicatedEmail,
    ExternalServiceCredentialRejected,
    ExternalServiceError,
    ExternalServiceInvalidResponse,
    ImplausibleBirthdate,
    InvalidDocumentNumber,
    IrregularDocumentNumber,
    NotFoundClient,
    UnderageClient,
)
from models import Event, Level, Status
from repositories import CatalogRepository, ClientRepository, EventRepository
from utils import clock
from utils.document_number import is_valid_cpf

MINIMUM_AGE = 18
MAXIMUM_AGE = 130

MINIMUM_GOLD_SCORE = 600

REGULAR_SITUATION = "REGULAR"
HIGH_FRAUD_RISK = "HIGH"
SERASA_REQUIRED_FIELDS = ["has_restriction", "fraud_risk", "score", "has_late_payments"]

CREDENTIAL_REJECTED_STATUSES = {401, 403}

BLOCKED_BY_RESTRICTION = "restriction"
BLOCKED_BY_FRAUD_RISK = "fraud_risk"


class ClientController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.client_repository = ClientRepository(self.context)
        self.catalog_repository = CatalogRepository(self.context)
        self.event_repository = EventRepository(self.context)
        self.receita_connector = ReceitaConnector()
        self.serasa_connector = SerasaConnector()

    def create(self, client_data: dict) -> dict:
        self.logger.debug("Cadastrando um novo cliente")

        document_number = client_data["document_number"]

        email = client_data["email"].lower()
        birthdate = clock.parse_date("birthdate", client_data["birthdate"])

        if not is_valid_cpf(document_number):
            raise InvalidDocumentNumber(document_number)

        if self.client_repository.get_by_document_number(document_number) is not None:
            raise DuplicatedDocumentNumber(document_number)

        if self.client_repository.get_by_email(email) is not None:
            raise DuplicatedEmail(email)

        if birthdate > clock.today():
            raise BirthdateInFuture(client_data["birthdate"])

        age = self._age_in_years(birthdate)

        if age < MINIMUM_AGE:
            raise UnderageClient(age, MINIMUM_AGE)

        if age > MAXIMUM_AGE:
            raise ImplausibleBirthdate(client_data["birthdate"], MAXIMUM_AGE)

        # Daqui para a frente vêm Receita e Serasa, que podem levar até o
        # timeout cada uma. Encerrar a transação de leitura devolve a conexão
        # ao pool durante a espera: antes, cada cadastro lento segurava uma
        # conexão parada, e 15 cadastros juntos travavam a API inteira.
        # A duplicidade continua garantida pelo UNIQUE na hora de gravar.
        self.session.rollback()

        situation = self._consult_receita(document_number)

        if situation != REGULAR_SITUATION:
            raise IrregularDocumentNumber(document_number, situation)

        credit_report = self._consult_serasa(document_number)

        classification = {"receita_situation": situation}
        classification.update(credit_report)

        blocking_reason = self._blocking_reason(credit_report)

        if blocking_reason is not None:
            status = self.catalog_repository.get_status(Status.BLOCKED)
            level = None
            event_type = Event.CLIENT_BLOCKED
            severity = Event.WARNING
            classification["reason"] = blocking_reason
        else:
            status = self.catalog_repository.get_status(Status.ACTIVE)
            level = self.catalog_repository.get_level(self._classify(credit_report))
            event_type = Event.CLIENT_REGISTERED
            severity = Event.INFO
            classification["level"] = level.enumerator

        new_client_data = {
            "name": client_data["name"].strip(),
            "email": email,
            "document_number": document_number,
            "birthdate": birthdate,
            "monthly_income": int(client_data["monthly_income"]),
        }

        client = self.client_repository.create(new_client_data, status, level)
        self.event_repository.create(event_type, severity, client=client, detail=classification)

        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()

            if self.client_repository.get_by_document_number(document_number) is not None:
                raise DuplicatedDocumentNumber(document_number)

            if self.client_repository.get_by_email(email) is not None:
                raise DuplicatedEmail(email)

            raise

        client_dto = ClientDTO.obj_to_dict(client)
        self.session.commit()

        return client_dto

    def get_by_key(self, client_key: str) -> dict:
        self.logger.debug(f"Buscando o cliente de chave {client_key}")

        client = self.client_repository.get_by_key(client_key)

        if client is None:
            raise NotFoundClient(client_key)

        return ClientDTO.obj_to_dict(client)

    def get_list(self, limit: int, offset: int, filters: dict) -> dict:
        clients_list = self.client_repository.list_page(limit, offset, filters)

        is_last_page = True
        if len(clients_list) > limit:
            is_last_page = False
            clients_list = clients_list[:-1]

        return {
            "clients_list_dto": ClientDTO.list_obj_to_list_dict(clients_list),
            "is_last_page": is_last_page,
        }

    def _consult_receita(self, document_number: str) -> str:
        response = self.receita_connector.get_document_situation(document_number)
        service_name = self.receita_connector.service_name

        if response.status == 404:
            raise DocumentNotFoundAtReceita(document_number)

        self._check_service_answer(service_name, response)

        situation = response.json.get("situation")
        if not isinstance(situation, str) or not situation:
            raise ExternalServiceInvalidResponse(service_name, "campo situation ausente ou vazio")

        return situation

    def _consult_serasa(self, document_number: str) -> dict:
        response = self.serasa_connector.get_credit_report(document_number)
        service_name = self.serasa_connector.service_name

        self._check_service_answer(service_name, response)

        for field in SERASA_REQUIRED_FIELDS:
            if field not in response.json:
                raise ExternalServiceInvalidResponse(service_name, f"campo {field} ausente")

        score = response.json["score"]
        if score is not None and (isinstance(score, bool) or not isinstance(score, int)):
            raise ExternalServiceInvalidResponse(service_name, "campo score não é um número inteiro")

        if not isinstance(response.json["fraud_risk"], str):
            raise ExternalServiceInvalidResponse(service_name, "campo fraud_risk não é texto")

        return {
            "has_restriction": bool(response.json["has_restriction"]),
            "fraud_risk": response.json["fraud_risk"],
            "score": response.json["score"],
            "has_late_payments": bool(response.json["has_late_payments"]),
        }

    def _check_service_answer(self, service_name: str, response) -> None:
        if response.status in CREDENTIAL_REJECTED_STATUSES:
            raise ExternalServiceCredentialRejected(service_name, response.status)

        if response.status != 200:
            raise ExternalServiceError(service_name, response.status)

        if not isinstance(response.json, dict):
            raise ExternalServiceInvalidResponse(service_name, "a resposta não é um objeto JSON")

    def _blocking_reason(self, credit_report: dict):
        if credit_report["has_restriction"]:
            return BLOCKED_BY_RESTRICTION

        if credit_report["fraud_risk"] == HIGH_FRAUD_RISK:
            return BLOCKED_BY_FRAUD_RISK

        return None

    def _classify(self, credit_report: dict) -> str:
        score = credit_report["score"]

        if score is not None and score >= MINIMUM_GOLD_SCORE and not credit_report["has_late_payments"]:
            return Level.GOLD

        return Level.SILVER

    def _age_in_years(self, birthdate: date) -> int:
        today = clock.today()
        age = today.year - birthdate.year

        if (today.month, today.day) < (birthdate.month, birthdate.day):
            age = age - 1

        return age
