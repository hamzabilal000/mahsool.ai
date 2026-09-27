# Mahsool AI backend on a Windows laptop, public through ngrok. Steps: docs/RUN_ON_MY_LAPTOP.md
#
#   .\scripts\run_local.ps1          # first time: installs everything; later: just starts
#   .\scripts\run_local.ps1 -Check   # is it working? (local and public)
#
# First run: creates .venv (Python 3.11), installs the dependencies with CPU-only PyTorch,
# installs the prebuilt search index, asks for your GROQ_API_KEY once and saves it in .env
# (never committed; .gitignore). Every run: starts ngrok on your static domain in a second
# window and the backend (local SQLite) in this window. Stop: Ctrl+C here, close the ngrok window.
param([switch]$Check)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$EnvFile = Join-Path $Root ".env"
$DefaultDomain = "resident-coil-delusion.ngrok-free.dev"

function Say($text) { Write-Host "== $text" -ForegroundColor Cyan }
function Fail($text) { Write-Host "!! $text" -ForegroundColor Red; exit 1 }

# --- .env: KEY=value lines, written as UTF-8 without BOM (a BOM breaks the first key) ---------
function Read-DotEnv {
    $values = @{}
    if (Test-Path $EnvFile) {
        foreach ($line in Get-Content $EnvFile) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') { $values[$Matches[1]] = $Matches[2].Trim() }
        }
    }
    return $values
}
function Set-DotEnv($key, $value) {
    $lines = @()
    if (Test-Path $EnvFile) { $lines = @(Get-Content $EnvFile | Where-Object { $_ -notmatch "^\s*$key\s*=" }) }
    $lines += "$key=$value"
    [IO.File]::WriteAllText($EnvFile, (($lines -join "`n") + "`n"), (New-Object Text.UTF8Encoding($false)))
}

$config = Read-DotEnv
$Domain = if ($env:NGROK_DOMAIN) { $env:NGROK_DOMAIN } elseif ($config["NGROK_DOMAIN"]) { $config["NGROK_DOMAIN"] } else { $DefaultDomain }

if ($Check) {
    try { Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 10 | Out-Null; Write-Host "backend (local):  OK" -ForegroundColor Green }
    catch { Write-Host "backend (local):  NOT ANSWERING (is the backend window still open?)" -ForegroundColor Red }
    try {
        Invoke-RestMethod "https://$Domain/health" -Headers @{ "ngrok-skip-browser-warning" = "true" } -TimeoutSec 20 | Out-Null
        Write-Host "public (ngrok):   OK  https://$Domain" -ForegroundColor Green
    } catch { Write-Host "public (ngrok):   NOT ANSWERING (is the ngrok window open?)" -ForegroundColor Red }
    exit 0
}

# --- 1. tools -----------------------------------------------------------------------------
Say "1/5 checking Git and ngrok"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "Git is not installed (docs/RUN_ON_MY_LAPTOP.md, step 1)." }
if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) { Fail "ngrok is not installed or not on PATH (docs/RUN_ON_MY_LAPTOP.md, step 1)." }

# --- 2. virtual environment and dependencies (again only when pyproject.toml changes) ---------
Say "2/5 Python environment (Python 3.11 through the py launcher)"
# The default python may be another version (e.g. 3.14): always ask the launcher for 3.11.
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Fail "The Python launcher 'py' was not found. Install Python 3.11 from python.org (it includes 'py'), see docs/RUN_ON_MY_LAPTOP.md step 1."
}
# (try/catch: Windows PowerShell 5.1 turns the launcher's error text into an exception.)
$has311 = $false
try { & py -3.11 -c "import sys" 2>$null; $has311 = ($LASTEXITCODE -eq 0) } catch { $has311 = $false }
if (-not $has311) {
    Fail "Python 3.11 is not installed. Install Python 3.11 from python.org (you can keep your other Python). 'py --list' shows what you have."
}
if (Test-Path $Py) {
    # A .venv made with another Python version is replaced.
    $venvVer = & $Py -c "import sys; print('%d.%d' % sys.version_info[:2])"
    if ($venvVer -ne "3.11") { Say "replacing .venv (Python $venvVer) with Python 3.11"; Remove-Item -Recurse -Force .venv }
}
if (-not (Test-Path $Py)) {
    & py -3.11 -m venv .venv
    if (-not (Test-Path $Py)) { Fail "Could not create .venv with 'py -3.11 -m venv .venv'." }
}
$Stamp = Join-Path $Root ".venv\installed.txt"
$want = (Get-FileHash (Join-Path $Root "pyproject.toml")).Hash
$have = if (Test-Path $Stamp) { Get-Content $Stamp } else { "" }
if ($have -ne $want) {
    Say "installing dependencies (first time: 10-20 minutes, ~2 GB)"
    & $Py -m pip install --upgrade pip
    & $Py -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE -ne 0) { Fail "PyTorch install failed." }
    & $Py -m pip install -e ".[ml]"
    if ($LASTEXITCODE -ne 0) { Fail "Dependency install failed." }
    Set-Content $Stamp $want
}

# --- 3. search index ------------------------------------------------------------------------
Say "3/5 search index"
& $Py scripts/get_index.py
if ($LASTEXITCODE -ne 0) { Fail "Could not install the search index." }

# --- 4. keys (asked once) ---------------------------------------------------------------------
Say "4/5 settings in .env"
if (-not $config["GROQ_API_KEY"]) {
    $secure = Read-Host "Paste your GROQ_API_KEY (starts with gsk_) and press Enter" -AsSecureString
    $key = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
    if (-not $key) { Fail "No key given." }
    Set-DotEnv "GROQ_API_KEY" $key.Trim()
}
if (-not $config["NGROK_DOMAIN"]) { Set-DotEnv "NGROK_DOMAIN" $Domain }
if (-not $config["MAHSOOL_SQLITE_PATH"]) { Set-DotEnv "MAHSOOL_SQLITE_PATH" "data/mahsool.db" }

# --- 5. start -------------------------------------------------------------------------------
Say "5/5 starting ngrok (second window) and the backend (this window)"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'Mahsool ngrok'; ngrok http 127.0.0.1:8000 --url=https://$Domain"
Write-Host ""
Write-Host "Public address: https://$Domain   (ready when you see 'Application startup complete')" -ForegroundColor Green
Write-Host "Stop: press Ctrl+C here and close the ngrok window." -ForegroundColor Green
Write-Host ""
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue  # local SQLite, not Postgres
# ngrok connects from 127.0.0.1 and sends the visitor's address in X-Forwarded-For; uvicorn trusts
# it only from there, so the daily limit per visitor counts real visitors.
& $Py -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1
