# RFC v8 → v8.1: trechos corrigidos

Written for: o time (Rafael Almeida · Guilherme Silva Xavier) ao atualizar o PDF da RFC antes da banca.

A RFC v8 está em PDF, fora do repositório. Por isso, este arquivo traz o texto corrigido de cada trecho que mudou, pronto para colar no documento. Cada trecho diz a seção, o texto atual e o texto novo.

Quatro coisas mudaram, e todas são de texto ou de decisão já tomada no código:

1. A senha é conferida fora da trava (§2.4, §5.3, §6.1).
2. Mais recusas viram evento (§2.3, §5.7).
3. A abertura de conta grava evento para cliente bloqueado e para segunda conta (§5.2).
4. O resultado dos testes está descrito com o número real (§7.2).

---

## §2.3 Status, bloqueios e eventos

**Atual:**

> Vira evento (event) toda mudança de estado, todo alerta de renda e toda recusa que depende do estado da conta (saldo, limite, renda, senha, conta bloqueada, ID em conflito), confirmado antes da resposta de erro. Erro de formato e recurso inexistente vão só para o log.

**Novo:**

> Vira evento (event) toda mudança de estado, todo alerta de renda e toda recusa que depende do estado do cliente ou da conta: saldo, limite, renda, senha, conta bloqueada, ID em conflito, cliente bloqueado na análise ou que já tem conta, e chave Pix que já existe ou que passaria do limite de 5 chaves. O evento é gravado antes da resposta de erro. Erro de formato e recurso inexistente vão só para o log.

---

## §2.4 Pedidos simultâneos

**Atual:**

> Antes de ler saldo, limite, renda e senha, a API trava as contas envolvidas (SELECT … FOR UPDATE) em ordem crescente de id; quem chega depois espera e lê o valor já atualizado. Operação, lançamentos e saldos vão num único commit, e toda recusa acontece antes de mover dinheiro. O CHECK de saldo e o UNIQUE do ID são a última barreira.

**Novo:**

> Antes de ler saldo e limite, e antes de gravar o contador de senha, a API trava as contas envolvidas (SELECT … FOR UPDATE) em ordem crescente de id; quem chega depois espera e lê o valor já atualizado. A senha é a única exceção à ordem: o hash da conta não muda (não existe troca de senha), então ela é conferida antes da trava e só o resultado é registrado com a conta travada (5.3). Operação, lançamentos e saldos vão num único commit, e toda recusa acontece antes de mover dinheiro. O CHECK de saldo e o UNIQUE do ID são a última barreira.

---

## §5.2 Abrir conta

**Atual:**

> A senha tem 6 dígitos e só é enviada na abertura. É guardada com bcrypt (password_hash) e nunca volta numa resposta nem vai para o log.

**Novo:**

> A senha tem 6 dígitos. Ela é cadastrada na abertura e enviada depois em toda operação que tira dinheiro ou mexe nas chaves Pix (5.3). É guardada com bcrypt (password_hash) e nunca volta numa resposta nem vai para o log.

**Atual (eventos do fluxo):** o fluxo não diz que as recusas geram evento.

**Acrescentar ao texto do fluxo:**

> Cliente bloqueado na análise e cliente que já tem conta são recusados com evento (operation_refused), ligado ao cliente.

---

## §5.3 Autenticar

**Atual:**

> A senha é conferida com a conta travada. Cada erro soma 1 em failed_password_attempts e gera um evento; um acerto zera o contador. A 3ª errada seguida bloqueia a conta. Contador e evento são gravados mesmo com a recusa (2.3).

**Novo:**

> A senha é conferida antes da trava, porque o hash da conta não muda. O resultado é então registrado com a conta travada: o contador é lido e gravado sob trava, para que duas tentativas simultâneas não se percam. Cada erro soma 1 em failed_password_attempts e gera um evento; um acerto zera o contador. A 3ª errada seguida bloqueia a conta. Contador e evento são gravados mesmo com a recusa (2.3).

**Observação para o fluxo 5.5 e 5.7:** nos diagramas, o losango "Senha confere?" aparece depois de "Trava as duas contas". Na prática, o bcrypt roda antes da trava, e o losango de senha que registra o contador continua depois dela. Basta uma nota de rodapé no diagrama.

---

## §5.7 Cadastrar chave Pix

**Acrescentar ao texto do fluxo:**

> As recusas deste fluxo que dependem do estado da conta viram evento (operation_refused), ligado à conta: chave já cadastrada nesta conta, chave já cadastrada em outra conta e limite de 5 chaves. O evento guarda o tipo da chave, nunca o valor: a chave é dado pessoal (CPF, e-mail ou telefone), e o evento fica no banco. Recusa de formato (valor errado para o tipo) não gera evento.

---

## §6.1 Escolhas e custos (nova linha na tabela)

| ESCOLHEMOS | DESCARTAMOS | POR QUÊ, E O CUSTO |
|---|---|---|
| Conferir a senha antes da trava; registrar o contador com a trava | Conferir a senha com a conta travada | O bcrypt leva ~0,3 s de propósito. Com a trava, duas operações da mesma conta esperavam uma pela outra esse tempo todo: 2,55 s para duas saídas simultâneas, contra 1,3 s depois da mudança. A consistência não muda, porque o hash não muda. Custo: a leitura do hash acontece fora da trava. |

---

## §7.2 O principal problema resolvido

**Atual:**

> ... Os oito cenários testados no PostgreSQL (saídas simultâneas, limite do dia, reenvios, senha, renda e troca de tarifa) deram o resultado esperado, e o saldo de todas as contas continuou igual à soma dos lançamentos.

**Novo:**

> ... A suíte automatizada tem 124 testes de integração, rodados contra a API e o PostgreSQL. Eles cobrem saídas simultâneas, limite do dia, reenvios, concorrência de ID, senha, renda e troca de tarifa, e em 9 pontos verificam que o saldo de cada conta é igual à soma dos seus lançamentos.

---

## Versão

Ao colar, atualize a capa: **VERSÃO 8.1**, com a data da alteração, e uma linha de histórico: *"v8.1: senha conferida fora da trava (2.4, 5.3, 6.1); eventos para recusas de cliente e chave Pix (2.3, 5.2, 5.7); texto dos testes (7.2)."*
