# ADR-0004 — Navegação por espaços de trabalho independentes

**Data:** 2026-10-15  
**Estado:** ACCEPTED para POC 0.4

## Problema

A POC 0.3 usa um componente React central para alternar entre conversas, filas, operadores e Mesa do Operador. O usuário comprovou que as regras básicas de atendimento funcionam, mas a mistura de contextos prejudica a UX, gera interfaces densas e facilita regressões de layout. A Mesa do Operador chegou a ter ações essenciais cortadas pela altura fixa do shell administrativo.

## Decisão

1. Separar **por papéis e rotas de navegação**, não por microfrontends nem aplicações de backend distintas.
2. Criar três shells visuais independentes na SPA React:
   - `/operador`: layout dedicado à caixa de trabalho, conversação, transferência e encerramento.
   - `/supervisao/*`: dashboard e telas de monitoramento sem composição de mensagens.
   - `/administracao`: espaço reservado a configurações; **somente landing page**, sem fingir funções que não existem.
3. Isolar a geração de dados sintéticos em `/laboratorio`.
4. Usar **React Router** para URLs profundas, navegação histórica e links diretos.
5. Extrair as telas para módulos React distintos em `web/src/workspaces/`; `App.tsx` conserva somente conexão à POC, snapshot, comando de criação/oferta/presença e orquestração.
6. Conservar FastAPI, SQLite, endpoints de distribuição e os fluxos já homologados.
7. Preservar `start.cmd` e `start.cmd --check`, sem GitHub Actions.

## Rotas

| Caminho | Público futuro | Função |
|---|---|---|
| `/operador` | OPERATOR | Inbox, aceite/recusa, mensagens, transferência e fechamento |
| `/supervisao` | SUPERVISOR | Visão executiva/operacional, indicadores e saúde |
| `/supervisao/conversas` | SUPERVISOR | Consulta **somente leitura** de conversas e auditoria |
| `/supervisao/filas` | SUPERVISOR | Estado por fila, ofertas pendentes e despacho |
| `/supervisao/equipe` | SUPERVISOR | Disponibilidade e capacidade |
| `/laboratorio` | DEMO | Abertura de tickets sintéticos |
| `/administracao` | ADMIN | Área reservada para cadastro e políticas futuras |

## Segurança — limite explícito da POC

O roteador separa **interfaces**, não permissões. Todos continuam com uma chave de laboratório compartilhada e com seleção fictícia de identidade do operador. Não utilizar a existência de URLs diferentes como evidência de RBAC. A autorização real ocorrerá no backend com Entra ID/OIDC/OAuth, isolamento de tenant/operação e enforcement de papéis; acesso ao portal de supervisão pelo operador ficará condicionado ao perfil real.

## Alternativas rejeitadas

- Manter toda a plataforma em abas internas de um componente: rejeitada por UX e acoplamento.
- Construir três backends e três SPAs separadas: rejeitada nesta fase por duplicação e manutenção.
- Implementar controle de acesso visual como se fosse autenticação: rejeitado por risco de falsa segurança.

## Consequências

A navegação nasce com estrutura adequada à futura evolução do produto. No curto prazo, React Router acrescenta dependência npm e requer testes de rotas, build e regressão responsiva. Não são implementados SSO, new endpoints, filtros server-side nem persistência de novas preferências.
