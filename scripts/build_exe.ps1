<#
.SYNOPSIS
    Build HMS as a standalone Windows executable using PyInstaller.

.DESCRIPTION
    This script:
    1. Checks prerequisites (Python, venv, PyInstaller)
    2. Installs production + build dependencies
    3. Runs PyInstaller with the hms.spec file
    4. Validates the output executable exists
    5. Reports the file size

.EXAMPLE
    .\scripts\build_exe.ps1

.NOTES
    Output: dist\HMS.exe
    Estimated size: 80-150 MB
#>

param(
    [switch]$SkipInstall,   # Skip pip install step
    [switch]$Clean           # Clean build artifacts before building
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Push-Location $ProjectRoot

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  HMS Build Script — Windows Executable" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 0: Clean (optional) ────────────────────────────────────────────
if ($Clean) {
    Write-Host "[0/5] Cleaning previous build artifacts..." -ForegroundColor Yellow
    if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
    if (Test-Path "dist")  { Remove-Item -Recurse -Force "dist" }
    Write-Host "      [OK] Cleaned build/ and dist/" -ForegroundColor Green
    Write-Host ""
}

# ── Step 1: Check Python ────────────────────────────────────────────────
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
try {
    $pyVersion = python --version 2>&1
    Write-Host "      [OK] $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "      [FAIL] Python not found in PATH" -ForegroundColor Red
    Write-Host "      Install Python 3.11+ from https://python.org" -ForegroundColor Red
    Pop-Location
    exit 1
}

# ── Step 2: Check / activate virtual environment ────────────────────────
Write-Host "[2/5] Checking virtual environment..." -ForegroundColor Yellow
$venvActivate = Join-Path $ProjectRoot "venv\Scripts\Activate.ps1"

if (Test-Path $venvActivate) {
    & $venvActivate
    Write-Host "      [OK] venv activated" -ForegroundColor Green
} else {
    Write-Host "      [WARN] venv not found — using system Python" -ForegroundColor DarkYellow
    Write-Host "      Run 'python -m venv venv' first for isolation" -ForegroundColor DarkYellow
}

# ── Step 3: Install dependencies ────────────────────────────────────────
if (-not $SkipInstall) {
    Write-Host "[3/5] Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt --quiet 2>&1 | Out-Null
    pip install pyinstaller --quiet 2>&1 | Out-Null
    Write-Host "      [OK] Dependencies installed (including PyInstaller)" -ForegroundColor Green
} else {
    Write-Host "[3/5] Skipping dependency install (-SkipInstall)" -ForegroundColor DarkYellow
}

# ── Step 4: Verify PyInstaller ──────────────────────────────────────────
Write-Host "[4/5] Verifying PyInstaller..." -ForegroundColor Yellow
try {
    $piVersion = pyinstaller --version 2>&1
    Write-Host "      [OK] PyInstaller $piVersion" -ForegroundColor Green
} catch {
    Write-Host "      [FAIL] PyInstaller not found. Run: pip install pyinstaller" -ForegroundColor Red
    Pop-Location
    exit 1
}

# ── Step 5: Build ───────────────────────────────────────────────────────
Write-Host "[5/5] Building HMS.exe..." -ForegroundColor Yellow
Write-Host "      This may take 2-5 minutes..." -ForegroundColor DarkYellow
Write-Host ""

$startTime = Get-Date
pyinstaller hms.spec --noconfirm 2>&1 | ForEach-Object {
    if ($_ -match "ERROR|FAIL|error") {
        Write-Host "      $_" -ForegroundColor Red
    } elseif ($_ -match "WARNING|warn") {
        # Suppress most warnings to reduce noise
    } else {
        Write-Host "      $_" -ForegroundColor DarkGray
    }
}
$buildTime = (Get-Date) - $startTime

Write-Host ""

# ── Verify output ───────────────────────────────────────────────────────
$exePath = Join-Path $ProjectRoot "dist\HMS.exe"

if (Test-Path $exePath) {
    $fileSize = (Get-Item $exePath).Length
    $fileSizeMB = [math]::Round($fileSize / 1MB, 1)

    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  BUILD SUCCESSFUL" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Output:     dist\HMS.exe" -ForegroundColor White
    Write-Host "  Size:       $fileSizeMB MB" -ForegroundColor White
    Write-Host "  Build time: $([math]::Round($buildTime.TotalSeconds, 1))s" -ForegroundColor White
    Write-Host ""
    Write-Host "  To run:" -ForegroundColor Cyan
    Write-Host "    .\dist\HMS.exe" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  The executable starts both the API server (port 8000)" -ForegroundColor DarkGray
    Write-Host "  and the Flet UI (port 8080) in a single process." -ForegroundColor DarkGray
} else {
    Write-Host "============================================" -ForegroundColor Red
    Write-Host "  BUILD FAILED" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Expected output: dist\HMS.exe" -ForegroundColor Red
    Write-Host "  Check the build log above for errors." -ForegroundColor Red
    Write-Host ""
    Write-Host "  Common fixes:" -ForegroundColor Yellow
    Write-Host "    1. Activate venv: venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "    2. Reinstall: pip install -r requirements.txt pyinstaller" -ForegroundColor Yellow
    Write-Host "    3. Clean build: .\scripts\build_exe.ps1 -Clean" -ForegroundColor Yellow
    Pop-Location
    exit 1
}

Pop-Location
