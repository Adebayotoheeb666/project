# PowerShell Script to Build LSIA MSI Installer using WiX Toolset
param(
    [string]$OutputDir = "$PSScriptRoot\..\..\installer_output",
    [string]$Version = "1.0.0.0"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Building LSIA School Computer Windows MSI Installer" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# Check for WiX toolset
$Candle = Get-Command "candle.exe" -ErrorAction SilentlyContinue
$Light = Get-Command "light.exe" -ErrorAction SilentlyContinue
$Heat = Get-Command "heat.exe" -ErrorAction SilentlyContinue

if (-not $Candle -or -not $Light -or -not $Heat) {
    $WixPath = "${env:ProgramFiles(x86)}\WiX Toolset v3.11\bin"
    if (Test-Path "$WixPath\candle.exe") {
        $env:PATH = "$WixPath;$env:PATH"
        $Candle = "$WixPath\candle.exe"
        $Light = "$WixPath\light.exe"
        $Heat = "$WixPath\heat.exe"
    } else {
        Write-Host "[!] WiX Toolset was not found in PATH or standard location." -ForegroundColor Yellow
        Write-Host "Please ensure WiX Toolset v3.11 is installed."
        exit 1
    }
}

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$TempObj = Join-Path $OutputDir "obj"
if (-not (Test-Path $TempObj)) {
    New-Item -ItemType Directory -Path $TempObj -Force | Out-Null
}

$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$ServerDir = Join-Path $RepoRoot "server"
$AdminDistDir = Join-Path $RepoRoot "admin\dist"

if (-not (Test-Path $AdminDistDir)) {
    Write-Host "[!] Admin dist directory not found at $AdminDistDir. Please run 'npm run build' in admin folder first." -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/4] Staging server files..." -ForegroundColor Green
$StageServerDir = Join-Path $TempObj "stage_server"
if (Test-Path $StageServerDir) {
    Remove-Item -Recurse -Force $StageServerDir
}
New-Item -ItemType Directory -Path $StageServerDir -Force | Out-Null

Copy-Item -Path (Join-Path $ServerDir "pyproject.toml") -Destination $StageServerDir\
Copy-Item -Recurse -Path (Join-Path $ServerDir "lsia") -Destination (Join-Path $StageServerDir "lsia")
Get-ChildItem -Path $StageServerDir -Include "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force

Write-Host "[2/4] Harvesting server and admin files with heat..." -ForegroundColor Green
& $Heat dir "$StageServerDir" -cg ServerFilesGroup -dr SERVERFOLDER -scom -sfrag -srd -var "var.StageServerDir" -out "$TempObj\ServerFiles.wxs"
& $Heat dir "$AdminDistDir" -cg AdminFilesGroup -dr ADMINDISTFOLDER -scom -sfrag -srd -var "var.AdminDistDir" -out "$TempObj\AdminFiles.wxs"

Write-Host "[3/4] Compiling WiX XML source files (candle)..." -ForegroundColor Green
& $Candle "$PSScriptRoot\Product.wxs" "$TempObj\ServerFiles.wxs" "$TempObj\AdminFiles.wxs" `
    -dRepoRoot="$RepoRoot" -dStageServerDir="$StageServerDir" -dAdminDistDir="$AdminDistDir" `
    -ext WixFirewallExtension -ext WixUIExtension `
    -out "$TempObj\"

Write-Host "[4/4] Linking into MSI installer (light)..." -ForegroundColor Green
$MsiOutput = Join-Path $OutputDir "LSIASchoolComputer.msi"
& $Light "$TempObj\Product.wixobj" "$TempObj\ServerFiles.wixobj" "$TempObj\AdminFiles.wixobj" `
    -ext WixFirewallExtension -ext WixUIExtension `
    -sval `
    -out "$MsiOutput"

if (-not (Test-Path $MsiOutput)) {
    Write-Host "[ERROR] MSI output was not generated!" -ForegroundColor Red
    exit 1
}

$MsiSize = (Get-Item $MsiOutput).Length / 1MB
Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  [SUCCESS] MSI Installer built successfully!" -ForegroundColor Green
Write-Host "  Location: $MsiOutput ($([math]::Round($MsiSize, 2)) MB)" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
