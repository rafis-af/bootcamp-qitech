
import asyncio

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

SLOW_RESPONSE_SECONDS = 6

RECEITA_SITUATION_BY_PREFIX = {
    "900": "SUSPENSA",
    "901": "CANCELADA",
}
RECEITA_SLOW_PREFIX = "910"
# Falhas da Receita: o status HTTP é o que o prefixo pede. "941" responde
# 200, mas sem o campo "situation" (fora do formato combinado).
RECEITA_HTTP_STATUS_BY_PREFIX = {"940": 500, "942": 401, "947": 404}
RECEITA_MALFORMED_PREFIX = "941"

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
SERASA_HTTP_STATUS_BY_PREFIX = {"950": 500}
SERASA_MALFORMED_PREFIX = "951"  # 200, mas sem o campo "score"


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

    if prefix in RECEITA_HTTP_STATUS_BY_PREFIX:
        return JSONResponse(status_code=RECEITA_HTTP_STATUS_BY_PREFIX[prefix], content={"error": "mock failure"})

    if prefix == RECEITA_MALFORMED_PREFIX:
        return {"document_number": document_number}

    situation = RECEITA_SITUATION_BY_PREFIX.get(prefix, "REGULAR")

    return {"document_number": document_number, "situation": situation}


@app.post("/serasa/score")
async def consult_serasa(payload: dict) -> dict:
    document_number = payload["document_number"]
    prefix = prefix_of(document_number)

    if prefix == SERASA_SLOW_PREFIX:
        await asyncio.sleep(SLOW_RESPONSE_SECONDS)

    if prefix in SERASA_HTTP_STATUS_BY_PREFIX:
        return JSONResponse(status_code=SERASA_HTTP_STATUS_BY_PREFIX[prefix], content={"error": "mock failure"})

    report = dict(SERASA_CLEAN_REPORT)
    report.update(SERASA_CHANGES_BY_PREFIX.get(prefix, {}))
    report["document_number"] = document_number

    if prefix == SERASA_MALFORMED_PREFIX:
        del report["score"]

    return report
