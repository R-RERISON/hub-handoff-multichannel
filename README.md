# Handoff Hub Multichannel — SQLite POC v0.2

## Inicialização recomendada no Windows — um único comando

No PowerShell do VS Code, na raiz do projeto:

    .\start.cmd

O inicializador instala dependências quando necessário, gerencia o segredo local da POC, sobe FastAPI e Vite no mesmo terminal e abre o navegador. Encerre tudo com Ctrl+C.

Para testes automatizados sem iniciar serviços:

    .\start.cmd --check

Manual completo: [Setup em um comando](docs/setup-one-command.md).


Plataforma independente para atendimento humano originado em bots/agentes. **Esta versão é uma POC de simulação local.** Não integra o Microsoft Teams, Cisco Finesse ou bases corporativas; não está apta a produção.

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
