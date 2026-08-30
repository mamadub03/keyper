<#
  Keyper — one-command local launcher (Windows / PowerShell).

  Brings up the whole stack and opens the browser:

    auth lab (uvicorn :8090)
      -> cloudflared quick tunnel   (public URL, so AgentCore Browser can reach the lab)
    API / BFF (uvicorn :8000)       (KEYPER_INVOKE_MODE=local -> agent runs in-process)
    web UI (vite :5173)             (form pre-filled with the 4 demo scenarios)

  The only prerequisite is AWS credentials configured once with `aws configure`
  (or SSO). Nothing is typed into the app. Ctrl+C tears everything down.

  Usage:  ./run.ps1            # full demo (lab + tunnel + API + UI)
          ./run.ps1 -NoTunnel  # skip lab+tunnel; UI form starts blank
#>
[CmdletBinding()]
param([switch]$NoTunnel)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

$procs = @()
function Start-Bg([string]$file, [string]$args, [hashtable]$env = @{}) {
  foreach ($k in $env.Keys) { [Environment]::SetEnvironmentVariable($k, $env[$k], "Process") }
  $p = Start-Process -FilePath $file -ArgumentList $args -PassThru -NoNewWindow
  $script:procs += $p
  return $p
}
function Cleanup {
  Write-Host "`nShutting down..." -ForegroundColor Yellow
  foreach ($p in $script:procs) {
    if ($p -and -not $p.HasExited) {
      try { taskkill /PID $p.Id /T /F *> $null } catch {}
    }
  }
}

# --- resolve tools -----------------------------------------------------------
$py = (Get-Command python -ErrorAction SilentlyContinue)?.Source
if (-not $py) { throw "python not found on PATH (need 3.12+)." }

$cf = (Get-Command cloudflared -ErrorAction SilentlyContinue)?.Source
if (-not $cf) {
  $guess = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
  if (Test-Path $guess) { $cf = $guess }
}
if (-not $NoTunnel -and -not $cf) {
  throw "cloudflared not found. Install it with:  winget install --id Cloudflare.cloudflared`n" +
        "or run ./run.ps1 -NoTunnel and type service URLs into the form yourself."
}

# --- preflight: AWS creds --------------------------------------------------
Write-Host "Checking AWS credentials..." -ForegroundColor Cyan
try { aws sts get-caller-identity --output text *> $null }
catch { throw "AWS credentials not working. Run 'aws configure' (or 'aws sso login') first." }

if (-not $env:KEYPER_AWS_REGION) { $env:KEYPER_AWS_REGION = "us-west-2" }

# --- deps (install once) --------------------------------------------------
& $py -c "import strands, fastapi" *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Installing Python dependencies (one-time)..." -ForegroundColor Cyan
  & $py -m pip install -e ".[dev]" | Out-Host
}
if (-not (Test-Path "$root\web\node_modules")) {
  Write-Host "Installing web dependencies (one-time)..." -ForegroundColor Cyan
  Push-Location "$root\web"; npm install | Out-Host; Pop-Location
}

try {
  # --- 1. auth lab ------------------------------------------------------
  if (-not $NoTunnel) {
    Write-Host "Starting auth lab on :8090..." -ForegroundColor Cyan
    Start-Bg $py "-m uvicorn app:app --app-dir auth-lab --port 8090 --log-level warning" | Out-Null

    # --- 2. tunnel ----------------------------------------------------
    Write-Host "Opening cloudflared tunnel..." -ForegroundColor Cyan
    $tlog = New-TemporaryFile
    Start-Bg $cf "tunnel --url http://localhost:8090 --no-autoupdate --logfile `"$($tlog.FullName)`"" | Out-Null

    $labUrl = $null
    foreach ($i in 1..40) {
      Start-Sleep -Milliseconds 750
      $m = Select-String -Path $tlog.FullName -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue | Select-Object -First 1
      if ($m) { $labUrl = $m.Matches[0].Value; break }
    }
    if (-not $labUrl) { throw "Tunnel did not report a URL in time. Check $($tlog.FullName)." }
    $env:KEYPER_LAB_URL = $labUrl
    Write-Host "  lab reachable at $labUrl" -ForegroundColor Green
  }

  # --- 3. API --------------------------------------------------------
  Write-Host "Starting API on :8000..." -ForegroundColor Cyan
  Start-Bg $py "-m uvicorn api.main:app --port 8000 --log-level warning" | Out-Null

  # --- 4. web UI ---------------------------------------------------
  Write-Host "Starting web UI on :5173..." -ForegroundColor Cyan
  Push-Location "$root\web"
  Start-Bg "npm" "run dev -- --host 127.0.0.1 --strictPort" | Out-Null
  Pop-Location

  Start-Sleep -Seconds 3
  Start-Process "http://localhost:5173"
  Write-Host "`nKeyper is up. Open http://localhost:5173  —  Ctrl+C to stop.`n" -ForegroundColor Green

  while ($true) { Start-Sleep -Seconds 3600 }
}
finally { Cleanup }
