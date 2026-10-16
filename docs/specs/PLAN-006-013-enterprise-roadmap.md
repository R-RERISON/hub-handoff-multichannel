# Plano de implementação — SPEC-006 a SPEC-013

**Tipo:** roadmap executável, design-only. **Não altera** o funcionamento homologado da POC 0.5.  
**Baseline:** `feat/005-rbac-auto-dispatch`  
**Marco atual:** POC operacional validada pelo usuário; evolução enterprise ainda não autorizada para produção.  
**Referência arquitetural:** [RFC-006](../architecture/RFC-006-enterprise-operating-model.md).

## 0. Diretrizes de execução e governança

- **Uma SPEC = um vertical slice testável**, com backend + modelo + frontend + autorização + testes + rollback; não liberar telas que anunciem funcionalidades não operacionais.
- Fluxo: `SPEC → ADR/migration → teste negativo e positivo → implementação → pytest/ruff/frontend build → homologação VS Code → PR → promoção`.
- Não usar GitHub Actions. Não sobrescrever nem resetar SQLite de homologação para corrigir build.
- Criar branches independentes/empilhadas em sequência controlada; o PR #13 da POC-005 deve ter baseline estável/promovida antes de empilhar vários ciclos novos.
- Alembic substitui `Base.metadata.create_all` para **alteração de schema**, sem exigir automaticamente SQL Server já na primeira SPEC.
- Prefira **soft-delete/archiving e eventos** para entidades utilizadas historicamente.
- Proteger todas as listagens, contadores, arquivos e eventos com escopo server-side e política explícita. Não confiar em filtros React.
- Incluir mecanismo de versionamento de configuração e ETag/optimistic-lock quando múltiplos gestores editarem a mesma fila.
- Migrations podem ser `upgrade` com rollback estrutural somente quando seguro; dados históricos/atribuições têm rollback por *forward fix* e restauração testada, nunca `DROP TABLE` imprudente.

## 1. Entrega em ondas

| SPEC | Foco | Dependência | Resultado verificável |
|---|---|---|---|
| **006 — Fundações** | Alembic + grants de papel/escopo por fila + ownership histórico; refator de API auth/service | POC-005 | Supervisor/Auditor N1 não conseguem ler N2; Operador continua atendendo, sem regressão |
| **007 — Administração** | CRUD de operações/filas/pessoas/identidades/papéis e ciclo de vida; módulo integrações em configuração | SPEC-006 | Admin cria fila especializada, cadastra operador, vincula e delega responsáveis |
| **008 — Supervisão** | Área independente por fila: equipe, capacidade, status, prioridades, escalonamento, dashboards operacionais | SPEC-007 | Supervisor A vê e gerencia só suas filas; outro gestor opera fila independente |
| **009 — Auditoria** | Portal de auditor com pesquisa, histórico por segmento e evidências, filtros, logs de acesso | SPEC-006 + 008 | Auditor N1 lê apenas segmentos/evidências N1, nunca N2 sem concessão |
| **010 — Monitoria Assistida** | MONITOR role + live read-only + coaching privado/ACK + popup operador | SPEC-006 + 008 | Monitor observa e orienta operador, sem enviar texto ao usuário |
| **011 — Mídia** | Upload seguro de print, quarentena/verificação, download autorizado e preview | SPEC-006 + 009 | Screenshot em conversa, acessível ao operador e leitores autorizados |
| **012 — Canal real** | Inbox/outbox duráveis, adapter Teams Embedded, identidade de integração, ACK/retry/DLQ | SPEC-006 + 011* | Usuário envia texto e imagem ao bot original; operador recebe e responde com ACK |
| **013 — Métricas e readiness** | SLA/indicadores históricos/qualidade/exportação e observabilidade/hardening | SPEC-008/009/010/012 | Métricas reproduzíveis, carga, segurança e falhas avaliadas por gates |

(*) O primeiro adapter de canal pode iniciar **somente texto** antes da SPEC-011 se o contrato registrar capacidades, isolar os blobs e não quebrar eventos multimídia posteriores. O suporte completo a imagem exige a entrega 011 + testes reais por canal.

## 2. SPEC-006 — Escopos e migração (primeiro incremento obrigatório)

**Modelo:** `roles`, `permissions` (catálogo), `role_assignments`, `queue_segments`, `access_audit_events`, `schema_versions` via Alembic (sem SQL temporário improvisado). Considerar `user_role_grants` parametrizado se catálogo constante. A sessão atual mantém sua identidade `operator_id`.

**APIs propostas:** GET `/v1/me/permissions`; GET/POST/DELETE `/v1/admin/role-assignments`; GET `/v1/me/queues`; serviço interno `authorize(resource, action)`. Nenhuma dessas rotas está pronta hoje.

**Casos gate:**
1. Supervisor S com grants N1/N3 não acessa N2 por GET/list/export/write ou URL forjada.
2. Auditor A com N1 não lê mensagens ou anexos de segmentos N2 do mesmo ticket transferido.
3. Revoke imediatamente impede nova consulta no próximo request.
4. Operador ainda pode aceitar/transferir/encerrar no próprio ticket.
5. O banco SQLite de homologação migra sem perder filas/handoff/mensagens. Backup, checksums, upgrade dry-run e teste de restauração.
6. Troca de sessão/perfil não reaproveita caches de dados de outro usuário.

**Aceite:** 0 vazamentos de escopo nos testes, invariantes FIFO/capacidade intactos, migrations versionadas, scripts de rollback/restore documentados.

## 3. SPEC-007 — Administração de plataforma

**Entidades:** operações, filas, usuários, operator profiles, memberships, grants, connector registrations, routing drafts, policy revisions.

**Telas:** Filas (criar/editar/pausar/arquivar), Pessoas, Perfis/Concessões, Operações, Conectores (primeiro apenas registro/configuração), Políticas.

**Fluxo gerencial:** Admin cadastra fila Financeiro dentro da operação, cria/vincula dois operadores, concede `SUPERVISOR[queue=Financeiro]` a uma pessoa e `AUDITOR[queue=Financeiro]` a outra, configura disponibilidade e ativa. Mudanças exigem auditoria; secret de connector não pode voltar em GET.

**Gate:** não permitir archivar fila com demandas pendentes sem política de drenagem; FKs preservadas; idempotência de requests; duplicidade de código detectada; revogação de operador com sessão ativa exige fluxo controlado, não apagamento.

## 4. SPEC-008 — Supervisão de filas independente

**Tela inicial:** cards de filas sob gestão. Tela de detalhe `/supervisao/filas/:id` com seções: Operação | Equipe | Políticas | Conversas | Indicadores.

**Regras:** supervisor não altera config global, não edita concessão fora de sua fila e não envia mensagens em nome do operador. Indicadores básicos: waiting, OFFERED, ACTIVE, disponível/pausa/offline, aging, reofertas, transferência, throughput e ocupação (denominadores definidos).

**Gate:** supervisionar 2 filas com configurações diferentes sem cruzar filtros/retornar itens de outra; operador removido não recebe nova oferta; operador com atendimento ativo conclui com preservação de histórico; alterações de capacidade obedecem reservas existentes.

## 5. SPEC-009 — Auditoria com escopo histórico

**Modelo:** `conversation_audit_notes` opcional, `audit_access_events`, trilha de segmentos, export_jobs `QUEUED|READY|EXPIRED`. A auditoria não deve salvar classificação subjetiva em `messages`.

**Gate:** acesso limitado às filas/segmentos concedidos; exportação é auditada e expira; mascaramento/retention observados; consultas paginadas (sem `GET /dashboard` retornar 200 casos indiscriminadamente); operador/supervisor sem permission `audit.export` recebe 403/404.

## 6. SPEC-010 — Monitoria e coaching

**Modelo:** `monitor_assignments` como role grants; `coaching_recommendations` com destinatário, operador, fila/segmento, texto, prioridade, TTL, estado e decisões.

**Fluxo:** monitor seleciona ticket ativo da fila autorizada → recebe texto/estado ao vivo (somente leitura) → escreve recomendação interna → operador recebe cartão discreto → pode (a) reconhecer, (b) copiar sugestão para rascunho e editar, (c) dispensar → evento auditado. Mesmo se aceitar a sugestão, somente comando de envio explícito do operador cria `messages/OutboxEvent`.

**Gate:** monitor de outra fila não vê atendimento; recomendação não gera mensagens externas; 2 recomendações simultâneas não bloqueiam o chat; usuário e bot não recebem coaching; expiração e ACK não duplicam; sem spam sem limite.

**Sinalização mais segura:** INFO sem popup bloqueante; ALERT exige destaque não modal; crítico apenas conforme política e logs. Suporte a futura base de conhecimento citada, não IA autônoma nesta entrega.

## 7. SPEC-011 — Prints e anexos seguros

**Primeiro escopo:** PNG/JPEG/WebP, limites de upload configurados (proposta 10 MiB por arquivo e até 3 por mensagem; valores a homologar). Metadados e blob privado separados.

**Gate:** negar extensão/MIME falso, `..\`, arquivos enormes, SVG/HTML/EXE, malware/quarentena, download sem grant e arquivo de outra fila. Só status `CLEAN` pode ser servido; envio externo respeita capability matrix. Testar integridade de SHA-256, expiração e deleção/retention.

**UX:** colar imagem Ctrl+V e arrastar/soltar sobre composer; upload progress, miniatura, abrir com zoom, descrição opcional, erro claro e exclusão antes do envio. Não confirmar entrega ao usuário se ainda `PENDING_ADAPTER`.

## 8. SPEC-012 — Integração e usuário final

**Spike obrigatório, antes do adapter:** validar capacidades reais do bot Teams de origem, autenticação e tenant, como os arquivos são recebidos/autorizados, formato de inbound/outbound, ACK e idempotência; não presumir que conversationId de um bot pode ser reutilizado por outro.

**Vertical slice A:** texto (user→bot original→adapter→Hub→operador→Hub outbox→adapter→bot original→user). Entrega só vira DELIVERED após ACK; falha com retry/backoff/DLQ e UI honesta.

**Vertical slice B:** arquivos/imagens com token do canal e ACL coerentes, quando suporte do Teams estiver homologado.

**Gate:** duplicatas do canal não criam tickets/mensagens duplicados; operação A não usa credenciais de B; durante HUMAN_ACTIVE LLM do bot não responde ao usuário; interrupção de Teams conserva outbox e não perde dados; políticas de retorno ao bot e timeout definidas.

## 9. SPEC-013 — Indicadores, qualidade e readiness

**KPI calculado sobre eventos com semântica documentada:**
- backlog e aging por fila (tempo no trecho), oferta/aceite, abandono, TMA/TME, taxa de transferência, reabertura e capacidade;
- alertas de espera/SLA e notificações internas;
- monitoria: recomendações enviadas, reconhecidas, aceitas e descartadas, nunca contá-las como respostas ao usuário;
- auditoria: volume revisado, checklist de qualidade e conformidade, não score automático sem metodologia aprovada.

**Gate operacional:** teste de concorrência >1 processo usando mecanismo apropriado ao banco final, limites de carga definidos a partir da demanda real, backup/recovery, revisão LGPD, relatórios segmentados, autenticação Entra, observabilidade, E2E Teams, acessibilidade, gestão de segredos e política de deploy/reversão.

## 10. Estrutura de código sugerida (evolução, não refator monolítico num único PR)

```text
src/handoff_hub/
  identity/       # principal, SSO, accounts
  authorization/  # role grants, queue scoping, audit access
  administration/ # queue/operator/integration lifecycle
  dispatch/       # policies, turn position, queue segments
  conversations/  # session/message/transfer
  monitoring/     # private coaching
  media/          # secure blob storage, scan/quarantine
  integrations/   # channel inbox/outbox and adapters
  reporting/      # event-sourced metrics
web/src/
  portals/admin/
  portals/supervisor/
  portals/auditor/
  portals/monitor/
  portals/operator/
  shared/         # design system, auth/data access, notifications
```

`poc_api.py` e `poc_auth.py` podem ser mantidos temporariamente como adapters de compatibilidade, movendo a lógica por pequenas fatias com testes, sem quebrar a POC. Documentar depreciação de endpoints em vez de removê-los silenciosamente.

## 11. Contrato de não regressão transversal (gate para cada SPEC)

| Domínio homologado | Cenário preservado |
|---|---|
| Login/RBAC | ADMIN/SUPERVISOR/OPERATOR/AUDITOR, lockout, revoke, 401/403 |
| Intake | sem regra/queue explícita → N1; destino explícito autorizado → fila destino |
| Dispatch | FIFO + round robin, AVAILABLE + heartbeat, lease/timeout, capacidade e cooldown |
| Sessão | oferta→aceite→resposta→transferência N2→fechamento |
| Mensagens | dedupe, outbox PENDING_ADAPTER não vira DELIVERED fictício |
| UX | Mesa operador sem scroll da página e composer fixo; pop-up novo atendimento |
| Segurança | deny-by-default por fila, operação e objeto, com testes negativos |
| Dados | migrations com backup, preservação de históricos, exclusões controladas |

**Comando local exigido:** `.\start.cmd --check`, mais testes novos de escopo e E2E que cada SPEC adicionar. Usar banco de testes sintético separado do SQLite homologado. Sem GitHub Actions.

## 12. Estratégia de rollback

- Cada SPEC publica migração versionada, backup e plano de restauração; regressão funcional → desativar feature flag e retornar ao frontend/API anterior compatível.
- Mudança de política de fila → reverter a versão da política, não apagar `dispatch_turns` nem os atendimentos.
- Alteração de concessões → revogar grants e invalidação de cache/sessão quando necessário.
- Falha de adapter → feature flag desativa saída/inbound, conserva inbox/outbox até reconciliação.
- Falha de upload/scanner → bloquear visualização/download, conservar metadados/quarentena e permitir limpeza segura.
- Nunca fazer rollback que destrua auditoria, mensagens e históricos de operador.

## 13. Critérios para aprovação do plano

1. Aprovar seis personas e separação de responsabilidades, incluindo ADMIN sem leitura irrestrita de conteúdo por padrão.
2. Aprovar a unidade de segurança `operação → fila → segmento do atendimento`.
3. Aprovar primeiro investimento em SPEC-006 (grants/migration), em vez de iniciar pela criação de dashboards.
4. Aprovar monitoria com recomendações internas sem postagem automática e anexo de imagens com segurança server-side.
5. Confirmar plataforma de destino do primeiro adapter (Teams Embedded com o bot original) antes de SPEC-012.

**Não há código de produção alterado por esta proposta.**
