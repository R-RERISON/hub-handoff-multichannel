# POC-003 — Operação humana com oferta, aceite, recusa e transferência

Data: 2026-10-15 | Status: IMPLEMENTED / AWAITING LOCAL VALIDATION

## Contexto

O usuário validou o ciclo anterior de criação, distribuição direta, mensagens e encerramento. A evolução desta etapa constrói a operação **oferta / aceite / recusa** com uma mesa independente de atendimento. O bot originador da conversa continua fora da operação humana.

Este incremento preserva o fluxo de demonstração antigo `POST /v1/dispatch/next` para regressão, mas apresenta o **novo caminho recomendado** usando `POST /v1/dispatch/offer`.

## Fluxo funcional

1. **Conversas:** crie uma solicitação fictícia (estado QUEUED).
2. **Filas:** clique Ofertar próximo na fila Suporte N1. O backend seleciona operador com presença AVAILABLE e capacidade livre; fica OFFERED.
3. **Mesa do Operador:** selecione Ana ou Bruno conforme a oferta. Aceite para ACTIVE ou recuse para QUEUED.
4. **Atendimento:** troque mensagens em simulação local. Resposta humana fica na outbox com status PENDING_ADAPTER (nada é enviado ao Teams).
5. **Transferência:** envie para Suporte N2, informando o motivo. O operador libera capacidade, o atendimento retorna QUEUED em N2 e a trilha é gravada.
6. **Nova oferta em N2:** o supervisor oferta a fila N2 ao operador Bruno. Aceite e conclua.
7. **Encerramento:** operador responsável conclui o atendimento; capacidade é liberada. A outbox não é marcada como entregue.

## Modelo de dados aditivo

| Tabela | Descrição |
|---|---|
| `handoff_offers` | Cada oferta com operador, prazo, estado PENDING/ACCEPTED/DECLINED/EXPIRED e data da decisão |
| `session_transfers` | Histórico de origem/destino, operador anterior, motivo e horário |
| `session_events` | Trilha existente ampliada: OFFERED, ACCEPTED, DECLINED, OFFER_EXPIRED, TRANSFERRED, CLOSED |

As duas novas tabelas são criadas automaticamente pelo `Base.metadata.create_all` na POC; **não há upgrade de colunas existentes nem migração de dados legados**. Essa estratégia de bootstrap não substitui o Alembic planejado.

## Contrato implementado

| Método/Endpoint | Uso |
|---|---|
| POST /v1/dispatch/offer | Cria uma oferta para o primeiro ticket QUEUED elegível |
| GET /v1/operators/{operator_id}/work | Ofertas e atendimentos ativos do operador |
| POST /v1/handoffs/{id}/accept | Aceita uma oferta pendente; corpo `{"operator_id":"op-ana"}` |
| POST /v1/handoffs/{id}/decline | Recusa a oferta, liberando capacidade |
| POST /v1/handoffs/{id}/transfer | Transfere sessão ativa, com operator_id, queue_id e reason |
| POST /v1/operators/{operator_id}/handoffs/{id}/close | Encerramento verificando responsabilidade da sessão |
| POST /v1/offers/expire | Expiração manual de ofertas vencidas, para a POC |
| GET /v1/handoffs/{id}/timeline | Eventos e transferências auditadas |

Os endpoints são autenticados **apenas pela chave de POC compartilhada**; o seletor de operador representa identidade fictícia, não é SSO nem autorização individual. **Não publicar fora de localhost.**

## Políticas temporárias

- Prazo da oferta: 120 segundos.
- Recusa: operador que recusou não recebe a mesma oferta por 120 segundos.
- Capacidade: soma de ofertas em aberto (OFFERED) e atendimentos ativos (ACTIVE).
- Operador precisa estar AVAILABLE e participar da fila.
- O mecanismo atual de reavaliação de expiração é acionado pelo novo dispatcher e pela operação explícita POST /v1/offers/expire; ainda **não existe worker durável**.
- O operador não pode aceitar oferta vencida, atender em fila não autorizada ou transferir atendimento de outra operação.
- Retentativas indevidas resultam em erro 409 e não duplicam efeitos.

## Gaps conhecidos

1. Sem RBAC/Entra ID: os endpoints legados ainda usam chave compartilhada; não tratar como segurança de produção.
2. Sem Alembic: esquema incremental via create_all é somente POC descartável.
3. Sem inbox/outbox worker ou ACK externo: mensagens continuam sem entrega ao Teams.
4. Sem controle de autorização por perfil nos endpoints antigos de demonstração.
5. Sem operação em rede ou multi-instância: SQLite BEGIN IMMEDIATE oferece serialização do escritor local; a estratégia SQL Server será outra.
6. Sem redirecionamento direto operador-para-operador; esta fase transfere para fila.
7. Sem horários, SLAs, turnos ou skill-based routing.

## Homologação pelo VS Code

Fechar o inicializador anterior (Ctrl+C), fazer backup do SQLite antes de atualizar se desejar preservar o estado de demonstração e executar:

```powershell
git status --short
git switch feat/003-operator-workflow
git pull --ff-only origin feat/003-operator-workflow
.\start.cmd --check
.\start.cmd
```

No navegador: Conversas → Nova solicitação → Filas → Ofertar próximo (N1) → Mesa do Operador → Selecionar identidade → Aceitar → Simular conversa → Transferir para N2 → Filas → Ofertar N2 → Mesa do Operador (Bruno) → Aceitar → Encerrar.

**Não utilizar GitHub Actions.**

## Gates de testes propostos

- Execução dos testes locais existentes.
- Testes novos: oferta concorrente/sem sobrealocação, operador errado, aceite duplicado, recusa, transferência e trilha, expiração, controle de capacidade entre modo direto e nova oferta, encerramento vinculado a operador.
- Build TypeScript + Vite da nova Mesa do Operador.
- Revalidação manual no navegador e observação dos estados no SQLite.

**Nota:** a implementação está publicada para testes; nenhum gate da nova etapa será reportado como aprovado até confirmação de execução.


## Correção pós-homologação — N1 → N2 (UX-003.1)

### Evidência recebida

No log da POC, `POST /transfer` devolveu HTTP 200 e em seguida `POST /dispatch/offer` também devolveu HTTP 200. Entretanto, todas as consultas subsequentes da Mesa do Operador foram feitas a `/v1/operators/op-ana/work`. No seed demonstrativo, **apenas op-bruno pertence à fila N2**. A resposta HTTP 200 do dispatcher não assegura `result=offered`; pode ser `empty_queue` ou `no_operator_available`.

### Regra

Após transferir N1 → N2, a sessão muda para **QUEUED, queue_id=n2**. Quando a supervisão cria uma oferta para N2, ela passa a **OFFERED, queue_id=n2, operator_id=op-bruno**. A quantidade `waiting` fica zero nesse instante, porque a oferta já saiu da espera. O ticket não deve desaparecer dos indicadores nem exigir que o supervisor adivinhe quem foi selecionado.

### Alterações

- `GET /v1/dashboard`: cada fila apresenta contadores distintos de `waiting`, `offered` e `active`.
- Tela Filas: apresenta os três estados, com listagem das sessões oferecidas e identidade destinatária.
- Ao clicar **Ofertar próximo**, o frontend navega automaticamente à Mesa do Operador correto (no N2: Bruno).
- O botão **Abrir mesa de Bruno** permite retornar à oferta diretamente pela fila.
- Mesa do Operador respeita a identidade recebida pelo roteamento; não volta sempre para Ana.
- Filtro Conversas inclui estado `Ofertadas`.
- Novo teste de regressão `test_n1_to_n2_queue_counters_and_bruno_inbox` verifica fila N2 aguardando, depois N2 ofertada, visibilidade exclusiva na inbox de Bruno e vínculo correto da sessão.
- Correção Ruff `UP035`: `collections.abc.Callable`.

### Reproduzir no VS Code

Pare `start.cmd` com Ctrl+C. Faça `git fetch origin` e `git pull --ff-only origin feat/003-operator-workflow`. Execute `.\start.cmd --check`, depois `.\start.cmd`.

1. Abra ticket N1, oferte e aceite com Ana.
2. Transfira para N2. Na aba Filas, N2 mostra **1 na fila**.
3. Clique **Ofertar próximo** na N2.
4. O sistema deve abrir automaticamente Mesa do Operador com **Bruno** selecionado e a oferta visível.
5. Na aba Filas, N2 mostra **0 na fila, 1 ofertado** até o aceite.
6. Bruno aceita, a sessão fica ACTIVE em N2 e mantém histórico de transferência.

Se não houver capacidade em N2, a sessão deve continuar em `QUEUED` e a interface informar `no_operator_available`.

**Validação desta correção ainda depende de `start.cmd --check` e da inspeção visual no Windows.**


## UX-003.2 — Correção de corte da Mesa do Operador

### Reprodução / causa

Captura em desktop mostra a tela da Mesa do Operador terminando antes dos controles de transferência e encerramento. A folha de estilos global aplica `height:100dvh` e `overflow:hidden` à área `.content` em telas largas; a implementação adicional ainda usava `.desk-layout{overflow:hidden}`, comprimindo uma grade contendo cabeçalho, conversação, campo de resposta, transferência e histórico.

O conteúdo estava presente no DOM, mas não era acessível pela rolagem principal.

### Ajuste publicado

- `App.tsx` atribui `content--desk` somente à Mesa do Operador.
- Removida a segunda linha de métricas globais no workspace do operador (a Mesa possui indicadores próprios).
- `.content--desk` recebe `overflow-y:auto` e altura controlada pela viewport; sidebar permanece independente.
- `.desk-layout` deixa de cortar conteúdo. A grade possui altura mínima suficiente e o histórico das mensagens mantém rolagem interna.
- As ações da base do chat (resposta, transferência, encerramento, timeline) não encolhem nem são cortadas.
- Breakpoints abaixo de 1180/1000/620px reorganizam formulário de transferência, painéis e ações.

### Homologação obrigatória

No VS Code, após atualizar a branch, executar `.\start.cmd --check` e `.\start.cmd`.

Com atendimento ativo:
1. Abrir Mesa do Operador em navegador desktop (por exemplo, 1730x865).
2. Rolar a **área principal**, não a sidebar; conferir que **Transferir** e **Encerrar atendimento** estão acessíveis.
3. Conferir rolagem independente da lista de mensagens.
4. Validar também em 1366x768, 1280x720 e uma largura de 800px usando DevTools.
5. Testar transferência para N2, aceite de Bruno e encerramento.
6. Confirmar que Conversas, Filas e Operadores não sofreram regressão visual.

**Nenhuma alteração em SQLite ou nas APIs de negócio.** Não marcar homologado sem retorno da execução Windows.
