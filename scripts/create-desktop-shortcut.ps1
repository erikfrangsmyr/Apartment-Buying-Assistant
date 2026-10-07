# Create a desktop shortcut that runs start-app.ps1
# Usage: powershell -ExecutionPolicy Bypass -File scripts\create-desktop-shortcut.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$StartScript = Join-Path $PSScriptRoot "start-app.ps1"

if (-not (Test-Path $StartScript)) {
    Write-Error "Missing $StartScript"
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Apartment Buying Assistant.lnk"

$Wsh = New-Object -ComObject WScript.Shell
$Shortcut = $Wsh.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`""
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = "Starta bostadsassistenten och öppna webbappen"
$Shortcut.Save()

Write-Host "Skapade genväg:"
Write-Host "  $ShortcutPath"
Write-Host ""
Write-Host "Tips: kopiera scripts\share.local.ps1.example till scripts\share.local.ps1 om du använder token eller --share."
