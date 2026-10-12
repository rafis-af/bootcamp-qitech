# Banco do time — API (Bootcamp QI Tech 2026)

API de um banco digital: cadastro de cliente com classificação Ouro,
Prata ou Bloqueado, conta protegida por senha, depósito, transferência e
Pix com tarifa, limite diário e verificação de renda, e extrato paginado
— com cada operação acontecendo **uma vez só**, mesmo com pedidos
simultâneos ou repetidos.

É a implementação da **RFC** do time (Rafael Almeida · Guilherme Silva
Xavier), construída sobre a `bootcamp-base-api`: **Python + FastAPI**,
**PostgreSQL** com **SQLAlchemy**, contratos em **JSON Schema**, tudo em
**Docker**.

---

## 0. O que você precisa ter instalado

| O quê | Para quê | Como conferir |
|---|---|---|
| **Docker** (com o Docker Desktop no Mac/Windows) | roda a API, o banco e o mock | `docker compose version` |
| **Git** | trazer o projeto para o seu computador | `git --version` |
| **Python 3.11 ou mais novo** | rodar os testes (seção 6) | `python3 --version` |

---

## 1. Rodando

```bash
docker compose up
```

Um comando, sem criar arquivo nenhum antes. Sobem três serviços:

| Serviço | O que é |
|---|---|
| `api` | a API do banco, em http://localhost:3000 |
| `db` | o PostgreSQL, já com as 11 tabelas e os catálogos preenchidos |
| `mock` | faz o papel da Receita Federal e da Serasa (seção 5) |

Quando aparecer `Application startup complete`, a API está no ar.

Para desligar: `Ctrl+C` e depois `docker compose down`. Para desligar
**e apagar o banco** (recomeçar do zero): `docker compose down -v`.

---

## 2. Um passeio pela API

Todas as rotas, menos `/` e `/health_check`, pedem o cabeçalho
`INTERNAL-TOKEN` (seção 9). Os exemplos usam `curl`; **no Windows, use o
Git Bash** (no PowerShell, `curl` é outro programa).

Valores são sempre **inteiros em centavos**: `150000` é R$ 1.500,00.

### 2.1 Cadastrar um cliente

```bash
curl -X POST http://localhost:3000/client \
  -H "INTERNAL-TOKEN: default_token" -H "Content-Type: application/json" \
  -d '{
    "name": "Maria da Silva",
    "email": "maria.silva@exemplo.com.br",
    "document_number": "529.982.247-25",
    "birthdate": "1990-05-17",
    "monthly_income": 500000
  }'
```

```json
{"client_key":"3d71aefc-...","name":"Maria da Silva","email":"maria.silva@exemplo.com.br","document_number":"529.982.247-25","birthdate":"1990-05-17","monthly_income":500000,"status":"active","level":"gold","created_at":"2026-10-09T17:36:06.963159-03:00","account_key":null}
```

A API conferiu o CPF, consultou a Receita e a Serasa (o mock) e
classificou: `gold`. Troque o começo do CPF para ver os outros desfechos
(a tabela está na seção 5) — o CPF continua precisando ser válido.

### 2.2 Abrir a conta

```bash
curl -X POST http://localhost:3000/client/3d71aefc-.../account \
  -H "INTERNAL-TOKEN: default_token" -H "Content-Type: application/json" \
  -d '{"password": "123456"}'
```

A resposta traz o `account_key`, saldo `0`, status e nível. A senha
nunca volta.

### 2.3 Depositar

O `transaction_key` é um UUID **gerado por quem chama** — é o ID da
operação (RFC 2.2). Gere um novo a cada operação (`uuidgen`, ou qualquer
gerador de UUID).

```bash
curl -X POST http://localhost:3000/account/<account_key>/deposit \
  -H "INTERNAL-TOKEN: default_token" -H "Content-Type: application/json" \
  -d '{
    "transaction_key": "1b4e28ba-2fa1-11d2-883f-0016d3cca427",
    "amount": 100000,
    "method": "cash",
    "depositor_name": "Maria da Silva",
    "depositor_document_number": "529.982.247-25"
  }'
```

**Rode o mesmo comando de novo.** A resposta é a mesma operação, agora
com status **200** em vez de 201 — e o saldo não mudou. É o reenvio sendo
reconhecido. Mude o `amount` mantendo o mesmo ID e a resposta é **409**.

Depósito por TED leva `"method": "ted"` e `"source_bank_code": "341"`.

### 2.4 Transferir

```bash
curl -X POST http://localhost:3000/account/<account_key>/transfer \
  -H "INTERNAL-TOKEN: default_token" -H "Content-Type: application/json" \
  -d '{
    "transaction_key": "<um UUID novo>",
    "destination_account_key": "<account_key de outra conta>",
    "amount": 10000,
    "password": "123456"
  }'
```

A resposta traz `"fee": 150`: quem envia paga R$ 1,50, quem recebe ganha
o valor cheio.

### 2.5 Cadastrar chave Pix e enviar Pix

```bash
curl -X POST http://localhost:3000/account/<account_key do recebedor>/pix-key \
  -H "INTERNAL-TOKEN: default_token" -H "Content-Type: application/json" \
  -d '{"key_type": "email", "key_value": "joao@exemplo.com.br", "password": "654321"}'

curl -X POST http://localhost:3000/account/<account_key de quem envia>/pix \
  -H "INTERNAL-TOKEN: default_token" -H "Content-Type: application/json" \
  -d '{
    "transaction_key": "<um UUID novo>",
    "pix_key": "joao@exemplo.com.br",
    "amount": 500,
    "password": "123456"
  }'
```

Tipos de chave: `cpf` (só o do dono da conta), `email`, `phone`
(`+5511999999999`) e `random` (sem `key_value`: a API gera). A resposta
do Pix traz o `destination_name`, o nome do dono da chave.

### 2.6 Extrato

```bash
curl "http://localhost:3000/account/<account_key>/statement?limit=10&page=0" \
  -H "INTERNAL-TOKEN: default_token"
```

Do mais recente para o mais antigo. Cada linha traz o tipo, o valor com
sinal, o saldo depois do lançamento e o ID da operação. Período
opcional: `?date_from=2026-10-01&date_to=2026-10-31` (as duas pontas
entram; dias do calendário de São Paulo).

### Toda resposta tem um número de protocolo

O cabeçalho `x-request-id` da resposta identifica a requisição no log
(`docker compose logs api | grep <id>`) e na tabela de eventos, que
guarda o mesmo identificador.

---

## 3. Todas as rotas (RFC, seção 4)

| Método e rota | O que faz | Senha | Responde |
|---|---|---|---|
| `GET /` | identifica o serviço | — | `200` |
| `GET /health_check` | diz se está de pé | — | `204` |
| `POST /client` | cadastra e classifica o cliente | — | `201` (ativo ou bloqueado) |
| `GET /client/{client_key}` | consulta o cliente | — | `200` |
| `GET /clients` | lista, paginado | — | `200` |
| `POST /client/{client_key}/account` | abre a conta e cria a senha | cria | `201` |
| `GET /account/{account_key}` | saldo, status e nível | — | `200` |
| `PUT /account/{account_key}/status` | bloqueia ou desbloqueia | — | `200` |
| `POST /account/{account_key}/deposit` | deposita | — | `201` nova · `200` reenvio |
| `POST /account/{account_key}/transfer` | transfere | sim | `201` nova · `200` reenvio |
| `POST /account/{account_key}/pix-key` | cadastra chave Pix | sim | `201` |
| `GET /account/{account_key}/pix-keys` | lista as chaves | — | `200` |
| `POST /account/{account_key}/pix` | envia Pix | sim | `201` nova · `200` reenvio |
| `GET /account/{account_key}/statement` | extrato, paginado | — | `200` |

Listagens (`/clients` e `/statement`): `?limit=` (1 a 100, padrão 10) e
`?page=` (padrão 0). `/clients` filtra por `status`, `level` (os dois
repetíveis), `name` (por pedaço), `email` e `document_number`. Parâmetro
desconhecido é **400** — o schema não aceita o que não conhece.

---

## 4. As regras, e onde cada uma mora no código

| Regra (RFC) | Onde |
|---|---|
| Classificação Ouro/Prata/Bloqueado (5.1) | `src/controllers/client_controller.py` |
| Senha de 6 dígitos com bcrypt; 3 erradas seguidas bloqueiam (5.2, 5.3) | `src/utils/password.py`, `_authenticate` em `src/controllers/base_account_controller.py` |
| ID único da operação: reenvio devolve a original, outros dados → 409 (2.2) | `_find_replay` e `_save` em `src/controllers/transaction_controller.py` |
| Trava das contas em ordem crescente de id (2.4) | `_lock_accounts` (controller) e `lock` em `src/repositories/account_repository.py` |
| Limite diário do Prata, R$ 1.000 inclusive, sem a tarifa (2.1) | `_check_daily_limit` |
| Tarifa vigente por nível e tipo, guardada na operação (2.1) | `get_current_fee` em `src/repositories/catalog_repository.py` |
| Renda: alerta acima de 2×; com 3 alertas no mês, recusa e bloqueia (5.6) | `_check_income` |
| Saldo = soma dos lançamentos | `post` em `src/repositories/entry_repository.py` (o único lugar que muda o saldo) |
| Recusa que vira evento, gravado antes da resposta de erro (2.3) | `_refuse_with_event` em `src/controllers/base_account_controller.py` |

O "dia" do limite e o "mês" da cota seguem o calendário de **São Paulo**
(`src/utils/clock.py`), não o fuso do servidor.

---

## 5. O mock da Receita e da Serasa

O cadastro consulta a Receita (CPF regular?) e a Serasa (restrição,
fraude, score, atrasos) por connectors (`src/connectors/`). No docker
compose quem responde é o container `mock` (`mocks/app.py`), e a resposta
depende dos **três primeiros dígitos do CPF**:

| Começo do CPF | Resposta do mock | Desfecho do cadastro |
|---|---|---|
| qualquer outro | Receita REGULAR, Serasa limpa, score 800 | `201` Ouro |
| `900` / `901` | Receita SUSPENSA / CANCELADA | `422` QIT001007, nada gravado |
| `910` | Receita demora 6 s | `503` QIT001009 (sem resposta em 5 s), nada gravado |
| `920` | Serasa: restrição (nome sujo) | `201` bloqueado, sem nível |
| `921` | Serasa: risco de fraude alto | `201` bloqueado, sem nível |
| `922` | score 599 | `201` Prata |
| `923` | score 600 (a borda) | `201` Ouro |
| `924` | sem score | `201` Prata |
| `925` | score 800 com atraso | `201` Prata |
| `930` | Serasa demora 6 s | `503` QIT001009, nada gravado |
| `940` | Receita responde HTTP 500 | `502` QIT001041, nada gravado |
| `941` | Receita responde 200 sem o campo `situation` | `502` QIT001042, nada gravado |
| `942` | Receita recusa a credencial desta API (HTTP 401) | `502` QIT001043, nada gravado |
| `947` | Receita não encontra o CPF (HTTP 404) | `422` QIT001044, nada gravado |
| `950` | Serasa responde HTTP 500 | `502` QIT001041, nada gravado |
| `951` | Serasa responde 200 sem o campo `score` | `502` QIT001042, nada gravado |

O CPF ainda precisa ter os dígitos verificadores certos. Para trocar o
mock por um serviço de verdade, basta mudar `RECEITA_API_URL` e
`SERASA_API_URL` — o código não muda.

---

## 6. Rodando os testes

Os testes rodam **dentro do Docker**, num container próprio, contra a API
que está de pé no compose. Não precisa instalar Python nem nada na sua
máquina.

Com a API de pé (`(healthy)` no `docker compose ps`):

```bash
docker compose --profile tests run --build --rm tests
```

São 148 testes, cerca de 25 segundos. O resultado esperado no fim é
`148 passed`.

**Rodam em paralelo** (pytest-xdist, ligado no `pytest.ini` com `-n auto`:
um worker por CPU). Isso só é possível porque **nenhum teste depende de
outro**: cada um cria os próprios clientes e contas, olha só para o que
criou, e nunca apaga o banco. Dá para rodar qualquer teste sozinho, em
qualquer ordem.

A única exceção é o teste de tarifa: a tarifa vale para todo cliente
daquele nível, então, enquanto ele roda, outro teste pagaria a tarifa
errada. Ele leva a marca `@pytest.mark.exclusive` e roda sozinho — espera
os testes em andamento terminarem, roda, devolve a tarifa antiga, e os
outros seguem (a trava está em `tests/conftest.py`).

Um arquivo, um teste só, ou por palavra no nome:

```bash
docker compose --profile tests run --rm tests pytest tests/integration/account/test_password.py
docker compose --profile tests run --rm tests pytest "tests/integration/account/test_password.py::TestPassword::test_unblock_resets_the_attempts"
docker compose --profile tests run --rm tests pytest -k "password"
```

Para depurar, `-n 0` desliga o paralelismo (um teste de cada vez, e o
`print` aparece com `-s`): `... pytest -n 0 -s tests/...`.

> O serviço `tests` tem o perfil `tests`: por isso ele **não** sobe no
> `docker compose up` comum, só quando você pede com o comando acima.
> O `--build` garante que a imagem dos testes esteja com o código atual.

Quer rodar os testes na sua máquina, com a API de pé no `docker compose up`?
Precisa de Python 3.11 ou mais novo (testado do 3.11 ao 3.14):

```bash
python -m venv .venv
.venv\Scripts\activate          # no Linux/Mac: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

No Windows, rode com `pytest -n 0`: a trava do teste exclusivo usa
`fcntl`, que só existe no Linux e no Mac.

O que a suíte cobre, por arquivo:

| Pasta | O quê |
|---|---|
| `tests/integration/client/` | cada desfecho do cadastro, timeouts, duplicidade, listagem |
| `tests/integration/account/` | abertura, senha (bloqueio na 3ª, zerar no acerto), bloqueio manual |
| `tests/integration/transaction/` | depósito, transferência, Pix, limite diário, renda, tarifa dinâmica, idempotência e **concorrência** (saídas simultâneas, mesmo ID ao mesmo tempo, A→B e B→A sem deadlock) |
| `tests/integration/pix_key/` | tipos de chave, CPF do dono, limite de 5, chave disputada por duas contas |
| `tests/integration/statement/` | ordem, sinal, saldo depois, paginação, período |
| `tests/integration/test_error_messages.py` | cada erro com código e mensagem próprios: corpo inválido, Content-Type, campo por campo, caractere nulo, token, rota, regras de negócio, conta ocupada |
| `tests/integration/client/test_external_service_errors.py` | cada falha da Receita e da Serasa (QIT001041 a QIT001044), com a conferência de que nada foi gravado |
| `tests/unit/` | os erros de infraestrutura (pool esgotado, banco fora do ar, timeout, conflito, erro inesperado) e a Receita fora do ar (QIT001040), chamando o código direto, porque nenhuma rota consegue provocá-los de forma confiável |

Uma exceção à regra "só HTTP", e ela é explicada em
`tests/utils/db_utils.py`: os testes **leem** a tabela de eventos (nenhuma
rota da v1 devolve eventos) e **trocam a tarifa** direto no banco (na RFC,
isso é dado, sem rota e sem deploy).

---

## 7. O banco de dados

São 11 tabelas (`database/database.sql`), em três grupos:

| Grupo | Tabelas |
|---|---|
| catálogos | `status`, `level`, `transaction_type`, `fee` |
| cadastro | `client`, `account`, `pix_key` |
| dinheiro e histórico | `transaction`, `deposit`, `entry`, `event` |

O que o próprio banco garante, mesmo que o código erre:

- **saldo nunca negativo**: `CHECK` na conta e em cada lançamento;
- **nada duplicado**: `UNIQUE` em CPF, e-mail, conta por cliente, chave
  Pix, `transaction_key`, depósito por operação e tarifa vigente por
  nível e tipo (índice único parcial);
- **operação coerente**: origem ≠ destino, valor de 1 a 100.000.000, TED
  sempre com banco de origem, sinal do lançamento conforme o tipo.

Os models em `src/models/` descrevem as mesmas tabelas em Python
(SQLAlchemy), uma por arquivo.

### Mudar uma tarifa

Tarifa é dado (RFC 2.1). Fechar a vigente e abrir outra, numa transação:

```sql
BEGIN;
UPDATE fee SET ends_at = NOW()
WHERE ends_at IS NULL
  AND level_id = (SELECT id FROM level WHERE enumerator = 'silver')
  AND transaction_type_id = (SELECT id FROM transaction_type WHERE enumerator = 'transfer');
INSERT INTO fee (level_id, transaction_type_id, amount)
SELECT level.id, transaction_type.id, 200
FROM level, transaction_type
WHERE level.enumerator = 'silver' AND transaction_type.enumerator = 'transfer';
COMMIT;
```

(`docker compose exec db psql -U bootcamp` abre o terminal do banco.) As
operações antigas continuam com a tarifa que pagaram.

---

## 8. Quando dá errado

### `port is already allocated`

Outro programa já usa a porta (é comum um Postgres instalado ocupando a
5432). Copie `.env.example` para `.env` e troque `API_PORT` / `DB_PORT`.
Mexeu no `DB_PORT`? Mude também a porta da `DATABASE_URL` no `.env`.

### `relation "..." does not exist`

O `database/database.sql` roda **uma vez só**, quando o banco nasce.
Mudou o schema? `docker compose down -v` e `docker compose up` — o `-v`
apaga o banco e tudo que estava nele.

### Mudou o `requirements.txt` e a API não enxerga a biblioteca nova

A dependência mora dentro da imagem: `docker compose build api` e
`docker compose up -d`.

### Mudou um arquivo de `src/schemas/` e nada mudou

Os schemas são lidos uma vez e guardados em memória, e o `--reload` só
observa arquivos `.py`: `docker compose restart api`.

### `Não consegui falar com a API` nos testes

A API não está de pé, ou a porta do `.env` não é a que ela usa. No
Windows, `SERVER_LOCALHOST=0.0.0.0` não funciona como destino: use
`SERVER_LOCALHOST=localhost` no `.env`.

---

## 9. Configuração e autenticação

Toda configuração entra por variável de ambiente, com valor padrão no
`docker-compose.yml`. O `.env` é opcional, fica só na sua máquina e
nunca vai para o Git; o `.env.example` mostra o que dá para trocar.

As rotas pedem o cabeçalho do sistema que chama:

```
INTERNAL-TOKEN: default_token
```

Sem ele, **403** — e a mensagem diz se o header faltou ou veio errado. A
senha da conta é outra coisa: 6 dígitos, criados na abertura, pedidos em
toda operação que tira dinheiro ou mexe em chave Pix.

### Banco: pool e limites de tempo

Estas variáveis têm padrão no código (`src/constants.py`) e só precisam
entrar no `.env` para mudar o valor:

| Variável | Padrão | Para que serve |
|---|---|---|
| `DB_POOL_SIZE` | `10` | conexões que ficam abertas com o banco |
| `DB_MAX_OVERFLOW` | `20` | conexões extras no pico |
| `DB_POOL_TIMEOUT` | `10` | segundos que um pedido espera por conexão livre antes do `503 QIT000429` |
| `DB_LOCK_TIMEOUT_MS` | `5000` | quanto um pedido espera a trava de uma conta ocupada antes do `409 QIT000011` |
| `DB_STATEMENT_TIMEOUT_MS` | `15000` | teto de qualquer consulta, antes do `503 QIT000504` |
| `DB_IDLE_IN_TRANSACTION_TIMEOUT_MS` | `30000` | derruba transação aberta e parada |

Some `DB_POOL_SIZE + DB_MAX_OVERFLOW` de todas as instâncias da API e
confira que cabe no `max_connections` do PostgreSQL (100 por padrão).

---

## 10. As pastas

```
src/
  app.py           ← liga tudo: middlewares, as 14 rotas, os error handlers
  resources/       ← recebe o HTTP e decide o status da resposta
  schemas/         ← o formato do que entra (JSON Schema)
  controllers/     ← as regras: o que pode e o que não pode
  repositories/    ← as conversas com o banco — só aqui existe query
  models/          ← as tabelas, descritas em Python
  dtos/            ← o que sai na resposta
  connectors/      ← Receita e Serasa
  errors/          ← cada erro com seu código
  middlewares/     ← o que acontece com toda requisição
  utils/           ← CPF, senha, calendário de São Paulo, valores em R$, log
database/database.sql  ← as 11 tabelas, em SQL
mocks/                 ← o mock da Receita e da Serasa
tests/                 ← os testes
```

A explicação de cada camada (e por que elas são separadas) está em
`docs/como-o-projeto-e-organizado.md`. A revisão de erros e gargalos
(o que mudou, com as medições, e o que ficou como recomendação) está em
`docs/revisao-erros-e-gargalos.md`.

---

## 11. Os códigos de erro

Todo erro responde no mesmo formato. Quando o erro é de um campo só, a
resposta traz também `field`, para quem chamou saber o que corrigir:

```json
{"title": "Insufficient balance", "description": "The balance 1000 does not cover the amount 5000 plus the fee 150.", "translation": "Saldo insuficiente: a operação precisa de R$ 51,50 (R$ 50,00 + tarifa de R$ 1,50), e o saldo é R$ 10,00.", "code": "QIT001022", "field": "amount"}
```

O `translation` é escrito para o caso: um erro de schema diz qual campo
e em que formato ele deveria vir ("O campo 'document_number' precisa ser
um CPF no formato 000.000.000-00"), sem nunca repetir o valor recebido
(a senha não volta numa resposta de erro).

**Requisição e infraestrutura**

| Código | HTTP | Quando |
|---|---|---|
| `QIT000001` | 400 | um campo do corpo ou da query está fora do formato (a mensagem diz qual e como corrigir) |
| `QIT000002` | 403 | faltou o `INTERNAL-TOKEN`, ou ele está errado (a mensagem diz qual dos dois) |
| `QIT000003` | 400 | o corpo não é um JSON válido |
| `QIT000004` | 400 | a rota precisa de corpo, e ele não veio |
| `QIT000005` | 400 | o corpo é JSON, mas não é um objeto (`{...}`) |
| `QIT000006` | 415 | o corpo não foi enviado com `Content-Type: application/json` |
| `QIT000010` | 400 | os parâmetros se contradizem (`date_from` depois de `date_to`) |
| `QIT000011` | 409 | outra operação está usando a mesma conta (passou do `DB_LOCK_TIMEOUT_MS`); nada gravado, pode repetir |
| `QIT000012` | 409 | o dado repete um registro único que já existe (corrida entre dois pedidos iguais); nada gravado |
| `QIT000013` | 422 | um valor está fora do que o banco aceita (grande demais); nada gravado, e o erro vai para o log com traceback |
| `QIT000404` | 404 | a rota não existe (a mensagem repete método e caminho) |
| `QIT000405` | 405 | a rota existe, mas não com esse método (a mensagem lista os aceitos) |
| `QIT000429` | 503 | todas as conexões com o banco ocupadas; nada gravado, pode repetir |
| `QIT000500` | 500 | erro inesperado (bug); a mensagem traz o `X-Request-ID` para achar no log |
| `QIT000503` | 503 | banco de dados fora do ar; se caiu na hora de gravar, a operação pode ter sido gravada ou não: confira, ou repita com o mesmo `transaction_key` |
| `QIT000504` | 503 | a consulta passou do `DB_STATEMENT_TIMEOUT_MS`; nada gravado, pode repetir |

**Negócio**

| Código | HTTP | Quando |
|---|---|---|
| `QIT001001` | 404 | cliente não encontrado |
| `QIT001002` | 422 | CPF com formato certo, mas inválido (o `field` diz se é o do cliente ou o de quem depositou) |
| `QIT001003` | 409 | CPF já cadastrado (inclusive como bloqueado) |
| `QIT001004` | 409 | e-mail já cadastrado |
| `QIT001005` | 422 | menor de 18 anos |
| `QIT001006` | 422 | data que não existe no calendário |
| `QIT001007` | 422 | CPF não está REGULAR na Receita (a mensagem traz a situação) |
| `QIT001008` | 409 | cliente bloqueado na análise não abre conta |
| `QIT001009` | 503 | Receita ou Serasa sem resposta dentro do timeout — nada gravado, pode repetir |
| `QIT001010` | 404 | conta não encontrada (a do caminho) |
| `QIT001011` | 409 | o cliente já tem conta |
| `QIT001012` | 409 | conta bloqueada (a mensagem diz o que ela não pode fazer: depositar, enviar, cadastrar chave) |
| `QIT001013` | 401 | senha incorreta (a resposta diz quantas tentativas restam) |
| `QIT001014` | 409 | a conta já está nesse status |
| `QIT001015` | 404 | conta de destino não encontrada |
| `QIT001016` | 409 | conta de destino bloqueada |
| `QIT001017` | 423 | 3ª senha incorreta seguida: a conta acabou de ser bloqueada |
| `QIT001020` | 409 | `transaction_key` já usado por outra operação, com outros dados (a mensagem diz o tipo e o valor só se a operação for da mesma conta) |
| `QIT001021` | 422 | origem e destino são a mesma conta |
| `QIT001022` | 422 | saldo não cobre valor + tarifa (a mensagem mostra os valores) |
| `QIT001023` | 422 | passa do limite diário de saídas (a mensagem diz quanto ainda cabe hoje) |
| `QIT001024` | 422 | saída acima da renda com a cota do mês esgotada — conta bloqueada |
| `QIT001030` | 404 | chave Pix não encontrada |
| `QIT001031` | 409 | chave Pix já cadastrada em outra conta |
| `QIT001032` | 422 | chave `cpf` que não é o CPF do dono |
| `QIT001033` | 422 | a conta já tem 5 chaves |
| `QIT001034` | 422 | a chave Pix é da própria conta de origem |
| `QIT001035` | 409 | a chave Pix já está cadastrada nesta mesma conta |
| `QIT001040` | 503 | não foi possível conectar à Receita ou à Serasa (fora do ar ou endereço errado) |
| `QIT001041` | 502 | Receita ou Serasa respondeu com erro HTTP |
| `QIT001042` | 502 | Receita ou Serasa respondeu fora do formato combinado (a mensagem diz o que faltou) |
| `QIT001043` | 502 | Receita ou Serasa recusou a credencial desta API (é configuração) |
| `QIT001044` | 422 | o CPF não existe na base da Receita |
| `QIT001050` | 422 | data de nascimento no futuro |
| `QIT001051` | 422 | data de nascimento de mais de 130 anos |

A convenção: **409** é conflito com o que já está no banco; **422** é
"o pedido foi entendido, e a regra não deixa"; **502/503** é um serviço
ou o banco que falhou, e o mesmo pedido pode ser repetido. Os códigos de
negócio andam em faixas: `00100x` cliente, `00101x` conta e senha,
`00102x` dinheiro, `00103x` Pix, `00104x` Receita e Serasa, `00105x`
data de nascimento. Código repetido derruba a API no start
(`error_verification`) — de propósito.

---

## 12. A licença

MIT — veja o arquivo `LICENSE`.
