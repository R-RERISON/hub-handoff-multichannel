# ADR-0002 — Identidade do canal e modos de atendimento

Data: 2026-10-15 | Estado: ACCEPTED para design

## Embedded — padrão inicial
O bot de origem permanece como emissor e receptor Teams. O adapter autentica-se no Hub, recebe suas mensagens, confirma a entrega e publica respostas do operador **com a identidade do próprio bot original**. O Hub governa filas/estados/histórico, mas não controla diretamente um conversationId de outro bot. Durante HUMAN_ACTIVE, não alimentar o LLM com as mensagens que foram destinadas ao operador.

## Native — segunda etapa
Uma app/bot Teams pertencente ao Handoff Hub publica mensagens em sua conversa própria. O usuário pode ser conduzido a outra conversa. Pré-requisitos de instalação, permissões e políticas do tenant devem ser validados.

## Copilot Studio
Custom handoff adapter documentado atualmente apoia Direct Line; um agente publicado no Teams não se torna automaticamente controlável pelo Hub. Prova de conceito por canal obrigatória.

## Segurança
Credential por integração; scopes/operation_id; nenhuma leitura transversal entre bots; callbacks autenticados e eventos idempotentes.

## Fontes
- https://learn.microsoft.com/en-us/microsoftteams/platform/bots/how-to/conversations/send-proactive-messages
- https://learn.microsoft.com/en-us/microsoft-copilot-studio/configure-generic-handoff
- https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/channels
