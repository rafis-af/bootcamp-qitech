import functools
import json
import os
from typing import Optional

from jsonschema import RefResolver
from jsonschema.exceptions import ValidationError, best_match
from jsonschema.validators import validator_for

from constants import SCHEMA_PATH
from errors import InvalidSchema
from utils.money import format_brl


class SchemaCache:
    """Lê cada schema uma vez e guarda o validador pronto.

    O `jsonschema.validate()` confere o PRÓPRIO schema a cada chamada, o
    que custava ~1 ms por requisição; com o validador guardado, a
    validação do corpo cai para alguns centésimos de milissegundo.
    """

    schemas = {}
    validators = {}

    @staticmethod
    def get_schema(schema_file_name: str) -> dict:
        schema_path = os.path.join(SCHEMA_PATH, schema_file_name)

        if schema_path in SchemaCache.schemas:
            return SchemaCache.schemas[schema_path]

        if not os.path.isfile(schema_path):
            raise Exception(
                f"Nao encontrei o schema '{schema_file_name}' em {SCHEMA_PATH}. "
                + "Ou o arquivo nao existe, ou o nome escrito na rota esta diferente."
            )

        with open(schema_path, "r", encoding="utf-8") as arquivo:
            schema = json.loads(arquivo.read())

        SchemaCache.schemas[schema_path] = schema

        return schema

    @staticmethod
    def get_validator(schema_file_name: str):
        # O caro é o check_schema, e ele roda uma vez só por schema. O
        # validador em si é montado a cada chamada: o RefResolver guarda
        # estado enquanto resolve um $ref e não pode ser dividido entre
        # threads.
        if schema_file_name not in SchemaCache.validators:
            schema = SchemaCache.get_schema(schema_file_name)
            validator_class = validator_for(schema)
            validator_class.check_schema(schema)
            SchemaCache.validators[schema_file_name] = (validator_class, schema)

        validator_class, schema = SchemaCache.validators[schema_file_name]
        resolver = RefResolver(f"file://{SCHEMA_PATH}/", schema)

        return validator_class(schema, resolver=resolver)


def find_nul_character(instance) -> Optional[str]:
    """Nome do primeiro campo com um "\\x00" no texto, ou None.

    O PostgreSQL não aceita o caractere nulo em texto. Sem esta checagem,
    o driver falhava ao gravar e a API respondia 500 para um dado que o
    schema aceitava. Corpo e query são planos, então basta olhar o
    primeiro nível (e os itens das listas, que são de texto).
    """
    if not isinstance(instance, dict):
        return None

    for name, value in instance.items():
        values = value if isinstance(value, list) else [value]

        for item in values:
            if isinstance(item, str) and "\x00" in item:
                return name

    return None


def validate_or_raise(schema_file_name: str, instance: dict, where: str) -> None:
    nul_field = find_nul_character(instance)
    if nul_field is not None:
        noun_en, noun_pt = ("Field", "O campo") if where == "body" else ("Parameter", "O parâmetro")
        raise InvalidSchema(
            f"{noun_en} '{nul_field}' contains the NUL character (\\u0000), which is not accepted.",
            f"{noun_pt} '{nul_field}' contém o caractere nulo (\\u0000), que não é aceito.",
            nul_field,
        )

    validator = SchemaCache.get_validator(schema_file_name)
    error = best_match(validator.iter_errors(instance))

    if error is not None:
        description, translation, field = describe_schema_error(error, instance, where)
        raise InvalidSchema(description, translation, field)


class SchemaHandler:
    @staticmethod
    def validate(schema_file_name: str):
        def decorator_validate(func):
            @functools.wraps(func)
            def wrapper_validate(*args, **kwargs):
                if "payload" not in kwargs:
                    raise Exception(
                        f"A rota '{func.__name__}' foi decorada com o SchemaHandler, mas nao "
                        + "tem um parametro chamado 'payload'. E de la que sai o corpo a validar."
                    )

                validate_or_raise(schema_file_name, kwargs["payload"], "body")

                return func(*args, **kwargs)

            return wrapper_validate

        return decorator_validate

    @staticmethod
    def validate_query_params(schema_file_name: str):
        def decorator_validate(func):
            @functools.wraps(func)
            def wrapper_validate(*args, **kwargs):
                request = kwargs.get("request")
                if request is None:
                    raise Exception(
                        f"A rota '{func.__name__}' foi decorada com o validate_query_params, mas "
                        + "nao tem um parametro chamado 'request'. E de la que sai a query string."
                    )

                schema = SchemaCache.get_schema(schema_file_name)
                query_params = query_params_to_dict(request.query_params, schema)

                validate_or_raise(schema_file_name, query_params, "query")

                return func(*args, **kwargs)

            return wrapper_validate

        return decorator_validate


def query_params_to_dict(query_params, schema: dict) -> dict:
    properties = schema.get("properties", {})
    parsed_params = {}

    for param_name in query_params.keys():
        declared = properties.get(param_name, {})

        if declared.get("type") == "array":
            parsed_params[param_name] = query_params.getlist(param_name)
        else:
            parsed_params[param_name] = query_params[param_name]

    return parsed_params


# ---------------------------------------------------------------------------
# Mensagem de erro por campo
#
# O jsonschema descreve o erro em inglês e com a regex crua
# ("'123' does not match '^\\d{3}...$'"). Quem chama a API precisa saber
# QUAL campo está errado e COMO ele deveria vir. Abaixo, cada campo diz o
# formato que espera, em inglês (description) e em português (translation).
# Nenhuma mensagem repete o valor recebido: assim a senha nunca volta
# numa resposta de erro.
# ---------------------------------------------------------------------------

SENSITIVE_FIELDS = {"password"}

CPF_FORMAT = ("a CPF formatted as 000.000.000-00", "um CPF no formato 000.000.000-00")
DATE_FORMAT = ("a date formatted as YYYY-MM-DD", "uma data no formato AAAA-MM-DD")
EMAIL_FORMAT = ("a valid e-mail, like name@domain.com", "um e-mail válido, como nome@dominio.com")
UUID_FORMAT = ("a UUID, like 123e4567-e89b-12d3-a456-426614174000", "um UUID, como 123e4567-e89b-12d3-a456-426614174000")
PHONE_FORMAT = (
    "a phone formatted as +55 + area code + number, digits only (e.g. +5511987654321)",
    "um telefone no formato +55 + DDD + número, só dígitos (ex.: +5511987654321)",
)
NAME_FORMAT = ("a name with at least one letter (not only spaces)", "um nome com pelo menos uma letra (não pode ser só espaços)")

FIELD_FORMATS = {
    "document_number": CPF_FORMAT,
    "depositor_document_number": CPF_FORMAT,
    "birthdate": DATE_FORMAT,
    "date_from": DATE_FORMAT,
    "date_to": DATE_FORMAT,
    "email": EMAIL_FORMAT,
    "transaction_key": (
        UUID_FORMAT[0] + " (generate a new one for each operation)",
        UUID_FORMAT[1] + " (gere um novo para cada operação)",
    ),
    "destination_account_key": ("the destination account key, " + UUID_FORMAT[0], "a chave da conta de destino, " + UUID_FORMAT[1]),
    "password": ("the 6-digit numeric password", "a senha de 6 dígitos numéricos"),
    "source_bank_code": ("the 3-digit bank code, like 341", "o código do banco com 3 dígitos, como 341"),
    "limit": ("an integer from 1 to 100", "um número inteiro de 1 a 100"),
    "page": ("an integer starting at 0", "um número inteiro a partir de 0"),
    "name": NAME_FORMAT,
    "depositor_name": NAME_FORMAT,
}

PIX_KEY_FORMATS = {
    "cpf": CPF_FORMAT,
    "email": EMAIL_FORMAT,
    "phone": PHONE_FORMAT,
}

MONEY_FIELDS = {"amount", "monthly_income"}

# Campo que não pode vir naquele caso (os "false" dos schemas).
FORBIDDEN_FIELD_MESSAGES = {
    "key_value": (
        "Do not send key_value for a random key: the bank generates it.",
        "Não envie key_value para chave do tipo random: o banco é quem gera a chave.",
    ),
    "source_bank_code": (
        "Do not send source_bank_code for a cash deposit: cash has no origin bank.",
        "Não envie source_bank_code em depósito em espécie (cash): dinheiro em espécie não tem banco de origem.",
    ),
}

# Campo que é obrigatório só em alguns casos (os "if/then" dos schemas).
CONDITIONAL_REQUIRED_MESSAGES = {
    "source_bank_code": (
        "A TED deposit needs source_bank_code (the 3-digit origin bank code).",
        "Depósito por TED precisa de source_bank_code (o código do banco de origem, com 3 dígitos).",
    ),
    "key_value": (
        "Send key_value: only random keys are generated by the bank.",
        "Informe key_value: só a chave do tipo random é gerada pelo banco.",
    ),
}

TYPE_NAMES = {
    "integer": ("an integer (no decimals)", "um número inteiro (sem casas decimais)"),
    "number": ("a number", "um número"),
    "string": ("a text (between quotes)", "um texto (entre aspas)"),
    "boolean": ("true or false", "true ou false"),
    "array": ("a list", "uma lista"),
    "object": ("an object", "um objeto"),
    "null": ("null", "null"),
}


def field_of(error: ValidationError) -> str:
    path = [str(part) for part in error.absolute_path if not isinstance(part, int)]
    return ".".join(path)


def describe_schema_error(error: ValidationError, instance: dict = None, where: str = "body") -> tuple:
    """Devolve (description em inglês, translation em português, campo)."""
    noun_en, noun_pt = ("Field", "O campo") if where == "body" else ("Parameter", "O parâmetro")
    validator = error.validator
    field = field_of(error)

    if validator == "required":
        missing = [name for name in error.validator_value if not isinstance(error.instance, dict) or name not in error.instance]
        field = missing[0] if missing else field
        conditional = "if" in error.relative_schema_path or "then" in error.relative_schema_path or "else" in error.relative_schema_path
        if conditional and field in CONDITIONAL_REQUIRED_MESSAGES:
            description, translation = CONDITIONAL_REQUIRED_MESSAGES[field]
            return description, translation, field
        return (
            f"{noun_en} '{field}' is required.",
            f"{noun_pt} '{field}' é obrigatório e não foi enviado.",
            field,
        )

    if validator == "additionalProperties":
        allowed = sorted(error.schema.get("properties", {}).keys())
        received = error.instance if isinstance(error.instance, dict) else {}
        extras = sorted(name for name in received if name not in allowed)
        extra = extras[0] if extras else "?"
        return (
            f"{noun_en} '{extra}' is not accepted here. Accepted: {', '.join(allowed)}.",
            f"{noun_pt} '{extra}' não existe nesta rota. Aceitos: {', '.join(allowed)}.",
            extra,
        )

    if validator is None or error.schema is False:
        description, translation = FORBIDDEN_FIELD_MESSAGES.get(
            field,
            (f"{noun_en} '{field}' cannot be sent in this case.", f"{noun_pt} '{field}' não pode ser enviado neste caso."),
        )
        return description, translation, field

    if validator == "type":
        expected = error.validator_value
        if isinstance(expected, list):
            expected = expected[0]
        type_en, type_pt = TYPE_NAMES.get(expected, (expected, expected))
        in_cents = field in MONEY_FIELDS
        return (
            f"{noun_en} '{field}' must be {type_en}{', in cents' if in_cents else ''}.",
            f"{noun_pt} '{field}' precisa ser {type_pt}{', em centavos (R$ 10,50 = 1050)' if in_cents else ''}.",
            field,
        )

    if validator in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
        limit = error.validator_value
        smallest = validator in ("minimum", "exclusiveMinimum")
        word_en = "at least" if smallest else "at most"
        word_pt = "no mínimo" if smallest else "no máximo"
        shown = f"{limit} ({format_brl(limit)})" if field in MONEY_FIELDS else str(limit)
        if field == "monthly_income" and smallest:
            return (
                "Field 'monthly_income' must be greater than zero, in cents.",
                "A renda mensal (monthly_income) precisa ser maior que zero, em centavos.",
                field,
            )
        return (
            f"{noun_en} '{field}' must be {word_en} {limit}.",
            f"{noun_pt} '{field}' precisa ser {word_pt} {shown}.",
            field,
        )

    if validator == "minLength":
        if error.validator_value <= 1:
            return f"{noun_en} '{field}' cannot be empty.", f"{noun_pt} '{field}' não pode ficar vazio.", field
        return (
            f"{noun_en} '{field}' must have at least {error.validator_value} characters.",
            f"{noun_pt} '{field}' precisa ter pelo menos {error.validator_value} caracteres.",
            field,
        )

    if validator == "maxLength":
        return (
            f"{noun_en} '{field}' must have at most {error.validator_value} characters.",
            f"{noun_pt} '{field}' pode ter no máximo {error.validator_value} caracteres.",
            field,
        )

    if validator == "pattern":
        expected = FIELD_FORMATS.get(field)
        if field == "key_value" and isinstance(instance, dict):
            expected = PIX_KEY_FORMATS.get(instance.get("key_type"), expected)
        if expected is not None:
            return (
                f"{noun_en} '{field}' must be {expected[0]}.",
                f"{noun_pt} '{field}' precisa ser {expected[1]}.",
                field,
            )
        return f"{noun_en} '{field}' has an invalid format.", f"{noun_pt} '{field}' está num formato inválido.", field

    if validator == "enum":
        accepted = ", ".join(str(value) for value in error.validator_value)
        return (
            f"Invalid value in '{field}'. Accepted: {accepted}.",
            f"Valor inválido em '{field}'. Aceitos: {accepted}.",
            field,
        )

    if validator == "const":
        return (
            f"Invalid value in '{field}'. Expected: {error.validator_value}.",
            f"Valor inválido em '{field}'. Esperado: {error.validator_value}.",
            field,
        )

    if validator == "minItems":
        return (
            f"{noun_en} '{field}' needs at least {error.validator_value} value(s).",
            f"{noun_pt} '{field}' precisa de pelo menos {error.validator_value} valor.",
            field,
        )

    # Qualquer outro caso: a mensagem do jsonschema, sem o valor se o campo for sensível.
    message = error.message
    if field in SENSITIVE_FIELDS:
        message = "invalid value"

    if field:
        return f"{message} in {field}", f"Valor inválido em '{field}'.", field

    return message, "Payload inválido.", None
