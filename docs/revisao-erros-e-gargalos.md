# Revisão: tratamento de erros e gargalos

Revisão feita sobre a API v1 em 12/10/2026. Tudo o que está marcado como
**corrigido** está no código e coberto pelos testes (121 testes passando,
96 antigos + 25 novos). O que está em **recomendações** ficou de fora de
propósito: muda regra de negócio, segurança ou infraestrutura, e é decisão
do time.

## 1. Erros com mensagem própria

Antes, vários casos diferentes caíam no mesmo erro: todo problema de
schema respondia "Payload Inválido" com a regex crua em inglês, Receita
fora do ar e Receita lenta diziam as duas "não respondeu a tempo", e
banco fora do ar, conta travada ou pool esgotado viravam o mesmo
500 "erro interno". Agora cada caso tem código e mensagem próprios, e o
erro de um campo traz `field` na resposta.

| Situação | Antes | Agora |
|---|---|---|
| Corpo que não é JSON | `QIT000001` "JSON decode error in 1" | `QIT000003` "O corpo da requisição não é um JSON válido (erro perto da posição 1)" |
| Corpo vazio | `QIT000001` "Field required" | `QIT000004` "Esta rota precisa de um corpo em JSON" |
| Corpo é lista | `QIT000001` "Input should be a valid dictionary" | `QIT000005` "O corpo precisa ser um objeto JSON" |
| Campo faltando | `'email' is a required property` / "Payload Inválido" | "O campo 'email' é obrigatório e não foi enviado" + `field` |
| Formato errado | `'123' does not match '^\d{3}...$'` | "O campo 'document_number' precisa ser um CPF no formato 000.000.000-00" |
| Valor com centavos | `10.5 is not of type 'integer'` | "precisa ser um número inteiro, em centavos (R$ 10,50 = 1050)" |
| TED sem banco / espécie com banco | `False schema does not allow '001'` | "Depósito em espécie não tem banco de origem: não envie source_bank_code" |
| Sem token / token errado | mesma mensagem | "falta o header INTERNAL-TOKEN" × "o header enviado está errado" |
| Rota ou método errado | texto genérico | "A rota GET /contas não existe" / "não aceita DELETE. Métodos aceitos: GET" |
| Receita/Serasa recusou conexão | "não respondeu a tempo" (mentira) | `QIT001040` "não foi possível conectar" |
| Receita/Serasa respondeu 500 | "não respondeu a tempo" | `QIT001041` "respondeu com erro (HTTP 500)" |
| Resposta fora do formato | "não respondeu a tempo" | `QIT001042` "formato inesperado (campo score não é um número inteiro)" |
| Token da Receita recusado | "não respondeu a tempo" | `QIT001043` "recusou a credencial desta API" |
| CPF que a Receita não conhece (404) | "não respondeu a tempo" | `QIT001044` "não existe na base da Receita" |
| Banco fora do ar | `500` erro interno | `503 QIT000503`, avisando que, se caiu na hora de gravar, é preciso conferir antes de repetir |
| Conta travada por outra operação | requisição esperava para sempre | `409 QIT000011` depois de 5 s |
| Consulta lenta demais | sem limite | `503 QIT000504` depois de 15 s |
| Pool de conexões esgotado | `500` depois de 30 s | `503 QIT000429` depois de 10 s |
| CPF/e-mail duplicado na corrida | `500` | `409 QIT000012` (ou o duplicado específico) |
| Valor grande demais para o banco | `500` | `422 QIT000013` |
| Destino da transferência não existe | `QIT001010` (igual à origem) | `QIT001015` "A conta de destino não foi encontrada" |
| Destino bloqueado | `QIT001012` (igual à origem) | `QIT001016` |
| 3ª senha errada | `409 QIT001012` "conta bloqueada" | `423 QIT001017` "bloqueada agora por segurança" |
| Pix para a própria chave | `QIT001021` (transferência para si) | `QIT001034` "a chave é da própria conta" |
| Chave Pix já na mesma conta | `QIT001031` (como se fosse de outra) | `QIT001035` |
| Nascimento no futuro | "The client is -64 years old" | `QIT001050`; mais de 130 anos: `QIT001051` |
| CPF de quem depositou inválido | "O CPF informado não é válido" | `field: depositor_document_number`, "O CPF de quem depositou..." |
| Saldo insuficiente | "Saldo insuficiente para o valor mais a tarifa" | "precisa de R$ 51,50 (R$ 50,00 + tarifa de R$ 1,50), e o saldo é R$ 10,00" |
| Limite diário | "passa do limite diário" | "hoje já saíram R$ 700,00, e ainda cabem R$ 300,00" |
| Conta bloqueada | "A conta está bloqueada" | diz o que ela não pode fazer: receber depósitos, enviar, cadastrar chave |
| `transaction_key` repetido com outros dados | "já foi usado" | diz o tipo e o valor da operação original, mas só se ela for da mesma conta (não expõe dados de outra conta) |

Nenhuma mensagem repete o valor recebido: a senha nunca volta numa
resposta de erro.

Só o `UNIQUE` vira `409`: uma violação de `CHECK` ou `NOT NULL` quer
dizer que o código deixou passar um dado que não devia, então continua
sendo bug.

O erro que ninguém previu (bug) continua sendo `500`, mas agora sai com
o `X-Request-ID` no header, o mesmo id no corpo ("informe o código ... ao
suporte") e a linha `SAIU 500` no log. Antes, o 500 escapava dos
middlewares e saía sem o id, sem como achar o erro no log.

## 2. Gargalos e bugs corrigidos

**Cadastro segurava conexão do banco esperando a Receita e a Serasa.** A
checagem de duplicidade abria a transação e ela ficava aberta durante as
duas chamadas externas (até 5 s cada). Com 15 cadastros lentos ao mesmo
tempo, o pool inteiro ficava parado e qualquer outra rota esperava.
Medido: um `GET /account` no meio de 15 cadastros com a Serasa lenta
levava **4,07 s**; agora leva **0,01 s**. A transação de leitura é
encerrada antes das chamadas; o `UNIQUE` continua garantindo a
duplicidade na hora de gravar.

**Senha conferida com a conta travada.** O bcrypt leva ~0,3 s de
propósito e rodava com a linha da conta travada, então duas operações da
mesma conta esperavam esse tempo uma pela outra. Medido: 8 transferências
simultâneas da mesma conta levavam **2,55 s**; agora **1,3 s**. A senha é
conferida antes da trava; com a trava, só o resultado é registrado.
Testado com 5 senhas erradas ao mesmo tempo: exatamente 3 tentativas
contadas, um bloqueio, e as outras duas recusadas como conta bloqueada.
Conta que já está bloqueada é recusada antes do bcrypt, sem gastar os
0,3 s.

**Sem limite de espera no banco.** Uma transação presa segurava a trava
da conta para sempre, e as requisições seguintes ficavam esperando até
esgotar threads e conexões. Agora o PostgreSQL recebe `lock_timeout`
(5 s), `statement_timeout` (15 s) e `idle_in_transaction_session_timeout`
(30 s), todos configuráveis (README, seção 9).

**Pool menor que o número de threads.** O uvicorn roda as rotas em até 40
threads; o pool tinha 5 conexões + 10 extras e esperava 30 s por uma
livre. Agora são 10 + 20, com espera de 10 s, configuráveis.

**Schema recompilado a cada requisição.** O `jsonschema.validate()`
confere o próprio schema toda vez (~1,26 ms por requisição). Com o
schema conferido uma vez só e guardado em memória, a validação cai para
~0,05 ms.

**Renda zero aceita.** Com `monthly_income = 0`, toda saída fica "acima
da renda": as 3 primeiras geram alerta e a 4ª bloqueia a conta, de
qualquer valor. A RFC não fixa um valor mínimo de renda; o schema agora
recusa zero com mensagem própria. É decisão do projeto, não exigência da
RFC.

**Chave de conta em maiúsculas.** A mesma conta escrita em maiúsculas
dava "não encontrada", e um reenvio legítimo com a chave em maiúsculas
virava conflito de `transaction_key`. As chaves agora são normalizadas,
assim como a chave Pix (sem espaços nas pontas e em minúsculas, nas
duas rotas: cadastro e envio).

**Listagem de clientes.** O filtro por e-mail diferenciava maiúsculas
(e o cadastro guarda em minúsculas), e `%` ou `_` no filtro de nome
funcionavam como curinga do LIKE.

**Segurança pequena.** O `INTERNAL-TOKEN` era comparado com `!=`, que
demora mais quando o começo do token acerta; agora usa
`hmac.compare_digest`. O log de entrada gravava CPF, e-mail e nome
usados como filtro na listagem; agora grava `***` no lugar do valor. E
um erro de banco não leva mais os valores do SQL (CPF, hash da senha)
para o log (`hide_parameters`).

## 3. Recomendações (não alteradas)

1. **Custo do bcrypt.** Com 12 rounds, cada transferência, Pix ou
   cadastro de chave gasta ~0,3 s de CPU: numa máquina de 2 núcleos, o
   teto é ~7 operações de dinheiro por segundo, para todas as contas
   somadas. Para uma senha de 6 dígitos, quem protege de verdade é o
   bloqueio na 3ª tentativa; 10 rounds (~70 ms) multiplicariam o teto
   por 4. Decisão de segurança do time.
2. **`/health_check` não olha o banco.** Responde 204 com o banco fora do
   ar. Vale uma rota de prontidão que faça um `SELECT 1`.
3. **Um processo só.** O `Dockerfile` sobe um uvicorn sem `--workers`, e o
   `CMD` em forma de shell não repassa o SIGTERM para o uvicorn (o
   desligamento espera o timeout do Docker). Use a forma
   `CMD ["uvicorn", ...]`. Ao aumentar os workers, some o pool de todos
   e confira o `max_connections` do PostgreSQL.
4. **Paginação por OFFSET.** O schema aceita `page` até 999.999.999; uma
   página muito alta obriga o banco a pular milhões de linhas. Agora o
   `statement_timeout` limita o estrago, mas vale um teto para `page`.
5. **Reenvio não confere a senha.** Um reenvio com o mesmo
   `transaction_key` devolve a operação original antes de olhar a senha.
   Como só sistemas internos chamam a API, o risco é baixo, mas é bom o
   time saber.
6. **Banco aceita renda zero.** O `CHECK` da tabela `client` é
   `monthly_income >= 0`; o schema já recusa zero. Ao recriar o banco,
   vale trocar para `> 0`.
7. **`.env` desatualizado.** O `.env` do projeto ainda tem as variáveis
   antigas de boleto e não tem as da Receita e da Serasa. O
   `.env.example` aponta os mocks para `http://mock:8080`, que só existe
   dentro do Docker: rodando fora dele, o cadastro responde `QIT001040`
   (antes, dizia que a Receita "não respondeu a tempo").
8. **404 da Receita.** A RFC não diz o que um 404 da Receita significa;
   o projeto passou a tratar como "CPF não existe na Receita" (QIT001044). Se a URL da Receita estiver errada no
   caminho, o erro vai dizer isso também; confira a URL ao trocar o mock
   pelo serviço de verdade.
9. **Detalhes menores.** A rota `/` mostra o PID do processo; os
   connectors abrem uma conexão nova a cada chamada (um
   `requests.Session` reaproveitaria); não há limite de tamanho para o
   corpo da requisição.
