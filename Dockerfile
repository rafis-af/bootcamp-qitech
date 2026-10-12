# Imagem oficial e publica do Python. Qualquer pessoa consegue baixar.
FROM python:3.11-slim AS base

# Roda a aplicacao com um usuario sem privilegios, nunca como root.
RUN adduser --system --no-create-home user

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copiar so o requirements primeiro faz o Docker reaproveitar o cache:
# enquanto as dependencias nao mudam, ele nao reinstala tudo de novo.
COPY requirements.txt /requirements.txt
RUN pip install --upgrade pip && pip install -r /requirements.txt

WORKDIR /app
COPY src /app

FROM base AS api
# Dependencias de desenvolvimento (pytest etc.), para rodar a suite com
# "docker compose exec api python -m pytest".
COPY requirements-dev.txt /requirements-dev.txt
RUN pip install -r /requirements-dev.txt

RUN chown -R user /app
USER user

# --no-server-header: o uvicorn nao anuncia a propria versao, que e
# informacao de menos pra quem procura uma versao com falha conhecida.
CMD uvicorn app:app --host 0.0.0.0 --port 3000 --no-server-header


# Imagem dos testes. Nao sobe nada: so roda o pytest contra a API que
# esta de pe no compose. O "docker compose run --rm tests" usa este estagio.
FROM base AS tests
COPY requirements-dev.txt /requirements-dev.txt
RUN pip install -r /requirements-dev.txt

WORKDIR /work
COPY pytest.ini /work/pytest.ini
COPY tests /work/tests

CMD ["pytest"]
