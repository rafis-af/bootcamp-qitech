# O mock da Receita e da Serasa. Imagem própria, separada da API: em
# produção ele não existe, e nada dele deve ir parar na imagem da API.
FROM python:3.11-slim

RUN adduser --system --no-create-home user

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

WORKDIR /mocks
COPY app.py /mocks/app.py

USER user

CMD uvicorn app:app --host 0.0.0.0 --port 8080 --no-server-header
