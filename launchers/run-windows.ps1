# Starts Tally on Windows: installs the Python helper (uv) the first time,
# pulls the latest version from GitHub, adds a Desktop shortcut, then opens the app window.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
try { $Host.UI.RawUI.WindowTitle = "Tally" } catch {}

function Pause-AndExit($code) {
  Write-Host ""
  Read-Host "  Press Enter to close"
  exit $code
}

Write-Host ""
Write-Host "   Tally"
Write-Host "   -----"
Write-Host ""

try {
  $uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
  if (-not (Test-Path $uv)) {
    $found = Get-Command uv -ErrorAction SilentlyContinue
    if ($found) { $uv = $found.Source }
  }
  if (-not (Test-Path $uv)) {
    Write-Host "  First-time setup: installing a small helper that runs Tally (uv)..."
    $env:UV_NO_MODIFY_PATH = "1"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" | Out-Null
    $uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
    if (-not (Test-Path $uv)) { throw "Couldn't install the helper. Check your internet connection and try again." }
  }

  & $uv run --quiet --no-project --python 3.12 python launchers/update.py

  # A Desktop shortcut with the Tally icon, made once.
  try {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $lnk = Join-Path $desktop "Tally.lnk"
    if (-not (Test-Path $lnk)) {
      $shell = New-Object -ComObject WScript.Shell
      $s = $shell.CreateShortcut($lnk)
      $s.TargetPath = Join-Path $Root "Start Tally (Windows).bat"
      $s.WorkingDirectory = $Root
      $s.IconLocation = (Join-Path $Root "launchers\icons\tally.ico") + ",0"
      $s.WindowStyle = 7
      $s.Description = "Tally - your friendly data analyst"
      $s.Save()
      Write-Host "  Added a Tally shortcut to your Desktop."
    }
  } catch {
    Write-Host "  (Couldn't add a Desktop shortcut. You can still start Tally from this folder.)"
  }

  if (-not (Test-Path (Join-Path $Root ".venv\Scripts\python.exe"))) {
    Write-Host "  Getting everything ready. The first start takes a minute or two..."
  }

  & $uv run --quiet --python 3.12 python -m tally
  if ($LASTEXITCODE -ne 0) { throw "Tally stopped because of a problem (see the messages above)." }
} catch {
  Write-Host ""
  Write-Host "  Sorry, something went wrong: $($_.Exception.Message)"
  Pause-AndExit 0
}
