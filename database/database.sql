-- ═════════════════════════════════════════════════════════════════
-- Banco do time — schema da v1 (RFC v8, seção 3)
--
-- São 11 tabelas, em três grupos:
--   catálogos ........... status, level, transaction_type, fee
--   cadastro ............ client, account, pix_key
--   dinheiro e histórico  transaction, deposit, entry, event
--
-- Duas convenções valem para o arquivo inteiro:
--
-- • Dinheiro é BIGINT em centavos: R$ 1,50 é 150. Nunca float.
-- • Instante é TIMESTAMPTZ (com fuso). O "dia" do limite diário e o
--   "mês" da cota de alertas seguem o calendário de São Paulo (RFC 2.1),
--   e só um instante com fuso permite fazer essa conta sem depender do
--   fuso em que o servidor do banco foi configurado.
--
-- Este arquivo roda UMA vez, quando o banco nasce. Mudou algo aqui?
--     docker compose down -v
--     docker compose up
-- ═════════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────────
-- Catálogos
-- ─────────────────────────────────────────────────────────────────

-- Um catálogo só, dividido entre cliente e conta (RFC 2.3).
CREATE TABLE status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO status (enumerator, description) VALUES
('active', 'Ativo'),
('blocked', 'Bloqueado');

-- O nível guarda as REGRAS do cliente como dado (RFC 2.1): mudar o
-- limite ou a regra de renda é um UPDATE, não um deploy.
-- daily_outflow_limit NULL quer dizer "sem limite" (Ouro).
CREATE TABLE level(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    description                     VARCHAR(255) NOT NULL,
    daily_outflow_limit             BIGINT,
    income_multiple                 SMALLINT NOT NULL,
    income_alerts_per_month         SMALLINT NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator),
    CHECK(daily_outflow_limit IS NULL OR daily_outflow_limit > 0),
    CHECK(income_multiple > 0),
    CHECK(income_alerts_per_month >= 0)
);

INSERT INTO level (enumerator, description, daily_outflow_limit, income_multiple, income_alerts_per_month) VALUES
('silver', 'Prata', 100000, 2, 3),
('gold', 'Ouro', NULL, 2, 3);

CREATE TABLE transaction_type(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO transaction_type (enumerator, description) VALUES
('deposit', 'Depósito'),
('transfer', 'Transferência'),
('pix', 'Pix');

-- A tarifa por nível e tipo de operação, com vigência (RFC 2.1).
-- Vigente é a linha sem fim (ends_at NULL). Mudar a tarifa é fechar a
-- vigente e abrir outra, na mesma transação:
--
--     UPDATE fee SET ends_at = NOW() WHERE ... AND ends_at IS NULL;
--     INSERT INTO fee (level_id, transaction_type_id, amount) VALUES (...);
--
-- Sem linha vigente, não há tarifa — é o caso do depósito.
CREATE TABLE fee(
    id                              SERIAL PRIMARY KEY,
    level_id                        INTEGER NOT NULL REFERENCES level(id),
    transaction_type_id             INTEGER NOT NULL REFERENCES transaction_type(id),
    amount                          BIGINT NOT NULL,
    starts_at                       TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    ends_at                         TIMESTAMPTZ,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    CHECK(amount >= 0),
    CHECK(ends_at IS NULL OR ends_at > starts_at)
);

-- "No máximo uma vigente por par" é um índice único PARCIAL: só as
-- linhas sem fim entram nele, então o histórico pode ter quantas
-- tarifas fechadas quiser.
CREATE UNIQUE INDEX fee_one_current_per_level_and_type
    ON fee(level_id, transaction_type_id)
    WHERE ends_at IS NULL;

-- R$ 1,50 para transferência e Pix, nos dois níveis.
INSERT INTO fee (level_id, transaction_type_id, amount)
SELECT level.id, transaction_type.id, 150
FROM level, transaction_type
WHERE transaction_type.enumerator IN ('transfer', 'pix');


-- ─────────────────────────────────────────────────────────────────
-- Cadastro
-- ─────────────────────────────────────────────────────────────────

-- level_id fica vazio no cliente bloqueado no cadastro: ele não tem
-- nível porque nunca vai ter conta (RFC 5.1).
CREATE TABLE client(
    id                              SERIAL PRIMARY KEY,
    client_key                      CHAR(36) NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    email                           VARCHAR(255) NOT NULL,
    document_number                 CHAR(14) NOT NULL,
    birthdate                       DATE NOT NULL,
    monthly_income                  BIGINT NOT NULL,
    status_id                       INTEGER NOT NULL REFERENCES status(id),
    level_id                        INTEGER REFERENCES level(id),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(client_key),
    UNIQUE(document_number),
    UNIQUE(email),
    CHECK(monthly_income >= 0)
);

-- UNIQUE(client_id) é a regra "uma conta por cliente" escrita no banco.
-- password_hash tem 60 caracteres porque é o tamanho fixo de um bcrypt.
CREATE TABLE account(
    id                              SERIAL PRIMARY KEY,
    account_key                     CHAR(36) NOT NULL,
    client_id                       INTEGER NOT NULL REFERENCES client(id),
    status_id                       INTEGER NOT NULL REFERENCES status(id),
    balance                         BIGINT NOT NULL DEFAULT 0,
    password_hash                   VARCHAR(60) NOT NULL,
    failed_password_attempts        SMALLINT NOT NULL DEFAULT 0,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(account_key),
    UNIQUE(client_id),
    CHECK(balance >= 0),
    CHECK(failed_password_attempts >= 0)
);

-- Uma chave aponta para uma conta só: o UNIQUE(key_value) é o que barra
-- duas contas cadastrando a mesma chave ao mesmo tempo (RFC 5.7).
CREATE TABLE pix_key(
    id                              SERIAL PRIMARY KEY,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    key_type                        VARCHAR(10) NOT NULL,
    key_value                       VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(key_value),
    CHECK(key_type IN ('cpf', 'email', 'phone', 'random'))
);

CREATE INDEX pix_key_account_id ON pix_key(account_id);


-- ─────────────────────────────────────────────────────────────────
-- Dinheiro e histórico
-- ─────────────────────────────────────────────────────────────────

-- A operação. O transaction_key é gerado por quem chama e é o ID da
-- operação na API inteira; o UNIQUE dele é a última barreira contra o
-- dinheiro movido duas vezes (RFC 2.2).
--
-- origin_account_id é vazio no depósito (o dinheiro vem de fora) e
-- pix_key_id só existe no Pix. fee é o valor COBRADO, copiado da tarifa
-- vigente: se a tarifa mudar amanhã, a operação de hoje continua dizendo
-- quanto pagou.
CREATE TABLE transaction(
    id                              SERIAL PRIMARY KEY,
    transaction_key                 CHAR(36) NOT NULL,
    transaction_type_id             INTEGER NOT NULL REFERENCES transaction_type(id),
    origin_account_id               INTEGER REFERENCES account(id),
    destination_account_id          INTEGER NOT NULL REFERENCES account(id),
    pix_key_id                      INTEGER REFERENCES pix_key(id),
    amount                          BIGINT NOT NULL,
    fee_id                          INTEGER REFERENCES fee(id),
    fee                             BIGINT NOT NULL DEFAULT 0,
    above_income                    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(transaction_key),
    CHECK(amount BETWEEN 1 AND 100000000),
    CHECK(fee >= 0),
    CHECK(origin_account_id IS NULL OR origin_account_id <> destination_account_id)
);

-- O limite diário e a cota de alertas do mês perguntam "quanto esta
-- conta enviou entre tal e tal instante": é exatamente este índice.
CREATE INDEX transaction_origin_created_at ON transaction(origin_account_id, created_at);

-- O que só o depósito tem. TED sempre com banco de origem; espécie, nunca.
CREATE TABLE deposit(
    id                              SERIAL PRIMARY KEY,
    transaction_id                  INTEGER NOT NULL REFERENCES transaction(id),
    method                          VARCHAR(10) NOT NULL,
    depositor_name                  VARCHAR(255) NOT NULL,
    depositor_document_number       CHAR(14) NOT NULL,
    source_bank_code                CHAR(3),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(transaction_id),
    CHECK(method IN ('cash', 'ted')),
    CHECK(
        (method = 'ted' AND source_bank_code IS NOT NULL)
        OR (method = 'cash' AND source_bank_code IS NULL)
    )
);

-- Os lançamentos: de onde sai o extrato. O valor tem sinal (entrada
-- positiva, saída negativa) e o sinal tem de bater com o tipo.
-- balance_after é o saldo da conta logo depois deste lançamento.
CREATE TABLE entry(
    id                              SERIAL PRIMARY KEY,
    transaction_id                  INTEGER NOT NULL REFERENCES transaction(id),
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    entry_type                      VARCHAR(20) NOT NULL,
    amount                          BIGINT NOT NULL,
    balance_after                   BIGINT NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    CHECK(entry_type IN ('deposit', 'transfer_out', 'transfer_in', 'pix_out', 'pix_in', 'fee')),
    CHECK(balance_after >= 0),
    CHECK(
        (entry_type IN ('deposit', 'transfer_in', 'pix_in') AND amount > 0)
        OR (entry_type IN ('transfer_out', 'pix_out', 'fee') AND amount < 0)
    )
);

-- O extrato pede "os lançamentos desta conta, do mais novo para o mais
-- antigo": o índice já guarda as linhas nessa ordem.
CREATE INDEX entry_account_created_at ON entry(account_id, created_at DESC, id DESC);

-- Mudanças de estado, alertas e recusas de negócio (RFC 2.3), ligados a
-- quem interessar: cliente, conta, operação. request_id é o mesmo
-- identificador que aparece no log e no cabeçalho X-Request-ID.
CREATE TABLE event(
    id                              SERIAL PRIMARY KEY,
    event_key                       CHAR(36) NOT NULL,
    event_type                      VARCHAR(50) NOT NULL,
    severity                        VARCHAR(10) NOT NULL,
    client_id                       INTEGER REFERENCES client(id),
    account_id                      INTEGER REFERENCES account(id),
    transaction_id                  INTEGER REFERENCES transaction(id),
    request_id                      VARCHAR(64),
    detail                          JSONB NOT NULL DEFAULT '{}',
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(event_key),
    CHECK(severity IN ('info', 'warning', 'critical'))
);

CREATE INDEX event_account_id ON event(account_id);
CREATE INDEX event_client_id ON event(client_id);
