$ErrorActionPreference = "Stop"

$workspace = $PSScriptRoot
$python = Join-Path $workspace ".venv\Scripts\python.exe"
$payload = Join-Path $workspace "dist-fastest\D4C Mic Boost V.2.exe"
$uninstaller = Join-Path $workspace "Uninstall-D4CMic.ps1"
$output = Join-Path $workspace "dist-share"
$work = Join-Path $workspace "build-share"
$setupName = "D4C Mic Boost V.2 Setup"
$setupPath = Join-Path $output "$setupName.exe"

foreach ($requiredPath in @($python, $payload, $uninstaller)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required setup input is missing: $requiredPath"
    }
}

New-Item -ItemType Directory -Path $output -Force | Out-Null
$arguments = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", $setupName,
    "--distpath", $output,
    "--workpath", $work,
    "--add-data", "$payload;payload",
    "--add-data", "$uninstaller;payload",
    "setup_launcher.py"
)
& $python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Setup packaging failed with exit code $LASTEXITCODE."
}
if (-not (Test-Path -LiteralPath $setupPath -PathType Leaf)) {
    throw "PyInstaller completed without producing the setup executable: $setupPath"
}

Get-Item -LiteralPath $setupPath |
    Select-Object FullName, Length, LastWriteTime
