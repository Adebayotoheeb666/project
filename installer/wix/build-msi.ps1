# PowerShell Script to Build LSIA MSI Installer using WiX Toolset
param(
    [string]$OutputDir = "$PSScriptRoot\..\..\installer_output",
    [string]$Version = "1.0.0.0"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Building LSIA School Computer Windows MSI Installer" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# --- Locate WiX binaries ---
function Find-WixBin {
    # 1. Already in PATH
    $c = Get-Command "candle.exe" -ErrorAction SilentlyContinue
    if ($c) { return (Split-Path -Parent $c.Source) }

    # 2. Environment variable set by CI
    if ($env:WIXBIN -and (Test-Path "$env:WIXBIN\candle.exe")) { return $env:WIXBIN }

    # 3. Standard install locations
    $candidates = @(
        "C:\Program Files (x86)\WiX Toolset v3.11\bin",
        "C:\Program Files (x86)\WiX Toolset v3.14\bin",
        "C:\Program Files\WiX Toolset v3.11\bin",
        "$env:RUNNER_TEMP\wix311"
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path "$p\candle.exe")) { return $p }
    }

    # 4. Search Program Files
    $found = Get-ChildItem "C:\Program Files (x86)" -Filter "candle.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { return $found.DirectoryName }

    return $null
}

$WixBin = Find-WixBin
if (-not $WixBin) {
    Write-Host "[!] WiX Toolset was not found. Please install WiX Toolset v3.11." -ForegroundColor Red
    exit 1
}

Write-Host "  WiX bin: $WixBin" -ForegroundColor Green
$Candle = Join-Path $WixBin "candle.exe"
$Light  = Join-Path $WixBin "light.exe"
$Heat   = Join-Path $WixBin "heat.exe"

# --- Directories ---
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}
$TempObj = Join-Path $OutputDir "obj"
if (-not (Test-Path $TempObj)) {
    New-Item -ItemType Directory -Path $TempObj -Force | Out-Null
}

$RepoRoot     = (Resolve-Path "$PSScriptRoot\..\..").Path
$ServerDir    = Join-Path $RepoRoot "server"
$AdminDistDir = Join-Path $RepoRoot "admin\dist"

if (-not (Test-Path $AdminDistDir)) {
    Write-Host "[!] admin/dist not found at $AdminDistDir" -ForegroundColor Red
    Write-Host "    Run 'npm run build' in the admin folder first." -ForegroundColor Red
    exit 1
}

# --- Stage server files (exclude venv, caches, test artefacts) ---
Write-Host "[1/4] Staging server files..." -ForegroundColor Green
$StageServerDir = Join-Path $TempObj "stage_server"
if (Test-Path $StageServerDir) { Remove-Item -Recurse -Force $StageServerDir }
New-Item -ItemType Directory -Path $StageServerDir -Force | Out-Null

Copy-Item -Path (Join-Path $ServerDir "pyproject.toml") -Destination "$StageServerDir\"
Copy-Item -Recurse -Path (Join-Path $ServerDir "lsia") -Destination (Join-Path $StageServerDir "lsia")
Get-ChildItem -Path $StageServerDir -Include "__pycache__","*.pyc","*.pyo" -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Normalize paths to use forward slashes for WiX parameters
$TempObjDir = ($TempObj -replace '\\', '/') + '/'
$ServerWxs = Join-Path $TempObj "ServerFiles.wxs"
$AdminWxs  = Join-Path $TempObj "AdminFiles.wxs"

# --- Harvest ---
Write-Host "[2/4] Harvesting file lists with heat..." -ForegroundColor Green
& $Heat dir "$StageServerDir" -cg ServerFilesGroup -dr SERVERFOLDER -scom -sfrag -srd `
    -var "var.StageServerDir" -out "$ServerWxs"
if ($LASTEXITCODE -ne 0) { Write-Error "heat failed for server files"; exit 1 }

& $Heat dir "$AdminDistDir" -cg AdminFilesGroup -dr ADMINDISTFOLDER -scom -sfrag -srd `
    -var "var.AdminDistDir" -out "$AdminWxs"
if ($LASTEXITCODE -ne 0) { Write-Error "heat failed for admin dist files"; exit 1 }

# --- Compile ---
Write-Host "[3/4] Compiling WiX sources (candle)..." -ForegroundColor Green
& $Candle "$PSScriptRoot\Product.wxs" "$ServerWxs" "$AdminWxs" `
    -dRepoRoot="$RepoRoot" -dStageServerDir="$StageServerDir" -dAdminDistDir="$AdminDistDir" `
    -ext WixFirewallExtension -ext WixUIExtension `
    -out "$TempObjDir"
if ($LASTEXITCODE -ne 0) { Write-Error "candle compilation failed"; exit 1 }

# --- Link ---
Write-Host "[4/4] Linking MSI (light)..." -ForegroundColor Green
$MsiOutput = Join-Path $OutputDir "LSIASchoolComputer.msi"
$ProductObj = Join-Path $TempObj "Product.wixobj"
$ServerObj  = Join-Path $TempObj "ServerFiles.wixobj"
$AdminObj   = Join-Path $TempObj "AdminFiles.wixobj"

& $Light "$ProductObj" "$ServerObj" "$AdminObj" `
    -ext WixFirewallExtension -ext WixUIExtension `
    -sval -out "$MsiOutput"
if ($LASTEXITCODE -ne 0) { Write-Error "light linking failed"; exit 1 }

if (-not (Test-Path $MsiOutput)) {
    Write-Host "[ERROR] MSI output was not generated!" -ForegroundColor Red
    exit 1
}

$MsiSize = [math]::Round((Get-Item $MsiOutput).Length / 1MB, 2)
Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  [SUCCESS] MSI built: $MsiOutput ($MsiSize MB)" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
