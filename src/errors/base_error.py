import sys
import inspect


def error_verification():
    clsmembers = inspect.getmembers(sys.modules["errors"], inspect.isclass)

    errors_dict = dict()
    for _class in clsmembers:
        class_name = _class[0]
        class_type = _class[1]
        is_custom_exception = False
        if issubclass(class_type, QIException) and class_name != "QIException":
            is_custom_exception = True

        if is_custom_exception:
            code = class_type.code
            if errors_dict.get(code) is not None:
                used_class_name = errors_dict[code]
                raise Exception(f"The code {code} is being used twice: In {class_name} and {used_class_name}")
            errors_dict[code] = class_name
    return


class QIException(Exception):
    """Todo erro que a API devolve de propósito.

    `description` vai em inglês e `translation` em português, como na base.
    `field` é opcional: quando o erro é de um campo só (do corpo ou da
    query), ele sai na resposta para quem chamou saber qual corrigir.
    """

    def __init__(self, title, code, http_status, description, translation, field=None) -> None:
        super().__init__(description)
        self.title = title
        self.description = description
        self.translation = translation
        self.code = code
        self.http_status = http_status
        self.field = field


class MethodNotAllowed(QIException):
    code = "QIT000405"

    def __init__(self, method: str = None, path: str = None, allowed_methods: list = None) -> None:
        title = "Method not allowed"
        http_status = 405

        if method is None or path is None:
            description = "The requested method is forbidden for this resource."
            translation = "O método desejado não foi encontrado para esse recurso."
        else:
            allowed = ", ".join(allowed_methods or []) or "nenhum"
            description = f"The route {path} does not accept {method}. Allowed: {allowed}."
            translation = f"A rota {path} não aceita {method}. Métodos aceitos: {allowed}."

        super().__init__(title, self.code, http_status, description, translation)


class InternalError(QIException):
    code = "QIT000500"

    def __init__(self, request_id: str = None) -> None:
        title = "Internal Error"
        http_status = 500
        description = "An internal error has occurred and its being investigated."
        translation = "Um erro interno aconteceu e está sendo investigado."

        if request_id:
            description = f"{description} Request id: {request_id}."
            translation = f"{translation} Informe o código {request_id} ao suporte."

        super().__init__(title, self.code, http_status, description, translation)


class NotFoundResource(QIException):
    code = "QIT000404"

    def __init__(self, method: str = None, path: str = None) -> None:
        title = "Resource not Found"
        http_status = 404

        if method is None or path is None:
            description = "The requested resource could not be found but may be available in the future. Subsequent requests by the client are permissible."
            translation = "O resource solicitado não pode ser encontrado, mas pode estar disponível no futuro. Requests subsequentes do cliente são permitidos."
        else:
            description = f"The route {method} {path} does not exist in this API."
            translation = f"A rota {method} {path} não existe nesta API. Confira o caminho e o método."

        super().__init__(title, self.code, http_status, description, translation)


class InvalidSchema(QIException):
    code = "QIT000001"

    def __init__(self, __description, translation: str = None, field: str = None) -> None:
        title = "Bad Request"
        http_status = 400
        description = __description

        if translation is None:
            translation = "Payload Inválido"

        super().__init__(title, self.code, http_status, description, translation, field)


class ForbiddenNotInternal(QIException):
    code = "QIT000002"

    def __init__(self, token_was_sent: bool = True) -> None:
        title = "Forbidden"
        http_status = 403

        if token_was_sent:
            description = "Request must be internal: the INTERNAL-TOKEN header is wrong."
            translation = "Requisição precisa ser interna: o header INTERNAL-TOKEN enviado está errado."
        else:
            description = "Request must be internal: the INTERNAL-TOKEN header is missing."
            translation = "Requisição precisa ser interna: falta o header INTERNAL-TOKEN."

        super().__init__(title, self.code, http_status, description, translation)


class InvalidJson(QIException):
    code = "QIT000003"

    def __init__(self, position=None) -> None:
        title = "Invalid JSON"
        http_status = 400

        where = ""
        onde = ""
        if position is not None:
            where = f" near position {position}"
            onde = f" (erro perto da posição {position})"

        description = f"The request body is not valid JSON{where}."
        translation = f"O corpo da requisição não é um JSON válido{onde}. Confira aspas, vírgulas e chaves."
        super().__init__(title, self.code, http_status, description, translation)


class MissingBody(QIException):
    code = "QIT000004"

    def __init__(self) -> None:
        title = "Missing body"
        http_status = 400
        description = "This route needs a JSON body, and none was sent."
        translation = "Esta rota precisa de um corpo em JSON, e nenhum foi enviado."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidBodyType(QIException):
    code = "QIT000005"

    def __init__(self) -> None:
        title = "Body must be a JSON object"
        http_status = 400
        description = "The request body must be a JSON object ({...}), not a list, text or number."
        translation = "O corpo da requisição precisa ser um objeto JSON ({...}), não uma lista, texto ou número."
        super().__init__(title, self.code, http_status, description, translation)


class UnsupportedMediaType(QIException):
    code = "QIT000006"

    def __init__(self) -> None:
        title = "Unsupported media type"
        http_status = 415
        description = "The request body must be sent with Content-Type: application/json."
        translation = "O corpo da requisição precisa ser enviado com o header Content-Type: application/json."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidParameter(QIException):
    code = "QIT000010"

    def __init__(self, description, translation: str = None, field: str = None) -> None:
        title = "Invalid Parameter"
        http_status = 400

        if translation is None:
            translation = "Parâmetros inválidos foram fornecidos na requisição."

        super().__init__(title, self.code, http_status, description, translation, field)


# ---------------------------------------------------------------------------
# Erros de infraestrutura: o pedido estava certo, mas algo por baixo falhou.
# Cada um diz o que houve e se dá para tentar de novo. Nenhum grava nada:
# a transação do banco é desfeita antes da resposta.
# ---------------------------------------------------------------------------


class ResourceBusy(QIException):
    code = "QIT000011"

    def __init__(self) -> None:
        title = "Resource busy"
        http_status = 409
        description = "Another operation is using the same account right now. Nothing was saved; retry in a moment."
        translation = "Outra operação está usando a mesma conta agora. Nada foi gravado; tente de novo em instantes."
        super().__init__(title, self.code, http_status, description, translation)


class DataConflict(QIException):
    code = "QIT000012"

    def __init__(self) -> None:
        title = "Data conflict"
        http_status = 409
        description = "The data conflicts with a record that already exists. Nothing was saved."
        translation = "Os dados conflitam com um registro que já existe. Nada foi gravado."
        super().__init__(title, self.code, http_status, description, translation)


class DataOutOfRange(QIException):
    code = "QIT000013"

    def __init__(self) -> None:
        title = "Value out of range"
        http_status = 422
        description = "A value is outside what the database accepts (too large or in an invalid format). Nothing was saved."
        translation = "Um dos valores está fora do que o banco aceita (grande demais ou em formato inválido). Nada foi gravado."
        super().__init__(title, self.code, http_status, description, translation)


class ServiceOverloaded(QIException):
    code = "QIT000429"

    def __init__(self) -> None:
        title = "Service overloaded"
        http_status = 503
        description = "All database connections are busy. Nothing was saved; retry in a few seconds."
        translation = "Todas as conexões com o banco estão ocupadas. Nada foi gravado; tente de novo em alguns segundos."
        super().__init__(title, self.code, http_status, description, translation)


class DatabaseUnavailable(QIException):
    code = "QIT000503"

    def __init__(self) -> None:
        title = "Database unavailable"
        http_status = 503
        description = (
            "The database is unavailable right now. If it failed while saving, the operation may or may not have been "
            "saved: check before retrying (retrying with the same transaction_key is always safe)."
        )
        translation = (
            "O banco de dados está fora do ar agora. Se a falha foi na hora de gravar, a operação pode ter sido gravada "
            "ou não: confira antes de repetir (com o mesmo transaction_key, repetir é sempre seguro)."
        )
        super().__init__(title, self.code, http_status, description, translation)


class OperationTimeout(QIException):
    code = "QIT000504"

    def __init__(self) -> None:
        title = "Operation timeout"
        http_status = 503
        description = "The operation took too long in the database and was canceled. Nothing was saved; retry."
        translation = "A operação demorou demais no banco e foi cancelada. Nada foi gravado; tente de novo."
        super().__init__(title, self.code, http_status, description, translation)
