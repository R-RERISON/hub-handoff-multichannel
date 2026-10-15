# Constituição de Engenharia — Handoff Hub Multichannel

Versão 1.1 | 2026-10-15 | Baseline POC SQLite

## Missão
Handoff Hub governa sessões, filas, operadores, roteamento, mensagens, SLA e auditoria. Bot ou agente original é adapter do canal; não armazena regras de negócio do atendimento humano.

## Decisões atuais
- SQLite para POC local, com esquema SQLAlchemy 2 e migração futura avaliada para SQL Server.
- FastAPI e monólito modular no backend; React/TypeScript/Vite no frontend.
- Embedded Handoff como primeiro canal (bot original transporta mensagens); Native Handoff posterior.
- Scripts legados são **base para requisitos e validação funcional**, não fonte de migração de dados ou cópia de implementação.
- **Não utilizar GitHub Actions**. Testes, lint e build devem ser executados localmente, com evidência anexada ao PR.

## Invariantes de qualidade
1. Persistir estado em banco; não depender de dicionários globais.
2. Despacho atômico e capacidade por operador, com testes concorrentes.
3. Idempotência para solicitações e mensagens; auditabilidade de transições.
4. Controlar recebimento e envio externo por inbox/outbox duráveis antes de plugar Teams.
5. Isolamento por operação e integração nas versões de produção.
6. Entra ID/OIDC e OAuth2 por integração antes de publicar além de localhost.
7. Nunca reutilizar a identidade, credenciais ou identificadores de conversa de outro bot.
8. Não alterar estado silenciosamente ao falhar Finesse, Teams, worker ou IA.
9. SQL parametrizado e validações de entrada; proteção LGPD e retenção.
10. Migração de banco implica novos testes de isolamento e concorrência; sintaxe SQLite não é portável automaticamente.

## Regras SPEC
Toda SPEC informa objetivo, escopo, modelo, contrato, segurança, testes, limites e rollback. POC não é produção. PRs só avançam com execução local documentada. Não criar ferramentas de CI pagas nem workflows do GitHub.
