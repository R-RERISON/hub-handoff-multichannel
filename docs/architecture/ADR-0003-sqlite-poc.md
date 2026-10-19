# ADR-0003 — SQLite durante a POC, SQL Server somente após validação

Data: 2026-10-15 | Estado: ACCEPTED para POC

## Contexto
O Handoff Hub precisa validar entidades e regras reais com baixo custo, sem provisionamento de infraestrutura nem dependência do banco usado pelo chatbot legado.

## Decisão
Iniciar em **SQLite local**, usando SQLAlchemy 2, WAL, foreign keys ON, busy_timeout e BEGIN IMMEDIATE em operações concorrentes críticas. Frontend React/TypeScript/Vite e Backend Python/FastAPI. Realizar testes e build localmente, sem GitHub Actions.

O modelo relacional nasce do comportamento funcional observado no handoff existente, não de cópia de estrutura, código ou migração de dados.

## Garantias e limitações
- SQLite WAL permite leitores simultâneos, mas apenas um writer por vez; manter em host único, armazenamento local.
- Demo restrita a 127.0.0.1, com chave de POC; sem Entra ID, OAuth2, RBAC ou isolamento completo.
- Atribuição manual com transação SQLite; sem worker real Teams nem Cisco Finesse.
- Estados da POC: QUEUED, ACTIVE e CLOSED; todos os outros são planejados para próximas SPECs.

## Migração futura para SQL Server
1. Definir schema-alvo estável e política de retenção.
2. Introduzir Alembic com migrations antes de qualquer dado não descartável.
3. Revisar constraints, tipos, índices, compatibilidade de migrations e UTC.
4. Substituir BEGIN IMMEDIATE por mecanismo correto SQL Server.
5. Executar testes concorrentes, de recuperação e carga no banco-alvo.
6. Migrar **somente dados produzidos pelo novo Hub** se aprovado; a base legada não é fonte.

## Alternativas
- SQL Server desde a primeira entrega: adiado por custo de setup e dependência operacional.
- SQLite como produção multi-host: rejeitado pelo modelo de concorrência/arquivos.
- Copiar banco atual: rejeitado, pois produziria acoplamento e dívida legada.
