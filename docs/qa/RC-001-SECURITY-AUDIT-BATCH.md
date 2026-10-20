# RC-001 — Bloco único de homologação: Segurança e Auditoria

**Base de trabalho:** PR #55, SHA `27d6528058f0601e81cb95795830cedab04b09da`.
**Branch:** `feat/rc001-security-audit-batch`.
**Estado:** CODED / QA_NEW_SHA_NOT_RUN / DRAFT / NO_MERGE.
**Política:** testar *blocos*, não microcorreções. O gate isolado não incorpora
o hotfix à RC-001 automaticamente e não transforma um teste local em produção.

## Escopo reunido (uma rodada Windows)

- **G00/G01:** identidade SHA, árvore limpa, diff bloqueando segredos/DB,
  build e regressão integral no `start.cmd --check`.
- **G02:** RBAC, revogação, cross-operation, grants, mudanças de papéis
  pós-preflight, 401/403/404, concorrência e fail-closed transacional.
- **G05:** matriz explícita Admin/Supervisor/Auditor/Operador Ana/Bruno,
  leitura segregada e escrita não autorizada sem efeito persistente.
- **G08:** leituras VERIFIED, journals de concessão/revogação/negação,
  ausência de payload sensível, rollback de grants se persistência de
  auditoria falhar, HTTP 404 preservado para negações. Prova com
  SQLite criado e descartado por `release_probe.py`.
- **G09:** preparar o manifesto/risco/diff para **review independente**
  posterior. Não é possível aprovar G09 com a própria execução automatizada.
- **G10:** continua necessariamente pendente de aceite humano.

O runner gera APENAS `summary.json` com SHAs, contagens e estados fixos;
não salva stdout/stderr bruto, senhas, tokens, nomes de clientes, dados
reais, dumps ou SQL. A ausência de escrita no banco original depende do
isolamento e do review do escopo, e **não** é declarada como medição instrumental
independente no JSON. Em caso de falha imprime nome da etapa e exit code;
o executor pode investigar no lab separadamente, sem anexar dados sensíveis.

## Execução única (Windows, PowerShell)

1. Conferir portas/serviços do laboratório desativados. Na worktree RC
   `handoff-rc001-qa`, executar `git fetch origin`.
2. Obter o SHA EXATO desta branch do PR e criar worktree direta sob TEMP
   com nome `handoff-rc001-security-batch`:
   `git worktree add --detach "$env:TEMP\handoff-rc001-security-batch" <SHA>`.
   Não usar worktree G07/G03 existentes.
3. Abrir PowerShell na nova worktree, sem `HANDOFF_DB_URL` definido.
   Dependências devem estar instaladas para esta worktree
   (`start.cmd --check` exige Python/Node; seguir setup local oficial).
4. Executar **um único comando**:
   `& .\.venv\Scripts\python.exe scripts\rc001_integrated_gate.py --expected-sha <SHA>`.
5. O runner confere SHA local, SHA remoto origin, `git status` limpo,
   caminho **filho direto de TEMP via `os.path.samefile`** (suporta alias
   8.3 Windows), e diff RC-001→SHA sem banco/credencial/chave versionada.
6. Em seguida ele executa `start.cmd --check` (com argumento obrigatório),
   suíte dirigida G02/G05, suíte dirigida G08 e `release_probe.py`.
   No primeiro FAIL/TIMEOUT para; não cria PASS artificial.
7. Anexar **somente** o JSON sanitizado, SHA e contagens, nunca os bancos
   ou arquivos de credenciais dos testes. Se houver falha, registrar
   etapa/exit code para uma correção **em lote**, sem novos testes avulsos.

## Checklist humano consolidado — uma sessão, não 4 ciclos

Com um **único laboratório TEMP validado** iniciado por
`start.cmd --lab --lab-dir "<LAB>"` (nunca `start.cmd` puro):

1. Entrar como ADMIN, navegar diretório de pessoas/contas e filas, conferir
   leitura sem segredos e concessão/revogação em N1 em caso sintético.
2. SUPERVISOR: demonstrar visão N1/N2 permitida, alteração de fila autorizada
   e proibição de outra operação; sem grant administrativo.
3. AUDITOR: ler LIST/DETAIL VERIFIED em N1, provar 404 em N2; após revogação
   de grant, provar recusa imediata, depois restauração autorizada e journals.
4. Operadores Ana/N1 e Bruno/N2: transferência com nota interna segregada,
   conversa segmentada, não acessar workspace do outro operador.
5. Testar sessão revogada: token/sessão anterior deixa de acessar endpoints.
6. Com o laboratório sintético attestado e backend local do **mesmo banco**,
   podem-se rodar scripts existentes
   `release_grant_toggle.py`, `release_audit_scenarios.py`,
   `release_audit_evidence.py` de acordo com os runbooks anteriores;
   nunca pular `attest_running_backend` ou injetar token real.
7. Navegador Chrome/Edge em 1366×768 e 1920×1080, 100%/200% quando a
   experiência de cada persona estiver em questão. UI/UX G07 já validado
   em outro SHA, mas a RC integrada exigirá rechecagem.
8. Evidências sanitizadas: papel, operação, fila fictícia, HTTP, estado,
   timestamps, SHA, zero vazamento de outra operação, resultados de journal.

**G09 revisão independente:** revisor humano compara diff RC-001→branch,
manifests de dependências, contratos de auth/escopo/semântica HTTP,
migrations opt-in, possível conteúdo aproveitável das branches #14/#15/#17,
rollback, superfícies de exposição de segredo e conteúdo das evidências.
A ausência de reviewer não pode ser reportada como PASS.

**Regras de parada:** dado corporativo, path fora de TEMP, suspeita de
acesso ao banco original, escape de payload em journal, role escalation,
falha de backup/audit fail-closed, ou incompatibilidade de SHA → BLOCK.
Sem GitHub Actions, deploy, merge ou Teams/SQL corporativo.

## Estado de gates
`G00/G01/G02/G05/G08 = QA_NEW_SHA_NOT_RUN`;
`G09 = INDEPENDENT_REVIEW_REQUIRED`; `G10 = HUMAN_ACCEPTANCE_REQUIRED`.
G03 PASS no PR #55; G07 PASS no PR #52. **RC-001 original continua
`20ff982444310ef5c7dbce15d9d208ee0c1724b0` não integrada.**
