# SPEC-006A — Autorização por fila e migrações seguras (em homologação)

Primeiro incremento da evolução enterprise: filtros e permissões de SUPERVISOR/AUDITOR por fila, APIs de concessões para ADMIN, proteção de consultas de mensagens e dashboards, e migrações Alembic para SQLite com backup automático antes de atualizar o banco anterior.

**Pendente de homologação:** execute `.\\start.cmd --check` na branch `feat/006-queue-scoped-auth-foundation` e depois `.\\start.cmd`; não apague bancos nem senhas. Acesso a históricos transferidos fica temporariamente **negado** a quem não tiver concessão para todas as filas envolvidas, até a fatia SPEC-006B de segmentação histórica.

[Contrato e gates](docs/specs/SPEC-006A-queue-scopes-and-migrations.md).


## UX-005.1 — Mesa compacta e intake N1-first

Atualização da POC 0.5: a Mesa do Operador não usa mais rolagem da página; histórico de mensagens e lista de atendimento rolam apenas internamente quando necessário. Campo de resposta permanente (Enter envia; Shift+Enter adiciona linha), ações de Histórico, Transferir e Encerrar próximas ao cabeçalho da conversa. Em telas estreitas, as áreas alternam por abas.

O intake sem direcionamento explícito é **sempre N1**. O seed de demonstração vincula **Ana somente a N1** e **Bruno somente a N2**; um direcionamento com queue_id=n2 continua possível e transferências de N1 para N2 continuam automáticas. O banco de testes antigo é atualizado somente uma vez, preservando sessões ativas e mudanças subsequentes feitas pelo supervisor.

Validar com .\\start.cmd --check e .\\start.cmd após atualizar a branch. Não apague o SQLite ou as senhas.

Detalhes: [UX-005.1](docs/ux/UX-005-compact-operator-and-default-intake.md).

# Handoff Hub Multichannel — POC 0.5 / RBAC + filas automáticas

**Nova etapa:** login individual com autorização por perfil no backend, fila FIFO com rodízio durável por operador e notificação modal de novas ofertas. As telas de Operador, Supervisão e Administração continuam independentes. O SQLite recebe somente novas tabelas.

## Usuários de laboratório

| Perfil | Usuário |
|---|---|
| Administrador | admin.demo |
| Supervisor | supervisor.demo |
| Auditor | auditor.demo |
| Operador N1 | ana.demo |
| Operador N1/N2 | bruno.demo |

As senhas **não estão no código**: são geradas aleatoriamente no primeiro start.cmd e gravadas em data/demo-credentials.txt (ignorado pelo Git). Visualizar no PowerShell com Get-Content .\data\demo-credentials.txt. Para rotacionar senhas e invalidar sessões, parar o servidor e executar .\start.cmd --reset-users.

### Nova homologação Windows

    git status --short
    git fetch origin
    git switch --track origin/feat/005-rbac-auto-dispatch
    git pull --ff-only origin feat/005-rbac-auto-dispatch
    .\start.cmd --check
    .\start.cmd

Se a branch existir, usar git switch feat/005-rbac-auto-dispatch.

Para testes: login Supervisor em um navegador, login Ana e Bruno em navegadores/perfis separados, manter operadores Disponíveis e gerar solicitação sintética. A oferta aparecerá automaticamente na Mesa correta e abrirá um diálogo de aceite/recusa. Supervisão → Filas mostra ordem de distribuição e permite gerenciar membros; Supervisão → Equipe define capacidades.

**Não é produção enterprise ainda:** faltam Entra ID/OIDC, isolamento de operações, Alembic, workers externos e Teams real. Não expor esta POC fora do localhost e nunca utilizar dados de atendimento reais.

Detalhamento: [SPEC-005](docs/specs/POC-005-rbac-auto-dispatch.md).


# Handoff Hub Multichannel — POC 0.4 (workspaces separados)

## Navegação atual

Após autenticar com a chave local, acesse a **tela de escolha de workspace**. Cada espaço é uma página independente e possui uma URL própria:

| Portal | URL local | Uso |
|---|---|---|
| Escolher espaço | http://127.0.0.1:5173/inicio | Seleção de contexto na POC |
| Mesa do Operador | http://127.0.0.1:5173/operador | Ofertas, mensagens, transferência, encerramento |
| Supervisão | http://127.0.0.1:5173/supervisao | Dashboard gerencial |
| Histórico | http://127.0.0.1:5173/supervisao/conversas | Consulta somente leitura |
| Filas | http://127.0.0.1:5173/supervisao/filas | Distribuição e ofertas |
| Equipe | http://127.0.0.1:5173/supervisao/equipe | Presença e capacidade |
| Laboratório | http://127.0.0.1:5173/laboratorio | Gerar tickets fictícios |
| Administração | http://127.0.0.1:5173/administracao | Estrutura planejada, sem CRUD real |

A navegação entre portais é demonstrativa e **não representa RBAC ou SSO**. O backend e o SQLite permanecem inalterados nesta entrega.

**Para atualizar e validar:**

```powershell
git status --short
git fetch origin
git switch --track origin/feat/004-separated-workspaces
git pull --ff-only origin feat/004-separated-workspaces
.\start.cmd --check
.\start.cmd
```

Se a branch já existir localmente, use `git switch feat/004-separated-workspaces`.

Leia [ADR-0004](docs/architecture/ADR-0004-separated-workspaces.md) e [UX-004](docs/ux/UX-004-workspace-separation.md).


## Inicialização recomendada no Windows — um único comando

No PowerShell do VS Code, na raiz do projeto:

    .\start.cmd

O inicializador instala dependências quando necessário, gerencia o segredo local da POC, sobe FastAPI e Vite no mesmo terminal e abre o navegador. Encerre tudo com Ctrl+C.

Para testes automatizados sem iniciar serviços:

    .\start.cmd --check

Manual completo: [Setup em um comando](docs/setup-one-command.md).


Plataforma independente para atendimento humano originado em bots/agentes. **Esta versão é uma POC de simulação local.** Não integra o Microsoft Teams, Cisco Finesse ou bases corporativas; não está apta a produção.


## Homologação visual orientada — UX-001

A interface de Conversas possui uma jornada guiada para a POC: **Criar solicitação → Distribuir → Receber mensagem → Responder → Encerrar**. O botão principal apresenta a próxima ação adequada ao estado da sessão selecionada. O sistema sinaliza mensagens simuladas e evita confundi-las com entregas reais no Teams.

Após atualizar pelo Git, execute ` .\\start.cmd --check ` para validar backend/frontend e ` .\\start.cmd ` para abrir o ambiente. Ver [roteiro completo da UX-001](docs/ux/UX-001-guided-handoff.md).

## Revisão pós-homologação — UX-002

A POC conta com um **snapshot** `GET /v1/dashboard` que consolida as leituras de filas, operadores, atendimentos e contagem da outbox em uma requisição. O frontend atualiza o contexto a cada 15 segundos quando a aba está visível, reduzindo o excesso de polling no console. Os filtros Conversas (Todas, Em atendimento, Na fila e Encerradas) são funcionais.

**Sem envio externo** é uma informação operacional: as respostas ficam registradas em `PENDING_ADAPTER` até existir um conector Teams. Encerrar o atendimento não marca essas respostas como entregues.

Validação local: `.\\start.cmd --check`; inicialização: `.\\start.cmd`. Roteiro detalhado: [UX-002](docs/ux/UX-002-operations-review.md). Não houve alteração de esquema SQLite nem conexão com Teams.

## POC-003 — Operação humana com mesa independente

O fluxo operacional adicional permite **ofertar** atendimento em uma fila, **aceitar ou recusar** na Mesa do Operador, conversar com usuário simulado, **transferir para N2** com motivo auditado e encerrar. O antigo fluxo guiado permanece disponível para testes de regressão.

Novo caminho de homologação: **Conversas → Criar solicitação → Filas → Ofertar próximo (N1) → Mesa do Operador → Aceitar → Conversar → Transferir N2 → Ofertar N2 → Aceitar → Encerrar**.

O banco SQLite existente recebe duas tabelas novas (`handoff_offers`, `session_transfers`) por bootstrap aditivo; os registros atuais são preservados. Esta POC não possui Entra ID, RBAC, integração Teams ou envio externo.

O guia técnico completo está em [POC-003 Operação Humana](docs/specs/POC-003-operator-workflow.md).

Atualização da branch: `git switch feat/003-operator-workflow` e `git pull --ff-only origin feat/003-operator-workflow`. Validar via `.\start.cmd --check` e executar via `.\start.cmd`.

## Stack escolhida
- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.
- **Banco POC:** SQLite em arquivo, WAL e BEGIN IMMEDIATE para despacho.
- **Banco futuro:** SQL Server após revisão de transações, constraints, queries e testes no banco-alvo.
- **Frontend:** React 19, TypeScript, Vite 6, CSS responsivo.
- **Testes:** Pytest local; build frontend via npm local. **Não usar GitHub Actions**.
- **Canal Teams:** adapter Embedded previsto; bot original permanece proprietário de sua conversa.
- **Autenticação futura:** Entra ID/OIDC e OAuth2. A chave X-POC-Key atual vale exclusivamente para laboratório local.

## Executar o backend localmente
Requer Python 3.12+.

    python -m venv .venv
    # ative o ambiente virtual no sistema operacional
    python -m pip install -e ".[dev]"

No PowerShell, configure uma chave própria e execute:

    $env:HANDOFF_POC_KEY = "INSIRA-UMA-CHAVE-LOCAL-ALEATORIA"
    python -m uvicorn handoff_hub.main:app --host 127.0.0.1 --port 8000 --reload

No Linux/macOS:

    export HANDOFF_POC_KEY="INSIRA-UMA-CHAVE-LOCAL-ALEATORIA"
    python -m uvicorn handoff_hub.main:app --host 127.0.0.1 --port 8000 --reload

Documentação HTTP de teste: http://127.0.0.1:8000/docs

## Frontend React
Em outro terminal:

    cd web
    npm install
    npm run dev

Abra http://127.0.0.1:5173. Informe a mesma chave local definida no backend. A chave fica apenas na memória da página, sem persistência no navegador. Após autenticar, o app cria somente registros fictícios de laboratório.

## Funcionalidades implementadas
- Seed de operação/integração/fila/operadores demonstrativos (idempotente).
- Criação de atendimentos em fila com Idempotency-Key.
- Distribuição manual do próximo atendimento a operador com capacidade disponível.
- Presença e capacidade de operadores.
- Mensagens usuário-operador em sessão, deduplicação de mensagens.
- Respostas de operador gravadas em outbox como PENDING_ADAPTER.
- Encerramento de atendimento com liberação de capacidade.
- Cockpit operacional, lista de filas, painel de operadores, conversa simulada, atualização periódica.
- Banco SQLite com nove tabelas, índices e FKs.

**Não implementado ainda:** autenticação corporativa, multioperação segura, mensagens reais Teams, worker de entrega, conectores, automação de distribuição, SLA, Finesse, Alembic e dashboards analíticos completos.

## Testes sem GitHub Actions

    python -m pytest -q
    ruff check src tests
    cd web
    npm run build

O teste de concorrência verifica que duas requisições concorrentes não atribuem mais do que a capacidade de um operador. Para o frontend é necessário ter acesso às dependências npm na máquina de execução.

## Documentação e governança
- [Constituição](CONSTITUTION.md)
- [Agentes](AGENTS.md)
- [ADR 0001](docs/architecture/ADR-0001.md)
- [ADR 0002](docs/architecture/ADR-0002-channel-ownership.md)
- [Esquema POC](docs/poc-data-model.md)
- [Roadmap](docs/roadmap.md)
- [Legado: referência funcional](docs/legacy-compatibility.md)
- [Contrato proposto (não implementado integralmente)](docs/contracts/openapi.yaml)

## Segurança
Executar **somente em 127.0.0.1**, sem publicar na rede. Não adicionar código, mensagens, segredos ou endpoints internos do sistema legado ao repositório. Os scripts originais definem comportamentos e requisitos, **não constituem migração técnica ou de dados**.
