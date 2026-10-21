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
   `handoff-rc001-operations-batch`, detached no SHA.
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
