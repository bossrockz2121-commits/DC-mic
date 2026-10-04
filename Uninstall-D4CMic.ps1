$ErrorActionPreference = "Stop"
$appName = "D4C Mic Boost V.2"
$installDirectory = Join-Path $env:LOCALAPPDATA "Programs\$appName"
$installedExecutable = Join-Path $installDirectory "$appName.exe"
$startMenuDirectory = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"

Add-Type -AssemblyName System.Windows.Forms
$running = Get-CimInstance Win32_Process -Filter "Name = '$appName.exe'" |
    Where-Object { $_.ExecutablePath -eq $installedExecutable }
if ($running) {
    [System.Windows.Forms.MessageBox]::Show(
        "Close D4C Mic Boost V.2 before uninstalling, then try again.",
        "Uninstall D4C Mic Boost V.2",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Warning
    ) | Out-Null
    exit 1
}

$confirmation = [System.Windows.Forms.MessageBox]::Show(
    "Remove D4C Mic Boost V.2 and its shortcuts for this Windows account?",
    "Uninstall D4C Mic Boost V.2",
    [System.Windows.Forms.MessageBoxButtons]::YesNo,
    [System.Windows.Forms.MessageBoxIcon]::Question
)
if ($confirmation -ne [System.Windows.Forms.DialogResult]::Yes) {
    exit 0
}

try {
    $desktop = [Environment]::GetFolderPath("Desktop")
    foreach ($shortcutPath in @(
        (Join-Path $desktop "$appName.lnk"),
        (Join-Path $startMenuDirectory "$appName.lnk"),
        (Join-Path $startMenuDirectory "Uninstall $appName.lnk")
    )) {
        if (Test-Path -LiteralPath $shortcutPath -PathType Leaf) {
            Remove-Item -LiteralPath $shortcutPath -Force
        }
    }

    if (Test-Path -LiteralPath $installDirectory -PathType Container) {
        Remove-Item -LiteralPath $installDirectory -Recurse -Force
    }
    [System.Windows.Forms.MessageBox]::Show(
        "D4C Mic Boost V.2 was removed.",
        "Uninstall complete",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null
}
catch {
    [System.Windows.Forms.MessageBox]::Show(
        "Uninstall failed:`r`n$($_.Exception.Message)",
        "Uninstall D4C Mic Boost V.2",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
    exit 1
}
