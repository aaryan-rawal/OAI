[CmdletBinding()]
param(
    [switch]$ApplyMigrations
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Frontend = Join-Path $ProjectRoot 'frontend'
$Backend = Join-Path $ProjectRoot 'backend'
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$Results = [System.Collections.Generic.List[object]]::new()

function Add-Result([string]$Name, [string]$Status, [string]$Detail) {
    $Results.Add([pscustomobject]@{ Check = $Name; Status = $Status; Detail = $Detail })
    Write-Host ("[{0}] {1} - {2}" -f $Status, $Name, $Detail)
}

function Invoke-Checked([string]$Name, [string]$File, [string[]]$Arguments, [string]$WorkingDirectory) {
    Push-Location $WorkingDirectory
    try {
        & $File @Arguments
        if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
        Add-Result $Name 'PASS' 'Command completed successfully.'
    }
    finally { Pop-Location }
}

Write-Host 'OptiFreight AI - Windows integration verification'
Write-Host "Project: $ProjectRoot"

if (-not (Test-Path (Join-Path $ProjectRoot '.env'))) {
    Add-Result '.env' 'BLOCKED' 'Root .env is missing. Restore your own file; this script will not create or modify it.'
} else {
    Add-Result '.env' 'PASS' 'Root .env exists; values were not read or printed.'
}

if (-not (Test-Path $Python)) {
    Add-Result 'Python environment' 'BLOCKED' 'Run setup.bat first to create .venv and install backend requirements.'
    $Python = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if ($Python) {
    Invoke-Checked 'Backend tests' $Python @('-m','pytest','-q') $Backend
    Invoke-Checked 'Alembic migration graph' $Python @('-m','alembic','heads') $Backend
} else {
    Add-Result 'Backend tests' 'BLOCKED' 'Python was not found.'
}

if (Test-Path $Frontend) {
    Invoke-Checked 'Frontend dependency install' 'npm.cmd' @('ci','--no-audit','--no-fund') $Frontend
    Invoke-Checked 'Frontend typecheck' 'npm.cmd' @('run','typecheck') $Frontend
    Invoke-Checked 'Frontend unit tests' 'npm.cmd' @('test') $Frontend
    Invoke-Checked 'Frontend production build' 'npm.cmd' @('run','build') $Frontend
} else {
    Add-Result 'Frontend' 'BLOCKED' 'frontend directory is missing.'
}

# The app must be running separately (run.bat) for live DB and route checks.
try {
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 5
    if ($health.status -eq 'ok') { Add-Result 'Backend health' 'PASS' 'FastAPI is responding.' }
    else { Add-Result 'Backend health' 'FAIL' 'Unexpected health response.' }
} catch {
    Add-Result 'Backend health' 'BLOCKED' 'Start run.bat in another terminal, then rerun this script.'
}

try {
    $ready = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health/ready' -TimeoutSec 8
    if ($ready.database -eq 'connected') { Add-Result 'PostgreSQL integration' 'PASS' 'Application reached PostgreSQL.' }
    else { Add-Result 'PostgreSQL integration' 'FAIL' 'Readiness response did not confirm database connectivity.' }
} catch {
    Add-Result 'PostgreSQL integration' 'BLOCKED' 'Database is unreachable, dependencies are missing, or migrations have not been applied.'
}

if ($ApplyMigrations) {
    $confirmation = Read-Host 'This will modify the configured PostgreSQL database. Type APPLY to continue'
    if ($confirmation -ceq 'APPLY' -and $Python) {
        Invoke-Checked 'Apply PostgreSQL migrations' $Python @('-m','alembic','upgrade','head') $Backend
    } else {
        Add-Result 'Apply PostgreSQL migrations' 'SKIPPED' 'Explicit confirmation was not provided.'
    }
} else {
    Add-Result 'Apply PostgreSQL migrations' 'SKIPPED' 'No database changes made. Rerun with -ApplyMigrations after backing up the database.'
}

try {
    $route = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/routes/surat_mumbai/verify' -TimeoutSec 25
    if ($route.road_network_verified -eq $true -and $route.truck_profile_verified -eq $true) {
        Add-Result 'Live truck routing' 'PASS' 'OSRM road route and reviewed HGV profile are confirmed.'
    } elseif ($route.road_network_verified -eq $true) {
        Add-Result 'Live truck routing' 'BLOCKED' 'Road routing responds, but HGV profile is not confirmed; matching remains fail-closed.'
    } else {
        Add-Result 'Live truck routing' 'BLOCKED' 'No verified OSRM road route was returned.'
    }
} catch {
    Add-Result 'Live truck routing' 'BLOCKED' 'Backend is unavailable or configured OSRM endpoints could not be reached.'
}

Write-Host ''
$Results | Format-Table -AutoSize
$failed = @($Results | Where-Object { $_.Status -eq 'FAIL' }).Count
$blocked = @($Results | Where-Object { $_.Status -eq 'BLOCKED' }).Count
Write-Host "Summary: $(@($Results | Where-Object Status -eq 'PASS').Count) passed, $failed failed, $blocked blocked, $(@($Results | Where-Object Status -eq 'SKIPPED').Count) skipped."
if ($failed -gt 0) { exit 1 }
