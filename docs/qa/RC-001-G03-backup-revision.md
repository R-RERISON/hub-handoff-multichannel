# RC-001 / G03 — Nome do backup deve refletir a revisão de origem

**Branch isolada:** `fix/rc001-g03-backup-revision-name` (sobre PR #52).
**Baseline de origem:** `1516e9fa0eb77bbdce34855205eef854ccb23757`.
**Estado:** CODED / WINDOWS_QA_NOT_RUN / NO_MERGE.

## Evidência da execução de 20/10/2026

No SHA da baseline, o executor confirmou em laboratório novo TEMP
`handoff-qa-006b4-nn458np5`: inspeção inicial 006b4 (22 tabelas, cinco
contas, dois operadores, duas filas); `upgrade-lifecycle --confirm-offline`
PASS para 007a2 (24 tabelas, integridade `ok`, contagens preservadas);
snapshot independente 006b4 com hash SHA-256 correspondente; 30 pytest
PASS, 1 SKIP; launcher retomou 007a2, API/Vite HTTP 200 e parou.
A guarda PowerShell necessitou normalizar ambos os caminhos por `Resolve-Path`
devido ao alias Windows 8.3. RC-001 e banco POC original não foram usados.

**Defeito:** mesmo quando a origem era 006b4, o backup recebeu prefixo
`pre006b1`. Conteúdo e hash estavam corretos; apenas o rótulo não era.

## Correção no código e contrato

`verified_backup` agora deriva o rótulo da revisão lida e aprovada por
`verify_database`, sem alterar conteúdo, sem copiar dados para GitHub,
sem escrever migração automática:
- Sem revisão: `preunversioned`
- 006b1: `pre006b1`
- 006b2: `pre006b2`
- 006b3: `pre006b3`
- 006b4: `pre006b4`
- 007a2: `pre007a2`

A guarda de pós-backup também compara a revisão da fonte anterior/posterior,
além do backup e contagens. Os testes cobrem todas as etiquetas de origem,
integridade, backup 006b4 antes de upgrade, 007a2 depois de upgrade e hashes.

**Importante:** backups antigos continuam com seu nome de origem; não
renomear ou excluir. Inspecionar conteúdo e hash, nunca confiar no nome
como fonte de verdade.

## Gates obrigatórios no SHA desta branch

1. Confirmar SHA remoto, worktree TEMP limpa e nenhuma API/dispatcher ativa;
   não atualizar nem usar a worktree congelada da RC-001.
2. Executar `.\start.cmd --check` (Pytest/Ruff/frontend/TypeScript/Vite)
   e `.\.venv\Scripts\python.exe -m pytest -q
   tests\test_schema_admin.py tests\test_spec007_queue_lifecycle.py
   tests\test_launcher_lab.py`. O número final deve ser registrado;
   nenhum PASS do SHA de G07 é automaticamente herdado.
3. Executar `.\.venv\Scripts\python.exe scripts\release_probe.py`.
4. Criar laboratório sintético novo em TEMP com
   `scripts\lab_environment.py create`. Resolver tanto `%TEMP%` quanto
   o caminho do lab com `Resolve-Path` para validação do pai 8.3/long path.
5. Inspecionar 006b4; com serviços parados, executar
   `python -m handoff_hub.schema_admin --database "$db"
   --backup-dir "$backups" upgrade-lifecycle --confirm-offline`.
6. Conferir o backup **gerado neste SHA**:
   `synthetic-pre006b4-*.db`, schema 006b4, 22 tabelas, integrity `ok`,
   row counts iguais, SHA-256 calculado igual ao reportado pelo upgrade.
7. Inspecionar o banco migrado 007a2: 24 tabelas, integrity `ok`,
   contagens preexistentes preservadas e duas tabelas novas vazias.
8. Restaurar **somente em uma cópia NOVA em TEMP**, nunca sobre o arquivo
   de laboratório ativo: copiar o backup para outro nome `restore-copy.db`
   e inspecionar a cópia, comparando contagens/hashes com backup.
9. Parar runtime; confirmar G07 SHA original e RC-001 não alterados.
   Registrar logs e evidências SANITIZADOS, sem SQLite, tokens nem senhas.

**Regras de parada:** incompatibilidade de revision, contagens, SHA,
integridade, restore em TEMP ou acesso à POC original: bloquear merge.
Este PR é **Draft** e depende do PR #52; G03 só pode ser fechado
formalmente depois de testes no seu próprio SHA e integração aprovada.
