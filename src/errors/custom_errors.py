from errors import QIException
from utils.money import format_brl


def _attempts(remaining: int) -> str:
    if remaining == 1:
        return "Resta 1 tentativa"
    return f"Restam {remaining} tentativas"


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------


class NotFoundClient(QIException):
    code = "QIT001001"

    def __init__(self, client_key) -> None:
        title = "Client not Found"
        http_status = 404
        description = f"Client with key {client_key} was not found."
        translation = f"O cliente com chave {client_key} não foi encontrado."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidDocumentNumber(QIException):
    code = "QIT001002"

    def __init__(self, document_number, field: str = "document_number") -> None:
        title = "Invalid Document Number"
        http_status = 422
        description = f"The document number {document_number} in {field} is not a valid CPF (check digits do not match)."

        if field == "depositor_document_number":
            translation = "O CPF de quem depositou não é válido: os dígitos verificadores não batem."
        else:
            translation = "O CPF informado não é válido: os dígitos verificadores não batem."

        super().__init__(title, self.code, http_status, description, translation, field)


class DuplicatedDocumentNumber(QIException):
    code = "QIT001003"

    def __init__(self, document_number) -> None:
        title = "Document Number already registered"
        http_status = 409
        description = f"There is already a client with the document number {document_number}."
        translation = "Já existe um cadastro com este CPF (inclusive cadastros bloqueados na análise)."
        super().__init__(title, self.code, http_status, description, translation, "document_number")


class DuplicatedEmail(QIException):
    code = "QIT001004"

    def __init__(self, email) -> None:
        title = "Email already registered"
        http_status = 409
        description = f"There is already a client with the email {email}."
        translation = "Já existe um cadastro com este e-mail."
        super().__init__(title, self.code, http_status, description, translation, "email")


class UnderageClient(QIException):
    code = "QIT001005"

    def __init__(self, age, minimum_age) -> None:
        title = "Client is underage"
        http_status = 422
        description = f"The client is {age} years old, and the minimum is {minimum_age}."
        translation = f"É preciso ter pelo menos {minimum_age} anos; pela data de nascimento, o cliente tem {age}."
        super().__init__(title, self.code, http_status, description, translation, "birthdate")


class InvalidDate(QIException):
    code = "QIT001006"

    def __init__(self, field, value) -> None:
        title = "Invalid Date"
        http_status = 422
        description = f"The value {value} in {field} is not a real date."
        translation = f"A data informada em {field} ({value}) não existe no calendário."
        super().__init__(title, self.code, http_status, description, translation, field)


class IrregularDocumentNumber(QIException):
    code = "QIT001007"

    def __init__(self, document_number, situation) -> None:
        title = "Irregular Document Number"
        http_status = 422
        description = f"The document number {document_number} is not regular at Receita (situation: {situation})."
        translation = f"O CPF informado não está regular na Receita Federal (situação: {situation})."
        super().__init__(title, self.code, http_status, description, translation, "document_number")


class ClientBlocked(QIException):
    code = "QIT001008"

    def __init__(self, client_key) -> None:
        title = "Client is blocked"
        http_status = 409
        description = f"Client with key {client_key} was blocked in the registration analysis and cannot open an account."
        translation = "Este cliente foi bloqueado na análise de cadastro (restrição ou risco de fraude) e não pode abrir conta."
        super().__init__(title, self.code, http_status, description, translation)


class BirthdateInFuture(QIException):
    code = "QIT001050"

    def __init__(self, value) -> None:
        title = "Birthdate in the future"
        http_status = 422
        description = f"The birthdate {value} is in the future."
        translation = f"A data de nascimento ({value}) está no futuro."
        super().__init__(title, self.code, http_status, description, translation, "birthdate")


class ImplausibleBirthdate(QIException):
    code = "QIT001051"

    def __init__(self, value, maximum_age) -> None:
        title = "Implausible birthdate"
        http_status = 422
        description = f"The birthdate {value} means an age above {maximum_age} years."
        translation = f"A data de nascimento ({value}) daria mais de {maximum_age} anos. Confira o ano."
        super().__init__(title, self.code, http_status, description, translation, "birthdate")


# ---------------------------------------------------------------------------
# Receita e Serasa: cada falha diz o que aconteceu com o serviço. Em todas,
# nada foi gravado e o mesmo pedido pode ser repetido.
# ---------------------------------------------------------------------------


class ExternalServiceUnavailable(QIException):
    """O serviço não respondeu dentro do tempo limite."""

    code = "QIT001009"

    def __init__(self, service_name, timeout_seconds=None) -> None:
        title = "External Service Unavailable"
        http_status = 503

        limit = " in time"
        limite = " a tempo"
        if timeout_seconds is not None:
            limit = f" within {timeout_seconds} s"
            limite = f" em {timeout_seconds} s"

        description = f"The service {service_name} did not answer{limit}. Nothing was saved; the request can be retried."
        translation = f"O serviço {service_name} não respondeu{limite}. Nada foi gravado; tente de novo."
        super().__init__(title, self.code, http_status, description, translation)


class ExternalServiceUnreachable(QIException):
    """Não deu nem para conectar: serviço fora do ar, endereço errado ou nome que não resolve."""

    code = "QIT001040"

    def __init__(self, service_name) -> None:
        title = "External Service Unreachable"
        http_status = 503
        description = f"Could not connect to the service {service_name} (it is down or its address is wrong). Nothing was saved; the request can be retried."
        translation = f"Não foi possível conectar ao serviço {service_name}: ele está fora do ar ou o endereço configurado está errado. Nada foi gravado; tente de novo."
        super().__init__(title, self.code, http_status, description, translation)


class ExternalServiceError(QIException):
    """O serviço respondeu, mas com um status de erro (5xx ou inesperado)."""

    code = "QIT001041"

    def __init__(self, service_name, status_code) -> None:
        title = "External Service Error"
        http_status = 502
        description = f"The service {service_name} answered with HTTP {status_code}. Nothing was saved; the request can be retried."
        translation = f"O serviço {service_name} respondeu com erro (HTTP {status_code}). Nada foi gravado; tente de novo."
        super().__init__(title, self.code, http_status, description, translation)


class ExternalServiceInvalidResponse(QIException):
    """O serviço respondeu 200, mas sem o formato combinado (não é JSON, falta campo ou tipo errado)."""

    code = "QIT001042"

    def __init__(self, service_name, problem) -> None:
        title = "External Service Invalid Response"
        http_status = 502
        description = f"The service {service_name} answered in an unexpected format: {problem}. Nothing was saved."
        translation = f"O serviço {service_name} respondeu num formato inesperado ({problem}). Nada foi gravado."
        super().__init__(title, self.code, http_status, description, translation)


class ExternalServiceCredentialRejected(QIException):
    """O serviço recusou o token desta API: problema de configuração, não do cliente."""

    code = "QIT001043"

    def __init__(self, service_name, status_code) -> None:
        title = "External Service Credential Rejected"
        http_status = 502
        description = f"The service {service_name} rejected this API's credential (HTTP {status_code}). Check its INTERNAL-TOKEN."
        translation = f"O serviço {service_name} recusou a credencial desta API (HTTP {status_code}). É configuração: confira o token do serviço."
        super().__init__(title, self.code, http_status, description, translation)


class DocumentNotFoundAtReceita(QIException):
    code = "QIT001044"

    def __init__(self, document_number) -> None:
        title = "Document Number not found at Receita"
        http_status = 422
        description = f"The document number {document_number} does not exist at Receita."
        translation = "O CPF informado não existe na base da Receita Federal."
        super().__init__(title, self.code, http_status, description, translation, "document_number")


# ---------------------------------------------------------------------------
# Conta
# ---------------------------------------------------------------------------


class NotFoundAccount(QIException):
    code = "QIT001010"

    def __init__(self, account_key) -> None:
        title = "Account not Found"
        http_status = 404
        description = f"Account with key {account_key} was not found."
        translation = f"A conta com chave {account_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class ClientAlreadyHasAccount(QIException):
    code = "QIT001011"

    def __init__(self, client_key) -> None:
        title = "Client already has an account"
        http_status = 409
        description = f"Client with key {client_key} already has an account."
        translation = "Este cliente já tem uma conta (é uma conta por cliente)."
        super().__init__(title, self.code, http_status, description, translation)


BLOCKED_ACCOUNT_REASON = {
    "deposit": ("cannot receive deposits", "não pode receber depósitos"),
    "transfer": ("cannot send money", "não pode enviar dinheiro"),
    "pix": ("cannot send Pix", "não pode enviar Pix"),
    "create_pix_key": ("cannot register Pix keys", "não pode cadastrar chave Pix"),
}


class AccountBlocked(QIException):
    code = "QIT001012"

    def __init__(self, account_key, operation: str = None) -> None:
        title = "Account is blocked"
        http_status = 409

        reason_en, reason_pt = BLOCKED_ACCOUNT_REASON.get(operation, ("cannot operate", "não pode operar"))

        description = f"Account with key {account_key} is blocked and {reason_en}. It must be unblocked first."
        translation = f"A conta está bloqueada e {reason_pt}. É preciso desbloqueá-la antes."
        super().__init__(title, self.code, http_status, description, translation)


class WrongPassword(QIException):
    code = "QIT001013"

    def __init__(self, remaining_attempts) -> None:
        title = "Wrong password"
        http_status = 401
        description = f"The account password is wrong. {remaining_attempts} attempt(s) left before the account is blocked."
        translation = f"Senha incorreta. {_attempts(remaining_attempts)} antes do bloqueio da conta."
        super().__init__(title, self.code, http_status, description, translation, "password")


class AccountStatusUnchanged(QIException):
    code = "QIT001014"

    def __init__(self, account_key, status) -> None:
        title = "Nothing to change"
        http_status = 409
        description = f"Account with key {account_key} is already {status}."

        if status == "blocked":
            translation = "A conta já está bloqueada."
        else:
            translation = "A conta já está ativa."

        super().__init__(title, self.code, http_status, description, translation, "status")


class NotFoundDestinationAccount(QIException):
    code = "QIT001015"

    def __init__(self, account_key) -> None:
        title = "Destination account not Found"
        http_status = 404
        description = f"The destination account {account_key} was not found."
        translation = f"A conta de destino ({account_key}) não foi encontrada. Confira a chave da conta."
        super().__init__(title, self.code, http_status, description, translation, "destination_account_key")


class DestinationAccountBlocked(QIException):
    code = "QIT001016"

    def __init__(self, account_key) -> None:
        title = "Destination account is blocked"
        http_status = 409
        description = f"The destination account {account_key} is blocked and cannot receive money."
        translation = "A conta de destino está bloqueada e não pode receber dinheiro. Nada foi enviado."
        super().__init__(title, self.code, http_status, description, translation)


class AccountBlockedByPassword(QIException):
    code = "QIT001017"

    def __init__(self, account_key, max_attempts) -> None:
        title = "Account blocked after wrong passwords"
        http_status = 423
        description = f"Wrong password {max_attempts} times in a row: account {account_key} was blocked for security."
        translation = f"Senha incorreta pela {max_attempts}ª vez seguida: a conta foi bloqueada por segurança. Peça o desbloqueio ao back-office."
        super().__init__(title, self.code, http_status, description, translation, "password")


# ---------------------------------------------------------------------------
# Movimentação
# ---------------------------------------------------------------------------


class TransactionKeyConflict(QIException):
    code = "QIT001020"

    def __init__(self, transaction_key, existing_type=None, existing_amount=None) -> None:
        title = "Transaction key already used"
        http_status = 409
        description = f"The transaction key {transaction_key} was already used by an operation with different data."

        existing = ""
        if existing_type is not None and existing_amount is not None:
            existing = f" ({existing_type} de {format_brl(existing_amount)})"

        translation = (
            f"Este transaction_key já foi usado por outra operação{existing}, com outros dados. "
            "Para uma operação nova, gere um ID novo."
        )
        super().__init__(title, self.code, http_status, description, translation, "transaction_key")


class SameAccountTransfer(QIException):
    code = "QIT001021"

    def __init__(self, account_key) -> None:
        title = "Origin and destination are the same"
        http_status = 422
        description = f"Account {account_key} cannot send money to itself."
        translation = "A conta de origem e a de destino são a mesma: não dá para transferir para si mesmo."
        super().__init__(title, self.code, http_status, description, translation, "destination_account_key")


class InsufficientBalance(QIException):
    code = "QIT001022"

    def __init__(self, balance, amount, fee) -> None:
        title = "Insufficient balance"
        http_status = 422
        description = f"The balance {balance} does not cover the amount {amount} plus the fee {fee}."
        translation = (
            f"Saldo insuficiente: a operação precisa de {format_brl(amount + fee)} "
            f"({format_brl(amount)} + tarifa de {format_brl(fee)}), e o saldo é {format_brl(balance)}."
        )
        super().__init__(title, self.code, http_status, description, translation, "amount")


class DailyLimitExceeded(QIException):
    code = "QIT001023"

    def __init__(self, daily_limit, sent_today, amount) -> None:
        title = "Daily limit exceeded"
        http_status = 422
        description = (
            f"The daily outflow limit is {daily_limit}. Already sent today: {sent_today}; "
            f"this operation would add {amount}."
        )
        available = max(daily_limit - sent_today, 0)
        translation = (
            f"Esta operação passa do limite diário de saídas ({format_brl(daily_limit)}): "
            f"hoje já saíram {format_brl(sent_today)}, e ainda cabem {format_brl(available)}."
        )
        super().__init__(title, self.code, http_status, description, translation, "amount")


class IncomeLimitExceeded(QIException):
    code = "QIT001024"

    def __init__(self, alerts_per_month, amount=None, income_limit=None) -> None:
        title = "Outflow above income"
        http_status = 422
        description = (
            f"The amount is above the income rule and the account already had {alerts_per_month} "
            "income alerts this month. The account was blocked for analysis."
        )

        values = ""
        if amount is not None and income_limit is not None:
            values = f" ({format_brl(amount)}, acima de {format_brl(income_limit)})"

        translation = (
            f"Saída acima da renda{values} com a cota de {alerts_per_month} alertas do mês esgotada. "
            "A conta foi bloqueada para análise."
        )
        super().__init__(title, self.code, http_status, description, translation)


# ---------------------------------------------------------------------------
# Pix
# ---------------------------------------------------------------------------


class NotFoundPixKey(QIException):
    code = "QIT001030"

    def __init__(self, key_value) -> None:
        title = "Pix key not Found"
        http_status = 404
        description = f"The Pix key {key_value} was not found."
        translation = "A chave Pix informada não existe. Confira se foi digitada como foi cadastrada."
        super().__init__(title, self.code, http_status, description, translation, "pix_key")


class PixKeyAlreadyRegistered(QIException):
    code = "QIT001031"

    def __init__(self, key_value) -> None:
        title = "Pix key already registered"
        http_status = 409
        description = f"The Pix key {key_value} is already registered to another account."
        translation = "Esta chave Pix já está cadastrada em outra conta."
        super().__init__(title, self.code, http_status, description, translation, "key_value")


class PixKeyNotOwnDocument(QIException):
    code = "QIT001032"

    def __init__(self) -> None:
        title = "CPF key must be the owner's"
        http_status = 422
        description = "A Pix key of type cpf must be the CPF of the account owner."
        translation = "A chave do tipo CPF precisa ser o CPF do dono da conta."
        super().__init__(title, self.code, http_status, description, translation, "key_value")


class PixKeyLimitReached(QIException):
    code = "QIT001033"

    def __init__(self, limit) -> None:
        title = "Pix key limit reached"
        http_status = 422
        description = f"The account already has {limit} Pix keys, the maximum allowed."
        translation = f"A conta já tem {limit} chaves Pix, o máximo permitido."
        super().__init__(title, self.code, http_status, description, translation)


class PixToOwnAccount(QIException):
    code = "QIT001034"

    def __init__(self, key_value) -> None:
        title = "Pix key belongs to the origin account"
        http_status = 422
        description = f"The Pix key {key_value} belongs to the origin account itself."
        translation = "A chave Pix informada é da própria conta de origem: não dá para enviar Pix para si mesmo."
        super().__init__(title, self.code, http_status, description, translation, "pix_key")


class PixKeyAlreadyInThisAccount(QIException):
    code = "QIT001035"

    def __init__(self, key_value) -> None:
        title = "Pix key already in this account"
        http_status = 409
        description = f"The Pix key {key_value} is already registered to this same account."
        translation = "Esta chave Pix já está cadastrada nesta mesma conta."
        super().__init__(title, self.code, http_status, description, translation, "key_value")
