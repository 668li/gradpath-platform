<#
.SYNOPSIS
  GradPath database migration script (Windows PowerShell)

.DESCRIPTION
  Wraps common Alembic operations: upgrade, downgrade, status, generate.
  Run from the repository root; DATABASE_URL is read from .env or env vars.

.EXAMPLE
  .\scripts\migrate.ps1 upgrade                 # Apply all pending migrations
  .\scripts\migrate.ps1 downgrade               # Roll back one revision
  .\scripts\migrate.ps1 status                  # Show current revision
  .\scripts\migrate.ps1 make "add user avatar"  # Generate a new autogenerate migration
  .\scripts\migrate.ps1 history                 # Show migration history
  .\scripts\migrate.ps1 heads                   # Show current heads
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('upgrade', 'downgrade', 'status', 'make', 'history', 'heads')]
    [string]$Action = 'status',

    [Parameter(Position = 1)]
    [string]$Message
)

$ErrorActionPreference = 'Stop'

# Switch to backend/ directory (parent of this script's directory)
$BackendDir = Split-Path -Parent $PSScriptRoot
Set-Location $BackendDir

# Pick a Python interpreter: venv first, then $env:PY, then `python`
function Resolve-Python {
    if ($env:VIRTUAL_ENV) {
        $venvPython = Join-Path $env:VIRTUAL_ENV (Join-Path 'Scripts' 'python.exe')
        if (Test-Path $venvPython) { return $venvPython }
    }
    if ($env:PY -and (Get-Command $env:PY -ErrorAction SilentlyContinue)) {
        return $env:PY
    }
    return 'python'
}

$Python = Resolve-Python

# Verify Alembic is available
$alembicCheck = & $Python -m alembic --help 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Alembic is not available. Install it with: pip install alembic`n$alembicCheck"
    exit 1
}

switch ($Action) {
    'upgrade' {
        Write-Host "==> Applying latest migrations (alembic upgrade head)" -ForegroundColor Cyan
        & $Python -m alembic upgrade head
    }
    'downgrade' {
        Write-Host "==> Rolling back one revision (alembic downgrade -1)" -ForegroundColor Cyan
        & $Python -m alembic downgrade -1
    }
    'status' {
        Write-Host "==> Current revision (alembic current)" -ForegroundColor Cyan
        & $Python -m alembic current
    }
    'make' {
        if (-not $Message) {
            Write-Error 'A message is required: .\scripts\migrate.ps1 make "your message"'
            exit 1
        }
        Write-Host "==> Generating new migration: $Message" -ForegroundColor Cyan
        & $Python -m alembic revision --autogenerate -m $Message
        Write-Host ''
        Write-Host 'Tip: Inspect the new file under migrations/versions/ and verify upgrade()/downgrade() before committing.' -ForegroundColor Yellow
    }
    'history' {
        Write-Host "==> Migration history (alembic history --verbose)" -ForegroundColor Cyan
        & $Python -m alembic history --verbose
    }
    'heads' {
        Write-Host "==> Current heads (alembic heads)" -ForegroundColor Cyan
        & $Python -m alembic heads
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "Command failed (exit code: $LASTEXITCODE)"
    exit $LASTEXITCODE
}
