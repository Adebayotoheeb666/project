# PowerShell startup script for LSIA School Computer
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Detect directory layout
if (Test-Path "$ScriptDir\server\lsia") {
    $ServerDir = "$ScriptDir\server"
    $IsInstalled = $true
} elseif (Test-Path "$ScriptDir\..\server\lsia") {
    $ServerDir = Resolve-Path "$ScriptDir\..\server"
    $IsInstalled = $false
} else {
    $ServerDir = $ScriptDir
    $IsInstalled = $false
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Local-First School Intelligence System (LSIA)" -ForegroundColor Cyan
Write-Host "  School Computer Administration Server" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

Set-Location $ServerDir

# Locate Python
$PythonCmd = Get-Command "python.exe" -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    $Candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe"
    )
    foreach ($c in $Candidates) {
        if (Test-Path $c) { $PythonCmd = $c; break }
    }
}
if (-not $PythonCmd) {
    Write-Host "[ERROR] Python 3.10+ was not found in PATH or standard locations." -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/ or the Microsoft Store." -ForegroundColor Red
    exit 1
}

if ($IsInstalled) {
    $VenvDir = Join-Path $env:LOCALAPPDATA "LSIA\venv"
    $env:LSIA_DATA_DIR = Join-Path $env:LOCALAPPDATA "LSIA\data"
    $BaseDir = Join-Path $env:LOCALAPPDATA "LSIA"
    if (-not (Test-Path $BaseDir)) {
        New-Item -ItemType Directory -Path $BaseDir -Force | Out-Null
    }
} elseif (Test-Path (Join-Path $ServerDir ".venv\Scripts\python.exe")) {
    $VenvDir = Join-Path $ServerDir ".venv"
} else {
    $VenvDir = Join-Path $ServerDir ".venv"
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "[INFO] Initializing Python virtual environment in $VenvDir..." -ForegroundColor Yellow
    & $PythonCmd -m venv "$VenvDir"
    & (Join-Path $VenvDir "Scripts\pip.exe") install -e .
}

Write-Host "[+] Starting LSIA server on http://0.0.0.0:8080" -ForegroundColor Green
Write-Host "[+] Local Administration Dashboard: http://127.0.0.1:8080" -ForegroundColor Green
Write-Host "[+] Teacher Phone LAN Sync Endpoint: http://<LAN-IP>:8080" -ForegroundColor Green

& (Join-Path $VenvDir "Scripts\uvicorn.exe") lsia.main:create_app --factory --host 0.0.0.0 --port 8080
