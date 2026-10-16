# SPEC-006B-2 - validate migration EXCLUSIVELY on a verified SQLite copy.
# Windows PowerShell 5.1 / PowerShell 7. Never changes the original database.
[CmdletBinding()]
param([switch]$ConfirmServicesStopped)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
$original = Join-Path $root 'data\handoff-poc.db'
$backupRoot = Join-Path $root 'data\backups\homolog006b2'
$baselineRevision = '006b1_poc_baseline'
$targetRevision = '006b2_queue_provenance'
$newTables = @(
    'session_queue_segments',
    'message_queue_provenance',
    'session_event_queue_provenance'
)
$copy = $null

function Invoke-Schema {
    param([Parameter(Mandatory=$true)][string[]]$Arguments)
    $output = & $python -m handoff_hub.schema_admin @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "schema_admin failed (exit $LASTEXITCODE): $($Arguments -join ' ')"
    }
    $raw = ($output -join [Environment]::NewLine)
    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "schema_admin returned empty output"
    }
    return ConvertFrom-Json -InputObject $raw
}

function Assert-Equal {
    param([string]$Name, $Actual, $Expected)
    if ("$Actual" -cne "$Expected") {
        throw "[FALHA] $Name : esperado='$Expected'; recebido='$Actual'"
    }
    Write-Host "[OK] $Name"
}

function Assert-Counts {
    param([string]$Name, $Before, $After)
    $namesBefore = @($Before.PSObject.Properties.Name | Sort-Object)
    $namesAfter = @($After.PSObject.Properties.Name | Sort-Object)
    Assert-Equal "$Name - tabelas" ($namesAfter -join ',') ($namesBefore -join ',')
    foreach ($table in $namesBefore) {
        $previousCount = [long]$Before.PSObject.Properties[$table].Value
        $currentCount = [long]$After.PSObject.Properties[$table].Value
        if ($previousCount -ne $currentCount) {
            throw "[FALHA] $Name - registros alterados em $table : $previousCount -> $currentCount"
        }
    }
    Write-Host "[OK] $Name - contagens de todas as $($namesBefore.Count) tabelas preservadas"
}

if (-not $ConfirmServicesStopped) {
    throw "Antes de continuar: encerre start.cmd/API/dispatcher e use -ConfirmServicesStopped"
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Ambiente Python do projeto nao encontrado: $python"
}
if (-not (Test-Path -LiteralPath $original -PathType Leaf)) {
    throw "Banco original nao encontrado: $original"
}

# Blocking ports are a useful warning, not a complete lock: confirmation
# above also asserts all SQLite writers have been stopped.
$listeners = @(Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -gt 0) {
    throw "Portas 8000/5173 ainda estao em uso. Encerre os servicos antes do teste."
}

Push-Location $root
try {
    Write-Host "SPEC-006B-2: original sera apenas inspecionado e copiado."
    $originalBefore = Invoke-Schema -Arguments @('--database', $original, 'inspect')
    Assert-Equal 'Integridade original' $originalBefore.integrity 'ok'
    Assert-Equal 'Original sem revision' $originalBefore.revision ''
    Assert-Equal 'Original com 17 tabelas' $originalBefore.table_count 17

    # Only 'backup' receives the original path. All mutating actions use
    # a different, verified path returned by the schema_admin backup command.
    $snapshotDir = Join-Path $backupRoot 'snapshots'
    $snapshot = Invoke-Schema -Arguments @(
        '--database', $original,
        '--backup-dir', $snapshotDir,
        'backup'
    )
    $copy = [System.IO.Path]::GetFullPath([string]$snapshot.path)
    $originalAbsolute = [System.IO.Path]::GetFullPath($original)
    $trustedPrefix = [System.IO.Path]::GetFullPath($snapshotDir).TrimEnd('\') + '\'
    if ($copy -ieq $originalAbsolute -or
        -not $copy.StartsWith($trustedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Caminho da copia inseguro: abortando antes de alterar qualquer banco.'
    }
    if (-not (Test-Path -LiteralPath $copy -PathType Leaf)) {
        throw 'Backup nao foi criado.'
    }

    $checksum = (Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash
    Assert-Equal 'SHA-256 da copia' $checksum ([string]$snapshot.sha256).ToUpperInvariant()
    $copyBefore = Invoke-Schema -Arguments @('--database', $copy, 'inspect')
    Assert-Equal 'Copia inicial sem revision' $copyBefore.revision ''
    Assert-Counts 'Snapshot vs. original' $originalBefore.row_counts $copyBefore.row_counts

    Write-Host '[ETAPA] Adotando 006B-1 somente na copia...'
    $adopted = Invoke-Schema -Arguments @(
        '--database', $copy,
        '--backup-dir', (Join-Path $backupRoot 'pre-adoption'),
        'adopt', '--confirm-offline'
    )
    Assert-Equal 'Adocao 006B-1' $adopted.revision $baselineRevision
    $copyBaseline = Invoke-Schema -Arguments @('--database', $copy, 'inspect')
    Assert-Equal 'Revision da copia baseline' $copyBaseline.revision $baselineRevision
    Assert-Counts 'Legado apos baseline' $originalBefore.row_counts $copyBaseline.row_counts

    Write-Host '[ETAPA] Aplicando 006B-2 somente na copia...'
    $upgraded = Invoke-Schema -Arguments @(
        '--database', $copy,
        '--backup-dir', (Join-Path $backupRoot 'pre-upgrade'),
        'upgrade', '--confirm-offline'
    )
    Assert-Equal 'Upgrade para 006B-2' $upgraded.revision $targetRevision
    $copyAfter = Invoke-Schema -Arguments @('--database', $copy, 'inspect')
    Assert-Equal 'Integridade da copia migrada' $copyAfter.integrity 'ok'
    Assert-Equal 'Revision final da copia' $copyAfter.revision $targetRevision
    Assert-Equal '20 tabelas no banco migrado' $copyAfter.table_count 20
    foreach ($table in $originalBefore.row_counts.PSObject.Properties.Name) {
        $oldCount = [long]$originalBefore.row_counts.PSObject.Properties[$table].Value
        $newCount = [long]$copyAfter.row_counts.PSObject.Properties[$table].Value
        if ($oldCount -ne $newCount) {
            throw "[FALHA] Contagem historica mudou para $table : $oldCount -> $newCount"
        }
    }
    Write-Host '[OK] Todos os registros das 17 tabelas antigas preservados'
    foreach ($name in $newTables) {
        Assert-Equal "$name permanece vazia" $copyAfter.row_counts.PSObject.Properties[$name].Value 0
    }

    $originalAfter = Invoke-Schema -Arguments @('--database', $original, 'inspect')
    Assert-Equal 'Integridade original posterior' $originalAfter.integrity 'ok'
    Assert-Equal 'Revision original posterior nula' $originalAfter.revision ''
    Assert-Equal 'Original ainda com 17 tabelas' $originalAfter.table_count 17
    Assert-Counts 'Original intocado' $originalBefore.row_counts $originalAfter.row_counts

    Write-Host ''
    Write-Host '[APROVADO] Upgrade Alembic 006B-2 exclusivamente na copia.'
    Write-Host '[APROVADO] Banco original nao versionado nem alterado.'
    Write-Host '[APROVADO] Todas as linhas legadas preservadas; 3 tabelas novas vazias.'
    Write-Host "Revisao da copia: $($copyAfter.revision)"
    Write-Host "Revisao original: null"
    Write-Host "Copia validada: $copy"
}
catch {
    Write-Host '[REPROVADO] Gate SPEC-006B-2 interrompido.'
    if ($copy) {
        Write-Host "Copia para diagnostico local: $copy"
    }
    throw
}
finally {
    Pop-Location
}
