# RC-001 — Bloco 02: Operação Integrada (G04 + G06 + regressão G07)

**Branch:** `feat/rc001-operations-batch`, empilhada sobre o PR #56,
cujo SHA `1d9c651ba29f5d1f9f02d31b5347cf5964b6b1f4`
tem regressão automatizada e matriz básica das cinco personas PASS relatados.
**Estado:** CODED / WINDOWS_QA_NEW_SHA_NOT_RUN / DRAFT / NO_MERGE.

## Objetivo e escopo

Reunir administração, ciclo de vida, fluxo operacional e histórico em um
único bloco de homologação, em vez de PRs/testes avulsos.

- **G01**: regressão de todo projeto, Ruff, arquitetura frontend, TypeScript/Vite.
- **G04**: oferta N1, aceite por Ana, mensagens, nota interna longa,
  transferência para N2, oferta e aceite por Bruno, encerramento,
  evidências de segmentos VERIFIED e segregação do histórico.
- **G06**: criação administrativa de fila auditada sem grant automático,
  DRAFT/ACTIVE/PAUSED/ARCHIVED com CAS, rejeição de fila indisponível,
  inventários de pessoas e filas, bloqueio por papel/cross-operation,
  concorrência e falhas fail-closed.
- **G07 parcial**: contrato da tela de login corrigido; ela não presume que
  as credenciais de LAB estejam no arquivo da POC original.
- **G03/G08**: release probe efêmero reexecutado como proteção transacional.
- **G09/G10**: revisão independente e aceite humano não são automáticos.

O novo teste `test_rc001_operations_batch.py` cruza criação/lifecycle 007a2
com a operação N1→N2 dentro da mesma base **TEMP**, usando somente contas
sintéticas. Não utiliza ambiente corporativo nem altera a base local antiga.
Os demais testes de fluxo/UI/regressão continuam compondo o pacote.

## Execução Windows — uma rodada automatizada

1. Ter Python 3.12/Node no host, parar launchers anteriores e
   `git fetch origin` no clone/worktree RC.
2. Confirmar **SHA exato do PR de bloco 02** e criar worktree TEMP separada
   `handoff-rc001-operations-retest`, detached no SHA. O destino antigo
   `handoff-rc001-operations-batch` pertence ao SHA bloqueado: preserve-o
   para diagnóstico, sem trocar HEAD ou alterar seus testes.
3. Confirmar `git status --porcelain` vazio e remover `HANDOFF_DB_URL`
   somente da sessão QA.
4. Execute **um único comando**:
   `python scripts\rc001_operational_gate.py --expected-sha <SHA>`.
5. Runner verifica diretório TEMP físico via `os.path.samefile`, SHA local
   e remoto, SHA congelado da RC, diff sem DB/segredos e worktree limpa.
6. Runner executa `start.cmd --check`, pytest dirigido G04, pytest dirigido
   G06, node-test arquitetura e `release_probe.py`, parando no primeiro erro.
   Gera `summary.json` sanitizado em TEMP (sem stdout/senhas/tokens/SQLite).
7. **Nada é automaticamente marcado como PASS** até logs no SHA exato;
   G09 e G10 continuam independentes.

## Sessão humana única — cenários completos

Em um **NOVO** laboratório TEMP 006b4, desligar API e worker; realizar backup
e `upgrade-lifecycle --confirm-offline` para 007a2 e inspecionar revisão,
hash e contagens (seguir runbook G03). Só depois iniciar
`start.cmd --lab --lab-dir "<LAB>"`.

### Administração e lifecycle
1. ADMIN: verificar pessoas e vínculos sem segredos; criar fila fictícia
   `qa-operacional`; ver DRAFT, sem grant/membership implícito.
2. Validar ausência de roteamento para DRAFT; ativar e conferir version CAS,
   pausar sem tickets, reativar, pausar e arquivar em fila vazia.
3. Tentar ação inválida/vencida; exigir 409 sem corromper estado ou diário.
4. Validar navegação Tab/tabelas administrativas em 1366×768 e 1920×1080,
   zoom 100%/200%.

### Atendimento completo
5. Em N1, supervisor cria solicitação sintética e Ana recebe/aceita
   **com mouse**, envia mensagem. Inspecionar feedback sem sobreposição.
6. Ana transfere N1→N2 com motivo longo. Nota interna fica visível apenas
   para operador de destino autorizado, nunca no histórico de mensagens
   apresentado ao cliente ou em segmentos de outras filas.
7. Bruno/N2 aceita **com mouse**, envia resposta e encerra. Conferir
   0 sessões ativas/ofertas pendentes e estado CLOSED no SQLite do LAB.
8. AUDITOR N1: VERIFIED LIST/DETAIL mostra apenas mensagens de N1, nunca
   conteúdo N2; N2 por AUDITOR N1 deve ser 404. SUPERVISOR N2 vê apenas seu
   segmento (conforme grants).
9. Testar teclado Tab/Enter e campos scrolláveis do diálogo, sem recorte
   horizontal ou interceptação de clique, nas resoluções do G07.

### Limpeza e aceite
10. Capturas/logs sanitizados sem credenciais ou payload sensível;
    revisão 007a2 e banco sintético, sem acesso ao POC original.
11. Encerrar launcher e portas, preservar os SHAs dos PRs #51/#52/#55/#56.
    G09 exige revisão independente; G10 aceite explícito; nenhum merge.

## Achado de segurança QA do Bloco 01

Durante a automação anterior foi usado um **servidor local HTTP temporário**
para disponibilizar senhas sintéticas ao navegador. O servidor foi
encerrado e o laboratório descartado; **não repetir esse mecanismo**.
Para novos testes, usar credenciais sintéticas manualmente no laboratório
ou acesso de teste isolado que não exponha uma lista de senhas num endpoint,
sem gravar token/senha nos artefatos.

## Critérios de parada

Falha em isolamento 401/403/404, escrita de grants implícitos, alteração de
fila sem CAS, integridade/versionamento, histórico N1/N2, actionability do
modal/teclado, journal fail-closed ou acesso ao SQLite original **bloqueia**
a entrega. Corrigir e revalidar como um só bloco. Não lançar a POC com
`start.cmd` simples nem promover `main` ou RC sem aprovação.

## Rodada bloqueada em 21/10/2026 e correção em lote

No SHA anterior `737da22a8a4072367e1b67c63f884f66a1a8ddd5`:
- `python scripts\\rc001_operational_gate.py` foi bloqueado na importação
  do helper `scripts.rc001_integrated_gate` antes de executar gates;
- `python -m scripts.rc001_operational_gate` iniciou o gate, mas G01 ficou
  **BLOCKED**: pytest **193 passed / 1 skipped**, Ruff **I001**
  no import block de `tests/test_rc001_operations_batch.py`. O build Vite
  e as suítes G04/G06/G07/release probe não foram alcançados.

Esta correção mantém **as duas formas de invocação** disponíveis, adiciona
teste de subprocesso `--help` para ambas e separa explicitamente com
`# isort: split` as importações do pacote Python e do harness de QA.
O SHA novo precisa de nova execução no Windows; nada é considerado PASS
por herança. **Não** executar `ruff --fix` na worktree de homologação
detached, pois alteraria o checkout e invalidaria o préflight de árvore limpa.

Para retestar em lote: atualizar as referências remotas por `git fetch`,
criar **nova** worktree `handoff-rc001-operations-retest` (não alterar a
worktree bloqueada), confirmar seu SHA e executar exatamente:
`python scripts\\rc001_operational_gate.py --expected-sha <NOVO_SHA>`.
Em caso de FAIL, registrar etapa, exit code e contagens, além de **diagnóstico
local sanitizado** de lint/testes; não divulgar stdout com tokens, senhas,
identificadores ou conteúdo de conversas.

**Revisões que continuam pendentes:** G04/G06/G07 em Windows no SHA corrigido,
cenários completos de navegador com ação real e G09/G10 independentes.

## Segundo reteste BLOCKED — 21/10/2026

A execução no SHA `cd18c18e48053662c14624611602150b77c19b28`
confirmou que a importação direta do runner foi corrigida.
O G01 iniciou, com **194 pytest PASS e 1 SKIP**, porém o Ruff
continuou recusando `tests/test_rc001_operations_batch.py` com
`I001`. A estratégia `# isort: split` **não resolveu o problema**.
O frontend build e os gates G04/G06/G07/release probe não foram
executados por fail-fast. Worktree limpa, sem acesso ao SQLite original.

### Correção consolidada neste SHA

Remover o marcador `# isort: split` e alinhar as importações
`handoff_hub` e `scripts` no mesmo bloco de módulos locais,
exatamente como o arquivo `tests/test_spec007_queue_lifecycle.py`
que já passou pelo Ruff nos gates anteriores. O contrato do runner
também passa a verificar que essa regressão não volte a ser introduzida.
O código de runtime/backend/frontend/migrations não foi alterado.

O reteste deve criar uma NOVA worktree TEMP chamada
`handoff-rc001-operations-final`. Preservar as anteriores para auditoria.
O comando é o mesmo da homologação integrada, com o SHA novo:
`python scripts\\rc001_operational_gate.py --expected-sha <SHA>`.
Nenhum PASS é herdado para os gates ainda não executados.

**Limitação:** esta correção foi conferida por comparação estática de
padrão com testes do próprio repositório; a aprovação Ruff real e todo
o gate Windows ainda precisam ser executados pelo executor local.

## Fast-fail de qualidade — mesma rodada, sem microtestes

Antes de iniciar o `start.cmd --check` integral, o runner agora
executa `start.cmd --setup-only` para preparar dependências (sem
iniciar a API/POC) e `ruff check src tests` no checkout.
Se `G00_RUFF_PREFLIGHT` reprovar, o runner **para nesse ponto** e
gera `summary.json` com nome da etapa/código, sem gastar uma rodada
inteira de Pytest. Se aprovar, roda a regressão integral (G01)
e, na sequência, G04/G06/G07/release probe **no mesmo comando**.

Isto é uma etapa de diagnóstico antecipado, não uma aprovação
independente nem substituto de G01 ou G09/G10.

## Terceira execução bloqueada — pré-flight Ruff I001 (21/10/2026)

No SHA `9bdb4d885b7c847004c16a8129ec7ee9976bd54a`,
em uma nova worktree TEMP limpa, o `G00_SETUP_ONLY` passou e
`G00_RUFF_PREFLIGHT` bloqueou com `I001`. O comando
`python -m ruff check --diff tests/test_rc001_operations_batch.py`
apontou somente **uma linha vazia excedente** entre o import de
`scripts.release_grant_toggle.bearer` e a constante `KEY`.
Esta rodada não executou G01, G04, G06, G07 nem release probe;
isso **não** deve ser relatado como aprovação parcial desses gates.

A correção altera apenas esse espaçamento, exatamente conforme
a indicação do Ruff, sem voltar a modificar a ordenação dos imports.
Adiciona teste contratual verificando **um único** newline vazio antes
de `KEY` e atualiza este runbook. Para homologação, criar worktree
TEMP nova (p.ex. `handoff-rc001-operations-rerun`), nunca modificar
`handoff-rc001-operations-final`. Executar o runner consolidado
e anexar apenas o `summary.json` sanitizado.

**Nota de escopo:** não foi possível executar o binário Ruff do Windows
neste ambiente de revisão; o próprio `G00_RUFF_PREFLIGHT` do novo SHA
precisa confirmar o PASS. G09/G10 continuam pendentes.
