# Start Apartment Buying Assistant and open the web app in your default browser.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\start-app.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$AppShareToken = $null
$ListenShare = $false
$AppPort = 8642

$LocalConfig = Join-Path $PSScriptRoot "share.local.ps1"
if (Test-Path $LocalConfig) {
    . $LocalConfig
}

if ($env:APP_PORT) {
    $AppPort = [int]$env:APP_PORT
}
if ($env:APP_SHARE_TOKEN) {
    $AppShareToken = $env:APP_SHARE_TOKEN
}
elseif ($env:SHARE_TOKEN) {
    $AppShareToken = $env:SHARE_TOKEN
}

$baseUrl = "http://127.0.0.1:$AppPort/app"
if ($AppShareToken) {
    $openUrl = "$baseUrl?token=$AppShareToken"
}
else {
    $openUrl = $baseUrl
}

$healthUrl = "http://127.0.0.1:$AppPort/health"

function Test-ServerUp {
    try {
        $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
        return $r.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

if (Test-ServerUp) {
    Write-Host "Server körs redan på port $AppPort — öppnar webbläsaren."
    Start-Process $openUrl
    exit 0
}

$serveArgs = @("scripts/serve.py")
if ($ListenShare) {
    $serveArgs += "--share"
}

$serverCmd = @"
Set-Location '$ProjectRoot'
if ('$AppShareToken') { `$env:APP_SHARE_TOKEN = '$AppShareToken' }
`$env:APP_PORT = '$AppPort'
uv run python $($serveArgs -join ' ')
"@

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-Command", $serverCmd
)

Write-Host "Startar server (nytt fönster) …"
$deadline = (Get-Date).AddSeconds(45)
while ((Get-Date) -lt $deadline) {
    if (Test-ServerUp) {
        Write-Host "Öppnar $openUrl"
        Start-Process $openUrl
        exit 0
    }
    Start-Sleep -Milliseconds 500
}

Write-Host "Servern svarar inte än på $healthUrl. Kolla serverfönstret för fel, öppna sedan manuellt:"
Write-Host "  $openUrl"
Start-Process $openUrl
exit 1
