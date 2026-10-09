from errors import QIException


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

    def __init__(self, document_number) -> None:
        title = "Invalid Document Number"
        http_status = 422
        description = f"The document number {document_number} is not a valid CPF."
        translation = "O CPF informado não é válido."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedDocumentNumber(QIException):
    code = "QIT001003"

    def __init__(self, document_number) -> None:
        title = "Document Number already registered"
        http_status = 409
        description = f"There is already a client with the document number {document_number}."
        translation = "Já existe um cadastro com este CPF."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedEmail(QIException):
    code = "QIT001004"

    def __init__(self, email) -> None:
        title = "Email already registered"
        http_status = 409
        description = f"There is already a client with the email {email}."
        translation = "Já existe um cadastro com este e-mail."
        super().__init__(title, self.code, http_status, description, translation)


class UnderageClient(QIException):
    code = "QIT001005"

    def __init__(self, age, minimum_age) -> None:
        title = "Client is underage"
        http_status = 422
        description = f"The client is {age} years old, and the minimum is {minimum_age}."
        translation = f"É preciso ter pelo menos {minimum_age} anos."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidDate(QIException):
    code = "QIT001006"

    def __init__(self, field, value) -> None:
        title = "Invalid Date"
        http_status = 422
        description = f"The value {value} in {field} is not a real date."
        translation = f"A data informada em {field} não existe."
        super().__init__(title, self.code, http_status, description, translation)


class IrregularDocumentNumber(QIException):
    code = "QIT001007"

    def __init__(self, document_number, situation) -> None:
        title = "Irregular Document Number"
        http_status = 422
        description = f"The document number {document_number} is not regular at Receita (situation: {situation})."
        translation = "O CPF informado não está regular na Receita Federal."
        super().__init__(title, self.code, http_status, description, translation)


class ClientBlocked(QIException):
    code = "QIT001008"

    def __init__(self, client_key) -> None:
        title = "Client is blocked"
        http_status = 409
        description = f"Client with key {client_key} is blocked and cannot open an account."
        translation = "Este cliente está bloqueado e não pode abrir conta."
        super().__init__(title, self.code, http_status, description, translation)


class ExternalServiceUnavailable(QIException):
    code = "QIT001009"

    def __init__(self, service_name) -> None:
        title = "External Service Unavailable"
        http_status = 503
        description = f"The service {service_name} did not answer in time. Nothing was saved; the request can be retried."
        translation = f"O serviço {service_name} não respondeu a tempo. Nada foi gravado; tente de novo."
        super().__init__(title, self.code, http_status, description, translation)


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
        translation = "Este cliente já tem uma conta."
        super().__init__(title, self.code, http_status, description, translation)


class AccountBlocked(QIException):
    code = "QIT001012"

    def __init__(self, account_key) -> None:
        title = "Account is blocked"
        http_status = 409
        description = f"Account with key {account_key} is blocked."
        translation = "A conta está bloqueada."
        super().__init__(title, self.code, http_status, description, translation)


class WrongPassword(QIException):
    code = "QIT001013"

    def __init__(self, remaining_attempts) -> None:
        title = "Wrong password"
        http_status = 401
        description = f"The account password is wrong. {remaining_attempts} attempt(s) left before the account is blocked."
        translation = f"Senha incorreta. Restam {remaining_attempts} tentativa(s) antes do bloqueio da conta."
        super().__init__(title, self.code, http_status, description, translation)


class AccountStatusUnchanged(QIException):
    code = "QIT001014"

    def __init__(self, account_key, status) -> None:
        title = "Nothing to change"
        http_status = 409
        description = f"Account with key {account_key} is already {status}."
        translation = "A conta já está nesse status."
        super().__init__(title, self.code, http_status, description, translation)


class TransactionKeyConflict(QIException):
    code = "QIT001020"

    def __init__(self, transaction_key) -> None:
        title = "Transaction key already used"
        http_status = 409
        description = f"The transaction key {transaction_key} was already used by an operation with different data."
        translation = "Este ID de operação já foi usado por outra operação, com outros dados."
        super().__init__(title, self.code, http_status, description, translation)


class SameAccountTransfer(QIException):
    code = "QIT001021"

    def __init__(self, account_key) -> None:
        title = "Origin and destination are the same"
        http_status = 422
        description = f"Account {account_key} cannot send money to itself."
        translation = "A conta de origem e a de destino são a mesma."
        super().__init__(title, self.code, http_status, description, translation)


class InsufficientBalance(QIException):
    code = "QIT001022"

    def __init__(self, balance, amount, fee) -> None:
        title = "Insufficient balance"
        http_status = 422
        description = f"The balance {balance} does not cover the amount {amount} plus the fee {fee}."
        translation = "Saldo insuficiente para o valor mais a tarifa."
        super().__init__(title, self.code, http_status, description, translation)


class DailyLimitExceeded(QIException):
    code = "QIT001023"

    def __init__(self, daily_limit, sent_today, amount) -> None:
        title = "Daily limit exceeded"
        http_status = 422
        description = (
            f"The daily outflow limit is {daily_limit}. Already sent today: {sent_today}; "
            f"this operation would add {amount}."
        )
        translation = "Esta operação passa do limite diário de saídas da conta."
        super().__init__(title, self.code, http_status, description, translation)


class IncomeLimitExceeded(QIException):
    code = "QIT001024"

    def __init__(self, alerts_per_month) -> None:
        title = "Outflow above income"
        http_status = 422
        description = (
            f"The amount is above the income rule and the account already had {alerts_per_month} "
            "income alerts this month. The account was blocked for analysis."
        )
        translation = "Saída acima da renda com a cota de alertas do mês esgotada. A conta foi bloqueada para análise."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundPixKey(QIException):
    code = "QIT001030"

    def __init__(self, key_value) -> None:
        title = "Pix key not Found"
        http_status = 404
        description = f"The Pix key {key_value} was not found."
        translation = "A chave Pix informada não existe."
        super().__init__(title, self.code, http_status, description, translation)


class PixKeyAlreadyRegistered(QIException):
    code = "QIT001031"

    def __init__(self, key_value) -> None:
        title = "Pix key already registered"
        http_status = 409
        description = f"The Pix key {key_value} is already registered."
        translation = "Esta chave Pix já está cadastrada."
        super().__init__(title, self.code, http_status, description, translation)


class PixKeyNotOwnDocument(QIException):
    code = "QIT001032"

    def __init__(self) -> None:
        title = "CPF key must be the owner's"
        http_status = 422
        description = "A Pix key of type cpf must be the CPF of the account owner."
        translation = "A chave do tipo CPF precisa ser o CPF do dono da conta."
        super().__init__(title, self.code, http_status, description, translation)


class PixKeyLimitReached(QIException):
    code = "QIT001033"

    def __init__(self, limit) -> None:
        title = "Pix key limit reached"
        http_status = 422
        description = f"The account already has {limit} Pix keys, the maximum allowed."
        translation = f"A conta já tem {limit} chaves Pix, o máximo permitido."
        super().__init__(title, self.code, http_status, description, translation)
