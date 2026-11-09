# PowerShell startup script for LSIA School Computer
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Detect directory layout
if (Test-Path "$ScriptDir\server\lsia") {
    $ServerDir = "$ScriptDir\server"
} elseif (Test-Path "$ScriptDir\..\server\lsia") {
    $ServerDir = Resolve-Path "$ScriptDir\..\server"
} else {
    $ServerDir = $ScriptDir
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Local-First School Intelligence System (LSIA)" -ForegroundColor Cyan
Write-Host "  School Computer Administration Server" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

Set-Location $ServerDir

$VenvPython = Join-Path $ServerDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "[!] Initializing local Python virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    & .venv\Scripts\pip install -e .
}

Write-Host "[+] Starting LSIA server on http://0.0.0.0:8080" -ForegroundColor Green
Write-Host "[+] Local Administration Dashboard: http://127.0.0.1:8080" -ForegroundColor Green
Write-Host "[+] Teacher Phone LAN Sync Endpoint: http://<LAN-IP>:8080" -ForegroundColor Green

& .venv\Scripts\uvicorn lsia.main:create_app --factory --host 0.0.0.0 --port 8080
