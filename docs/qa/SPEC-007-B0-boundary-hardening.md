# SPEC-007 / B0 — Boundary de operações, pessoas e membership

**Status:** CODED / B0.1_WINDOWS_QA_PASS / SECURITY_REVIEW_REQUIRED / INTEGRATION_PENDING.
**Branch:** feat/007b0-people-boundary-hardening, empilhada no
PR #48 (SPEC-007/A1.2), que teve PASS de código em 6503d30.
**Modo:** SQLite POC, sem esquema novo, somente laboratório TEMP sintético.

## Problema analisado

O middleware de autenticação já exigia grants por fila para
SUPERVISOR e restringia o role de determinadas rotas. Entretanto
endpoints legados de gerenciamento ainda podiam confiar no preflight
sem conferir a identidade e o escopo novamente **dentro da transação
de alteração**. Em particular, capacidade/presença de operador
não revalidavam operation_id para ADMIN no handler de escrita.
O impacto potencial é alterar operador de outra operação quando
identificado por ID conhecido.

## Contrato B0 implementado

- PATCH /v1/queues/{queue_id}/members/{operator_id}
  - Somente ADMIN ou SUPERVISOR com grant de gerenciamento na fila.
  - Revalida fila da operação autenticada dentro de BEGIN IMMEDIATE.
  - Operador deve pertencer à mesma operação; destino incompatível retorna 404.
  - Remover membership com oferta ou atendimento na fila continua 409.
- PATCH /v1/operators/{operator_id}/capacity
  - ADMIN gerencia apenas sua operação.
  - SUPERVISOR só altera operadores com TODAS as memberships
    em filas concedidas; revalidação dentro da transação.
  - Capacidade abaixo da ocupação mantém 409.
- PATCH /v1/operators/{operator_id}/presence
  - ADMIN gerencia apenas sua operação; SUPERVISOR exige mesmo
    escopo de memberships; OPERATOR altera apenas a própria presença.
  - Auditor permanece somente leitura.
- 404 para destino fora da operação no acesso ADMIN, evitando
  exposição do nome/identidade de outras operações. Sem retorno de
  dados de conversa, segredo, senha ou token.

Os guards preexistentes em authenticate() e assert_access()
permanecem ativos; os novos guards são uma segunda barreira de
autorização no momento da escrita, não substituem autenticação.
No B0.1, AuthSession e AuthUser são relidos dentro de BEGIN IMMEDIATE antes
das três mutações. Sessão revogada/expirada recebe 401; usuário desativado
ou papel já alterado é reavaliado antes da autorização. A exceção sem sessão
continua limitada ao create_app(api_key=...) explícito em testes.
O legado X-POC-Key em modo de teste NÃO é autenticação de produção.

## Testes B0/B0.1

Arquivo tests/test_spec007_people_boundaries.py:
1. ADMIN demo tenta editar capacidade, presença e membership fora da operação:
   404, sem divulgar nomes nem alterar os dados.
2. SUPERVISOR e AUDITOR não editam operador/fila fora de escopo;
   AUDITOR não realiza mutações locais.
3. ADMIN local, SUPERVISOR com grants e OPERATOR na própria presença
   continuam funcionais sem elevação implícita de grant.
4. Revogação da sessão após o preflight impede a escrita (401).
5. Mudança de papel após o preflight é reavaliada (403).
6. SUPERVISOR com grants parciais não altera capacidade/presença de operador
   membro de múltiplas filas.
7. Capacidade abaixo de atendimentos ativos é recusada (409).
8. Remoção de membership com atendimento ativo é recusada (409).

## QA no Windows

Em worktree DESCARTÁVEL de origin/feat/007b0-people-boundary-hardening:
- Verificar SHA do PR e executar start.cmd --check integral.
- Rodar testes específicos e seguir o contrato de autorização;
  comparar SQL antes/depois de requests negados em SQLite TEMP.
- Regressão de sessão N1→N2, rotação de fila e POC 006b4/007a2.
- Confirmar que o banco data/handoff-poc.db original nunca é usado.

## Evidência Windows — B0.1 — 2026-10-19

No commit `49a28ad`, `.\start.cmd --check` terminou com exit code 0:
170 testes Python aprovados, 1 ignorado, Ruff aprovado, 16 testes de
arquitetura frontend, TypeScript e Vite (1.601 módulos). Os oito testes
de `test_spec007_people_boundaries.py` passaram.

O ADMIN sintético recebeu HTTP 404 para capacidade, presença e membership
fora da operação; a resposta não divulgou identidades e os dados permaneceram
inalterados. Testes adicionais cobriram sessão revogada e papel alterado entre
preflight e escrita, grants parciais para operador multi-fila, capacidade
abaixo da ocupação e remoção de membership com atendimento ativo.

Execução em worktree descartável e fixtures SQLite TEMP; nenhum uso do banco
original ou teste visual foi necessário para este incremento sem mudança de UI.
Os eventos administrativos de capacity/presence/membership continuam pendentes
para B1/B2. A revisão independente de segurança continua obrigatória antes do
merge; não houve promoção à `main`.

## Fora do escopo B0

Ainda não implementa interface de pessoas nem gerenciador premium
de membership/grants. Auditoria transacional para membership,
capacidade e presença deve ser decidida na B1/B2; o journal atual
006b4 registra grants/QUEUE_CREATED, não estes eventos.
Nenhuma promoção à main, rollback produtivo ou SSO. Revisar
o diff antes de autorizar integração.
