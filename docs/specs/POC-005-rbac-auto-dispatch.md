# SPEC-005 — Perfis RBAC e despacho automático (SQLite POC)

Data: 2026-10-15. Estado: implementada na branch feat/005-rbac-auto-dispatch, pendente de testes locais e homologação no Windows.

## Perfis, credenciais e limites

| Perfil | Usuário de teste | Permissões |
|---|---|---|
| ADMIN | admin.demo | Configuração futura, supervisão e laboratório; sem atuar como operador |
| SUPERVISOR | supervisor.demo | Visão operacional, filas, equipe e laboratório; sem assumir atendimentos |
| OPERATOR | ana.demo | Própria mesa, aceite, recusa, mensagens, presença, transferência e encerramento |
| OPERATOR | bruno.demo | As mesmas funções, restritas à própria identidade e sessões |
| AUDITOR | auditor.demo | Consultas gerenciais e histórico, sem mutações nem leitura do conteúdo da outbox |
| INTEGRATION | não provisionado | A integração bot-to-hub terá credencial própria na futura SPEC |

As senhas são aleatórias, geradas **no computador de homologação**, não publicadas no GitHub nem no chat. Após iniciar com start.cmd, consulte o arquivo local ignorado pelo Git:

    Get-Content .\data\demo-credentials.txt

O arquivo contém cinco linhas com usuário, perfil e senha. Para trocar senhas (invalidando sessões anteriores) execute com o servidor parado:

    .\start.cmd --reset-users

O login utiliza PBKDF2-SHA256 com sal individual e 600.000 iterações, sessões Bearer opacas com hash SHA-256 persistido, prazo de oito horas e revogação. Cinco tentativas inválidas bloqueiam temporariamente a conta por quinze minutos. A API valida papéis e o vínculo da sessão com o operador, não apenas o menu React.

Este mecanismo continua **restrito a localhost**: não substitui Entra ID, OIDC, MFA, TLS e autorização corporativa multitenant. Não usar dados reais.

## Regras de distribuição

- Pedidos são atendidos por ordem de chegada (FIFO) na fila.
- Só entram no despacho operadores membros da fila, ONLINE por sessão autenticada recente, com presença AVAILABLE e capacidade livre.
- O worker avalia a fila a cada cerca de dois segundos e faz reserva atômica via BEGIN IMMEDIATE no SQLite.
- Cada oferta altera a posição de rodízio do operador **imediatamente**, com horário persistido por fila.
- O operador elegível menos recentemente ofertado é escolhido. Se só um estiver apto, ele poderá receber novamente quando houver capacidade.
- Capacidade engloba ofertas e atendimentos ativos; não se sobrealoca uma vaga.
- Oferta expira em 120 segundos, ou é devolvida à fila se o operador desconectar.
- Recusas e expirações têm cooldown de 120 segundos para evitar o mesmo ticket voltar imediatamente ao mesmo operador.
- A Mesa do Operador consulta as ofertas a cada três segundos e abre alerta modal quando recebe uma nova. O navegador pode exibir notificação de sistema após consentimento.
- A transferência N1 → N2 registra histórico e reentra automaticamente na fila N2.

Persistência aditiva: auth_users, auth_sessions, login_throttles e dispatch_turns. Banco SQL Server/Alembic, serviço separado de worker e eventos push continuam futuras SPECs.

## Ações para homologar

1. Login de supervisor.demo, Ana e Bruno em sessões separadas (abas ou perfis de navegador).
2. No supervisor, criar solicitação pelo Laboratório; com operadores desconectados deve ficar aguardando.
3. Logar Ana e mantê-la Disponível: verificar popup e opção de aceitar/recusar.
4. Com Ana e Bruno online e disponíveis, validar distribuição alternada por fila e capacidade.
5. Encerrar atendimento e observar operador voltar a ser elegível na ordem correta.
6. Transferir para N2 e verificar chegada somente a Bruno quando ele estiver online e disponível.
7. Testar 403: operador em dashboard, operador na caixa alheia, auditor tentando alteração, supervisor tentando resposta.
8. Sair do sistema: oferta não aceita deve retornar à fila após detecção de sessão offline.
9. Verificar build, qualidade e testes com .\start.cmd --check.
10. Validar popup e ações na resolução desktop e menor largura sem cortes.

## Git e VS Code

    cd C:\Projetos\hub-handoff\hub-handoff-multichannel
    git status --short
    git fetch origin
    git switch --track origin/feat/005-rbac-auto-dispatch
    git pull --ff-only origin feat/005-rbac-auto-dispatch
    .\start.cmd --check
    .\start.cmd

Se a branch local já existir, utilize git switch feat/005-rbac-auto-dispatch.

Sem GitHub Actions. Sem migração automática do sistema legado.

## Gates enterprise que permanecem abertos

Autenticação Entra ID/OIDC, RBAC granular e isolamento por operação, Alembic, worker multi-instância, entrega Teams de verdade, escalabilidade SQL Server, auditoria de segurança, proteção CSRF conforme modelo de sessão, SLOs e observabilidade, testes de carga e E2E. A POC é enterprise-oriented, não um produto homologado para produção.


## Revisão de estabilização posterior à implementação

- A identidade antiga baseada em X-POC-Key não é mais injetada pelo launcher no backend normal; permanece apenas no modo explícito dos testes legados. O health/ready verifica contas locais provisionadas.
- O rodízio usa timestamps UTC normalizados para evitar misturar datetime aware/naive durante reservas de múltiplos atendimentos.
- Novos testes incluem despacho paralelo sem sobrealocação, FIFO, reset de senhas invalidando tokens, recusa/expiração e proibição de impersonação pelo ADMIN.
- A Mesa do Operador mantém a sessão selecionada quando ativa a permissão de notificações e dá foco ao diálogo de nova oferta.
- O chat ativo também se atualiza periodicamente, sem botão de recarga.
- O Laboratório descreve corretamente a distribuição automática; operador autenticado não consegue criar mensagens fictícias como usuário.
- A supervisão apresenta primeiro operadores realmente elegíveis, mantendo a ordem persistida de atendimento.

Nenhuma aprovação local foi simulada: o gate final permanece a execução de start.cmd --check e a homologação real no VS Code do usuário.
