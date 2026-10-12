from typing import Optional
from uuid import uuid4

from database import Context
from models import Client, Level, Status


class ClientRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, client_data: dict, status: Status, level: Optional[Level]) -> Client:
        client = Client()

        client.client_key = str(uuid4())
        client.name = client_data["name"]
        client.email = client_data["email"]
        client.document_number = client_data["document_number"]
        client.birthdate = client_data["birthdate"]
        client.monthly_income = client_data["monthly_income"]
        client.status = status
        client.level = level

        self.session.add(client)
        return client

    def get_by_key(self, client_key: str) -> Optional[Client]:
        return self.session.query(Client).filter(Client.client_key == client_key.lower()).first()

    def get_by_document_number(self, document_number: str) -> Optional[Client]:
        return self.session.query(Client).filter(Client.document_number == document_number).first()

    def get_by_email(self, email: str) -> Optional[Client]:
        return self.session.query(Client).filter(Client.email == email).first()

    def list_page(self, limit: int, offset: int, filters: dict) -> list:
        query = self.session.query(Client)

        status_enumerators = filters.get("status_enumerators")
        if status_enumerators:
            query = query.join(Client.status).filter(Status.enumerator.in_(status_enumerators))

        level_enumerators = filters.get("level_enumerators")
        if level_enumerators:
            query = query.join(Client.level).filter(Level.enumerator.in_(level_enumerators))

        name = filters.get("name")
        if name is not None:
            # % e _ são curingas do LIKE: sem o escape, buscar "100%" ou "a_b"
            # trazia nomes que não têm esses caracteres.
            escaped_name = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.filter(Client.name.ilike(f"%{escaped_name}%", escape="\\"))

        email = filters.get("email")
        if email is not None:
            # O cadastro guarda o e-mail em minúsculas; o filtro precisa fazer igual.
            query = query.filter(Client.email == email.lower())

        document_number = filters.get("document_number")
        if document_number is not None:
            query = query.filter(Client.document_number == document_number)

        query = query.order_by(Client.created_at.desc(), Client.id.desc())

        return query.limit(limit + 1).offset(offset).all()
