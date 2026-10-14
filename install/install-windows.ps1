# One-line installer for Windows (paste into PowerShell):
#   irm https://raw.githubusercontent.com/bhg0012/ai-data-analysis-agent/main/install/install-windows.ps1 | iex
# Puts Tally in %LOCALAPPDATA%\Tally, adds a Tally shortcut to your Desktop, and starts it.
$ErrorActionPreference = "Stop"
$repo = if ($env:TALLY_REPO) { $env:TALLY_REPO } else { "bhg0012/ai-data-analysis-agent" }
$branch = if ($env:TALLY_BRANCH) { $env:TALLY_BRANCH } else { "main" }
$dest = Join-Path $env:LOCALAPPDATA "Tally"

Write-Host ""
Write-Host "  Installing Tally into $dest"
if (-not (Test-Path (Join-Path $dest "tally"))) {
  $tmp = Join-Path $env:TEMP ("tally-" + [guid]::NewGuid())
  New-Item -ItemType Directory -Path $tmp | Out-Null
  $zip = Join-Path $tmp "tally.zip"
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  Invoke-WebRequest -UseBasicParsing "https://codeload.github.com/$repo/zip/refs/heads/$branch" -OutFile $zip
  Expand-Archive -Path $zip -DestinationPath $tmp -Force
  $src = Get-ChildItem $tmp -Directory | Select-Object -First 1
  New-Item -ItemType Directory -Path $dest -Force | Out-Null
  Copy-Item -Path (Join-Path $src.FullName "*") -Destination $dest -Recurse -Force
  Remove-Item $tmp -Recurse -Force
} else {
  Write-Host "  Tally is already installed. Starting it (it will update itself)."
}
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $dest "launchers\run-windows.ps1")
