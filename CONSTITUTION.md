# Constituição do Handoff Hub Multichannel

Status: BASELINE v1 | 2026-10-15

## Missão
Ser a plataforma independente responsável por filas, operadores, sessões, roteamento, SLA, mensagens e auditoria. O bot é um adapter de canal e nunca é dono da operação humana.

## Invariantes
1. SQL Server é a fonte de verdade transacional; estado em memória ou Redis não decide alocação.
2. Reserva e aceite de operador são atômicos; capacidades não podem ser excedidas sob concorrência.
3. Comandos e mensagens são idempotentes, com eventos versionados e correlation_id.
4. Inbox e outbox duráveis protegem contra retries, duplicação, falhas e reinícios.
5. O sistema não promete exactly-once distribuído; usa at-least-once e deduplicação.
6. Cada operação, integração e sessão possui controle de acesso e isolamento.
7. Não se reutilizam identificadores e credenciais de conversa de outro bot no Teams.
8. O Handoff continua seguro mesmo sem Finesse ou serviços de IA.
9. Toda transição de estado é auditável; conteúdo e metadados observam retenção e LGPD.
10. A migração do Tornado deve ser gradual, reversível e testada em homologação.

## Engenharia
- Especificação e ADR antes de alterações estruturais.
- Domínio não importa dependências Teams, Finesse nem LLM.
- SQL parametrizado, OAuth2/OIDC/Entra e RBAC antes de expor endpoints mutáveis.
- Testes de domínio, contratos, concorrência, integração SQL Server, segurança e recuperação.
- CI no PR; não considerar funcionalidade pronta sem evidência do gate.
- Nunca publicar segredos, endereços internos, chats ou identidade real de usuários.
- Projetar primeiro como monólito modular; distribuir serviços só com justificativa operacional.

## Ciclo de SPEC
DISCOVERY -> SPECIFIED -> PLANNED -> IMPLEMENTING -> VALIDATED -> CLOSED.
Cada SPEC documenta escopo, requisitos, não objetivos, testes, segurança, observabilidade e rollback.
