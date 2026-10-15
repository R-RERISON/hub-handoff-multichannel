# Arquitetura — Visão de contexto

## Decisão consolidada: Embedded-first, Native-ready

    Usuário no Teams
       ↕
    Bot original (identidade e conversa do canal)
       ↕ adapter REST/webhook e ACK
    Handoff Hub API
       ↕
    Núcleo: Sessions | Queues | Dispatch | Messages | Operators | Audit
       ↕
    SQL Server (sessões, eventos, inbox, outbox, auditoria)
       ↕
    Workers de notificação e publicação
       ↕
    Workspace próprio do operador / Cockpit supervisor

O Hub possui as regras de negócio e o estado. O bot original apenas recebe e publica mensagens usando **suas próprias credenciais e conversation reference**. Enquanto a sessão estiver em atendimento humano, o bot suspende respostas automáticas e retransmite os eventos. Se o Hub ficar indisponível, não se deve liberar o LLM silenciosamente.

## Versão inicial
FastAPI em monólito modular, SQL Server com migrations, outbox/inbox duráveis, workers independentes do processo web. SSO Entra ID para operadores, OAuth2 client credentials para adapters, segregação por operação/tenant. React/TypeScript para workspace e supervisão. Redis ou broker são opcionais e não substituem a transação do banco.

## Domínios
- Integrations: registro de bots, capabilities, chaves e canais.
- Sessions: propriedade e histórico da sessão, estados, encerramento.
- Queue/Dispatch: regras de seleção, prioridade, reserva e aceite.
- Operators/Presence: status humano, capacidade e provider Finesse opcional.
- Messaging: inbox, outbox, anexos, sequência, idempotência e delivery status.
- Operations: jornada, feriado, SLA, transferência, pesquisa e indicadores.
- Identity: autenticação, autorização, tenant, operação e auditoria.

## Modo Native posterior
Handoff Hub terá seu próprio bot/aplicativo no Teams. Dependendo da configuração, o usuário abre outra conversa. A identidade do canal de origem não pode ser assumida por outro bot.

## Segurança e falhas
Conferir JWT, scopes, recurso e tenant em cada ação; autenticar callbacks; proteger dados pessoais; scanning de anexos e bloqueio de SSRF. Reservas atômicas. ACK perdido, eventos duplicados e reconciliação devem ser testados.

## Fontes oficiais
- https://learn.microsoft.com/en-us/microsoftteams/platform/bots/how-to/conversations/send-proactive-messages
- https://learn.microsoft.com/en-us/microsoft-copilot-studio/configure-generic-handoff
- https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/channels
- https://learn.microsoft.com/en-us/python/api/msteams-sdk-python
