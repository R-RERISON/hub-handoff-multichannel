# Prepare a NEW isolated 006b4 browser lab. Never read or modify the POC database.
# Compatible with Windows PowerShell 5.1 and PowerShell 7.
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
$original = [System.IO.Path]::GetFullPath((Join-Path $root 'data\handoff-poc.db'))
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Python .venv ausente. Execute .\start.cmd --setup-only primeiro.'
}
# Never let a running original-database server be mistaken for this QA lab.
$listeners = @(Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -gt 0) {
    throw 'Porta 8000/5173 ocupada: encerre instancias existentes antes de preparar o lab.'
}

# Keep ALL synthetic state outside the repository (including passwords).
$lab = Join-Path ([System.IO.Path]::GetTempPath()) (
    'handoff-qa-006b4-' + [guid]::NewGuid().ToString('N')
)
$lab = [System.IO.Path]::GetFullPath($lab)
$db = [System.IO.Path]::GetFullPath((Join-Path $lab 'synthetic.db'))
$credentials = Join-Path $lab 'synthetic-credentials.txt'
if ($db -ieq $original -or $db.StartsWith(
    ($root.TrimEnd('\') + '\'), [StringComparison]::OrdinalIgnoreCase
)) {
    throw 'Caminho inseguro: o banco de homologacao nao pode estar no repositorio.'
}
New-Item -ItemType Directory -Path $lab -ErrorAction Stop | Out-Null

# Refuse any preexisting file. No adopt, stamp, upgrade, copy or seed on original.
& $python -m handoff_hub.schema_admin --database $db create --confirm-offline
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar banco 006b4 DESCARTAVEL.' }

$seed = @'
import sys
from pathlib import Path
from handoff_hub.poc_db import make_session_factory
from handoff_hub.seed_demo_auth import provision

path = Path(sys.argv[1])
creds = Path(sys.argv[2])
factory, engine = make_session_factory(f"sqlite:///{path.as_posix()}")
try:
    accounts = provision(factory, creds)
    assert len(accounts) == 5, "Seed de cinco contas de laboratorio falhou"
finally:
    engine.dispose()
'@
# PowerShell 5.1/Windows native argument quoting strips quotes inside
# python -c strings (e.g. f"sqlite:///..." becomes fsqlite:///...).
# Execute a real UTF-8 file under TEMP, never inline code through argv.
$seedPath = Join-Path $lab 'seed-synthetic.py'
[System.IO.File]::WriteAllText(
    $seedPath, $seed, [System.Text.UTF8Encoding]::new($false)
)
& $python $seedPath $db $credentials
if ($LASTEXITCODE -ne 0) { throw 'Falha no seed exclusivamente sintetico.' }

$schemaOutput = & $python -m handoff_hub.schema_admin --database $db inspect
if ($LASTEXITCODE -ne 0) { throw 'Inspecao do banco sintetico falhou.' }
$schema = $schemaOutput | Out-String | ConvertFrom-Json
if ($schema.revision -cne '006b4_security_decisions' -or
    [int]$schema.table_count -ne 22 -or
    [int]$schema.row_counts.auth_users -ne 5) {
    throw 'Banco sintetico nao atende ao contrato de 006b4/22 tabelas.'
}

# Generate reproducible launchers in TEMP, not in data/ or source control.
$rootQuoted = $root.Replace("'", "''")
$dbQuoted = $db.Replace('\', '/').Replace("'", "''")
$pythonQuoted = $python.Replace("'", "''")
$webQuoted = (Join-Path $root 'web').Replace("'", "''")
$backend = @'
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$env:HANDOFF_DB_URL = 'sqlite:///{DB}'
Set-Location -LiteralPath '{ROOT}'
& '{PYTHON}' -m uvicorn handoff_hub.main:app --host 127.0.0.1 --port 8000
'@
$web = @'
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath '{WEB}'
& npm.cmd run dev
'@
$backend = $backend.Replace('{DB}', $dbQuoted).Replace('{ROOT}', $rootQuoted).Replace(
    '{PYTHON}', $pythonQuoted
)
$web = $web.Replace('{WEB}', $webQuoted)
$backendPath = Join-Path $lab 'run-backend.ps1'
$webPath = Join-Path $lab 'run-web.ps1'
[System.IO.File]::WriteAllText($backendPath, $backend, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText($webPath, $web, [System.Text.UTF8Encoding]::new($false))

Write-Host '[OK] Banco e credenciais totalmente sinteticos, revision 006b4.'
Write-Host "[OK] Diretorio isolado: $lab"
Write-Host '[SEGURANCA] Nunca use start.cmd --setup-users neste laboratorio.'
Write-Host '[TERMINAL 1] Inicie a API (Ctrl+C para encerrar):'
Write-Host ('  & "' + $backendPath + '"')
Write-Host '[TERMINAL 2] Inicie a interface (Ctrl+C para encerrar):'
Write-Host ('  & "' + $webPath + '"')
Write-Host '[BROWSER] http://127.0.0.1:5173'
Write-Host "[CREDENCIAIS TEMPORARIAS] $credentials"
Write-Host '[LIMPEZA] Ao terminar, encerre ambos os servicos e remova o diretorio de homologacao.'
