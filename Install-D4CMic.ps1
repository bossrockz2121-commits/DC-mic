$ErrorActionPreference = "Stop"
$appName = "D4C Mic Boost V.2"
$installDirectory = Join-Path $env:LOCALAPPDATA "Programs\$appName"
$installedExecutable = Join-Path $installDirectory "$appName.exe"
$startMenuDirectory = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$shortcutShell = $null

Add-Type -AssemblyName System.Windows.Forms

function Show-InstallMessage {
    param(
        [string]$Message,
        [string]$Title,
        [int]$Icon
    )

    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        $Message,
        $Title,
        [System.Windows.Forms.MessageBoxButtons]::OK,
        $Icon
    ) | Out-Null
}

try {
    $sourceExecutable = Join-Path $PSScriptRoot "$appName.exe"
    if (-not (Test-Path -LiteralPath $sourceExecutable -PathType Leaf)) {
        throw "The packaged application is missing: $sourceExecutable"
    }

    $desktop = [Environment]::GetFolderPath("Desktop")
    if (-not (Test-Path -LiteralPath $desktop -PathType Container)) {
        throw "The current user's Desktop folder could not be found."
    }

    New-Item -ItemType Directory -Path $installDirectory -Force | Out-Null
    Copy-Item -LiteralPath $sourceExecutable -Destination $installedExecutable -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "Uninstall-D4CMic.ps1") `
        -Destination (Join-Path $installDirectory "Uninstall-D4CMic.ps1") -Force

    $shortcutShell = New-Object -ComObject WScript.Shell
    foreach ($shortcutPath in @(
        (Join-Path $desktop "$appName.lnk"),
        (Join-Path $startMenuDirectory "$appName.lnk")
    )) {
        $shortcut = $shortcutShell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $installedExecutable
        $shortcut.WorkingDirectory = $installDirectory
        $shortcut.Description = "D4C Mic Boost V.2 - Discord microphone processor"
        $shortcut.Save()
    }

    $uninstallShortcut = $shortcutShell.CreateShortcut(
        (Join-Path $startMenuDirectory "Uninstall $appName.lnk")
    )
    $uninstallShortcut.TargetPath = "powershell.exe"
    $uninstallShortcut.Arguments = (
        '-NoProfile -ExecutionPolicy Bypass -File "' +
        (Join-Path $installDirectory "Uninstall-D4CMic.ps1") + '"'
    )
    $uninstallShortcut.WorkingDirectory = $installDirectory
    $uninstallShortcut.Description = "Uninstall $appName"
    $uninstallShortcut.Save()

    Show-InstallMessage `
        "Installed successfully.`r`n`r`nOpen $appName from your desktop. For Discord, use CABLE Output (VB-Audio Virtual Cable) as the input device." `
        $appName `
        ([System.Windows.Forms.MessageBoxIcon]::Information)
    Start-Process -FilePath $installedExecutable
}
catch {
    Show-InstallMessage `
        "Installation failed:`r`n$($_.Exception.Message)" `
        "$appName Setup" `
        ([System.Windows.Forms.MessageBoxIcon]::Error)
    exit 1
}
finally {
    if ($null -ne $shortcutShell) {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shortcutShell)
    }
}
