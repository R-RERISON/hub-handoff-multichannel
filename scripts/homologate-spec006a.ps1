# SPEC-006A local API authorization homologation.
# Run on Windows PowerShell 5.1 or PowerShell 7.
# Only synthetic data. Does not print credentials or bearer tokens.
[CmdletBinding()]
param(
    [string]$ApiBaseUrl = 'http://127.0.0.1:8000',
    [switch]$TestSupervisorRevocation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$credentialsPath = Join-Path $root 'data\demo-credentials.txt'
$script:Passed = 0

function Invoke-JsonApi {
    param(
        [string]$Uri,
        [string]$Method = 'POST',
        [hashtable]$Headers = @{},
        [Parameter(Mandatory=$true)]$Payload
    )

    # Windows PowerShell 5.1 may encode non-ASCII JSON with an ANSI codepage
    # when passed a string. Always send UTF-8 bytes.
    $json = ConvertTo-Json -InputObject $Payload -Depth 10 -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    return Invoke-RestMethod -Uri $Uri -Method $Method -Headers $Headers `
        -Body $bytes -ContentType 'application/json; charset=utf-8'
}

function New-DemoSession {
    param([string]$Username)
    $match = Get-Content $credentialsPath -Encoding UTF8 |
        Where-Object { $_.StartsWith("$Username [") } | Select-Object -First 1
    if (-not $match) {
        throw "Usuario $Username nao localizado em data/demo-credentials.txt"
    }
    $pieces = $match -split '\]: ', 2
    if ($pieces.Count -ne 2 -or [string]::IsNullOrWhiteSpace($pieces[1])) {
        throw "Formato invalido da credencial para $Username"
    }
    $response = Invoke-JsonApi -Uri "$ApiBaseUrl/v1/auth/login" `
        -Payload @{ username = $Username; password = $pieces[1] }
    if (-not $response.access_token) {
        throw "Login nao retornou token para $Username"
    }
    return @{ Authorization = 'Bearer ' + $response.access_token }
}

function Assert-StatusDenied {
    param(
        [string]$Name,
        [scriptblock]$Request,
        [int]$Expected
    )
    $observed = 200
    try {
        $null = & $Request
    }
    catch {
        if ($null -eq $_.Exception.Response) {
            throw "Erro inesperado em $Name : $($_.Exception.Message)"
        }
        $observed = [int]$_.Exception.Response.StatusCode
    }
    if ($observed -ne $Expected) {
        throw "REPROVADO: $Name. Esperado HTTP $Expected; recebido $observed"
    }
    $script:Passed += 1
    Write-Host "[OK] $Name : HTTP $observed"
}

function Assert-Queues {
    param([string]$Name, [hashtable]$Headers, [string[]]$Expected)
    $items = @(Invoke-RestMethod -Uri "$ApiBaseUrl/v1/me/queues" -Headers $Headers)
    $actual = @($items | ForEach-Object { $_.id } | Sort-Object)
    $wanted = @($Expected | Sort-Object)
    if (($actual -join ',') -ne ($wanted -join ',')) {
        throw "REPROVADO: $Name. Esperado [$($wanted -join ',')], recebido [$($actual -join ',')]"
    }
    $script:Passed += 1
    Write-Host "[OK] $Name : $($actual -join ',')"
}

if (-not (Test-Path -LiteralPath $credentialsPath)) {
    throw 'Arquivo local de credenciais ausente. Nao altere usuarios ou SQLite.'
}
$null = Invoke-RestMethod -Uri "$ApiBaseUrl/health/live"
$admin = New-DemoSession -Username 'admin.demo'
$supervisor = New-DemoSession -Username 'supervisor.demo'
$auditor = New-DemoSession -Username 'auditor.demo'

Write-Host 'SPEC-006A - conferindo grants iniciais'
Assert-Queues 'Administrador' $admin @('n1', 'n2')
Assert-Queues 'Supervisor' $supervisor @('n1', 'n2')
Assert-Queues 'Auditor' $auditor @('n1')

# Real request with accented strings: ensures UTF-8 works under Windows PowerShell.
$key = [guid]::NewGuid().ToString('N')
$ticketHeaders = @{ Authorization = $admin.Authorization; 'Idempotency-Key' = $key }
# Build accented text independently of the PS 5.1 file encoding.
$subject = 'Solicita' + [char]0x00E7 + [char]0x00E3 + 'o de valida' + [char]0x00E7 + [char]0x00E3 + 'o de permiss' + [char]0x00F5 + 'es N2'
$ticket = Invoke-JsonApi -Uri "$ApiBaseUrl/v1/handoffs" `
    -Headers $ticketHeaders -Payload @{
        operation_id = 'demo'
        integration_id = 'demo-bot'
        queue_id = 'n2'
        external_conversation_id = "spec006a-$key"
        requester_label = 'Homologacao de auditoria'
        subject = $subject
    }
if ($ticket.queue_id -ne 'n2' -or -not $ticket.id) {
    throw 'REPROVADO: abertura do ticket N2 explicito'
}
$script:Passed += 1
Write-Host '[OK] Ticket sintetico direcionado explicitamente para N2'

Assert-StatusDenied 'Auditor nao consulta rotacao N2' {
    Invoke-RestMethod -Uri "$ApiBaseUrl/v1/queues/n2/rotation" -Headers $auditor
} 404
Assert-StatusDenied 'Auditor nao le conversa N2' {
    Invoke-RestMethod -Uri "$ApiBaseUrl/v1/handoffs/$($ticket.id)/messages" -Headers $auditor
} 404
Assert-StatusDenied 'Auditor nao consulta outbox' {
    Invoke-RestMethod -Uri "$ApiBaseUrl/v1/outbox" -Headers $auditor
} 403

# Read-only diagnostic: do not automatically change operator membership/capacity.
$rotation = Invoke-RestMethod -Uri "$ApiBaseUrl/v1/queues/n2/rotation" -Headers $admin
$operators = @(Invoke-RestMethod -Uri "$ApiBaseUrl/v1/operators" -Headers $admin)
$anaOnN2 = @($rotation.operators | Where-Object { $_.operator_id -eq 'op-ana' }).Count -gt 0
$bruno = @($operators | Where-Object { $_.id -eq 'op-bruno' } | Select-Object -First 1)
Write-Host ("[INSPECAO] Ana membro de N2: " + $anaOnN2)
if ($bruno.Count -gt 0) {
    Write-Host ("[INSPECAO] Capacidade atual de Bruno: " + $bruno[0].capacity)
}
if ($anaOnN2) {
    Write-Warning 'Ana pertence a N2. Verifique se o vinculo foi criado acidentalmente no teste.'
}
if ($bruno.Count -gt 0 -and $bruno[0].capacity -ne 1) {
    Write-Warning 'Capacidade de Bruno difere do seed 1. Restaurar apenas se nao houve ajuste intencional.'
}

if ($TestSupervisorRevocation) {
    $profile = Invoke-RestMethod -Uri "$ApiBaseUrl/v1/auth/me" -Headers $supervisor
    if ([string]::IsNullOrWhiteSpace($profile.id)) {
        throw 'Nao foi possivel recuperar o user_id do supervisor. Nenhuma revogacao aplicada.'
    }
    # Baseline N2 was checked above. Restore this existing grant regardless
    # of whether an assertion fails after attempting revocation.
    $grant = @{ user_id = [string]$profile.id; queue_id = 'n2';
                role = 'SUPERVISOR'; enabled = $false }
    try {
        $null = Invoke-JsonApi -Uri "$ApiBaseUrl/v1/admin/queue-grants" `
            -Method PATCH -Headers $admin -Payload $grant
        Assert-Queues 'Supervisor imediatamente apos revogacao' $supervisor @('n1')
        Assert-StatusDenied 'Supervisor nao consulta N2' {
            Invoke-RestMethod -Uri "$ApiBaseUrl/v1/queues/n2/rotation" `
                -Headers $supervisor
        } 404
        Assert-StatusDenied 'Supervisor nao inclui operador em N2' {
            Invoke-JsonApi -Uri "$ApiBaseUrl/v1/queues/n2/members/op-ana" `
                -Method PATCH -Headers $supervisor -Payload @{enabled=$true}
        } 404
        Assert-StatusDenied 'Supervisor nao altera capacidade de Bruno' {
            Invoke-JsonApi -Uri "$ApiBaseUrl/v1/operators/op-bruno/capacity" `
                -Method PATCH -Headers $supervisor -Payload @{capacity=2}
        } 403
        Assert-StatusDenied 'Supervisor nao modifica grants' {
            Invoke-JsonApi -Uri "$ApiBaseUrl/v1/admin/queue-grants" `
                -Method PATCH -Headers $supervisor -Payload $grant
        } 403
    }
    finally {
        $grant.enabled = $true
        try {
            $null = Invoke-JsonApi -Uri "$ApiBaseUrl/v1/admin/queue-grants" `
                -Method PATCH -Headers $admin -Payload $grant
            Assert-Queues 'Grant N2 do supervisor restaurado' $supervisor @('n1', 'n2')
        }
        catch {
            Write-Warning 'Falha ao restaurar grant N2! Reexecutar restauracao como ADMIN.'
            throw
        }
    }
}
else {
    Write-Host '[INFO] Teste de revogacao nao executado; use -TestSupervisorRevocation.'
}
Write-Host "[RESULTADO] $script:Passed verificacoes aprovadas; nenhuma credencial exibida."
