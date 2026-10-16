# RFC-006 — Modelo operacional enterprise do Handoff Hub

**Estado:** PROPOSTA / DESIGN ONLY — sem mudanças de runtime  
**Baseline auditada:** `feat/005-rbac-auto-dispatch` (POC 0.5, 2026-10-16)  
**Princípio:** um núcleo modular, portais independentes, autorização por recurso e por fila, canais desacoplados. Preservar N1 como fallback seguro e nenhuma ação real Teams antes de adapter homologado.

## 1. Evidência: o que existe hoje (não confundir com produção)

| Capacidade | Situação | Evidência no repositório |
|---|---|---|
| React separado em portais Operador, Supervisão, Administração (landing) e Laboratório | Implementado | `web/src/App.tsx`, `web/src/workspaces/` |
| Login individual local, papéis ADMIN/SUPERVISOR/AUDITOR/OPERATOR, logout, heartbeat, tokens opacos | Implementado na POC | `poc_auth.py`, `auth_users`, `auth_sessions` |
| Autorização individual do operador em sessões | Parcial e funcional na POC | `poc_auth.py`: verificação de `operator_id` |
| Autorização por fila dos supervisores, auditores e monitores | **Não implementado** | AuthUser tem um único `role` e `operation_id`; não existem concessões por fila |
| Filas / operadores / membership / capacidade | Modelo e ações pontuais | `queues`, `operators`, `queue_memberships`, PATCH membership/capacity/presence |
| Cadastro completo de fila, operador, papéis, conectores, usuários | **Não implementado** | Sem CRUD de lifecycle; Administração é landing planejada |
| Oferta automática FIFO, rodízio persistido, capacidade, recusa, expiração | Implementado, single-node SQLite | `auto_dispatch.py`, `dispatch_turns`, `handoff_offers` |
| Intake N1 default; destino explícito permitido; seed Ana/N1 e Bruno/N2 | Implementado para demo | `demo_routing.py`, `HandoffCreate` |
| Transferência N1→N2, auditoria básica de eventos, timeline | Implementado na POC | `session_transfers`, `session_events` |
| Histórico de mensagens e dashboard consolidado | Básico, sem escopo de fila ou histórico paginado | `/v1/dashboard` retorna até 200 handoffs da operação sem filtro; `/messages` expõe conteúdo |
| Monitoria assistida, recomendações privadas e decisões do operador | **Não implementado** | Sem papel MONITOR ou coaching |
| Anexos/imagens, antivírus, storage seguro | **Não implementado** | `messages.content` textual; nenhum catálogo de attachments |
| Canal Teams/usuário final, webhook inbound, entrega e ACK real | **Não implementado** | Outbox `PENDING_ADAPTER`; contrato externo é rascunho |
| Alembic, Entra ID/OIDC, multi-instância, SQL Server, SLA/relatórios robustos | **Não implementado** | Documentação de arquitetura aponta gates futuros |

**Dívida estrutural observada:** `assert_access` autoriza supervisor e auditor por papel genérico; não limita consultas à fila. `GET /v1/dashboard` lê filas e handoffs de toda a base e `GET /v1/handoffs/{id}/messages` não filtra dados por objeto/fila para esses papéis. Isso exige correção anterior a novos portais de monitoria/auditoria. O `create_all` da POC não é estratégia de migração em produção.

## 2. Domínios e fronteiras

- **Platform Administration:** operações, estrutura de filas, canais, integrações, políticas globais, usuários e concessões. Não deve herdar automaticamente permissão para ler todo conteúdo de conversa; acesso excepcional auditado.
- **Queue Operations:** configuração delegada, equipes, horários, capacidade, roteamento, SLAs e indicadores de cada fila. Supervisor só atua em filas atribuídas.
- **Workforce & Presence:** operador, associações, skills futuras, jornada, disponibilidade, heartbeat, reserva e rodízio. UserAccount != OperatorProfile.
- **Conversation / Handoff:** atendimento, ownership atual, episódios de passagem entre filas, eventos, mensagens e estados.
- **Live Monitoring & Coaching:** leitura live permitida e recomendações **internas** para operadores, segregadas de mensagens ao usuário.
- **Compliance & Audit:** pesquisa/evidências/retenção/exportação estritamente limitadas a filas concedidas e a seus intervalos de responsabilidade.
- **Media:** arquivo/quarentena, validação, metadados, referência de mensagem, download autorizado, retenção e varredura.
- **Integration & Channel:** inbound canônico, bot de origem como proprietário do canal, inbox/outbox, ACK, retries e capability matrix.
- **Reporting:** eventos imutáveis, métricas reconstruíveis, SLA, backlog, occupancy e qualidade, com filtros autorizados.

**Arquitetura:** manter monólito modular FastAPI/React nesta etapa. Separar por módulos de domínio e ports/adapters; evitar microserviços e bancos múltiplos prematuros. SQLite só para desenvolvimento local; execução corporativa depende de storage, transações e IAM apropriados.

## 3. Personas e autoridade

| Persona | Portal proposto | Escopo efetivo | Ações |
|---|---|---|---|
| Administrador do Hub | `/administracao/*` | Plataforma / operação autorizada | CRUD de filas, conectores, integrações, políticas, usuários/grants; acesso excepcional auditado ao conteúdo |
| Supervisor | `/supervisao/filas/:queueId/*` | Conjunto de filas designadas (1..N) | Gerenciar operadores/membership, capacidade e políticas **delegadas**; dashboard e relatórios da própria fila; não enviar mensagens como operador |
| Auditor | `/auditoria/*` | Filas designadas e períodos aplicáveis | Consultar/exportar evidências autorizadas, leituras registradas; sem gestão nem resposta |
| Monitor | `/monitoria/*` | Filas designadas, sessões ativas permitidas | Acompanhar sessões, **receber e assumir pedidos de auxílio iniciados pelo operador**, orientar privadamente, registrar ACK/decisão; nunca escrever ao usuário |
| Operador | `/operador` | Apenas atendimentos próprios e memberships | Presença, ofertas, resposta, transferência, encerramento, feedback sobre recomendações |
| Usuário final | Canal do bot/app de origem | A própria conversa | Iniciar, enviar textos/anexos, receber respostas/estado; não faz login no portal de operadores |
| Integração (não-humana) | API/vínculo de canal | `integration_id` + `operation_id` autorizados | Ingerir solicitações e mensagens; receber eventos/delivery e confirmar ACK. Não tem privilégios de pessoas |

Perfis **não são hierarquias implícitas**: Supervisor não herda Monitor, Auditor não administra e Admin não se torna operador. Uma pessoa pode ter múltiplos grants de papéis e fila, mas toda decisão é avaliada no backend.

## 4. Controle de acesso: RBAC + escopo (ABAC/ReBAC)

Modelo recomendado:
- `users`: identidade; `operators`: perfil operacional separado.
- `role_definitions` e `permissions` são catálogo versionado de capacidades, ex.: `queue.read`, `queue.configure`, `queue.members.manage`, `conversation.read_live`, `conversation.read_audit`, `assistance.request`, `assistance.queue.read`, `assistance.claim`, `assistance.reply`, `assistance.read_own`, `coaching.create`, `coaching.ack`, `message.send_operator`, `media.download`, `integration.manage`.
- `role_assignments`: `user_id`, `role_id`, `scope_type` (PLATFORM|OPERATION|QUEUE), `scope_id`, validade opcional, concedido_por, motivo, revogação.
- `queue_memberships` continua sendo critério de **despacho**; `role_assignments` governa **permissões**. Não misturar.
- `queue_policy` define supervisor delegado e limites de edição; alterações sensíveis (ex.: política de retenção e acesso ao histórico) pertencem ao admin/segurança.
- Centralizar `authorize(principal, action, resource)` no serviço, incluindo escopo, tenant/operação, estado e ownership; proteger listagens com filtro SQL **antes** de paginação/contagem/ordenação.
- Acesso a uma sessão atual não dá automaticamente acesso a todo seu histórico **em outras filas**: introduzir `session_queue_segments` ou atribuição de segmento em mensagens/eventos. Auditor N1 vê por padrão apenas trecho/evidência N1; contexto interfilas somente quando política explícita permitir. Operador designado pode obter contexto necessário à continuidade do atendimento, sob autorização funcional.
- Registrar `authz_decision` para ações sensíveis e `audit_access_events` para leituras de conteúdo, exportações e download. Falha de escopo: 404 não-revelador quando apropriado, sem indicar existência de outras filas.

### Exemplos de acesso negativos obrigatórios
Auditor N1 não pode ler mensagens, anexos nem exportações de N2; supervisor N1 não pode vincular operador à fila N2; monitor N1 não acompanha chat N2; operador A não lê sessão de B; nenhum papel humano pode publicar mensagem com a identidade do bot/integration.

## 5. Administração do Hub

**Páginas:** `/administracao/operacoes`, `/administracao/filas`, `/administracao/usuarios`, `/administracao/roles`, `/administracao/integracoes`, `/administracao/roteamento`, `/administracao/politicas`, `/administracao/auditoria-config`.

**Cadastro de filas:** código estável, nome, operação, status DRAFT|ACTIVE|PAUSED|ARCHIVED, descrição, categoria, fallback (N1 da operação), prioridade, SLA, horário/feriados, capacidade, política de oferta/expiração, tratamento de indisponibilidade, reabertura e retenção. Bloquear delete físico com sessions/grants/memberships; usar archive com auditoria e migração explícita de pendentes quando permitido.

**Cadastro de pessoas:** nome, identidade (Entra futuramente), estado, funções, membros/skills, capacidade, limites de concorrência, filas e concessões. Desativação não apaga histórico; bloquear alterações que deixem sessões órfãs.

**Integrações/bots:** nome, canal, versão de protocolo, scopes, endpoint/adapter, status, capacidades (texto, imagem, anexos), segredo/referência de vault, health, retries e trilhas. Nenhum segredo legível pela UI após gravação.

## 6. Supervisão por fila

Rota principal `/supervisao/filas`: apenas filas do supervisor; ao selecionar, `/supervisao/filas/:id` expõe **workspace independente por fila** com:
- Visão operacional: aguardando, ofertados, ativos, abandono, capacidade, presença, transferências e aging;
- Equipe: adicionar/remover por identidade, vínculo, prioridade/skills, disponibilidade, capacidade e justificativa;
- Operação: pausas, regras, escalonamento, horários, SLA e backlog, sujeito aos grants;
- Conversas: lista de tickets da fila/intervalo, filtros e trilha;
- Relatórios: séries históricas autorizadas, exportações rastreáveis e evidência temporal.
Troca de fila deve atualizar simultaneamente autorização, cache, filtros e dados; nunca reaproveitar dados de fila anterior em estado de React.

**Roteamento:** N1 default da operação. Direcionamento explícito à fila especializada somente por integration confiável ou regra publicada/versionada de roteamento; payload externo não tem autoridade irrestrita para nomear qualquer queue_id. Motor `routing_rules` com prioridade, condição estruturada (integração, canal, categoria, intenção **confiável**), destino, vigência, modo dry-run e trilha `routing_decision`; fallback N1 se regra inativa/desconhecida.

## 7. Monitoria assistida: propostas viáveis

Monitor com grant `conversation.read_live` abre workspace próprio:
- grade: fila, operadores online, status, tickets ativos, tempo/aging, indicadores de risco;
- **espelhamento somente leitura** de mensagens já autorizadas, atualização live;
- **recomendação privada** associada a uma sessão e operador (`coaching_recommendations`), com tipo INFO|ALERT|SUGGESTED_REPLY|KNOWLEDGE_LINK, texto, autor, validade e prioridade;
- canal técnico interno separado de `messages` e de `outbox_events`. A recomendação **nunca** é entregue ao usuário final;
- popup discreto no operador sem cobrir composer. Ações `Confirmar leitura`, `Aceitar sugestão` (copia para rascunho, operador revisa e envia) e `Dispensar` (motivo opcional);
- estados SENT→DELIVERED→ACKNOWLEDGED|APPLIED_DRAFT|DISMISSED|EXPIRED; não classificar `APPLIED_DRAFT` como mensagem realmente enviada;
- audit trail de monitor, decisão, tempo de resposta e sessão;
- anti-spam/rate limit por monitor/sessão, limite de urgência, dedupe, expiração, política contra interferência;
- monitor **não** aceita, encerra, transfere nem envia mensagens de usuário, e não pode disparar comandos via conteúdo de recomendação.

### Assistência reativa iniciada pelo operador

O operador autenticado, responsável por uma sessão ACTIVE, aciona **Solicitar auxílio** em sua própria Mesa. Informa motivo (dúvida técnica, procedimento, comunicação, incidente, outro), resumo, prioridade e dados mínimos para a triagem; a conversa do usuário **não muda de fila nem de operador**.

- O pedido gera `assistance_requests` e eventos imutáveis, não `messages`, `handoff_offers` ou `outbox_events`.
- O Hub mantém **inbox de auxílios por fila**, consumida apenas por monitores com grant atual para a fila/segmento. Um monitor assume atomicamente a solicitação; múltiplos monitores não podem apropriar-se dela simultaneamente.
- O operador acompanha status de pedido: aguardando, assumido, em andamento, escalonado, resolvido ou cancelado. O drawer é não bloqueante e preserva o rascunho do chat.
- Sem monitor online, o pedido **permanece em espera**, com aging, prazo e escalonamento de política à supervisão responsável. Não se encaminha automaticamente ao N2 de atendimento.
- O monitor troca **orientações internas** com o operador por um canal isolado; só o operador decide se transfere um texto sugerido para o rascunho e posteriormente o envia ao usuário por uma ação distinta.
- Transferências de sessão e mudanças de fila exigem reavaliar grants e responsabilidade do auxílio; um monitor N1 não herda acesso a mensagens exclusivas de N2.
- Auditoria registra solicitante, motivo, quem assumiu, recomendações, tempos, estado e decisões. Princípio de minimização dos dados compartilhados.
- Pedido reativo e recomendação proativa compartilham o subsistema interno de coaching, mas são **entidades diferentes**. Uma recomendação proativa não exige abertura artificial de pedido pelo operador.

**Contrato detalhado:** [SPEC-010 — Monitoria Assistida Bidirecional](../specs/SPEC-010-bidirectional-assisted-monitoring.md), incluindo APIs candidatas, estados, concorrência, notificações e testes negativos.

Evoluções opcionais futuras: checklist de qualidade em andamento, escalonamento supervisionado com justificativa, link de artigo KB, alertas de silêncio prolongado/SLA. Sem automação por IA antes de métricas e política.

## 8. Auditoria por fila e dados sensíveis

Tela `/auditoria`: filas autorizadas, intervalo temporal, pesquisa, leitura dos trechos permitidos, histórico de transfers/ownership, anexos sujeitos a grant separado, registros de coaching (somente metadados por padrão), checklist/score manual e exportação sob permissão `audit.export`.

Atenção: eventos em um mesmo ticket podem pertencer a múltiplas filas. Conservar proveniência histórica, autorização por intervalo/segmento e regras de acesso a conteúdo compartilhado; não confundir a fila **atual** do ticket com a fila **que originou** cada evento. Retenção, mascaramento de dados pessoais e log de consultas são obrigatórios antes de conversas reais.

## 9. Anexos e prints

**Primeira entrega:** imagens PNG/JPEG/WebP do chat em POC (excluir SVG/HTML/executáveis), tamanho configurável (sugestão inicial: até 10 MiB por item, teto de 3 itens por mensagem; validar com canais); permitir preview e download autenticado.

**Arquitetura:** `attachments` com message_id, operation_id, queue_segment_id, uploader, mime detectado pelo servidor, bytes, SHA-256, estado UPLOADING|QUARANTINED|CLEAN|REJECTED|DELETED, storage_key opaca, datas, política de retenção. Bytes em storage privado fora do webroot; SQLite somente metadados. Verificar cabeçalho real, extensão allowlist, limites, autorização, antivírus/quarentena, nome aleatório, CSP/Content-Disposition e download por handler autenticado após status CLEAN.

O anexo acompanha o histórico quando há transferência com política de visibilidade explícita. Prever consentimento/redação de prints com informações sensíveis e checagem de malware. Integração ao Teams depende das capacidades reais do adapter.

## 10. Usuário final e canais

**Desenho do primeiro canal:** Teams `Embedded`: bot original recebe mensagens/arquivo do usuário, autentica sua identidade **como integração** perante o Hub e entrega evento inbound idempotente a `channel_inbox`; Hub normaliza e roteia, cria handoff, responde via `channel_outbox`; worker tenta entrega, adapter do bot de origem envia como o bot original e confirma ACK. Se falhar, persiste e reprocessa com backoff, DLQ e reconciliação.

Separar `external_conversation_id`, `external_message_id`, `channel_user_id` por integração e tenant; não assumir reutilização de conversationId ou credenciais entre bots. Não passar mensagens HUMAN_ACTIVE para o LLM do bot original. `Native` Teams e Webchat são adaptações posteriores da interface de canal.

**API futura, não implementada:** POST `/v1/integrations/{id}/inbound/messages`, POST `/v1/integrations/{id}/handoffs`, POST `/v1/integrations/{id}/acks`, GET `/v1/integrations/{id}/pending`; todos exigem auth de máquina + escopo de integração, assinatura/replay protection quando webhook, idempotência e limites de taxa. **Não expor os endpoints locais atuais de simulação como protocolo enterprise.**

## 11. Pré-requisitos para operação enterprise

1. Alembic com migrations reversíveis e backup/restore testados, antes de CRUD com dados persistentes.
2. Query-scoping, autorização de objeto/segmento por fila, teste de IDOR e trilha de acesso.
3. IAM corporativo Entra ID/OIDC (MFA e políticas de tenant), scopes de aplicações, segregação de conta/operador.
4. Worker durável separado, lease/leader election, retries, DLQ, idempotência sob concorrência e transação de SQL Server quando migrar (BEGIN IMMEDIATE é apenas SQLite).
5. API contrato versionado, central de eventos, observabilidade, logs estruturados/correlation_id, SLOs, segurança LGPD, retenção e política de anexos.
6. Testes de carga, isolamento N1/N2, cross-queue, cross-operation, falhas de canal e restauração. Todos os testes rodam localmente; **sem GitHub Actions**.

### Referências técnicas

- Constituição do projeto: `CONSTITUTION.md`.
- Ownership de canal: `docs/architecture/ADR-0002-channel-ownership.md`.
- Microsoft Entra RBAC: https://learn.microsoft.com/en-us/azure/active-directory/develop/howto-implement-rbac-for-apps
- Microsoft Teams proactive: https://learn.microsoft.com/en-us/microsoftteams/platform/bots/how-to/conversations/send-proactive-messages
- OWASP file upload: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html

**Fora de escopo deste RFC:** qualquer commit mutante na POC 0.5, conta/segredo real, upload de anexos, integração Teams ou abertura de acesso da API à rede. Este é um contrato proposto para aprovação.
