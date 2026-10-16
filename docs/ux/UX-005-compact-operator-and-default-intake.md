# UX-005.1 — Mesa compacta e entrada N1

Status: implementado na branch, pendente de homologação Windows.
Base: POC-005 RBAC e distribuição automática.

## Problema e diagnóstico

A Mesa do Operador possuía elementos gerenciais redundantes e rolagem da página. Isso afastava o campo de resposta e os controles da área de conversação. O segundo teste também apresentou Bruno como destinatário de um chamado genérico: a API já estabelecia N1 como default, mas o cadastro demonstrativo associava Bruno tanto ao N1 quanto ao N2.

## Decisão UX

- A página do operador ocupa exatamente a viewport (100dvh), sem rolagem externa.
- Cabeçalho reduzido: operador autenticado, presença e notificações opcionais.
- Esquerda: caixa de trabalho compacta, com scroll interno somente se necessário.
- Direita: conversa dominante; somente o histórico de mensagens tem rolagem interna.
- Composer e botão Enviar sempre visíveis; Enter envia, Shift+Enter quebra linha.
- Histórico, transferência e encerramento ficam na barra superior da conversa. Formulário de transferência e trilha auditável aparecem sob demanda.
- Avisos de sucesso/erro não deslocam a conversa; ofertas novas continuam gerando o modal.
- Em largura até 780px, alternância de painéis para manter a interação utilizável sem rolagem externa.
- Outbox ainda não é entrega Teams: respostas continuam PENDING_ADAPTER.

## Política de entrada

1. Chat novo sem queue_id explícito: fila N1.
2. Chat com queue_id explícito e válido: fila informada (ex.: N2).
3. Transferência de operador: fila de destino informada e validada.
4. Roteamento por intenção/canal: motor de políticas futuro, não ativado implicitamente.

A escolha de operador ocorre depois da escolha da fila, baseada em membership, sessão online, presença, capacidade e rodízio.

## Seed e migração idempotente

Cadastro demonstrativo inicial: Ana membro de N1, Bruno membro de N2.

A tabela aditiva demo_seed_revisions marca a revisão aplicada uma única vez. Na atualização de SQLite anterior:
- Remove a antiga associação Bruno/N1.
- Uma oferta pendente de N1 para Bruno volta à fila, com evento de auditoria.
- Sessões ACTIVE continuam atribuídas a Bruno até o encerramento.
- A revisão não é repetida em reinícios, preservando posteriores mudanças intencionais do supervisor.

O script de inicialização continua criando as contas de teste normalmente, sem apagar o banco ou redefinir senhas. Isso é migração de seed demonstrativo, não substitui Alembic enterprise.

## Gates

- [ ] start.cmd --check (Pytest, Ruff, testes de arquitetura, TS e Vite).
- [ ] 1730x865, 1366x768, 1280x720: nenhuma rolagem vertical da página do operador.
- [ ] Resposta, transferência e encerramento acessíveis sem rolagem da página.
- [ ] Mensagens extensas e worklist extensa rolam somente dentro dos painéis.
- [ ] Novo chat genérico entra em N1 e somente Ana é elegível no seed.
- [ ] Ana ocupada, Bruno livre: chat genérico permanece aguardando N1.
- [ ] Transferência para N2: Bruno recebe a oferta automaticamente.
- [ ] queue_id=n2 explícito: chat entra diretamente em N2.
- [ ] Histórico, outbox, RBAC e modal não sofrem regressões.
- [ ] Supervisor pode adicionar Bruno a N1 deliberadamente; ajuste permanece após reinício.
- [ ] Sem GitHub Actions.

## PowerShell

    cd C:\Projetos\hub-handoff\hub-handoff-multichannel
    git status --short
    git switch feat/005-rbac-auto-dispatch
    git pull --ff-only origin feat/005-rbac-auto-dispatch
    .\start.cmd --check
    .\start.cmd

Nenhuma modificação de dados corporativos ou integração Teams foi adicionada.
