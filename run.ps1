<#
  Keyper - one-command local launcher (Windows / PowerShell 5.1+).

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

$started = New-Object System.Collections.ArrayList

function Resolve-Tool([string]$name, [string[]]$fallbacks) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($f in $fallbacks) { if (Test-Path $f) { return $f } }
    return $null
}

function Start-Component([string]$exe, [string[]]$argv, [string]$workdir = $root) {
    $p = Start-Process -FilePath $exe -ArgumentList $argv -WorkingDirectory $workdir `
        -PassThru -NoNewWindow
    [void]$started.Add($p)
    return $p
}

function Stop-All {
    Write-Host "`nShutting down..." -ForegroundColor Yellow
    foreach ($p in $started) {
        if ($p -and -not $p.HasExited) {
            # /T also kills the child tree (uvicorn workers, vite esbuild, etc.)
            taskkill /PID $p.Id /T /F *> $null
        }
    }
}

# --- resolve tools --------------------------------------------------------
$py = Resolve-Tool "python" @()
if (-not $py) { throw "python not found on PATH (need 3.12+)." }

$npm = Resolve-Tool "npm" @("$env:ProgramFiles\nodejs\npm.cmd")
if (-not $npm) { throw "npm not found on PATH (need Node.js 20+)." }

$aws = Resolve-Tool "aws" @("$env:ProgramFiles\Amazon\AWSCLIV2\aws.exe",
                            "$env:LOCALAPPDATA\Programs\Amazon\AWSCLIV2\aws.exe")
if (-not $aws) { throw "aws CLI not found. Install AWS CLI v2 and run 'aws configure'." }

$cf = $null
if (-not $NoTunnel) {
    $cf = Resolve-Tool "cloudflared" @("${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe",
                                       "$env:ProgramFiles\cloudflared\cloudflared.exe")
    if (-not $cf) {
        throw "cloudflared not found. Install it with:`n" +
              "  winget install --id Cloudflare.cloudflared`n" +
              "or run ./run.ps1 -NoTunnel and type service URLs into the form yourself."
    }
}

# --- preflight: AWS credentials ----------------------------------------
Write-Host "Checking AWS credentials..." -ForegroundColor Cyan
& $aws sts get-caller-identity --output text *> $null
if ($LASTEXITCODE -ne 0) {
    throw "AWS credentials not working. Run 'aws configure' (or 'aws sso login') first."
}
if (-not $env:KEYPER_AWS_REGION) { $env:KEYPER_AWS_REGION = "us-west-2" }

# --- dependencies (install once) -------------------------------------
& $py -c "import strands, fastapi" *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Python dependencies (one-time)..." -ForegroundColor Cyan
    & $py -m pip install -e ".[dev]"
}
if (-not (Test-Path "$root\web\node_modules")) {
    Write-Host "Installing web dependencies (one-time)..." -ForegroundColor Cyan
    & $npm --prefix "$root\web" install
}

try {
    if (-not $NoTunnel) {
        Write-Host "Starting auth lab on :8090..." -ForegroundColor Cyan
        Start-Component $py @("-m", "uvicorn", "app:app", "--app-dir", "auth-lab",
                              "--port", "8090", "--log-level", "warning") | Out-Null

        Write-Host "Opening cloudflared tunnel..." -ForegroundColor Cyan
        $tlog = [System.IO.Path]::GetTempFileName()
        Start-Component $cf @("tunnel", "--url", "http://localhost:8090",
                              "--no-autoupdate", "--logfile", $tlog) | Out-Null

        $labUrl = $null
        foreach ($i in 1..60) {
            Start-Sleep -Milliseconds 750
            if (Test-Path $tlog) {
                $hit = Select-String -Path $tlog -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" |
                       Select-Object -First 1
                if ($hit) { $labUrl = $hit.Matches[0].Value; break }
            }
        }
        if (-not $labUrl) { throw "Tunnel did not report a URL in time. See $tlog" }
        $env:KEYPER_LAB_URL = $labUrl
        Write-Host "  lab reachable at $labUrl" -ForegroundColor Green
    }

    Write-Host "Starting API on :8000..." -ForegroundColor Cyan
    Start-Component $py @("-m", "uvicorn", "api.main:app",
                          "--port", "8000", "--log-level", "warning") | Out-Null

    Write-Host "Starting web UI on :5173..." -ForegroundColor Cyan
    Start-Component $npm @("--prefix", "$root\web", "run", "dev", "--",
                           "--host", "127.0.0.1", "--strictPort") | Out-Null

    Start-Sleep -Seconds 3
    Start-Process "http://localhost:5173"
    Write-Host "`nKeyper is up. Open http://localhost:5173  -  Ctrl+C to stop.`n" -ForegroundColor Green

    while ($true) { Start-Sleep -Seconds 3600 }
}
finally { Stop-All }
