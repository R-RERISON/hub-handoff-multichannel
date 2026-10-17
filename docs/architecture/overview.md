# Arquitetura atual — Handoff Hub Multichannel (POC SQLite / SPEC-006B-5.2)

## Contexto e fronteira do canal

Usuário simulado → FastAPI → SQLite → Workspaces React. Canal corporativo futuro: bot original → adapter Embedded → Hub → Mesa do Operador → outbox → adapter → canal Teams original. **Ainda não existe comunicação Teams real.** Scripts Tornado/legados são referências de comportamento, nunca dados ou código para migração.

O Handoff Hub é responsável pelo ciclo da sessão, fila, alocação, transferência, mensagens, autorização e auditoria. Identidade/bot/conversationId do canal original **não** pertencem ao Hub.

## Stack do candidato à main

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2, serviço automático de despacho SQLite (BEGIN IMMEDIATE, capacity, presence/heartbeat, FIFO e rodízio persistido).
- **Persistência:** SQLite WAL em um host, 17 tabelas de POC legado e **5 tabelas aditivas versionadas** na revisão 006b4: três de segmentos/proveniência, `history_access_audit` e `security_decisions`. SQLite original não versionado **não recebe essas tabelas implicitamente**.
- **Frontend:** React/TypeScript/Vite; portais distintos de Operador, Supervisão, Administração e Laboratório; navegação por perfil **não substitui** backend RBAC.
- **Autenticação local:** `auth_users` individuais, senha hasheada, sessões Bearer opacas, grants `QueueRoleGrant`. **Não é Entra ID/OIDC**.
- **Testes:** Pytest, Ruff, 11 testes de contrato frontend, TypeScript/Vite e gate de laboratório `scripts/release_probe.py`. **Sem GitHub Actions**.

## Segurança / proveniência

1. `SUPERVISOR` e `AUDITOR` têm visibilidade de fila com grant explícito e operação correspondente; não podem responder ou assumir atendimento do operador. `ADMIN` gerencia grants, sem operar como atendente.
2. O histórico completo de sessões transferidas não é liberado para perfis de supervisão. Um endpoint separado permite consultar **apenas segmentos e itens marcados `RUNTIME/VERIFIED`** da fila concedida; sem backfill de conversas legadas.
3. A revisão 006b3 introduziu o diário transacional das leituras autorizadas `history_access_audit`: falha de escrita **bloqueia entrega do conteúdo protegido**.
4. A revisão 006b4 adicionou `security_decisions`: negativa 403/404 *após autenticação e no handler de VERIFIED* registrada em transação independente (best effort, retorno negado não muda); grant/revoke `APPLIED` é gravado **na mesma transação** da concessão.
5. Auditoria ainda não é imutável/WORM; autenticação externa, retenção, política LGPD e observabilidade de falhas do journal são pendências de produção.

## Migrações e banco original

- **Original:** `data/handoff-poc.db` com 17 tabelas, sem `alembic_version`. Somente leitura e proteção do histórico; nunca migrar no fluxo comum nem para validar o release.
- **Lab descartável:** `schema_admin create --confirm-offline` cria 006b4 **apenas se o SQLite não existir**. Migrações de cópias requerem estágio correto, `--confirm-offline`, backup verificado e checagem de contagem de linhas.
- **QA release:** `scripts/release_probe.py` cria banco temporário e não lê o original; `scripts/prepare-main-integration-lab.ps1` prepara credenciais e banco sintéticos **fora do repositório** para inspeção visual.
- Adoção do legado POC só seria possível por comandos opt-in previstos para ambientes autorizados; **não é autorização para executá-los no banco original do desenvolvedor**.

## Evolução e bloqueadores

1. Revisão do PR de integração #28 e homologação E2E/visual de 006B-4.x/5.x com banco sintético.
2. Autenticação corporativa Entra ID/OIDC, multioperação reforçada, política de dados, retenção e logs invioláveis/WORM.
3. SQL Server após revisão de constraints/isolamento/locking e migrações específicas; `BEGIN IMMEDIATE` SQLite não é portável.
4. Workers/outbox externos e adaptador Teams Embedded, idempotência de entrega e reconciliação; canais nativos futuros.
5. SLA/CSAT e observabilidade/performance corporativa.

## Fontes técnicas

- https://www.sqlite.org/wal.html
- https://www.sqlite.org/lang_transaction.html
- https://docs.sqlalchemy.org/en/20/dialects/sqlite.html
- https://learn.microsoft.com/en-us/microsoftteams/platform/bots/how-to/conversations/send-proactive-messages

**Estado:** POC local — não homologado para produção.
