# SPEC-010 — Monitoria Assistida Bidirecional: monitor → operador e operador → monitor

**Status:** PROPOSTA PARA IMPLEMENTAÇÃO FUTURA. Nenhuma rota, tabela ou UI foi implementada por esta SPEC.  
**Dependências:** SPEC-006 (RBAC por fila e segmentos), SPEC-008 (supervisão por fila).  
**Princípio de segurança:** o canal de assistência é **interno ao Hub**, não pertence ao chat do usuário, à outbox da integração nem ao bot Teams.

## 1. Problema e objetivos

Existem **duas formas complementares** de assistência humana:

1. **Proativa (monitor → operador):** monitor autorizado identifica dificuldade ou risco ao acompanhar atendimento e envia recomendação privada ao operador.
2. **Reativa (operador → monitor):** operador que está atendendo solicita ajuda, informa assunto/necessidade e acompanha resposta, sem interromper ou transferir automaticamente a conversa do usuário.

A assistência é uma **atividade paralela e rastreável**, distinta de handoff, transferência de fila, atribuição de operador e envio de mensagens ao usuário. O operador permanece responsável por toda decisão e pelo envio final de sua resposta.

## 2. UX proposta

### Mesa do Operador

Com uma sessão ativa, botão contextual **Solicitar auxílio** próximo de Transferir e Encerrar. Um drawer lateral **não bloqueante** preserva histórico e composer da conversa. Formulário:
- **Motivo** obrigatório: dúvida técnica, validação de procedimento, dificuldade de comunicação, suspeita de incidente, outro;
- **Descrição** resumida obrigatória, sem dados pessoais desnecessários;
- **Prioridade** normal / alta, com regras de elevação validadas pelo backend para evitar abuso;
- **Contexto compartilhado**: por padrão somente identificador interno, fila, assunto, operador e resumo informado; monitor pode abrir conversa completa apenas com `conversation.read_live` autorizado. Anexos exigem `media.read` e liberação explícita;
- **Acompanhamento**: aguardando monitor → monitor assumiu → orientação recebida → resolvido; permitir cancelar/reabrir conforme política.

Ao chegar resposta do monitor, cartão de orientação privado no mesmo drawer, com alerta discreto. Ações: **Confirmar leitura**, **Inserir no rascunho** (não envia automaticamente), **Dispensar**, **Marcar auxílio resolvido**. Indicador do auxílio permanece visível no cabeçalho da conversa até a conclusão. Uma orientação não cobre o botão Enviar e não destrói o texto já digitado.

### Portal do Monitor

Separar duas áreas:
- **Solicitações de auxílio:** inbox por filas autorizadas, ordenável por prioridade, tempo aguardando, tema, operação e SLA. Acesso ao assunto/resumo minimizado antes do monitor assumir.
- **Monitoria proativa:** visão live somente das filas autorizadas, com recomendações vinculadas à conversa, não necessariamente a um pedido.

Na solicitação, monitor pode **Assumir**, orientar via canal interno, **Resolver** ou **Encaminhar para outro monitor/supervisor autorizado**, mantendo histórico. Em uma mesma solicitação, apenas um monitor é o responsável ativo por vez; outros monitores autorizados podem assumir após expiração ou transferência explícita.

### Supervisor

Em suas filas, visualizar backlog de auxílios, tempo de espera/atendimento, níveis de prioridade, monitor disponível e auxílios escalonados. Gerenciar escala e política de escalonamento delegada. Não responder como monitor sem grant específico.

## 3. Modelagem proposta (contrato inicial)

`assistance_requests`:
- `id`, `operation_id`, `handoff_id`, `queue_id`, `queue_segment_id`, `operator_id`;
- `reason_code`, `description`, `priority`, `status`;
- `assigned_monitor_user_id` (nullable), `created_at`, `claimed_at`, `resolved_at`, `cancelled_at`;
- `version` para concorrência, `idempotency_key`, `routing_policy_version`;
- `escalation_due_at` com deadline configurável; não fixar SLA arbitrário no código.

`assistance_events`: trilha append-only de REQUESTED, CLAIMED, MESSAGE_ADDED, ACKNOWLEDGED, DRAFT_APPLIED, DISMISSED, REASSIGNED, ESCALATED, RESOLVED, CANCELLED e EXPIRED; ator, horário e metadados sem segredos.

`assistance_messages`: conteúdo **interno**, autor, assistência, destinatário lógico, tipo NOTE|RECOMMENDATION|KNOWLEDGE_LINK, horários, eventual referência segura à base de conhecimento. Não reutilizar `messages` nem `outbox_events`.

`coaching_recommendations` existente no plano pode referenciar `assistance_request_id` (nullable). Recomendações proativas ficam sem pedido associado. O ACK da recomendação não é o encerramento automático da assistência.

**Restrição de simultaneidade:** primeira versão aceita no máximo uma solicitação não terminal por `handoff_id` e `operator_id`, salvo necessidade validada posteriormente; múltiplas interações podem ocorrer na solicitação existente. `CLAIMED` é transição atômica e idempotente. Não confundir capacidade de atendimento ao usuário com capacidade de monitoria.

## 4. Estados e fluxos

```text
Operador com conversa ACTIVE
  └─ Solicitar auxílio
       └─ REQUESTED / QUEUED (durável, fila de auxílio)
            ├─ Monitor autorizado Assume → CLAIMED
            │     ├─ troca de orientações internas → IN_PROGRESS
            │     ├─ resolvido → RESOLVED
            │     └─ indisponibilidade → REQUEUED ou ESCALATED
            ├─ Operador cancela → CANCELLED
            └─ SLA configurado vence → ESCALATED (sem apagar pedido)
```

- Status de request: `QUEUED`, `CLAIMED`, `IN_PROGRESS`, `ESCALATED`, `RESOLVED`, `CANCELLED` (eventos registram subestados).
- `QUEUED → CLAIMED` exige permissão por fila e transação atômica: dois monitores concorrentes não podem assumir o mesmo pedido.
- Monitor não disponível: solicitação **persiste**, recebe prazo/aging e aparece à supervisão autorizada; nunca retorna sucesso de assistência concluída sem monitor.
- Timeout/ausência: alerta escalonado à supervisão/monitor substituto autorizado conforme política; não “teleporta” solicitações para fila N2 de atendimento.
- Encerramento do atendimento: pendências de auxílio recebem evento de encerramento por ciclo da conversa, com resolução/cancelamento explícitos conforme política e motivo preservado.
- Transferência N1→N2: revisar `queue_segment_id`, revogar acesso indevido de N1 ao contexto N2 e exigir nova autorização do monitor que continuará. Por padrão, pendência não transitiva é suspensa/encerrada ou reencaminhada ao grupo N2, preservando eventos históricos e avisando operador.
- Operator offline: pedido persiste no servidor, com indicação do estado; orientações podem ser recuperadas no retorno caso ainda autorizadas.
- O operador pode continuar atendendo durante todo o auxílio; **auxílio não aumenta capacidade, não cria ticket externo e não altera a fila da conversa**.

## 5. Permissões e privacidade

| Ação | Permissão e escopo |
|---|---|
| Abrir/cancelar próprio auxílio | `assistance.request` + ownership da sessão ACTIVE |
| Ver próprio auxílio e orientações | `assistance.read_own` + sessão/identidade |
| Visualizar fila de pedidos | `assistance.queue.read` para fila concedida |
| Assumir/repassar auxílio | `assistance.claim` / `assistance.reassign` + MONITOR no segmento autorizado |
| Enviar orientação interna | `assistance.reply` + monitor responsável e grant vigente |
| Espelhar mensagens do usuário | `conversation.read_live` da fila/segmento; não conceder implicitamente |
| Consultar indicadores de auxílio | `assistance.metrics.read` + supervisor da fila |
| Ver trilha de auxílio em auditoria | `assistance.audit.read` + concessão segmentada |

**Controle central no backend:** deny-by-default em cada request e websocket/evento, validação do ownership e fila/segmento atuais, sem confiança em campos de usuário enviados no payload. Minimização de conteúdo no inbox e logs. Revogação de grant deve impedir leituras posteriores mesmo com aba já aberta. Nunca enviar mensagens da assistência ao usuário, Teams, LLM de origem ou outbox de atendimento.

## 6. API candidata — não implementada

- `POST /v1/handoffs/{id}/assistance-requests`: abre com `Idempotency-Key`, apenas operador responsável e sessão ACTIVE.
- `GET /v1/my/assistance-requests`: operador consulta os seus.
- `POST /v1/assistance-requests/{id}/cancel`: operador encerra pedido aguardando.
- `GET /v1/monitor/assistance-requests`: lista autorizada por fila, paginada e ordenada.
- `POST /v1/monitor/assistance-requests/{id}/claim`: reserva atômica; retorna 409 se já assumido.
- `POST /v1/monitor/assistance-requests/{id}/messages`: orientação privada.
- `GET /v1/assistance-requests/{id}/timeline`: somente partes autorizadas.
- `POST /v1/assistance-requests/{id}/resolve`, `/reassign`, `/escalate`, `/ack`: conforme papel, fase e concessão.

Notificações em tempo real: preferir SSE (um sentido) como primeira etapa, com cursor persistido/replay e polling de fallback; WebSocket se as interações exigirem bidirecionalidade. Não utilizar push somente em memória como fonte da verdade.

## 7. Métricas e governança

- Pedidos abertos por fila, motivo, prioridade, operador, status e faixa de espera;
- Tempo de aceite por monitor, tempo de orientação, duração até resolução, percentual escalonado e cancelado;
- Orientações reconhecidas, rascunhos aproveitados e dispensas, **sem afirmar envio ao usuário**;
- Definição de SLA própria para assistência, independente do tempo de espera do usuário;
- Limite de solicitações duplicadas, controle de spam e abuso de prioridade;
- Auditoria sobre quem leu, assumiu, orientou, transferiu e encerrou.

## 8. Testes de aceite obrigatórios

1. Operador N1 com sessão ACTIVE abre auxílio; request persistida e recuperável após refresh/restart.
2. Operador B não cria auxílio para conversa do operador A; recebe 403/404.
3. Monitor autorizado N1 vê pedido N1; monitor apenas N2 não descobre existência do pedido N1 por lista, detalhe ou evento push.
4. Dois monitores concorrentes assumindo o mesmo ID: **exatamente um sucesso**, outro 409 sem mensagens duplicadas.
5. Sem monitor conectado: pedido mantém `QUEUED`; supervisor vê aging e recebe escalonamento conforme prazo configurado.
6. Pedido assumido: orientação interna chega ao operador, sem ser persistida em `messages` ou `outbox_events`.
7. `Inserir no rascunho` **não dispara envio** nem apaga texto previamente digitado; só o botão Enviar publica mensagem do operador.
8. Transferência N1→N2: acesso às novas mensagens do segmento N2 é negado para monitor apenas N1; reencaminhamento auditado.
9. Encerramento do ticket durante auxílio: pendência tratada e registrada, sem perder trilha.
10. Cancelamento, reassign, timeout, reconexão e revogação de grant são idempotentes.
11. Notificação não cobre composer, não bloqueia chat e respeita acessibilidade/teclado.
12. Regression gates POC-005: login, rodízio, N1 default, ofertas, transferência, respostas e fechamento intactos.

## 9. Fatiamento sugerido da SPEC-010

- **010-A**: entidades, grants, migração Alembic, abertura e consulta do operador, inbox de monitores com aceite atômico.
- **010-B**: orientações privadas, ACK, drawer no operador, monitoria proativa reutilizando canal interno.
- **010-C**: SLA, escalonamento/reaferição, recuperação, notificações SSE/polling, relatórios e testes E2E.

Nenhum dessas etapas exige integração Teams real para validar o fluxo interno. Não usar GitHub Actions. Executar todos os testes localmente pelo `start.cmd --check` e testes adicionais de escopo/concorrrência.
