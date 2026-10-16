# SPEC-006A — Concessões por fila e isolamento de consultas

**Implementação inicial, aguardando homologação local.**  
Base: `feat/005-rbac-auto-dispatch`; PR separado da POC 0.5.  
Constituição e planejamento: `docs/architecture/RFC-006-enterprise-operating-model.md` (branch de RFC) e SPEC-006 a SPEC-013.

## Objetivo

Criar a primeira camada de segurança que faltava na POC: papel SUPERVISOR/AUDITOR **não implica acesso a todas as filas**. O backend valida a fila por requisição e filtra listagens/contadores antes de serializar a resposta. Operadores mantêm vínculo pessoal e o fluxo original de atendimento.

## Entregas efetivas nesta etapa

1. `queue_role_grants` — concessões explícitas `(user_id, queue_id, role)` com autor e data. Não se confunde com `queue_memberships` (habilitação para distribuição).
2. `queue_authorization.py` — serviços `granted_queues`, `require_queue`, `require_handoff` e `change_grant`; verificação de operação e papel.
3. `GET /v1/me/queues` — filas autorizadas do usuário em sessão.
4. `PATCH /v1/admin/queue-grants` — administrador concede/revoga permissões ao supervisor/auditor, validando operação e papel.
5. Scoping server-side em dashboard, filas, operadores, lista de atendimentos, histórico de mensagens/timeline e gestão de equipe.
6. Capacidade e presença: supervisores só ajustam operador quando **todas** as filas às quais ele pertence estão em seu escopo. A capacidade é global do operador; permitir alteração de uma única fila com efeitos nas demais seria inseguro.
7. Acesso a `/v1/outbox` negado a supervisor/auditor; não compartilhar payloads externos.
8. Historicamente transferidos: sem modelo de segmento ainda, **o backend nega todo o histórico do ticket** para supervisores/auditores, inclusive ao possuir a fila atual. A listagem de tickets não expõe o ticket transferido aos papéis escopados. Isso é temporário e intencional; a SPEC-006B implementará leitura por segmento sem exibir indevidamente N1 a N2.
9. Contas demonstrativas: supervisor recebe N1/N2, auditor recebe somente N1. Seed registrado em `demo_seed_revisions` apenas uma vez; revogações administrativas não são refeitas após reinício.
10. Testes de isolamento/IDOR e não regressão adicionados em `tests/test_queue_scopes.py`, com auditor N1 e chamadas diretas à API, supervisor revogado, usuário de outra fila, transferência e contadores.

## Limitações conhecidas desta entrega

- O modelo `AuthUser.role` ainda representa somente um papel principal; a SPEC-006B evoluirá os grants para múltiplos papéis por usuário, validade e autorização de segmentos.
- `Base.metadata.create_all` continua usado na POC e cria a nova tabela adicional; **isso não é Alembic nem é um processo de migração de produção**. Não publicar fora de localhost.
- Enquanto não houver segmentos, auditor/supervisor não conseguem ler o histórico completo de tickets transferidos. Não fazer workaround que libere conteúdos de outra fila.
- A administração dos grants é uma API inicial, sem UI, versionamento formal nem log imutável de revogação. Esses itens são gates antes de produção.
- Os testes foram adicionados ao repositório; execução Pytest/Ruff/frontend no Windows ainda é necessária.

## Gates de aceitação — obrigatórios antes de promover

- [ ] `.\start.cmd --check`: todos os testes Python, Ruff e frontend.
- [ ] Auditor N1 vê exclusivamente filas e tickets N1; chamada direta a mensagens N2 retorna 404.
- [ ] Supervisor N1 não muda membro da fila N2, não vê rotação N2, não cadastra ticket N2.
- [ ] Revogação do grant em sessão já autenticada bloqueia a próxima consulta.
- [ ] Supervisão ainda ajusta capacidade/presença de seus operadores sem afetar indevidamente outras filas.
- [ ] Ticket transferido não expõe histórico N1/N2 integral a supervisores/auditores.
- [ ] Login Ana/Bruno, N1 default, distribuição, oferta, chat, transferência e fechamento continuam funcionais.
- [ ] Banco existente não perde contas, senha, tickets, eventos ou fila.
- [ ] Nenhum GitHub Actions.

## Homologação Windows

```powershell
cd C:\Projetos\hub-handoff\hub-handoff-multichannel
git status --short
git fetch origin
git switch --track origin/feat/006-queue-scoped-authorization
git pull --ff-only origin feat/006-queue-scoped-authorization
.\start.cmd --check
.\start.cmd
```

Se branch já existir localmente, usar `git switch feat/006-queue-scoped-authorization`. Não apagar SQLite, não redefinir senhas e não utilizar dados reais.

## Próxima fatia: SPEC-006B

1. Alembic (migration baseline segura para banco SQLite já populado, scripts backup/restore);
2. `role_assignments` com papéis independentes e escopo por operação/fila;
3. `session_queue_segments` e provenance por mensagem/evento, inclusive transferência;
4. Logs append-only de decisões e leituras confidenciais;
5. Paginação e filtros seguros para auditores;
6. Regresso das visualizações históricas agora segmentadas, com testes negativos.

**Não começar SPEC-007 Administração completa antes da homologação e do isolamento correto da SPEC-006.**
