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

# Read a file another process is still writing to (cloudflared holds its
# output open). Get-Content / Select-String can trip over the write lock on
# Windows; opening with FileShare.ReadWrite does not.
function Read-Shared([string]$path) {
    if (-not (Test-Path $path)) { return "" }
    try {
        $fs = [System.IO.File]::Open($path, 'Open', 'Read', 'ReadWrite')
        $sr = New-Object System.IO.StreamReader($fs)
        $text = $sr.ReadToEnd()
        $sr.Close(); $fs.Close()
        return $text
    } catch { return "" }
}

# --- resolve tools --------------------------------------------------------
$py = Resolve-Tool "python" @()
if (-not $py) { throw "python not found on PATH (need 3.12+)." }

$npm = Resolve-Tool "npm" @("$env:ProgramFiles\nodejs\npm.cmd")
if (-not $npm) { throw "npm not found on PATH (need Node.js 20+)." }

$node = Resolve-Tool "node" @("$env:ProgramFiles\nodejs\node.exe")
if (-not $node) { throw "node not found on PATH (need Node.js 20+)." }

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
        # cloudflared prints the assigned URL to stderr. Capture both streams
        # to files we own so the URL scrape doesn't fight a write lock.
        $tout = Join-Path ([System.IO.Path]::GetTempPath()) "keyper-cf-out.log"
        $terr = Join-Path ([System.IO.Path]::GetTempPath()) "keyper-cf-err.log"
        Remove-Item $tout, $terr -ErrorAction SilentlyContinue
        $cfp = Start-Process -FilePath $cf -PassThru -NoNewWindow -WorkingDirectory $root `
            -ArgumentList @("tunnel", "--url", "http://localhost:8090", "--no-autoupdate") `
            -RedirectStandardOutput $tout -RedirectStandardError $terr
        [void]$started.Add($cfp)

        $labUrl = $null
        foreach ($i in 1..80) {
            Start-Sleep -Milliseconds 750
            $m = [regex]::Match((Read-Shared $terr) + (Read-Shared $tout),
                                "https://[a-z0-9-]+\.trycloudflare\.com")
            if ($m.Success) { $labUrl = $m.Value; break }
            if ($cfp.HasExited) { throw "cloudflared exited early. See $terr" }
        }
        if (-not $labUrl) { throw "Tunnel did not report a URL within 60s. See $terr" }
        $env:KEYPER_LAB_URL = $labUrl
        Write-Host "  lab reachable at $labUrl" -ForegroundColor Green
    }

    Write-Host "Starting API on :8000..." -ForegroundColor Cyan
    Start-Component $py @("-m", "uvicorn", "api.main:app",
                          "--port", "8000", "--log-level", "warning") | Out-Null

    Write-Host "Starting web UI on :5173..." -ForegroundColor Cyan
    # Launch Vite through node directly — avoids the npm.cmd shim and the
    # "space in C:\Program Files" quoting problems that come with routing a
    # .cmd through Start-Process / cmd.exe.
    $vite = Join-Path $root "web\node_modules\vite\bin\vite.js"
    Start-Component $node @($vite, "--host", "127.0.0.1", "--strictPort") "$root\web" | Out-Null

    # Wait for the three ports so a silent startup failure surfaces here
    # instead of the user meeting a dead page.
    foreach ($svc in @(@{n = "API"; p = 8000 }, @{n = "web UI"; p = 5173 })) {
        $ok = $false
        foreach ($i in 1..40) {
            Start-Sleep -Milliseconds 500
            if (Test-NetConnection -ComputerName "localhost" -Port $svc.p -WarningAction SilentlyContinue -InformationLevel Quiet) {
                $ok = $true; break
            }
        }
        if (-not $ok) { throw "$($svc.n) did not come up on port $($svc.p) — check the output above." }
    }

    Start-Process "http://localhost:5173"
    Write-Host "`nKeyper is up. Open http://localhost:5173  -  Ctrl+C to stop.`n" -ForegroundColor Green

    while ($true) { Start-Sleep -Seconds 3600 }
}
finally { Stop-All }
