
import asyncio

from fastapi import FastAPI, Response

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

SLOW_RESPONSE_SECONDS = 6

RECEITA_SITUATION_BY_PREFIX = {
    "900": "SUSPENSA",
    "901": "CANCELADA",
}
RECEITA_SLOW_PREFIX = "910"

SERASA_CLEAN_REPORT = {
    "has_restriction": False,
    "fraud_risk": "LOW",
    "score": 800,
    "has_late_payments": False,
}
SERASA_CHANGES_BY_PREFIX = {
    "920": {"has_restriction": True},
    "921": {"fraud_risk": "HIGH"},
    "922": {"score": 599},
    "923": {"score": 600},
    "924": {"score": None},
    "925": {"has_late_payments": True},
}
SERASA_SLOW_PREFIX = "930"


def prefix_of(document_number: str) -> str:
    digits = ""
    for character in document_number:
        if character.isdigit():
            digits = digits + character

    return digits[:3]


@app.get("/health_check")
def health_check() -> Response:
    return Response(status_code=204)


@app.post("/receita/cpf")
async def consult_receita(payload: dict) -> dict:
    document_number = payload["document_number"]
    prefix = prefix_of(document_number)

    if prefix == RECEITA_SLOW_PREFIX:
        await asyncio.sleep(SLOW_RESPONSE_SECONDS)

    situation = RECEITA_SITUATION_BY_PREFIX.get(prefix, "REGULAR")

    return {"document_number": document_number, "situation": situation}


@app.post("/serasa/score")
async def consult_serasa(payload: dict) -> dict:
    document_number = payload["document_number"]
    prefix = prefix_of(document_number)

    if prefix == SERASA_SLOW_PREFIX:
        await asyncio.sleep(SLOW_RESPONSE_SECONDS)

    report = dict(SERASA_CLEAN_REPORT)
    report.update(SERASA_CHANGES_BY_PREFIX.get(prefix, {}))
    report["document_number"] = document_number

    return report
