# UX-004 — Portal do Operador separado da Supervisão

**Status:** IMPLEMENTED / AWAITING WINDOWS ACCEPTANCE  
**Produto:** Handoff Hub POC 0.4  
**Branch:** `feat/004-separated-workspaces`

## Dor observada

O fluxo estava funcional, mas todas as atividades ficavam na mesma tela/navegação, obrigando o atendente a conviver com controles e indicadores gerenciais. A mistura agravou o problema de altura e dos botões cortados na versão anterior.

## Desenho de produto

### 1. Mesa do Operador — `/operador`

- Shell próprio, separado do painel de supervisão.
- Operador selecionável **apenas por ser POC**, até existir SSO.
- Ofertas recebidas, aceite/recusa, atendimentos ativos, chat, transferência, encerramento e trilha de auditoria.
- Sem indicadores de toda a operação e sem sidebar administrativa.
- Rolagem acessível, preservando mensagens e ações inferiores.

### 2. Supervisão — `/supervisao`

- Visão geral com KPIs, saúde do backend/adapter e estado das filas.
- Páginas específicas para **Conversas (somente leitura)**, **Filas (despacho)** e **Equipe (presença e capacidade)**.
- Links de acompanhamento entre páginas e atalho explícito para a Mesa do Operador enquanto durar a POC.

### 3. Administração — `/administracao`

- Layout independente, com cards dos domínios futuros: bots e integrações, operações/filas, perfis, políticas.
- Todos os cards marcados como **planejados**. Nenhuma API CRUD administrativa é simulada como funcional.

### 4. Laboratório — `/laboratorio`

- Espaço exclusivo para criar tickets fictícios.
- Passos de homologação: criação → fila → oferta → aceite → atendimento.
- Sem comandos de simulação misturados nos painéis executivos.

## Critérios de aceite

- [ ] Uma pessoa em `/operador` não vê o menu lateral de administração/supervisão.
- [ ] `/supervisao` apresenta visão gerencial, sem editor de mensagens.
- [ ] `/supervisao/conversas` consulta histórico sem endpoints de escrita do operador.
- [ ] `/supervisao/filas` mostra N1 e N2 com contagens corretas e gera oferta.
- [ ] Uma oferta N2 abre a Mesa do Bruno (identidade simulada).
- [ ] `/laboratorio` cria ticket na fila N1 e conduz ao gerenciamento de filas.
- [ ] Abrir diretamente `/operador`, `/administracao`, `/supervisao/filas` funciona no servidor Vite após login.
- [ ] Recarregar a página mantém a URL; a chave local é solicitada novamente por ser armazenada só na memória.
- [ ] Testar 1730×865, 1366×768, 1024×768 e 390×844; sem perda de acesso a transferência/encerramento.
- [ ] `start.cmd --check` aprova Pytest, Ruff, testes de contrato de rotas, TypeScript e Vite.
- [ ] Nenhuma tabela SQLite é modificada por esta SPEC.

## Passo a passo no VS Code (PowerShell)

Com a POC anterior encerrada:

```powershell
git status --short
git fetch origin
git switch --track origin/feat/004-separated-workspaces
git pull --ff-only origin feat/004-separated-workspaces
.\start.cmd --check
.\start.cmd
```

Se a branch já existir, use `git switch feat/004-separated-workspaces`.

**Execução manual:** acesse a aplicação, informe a chave local → Laboratório (criar solicitação) → Supervisão/Filas (ofertar N1) → Portal do Operador (aceitar) → transferir N2 → Supervisão/Filas (ofertar N2) → Portal do Operador (Bruno aceita e encerra) → Supervisão/Conversas (histórico).

## Gates e limitações

A validação estática inicial de referências e módulos foi realizada; compilação real React/TypeScript, teste local Node e homologação visual dependem de execução no VS Code. Esta é separação de navegação, **não segregação de acesso efetiva**.

Próximas evoluções: design tokens e componentes de produto, permissões/RBAC reais, Alembic, worker de outbox, integração Teams Embedded e testes E2E Playwright locais.
