# Handoff Hub Multichannel

Plataforma independente de orquestração de atendimento humano para bots, agentes e canais corporativos.

> **Status:** bootstrap do repositório. A implementação inicial e a especificação são revisadas em uma branch separada antes de entrar na `main`.

## Decisão arquitetural

- Núcleo API-first independente de bots e canais.
- **Embedded Handoff** como primeiro fluxo: a conversa permanece no bot original, que é o transportador das mensagens.
- **Native Handoff** como modo posterior, com aplicação própria no Teams.
- Operadores atendem em um workspace independente do bot de origem.
- Primeiro piloto: conector com o chatbot Python/Tornado existente.
- Nenhum código legado, credencial, hostname interno ou dado pessoal é importado automaticamente.

Consulte a proposta na branch `spec/001-foundation-architecture` quando publicada.
