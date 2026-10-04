import base64
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk


APP_NAME = "D4C Mic Boost V.2"
WINDOW_BG = "#11141b"
CARD_BG = "#1a1f29"
TEXT = "#f1f4f9"
MUTED = "#a1acbc"
ACCENT = "#72e0bb"


def resource_path(name):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "payload" / name


def create_shortcuts(install_dir):
    exe_path = install_dir / f"{APP_NAME}.exe"
    uninstall_path = install_dir / "Uninstall-D4CMic.ps1"
    powershell_script = r"""
$ErrorActionPreference = 'Stop'
$desktop = [Environment]::GetFolderPath('Desktop')
$startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
New-Item -ItemType Directory -Path $startMenu -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell
$items = @(
    @{ Path = (Join-Path $desktop 'D4C Mic Boost V.2.lnk'); Target = $env:D4C_INSTALLED_EXE; Args = '' },
    @{ Path = (Join-Path $startMenu 'D4C Mic Boost V.2.lnk'); Target = $env:D4C_INSTALLED_EXE; Args = '' },
    @{ Path = (Join-Path $startMenu 'Uninstall D4C Mic Boost V.2.lnk'); Target = 'powershell.exe'; Args = ('-NoProfile -ExecutionPolicy Bypass -File "' + $env:D4C_UNINSTALL_SCRIPT + '"') }
)
foreach ($item in $items) {
    $shortcut = $shell.CreateShortcut($item.Path)
    $shortcut.TargetPath = $item.Target
    $shortcut.Arguments = $item.Args
    $shortcut.WorkingDirectory = $env:D4C_INSTALL_DIR
    $shortcut.Description = 'D4C Mic Boost V.2'
    $shortcut.Save()
}
[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell)
"""
    encoded_script = base64.b64encode(powershell_script.encode("utf-16le")).decode("ascii")
    environment = os.environ.copy()
    environment["D4C_INSTALLED_EXE"] = str(exe_path)
    environment["D4C_UNINSTALL_SCRIPT"] = str(uninstall_path)
    environment["D4C_INSTALL_DIR"] = str(install_dir)
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded_script,
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(detail or f"Shortcut creation failed (exit {result.returncode}).")


class SetupWindow:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} Setup")
        self.root.geometry("480x370")
        self.root.resizable(False, False)
        self.root.configure(bg=WINDOW_BG)
        self.results = queue.Queue()
        self.is_installing = False

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(
            "Setup.TFrame",
            background=WINDOW_BG,
        )
        style.configure(
            "Card.TFrame",
            background=CARD_BG,
        )
        style.configure(
            "Title.TLabel",
            background=WINDOW_BG,
            foreground=TEXT,
            font=("Segoe UI Semibold", 22),
        )
        style.configure(
            "Version.TLabel",
            background=WINDOW_BG,
            foreground=ACCENT,
            font=("Segoe UI Semibold", 11),
        )
        style.configure(
            "Body.TLabel",
            background=CARD_BG,
            foreground=TEXT,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Hint.TLabel",
            background=CARD_BG,
            foreground=MUTED,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Status.TLabel",
            background=WINDOW_BG,
            foreground=ACCENT,
            font=("Segoe UI Semibold", 9),
        )
        style.configure(
            "Install.TButton",
            background=ACCENT,
            foreground=WINDOW_BG,
            font=("Segoe UI Semibold", 11),
            padding=(18, 10),
            borderwidth=0,
        )
        style.map(
            "Install.TButton",
            background=[("active", "#96f0d1"), ("disabled", "#303947")],
            foreground=[("disabled", MUTED)],
        )
        style.configure(
            "Setup.Horizontal.TProgressbar",
            background=ACCENT,
            troughcolor="#303947",
            borderwidth=0,
        )

        page = ttk.Frame(root, style="Setup.TFrame", padding=(28, 24))
        page.pack(fill="both", expand=True)
        top = ttk.Frame(page, style="Setup.TFrame")
        top.pack(fill="x", pady=(0, 19))
        ttk.Label(top, text="D4C MIC BOOST", style="Title.TLabel").pack(side="left")
        ttk.Label(top, text="V.2", style="Version.TLabel").pack(
            side="left", padx=(10, 0), pady=(9, 0)
        )

        card = ttk.Frame(page, style="Card.TFrame", padding=(17, 16))
        card.pack(fill="x")
        ttk.Label(card, text="Install for your Windows account", style="Body.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            card,
            text="No administrator permission required.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(5, 0))
        ttk.Label(
            card,
            text="Creates Desktop and Start Menu shortcuts, plus an uninstaller.",
            style="Hint.TLabel",
            wraplength=405,
        ).pack(anchor="w", pady=(7, 0))

        self.driver_warning = tk.Label(
            page,
            text="VB-Audio Virtual Cable is a separate driver. Friends must install "
            "it before routing the processed mic into Discord.",
            background=WINDOW_BG,
            foreground="#ffca70",
            justify="left",
            wraplength=420,
            font=("Segoe UI", 9),
        )
        self.driver_warning.pack(anchor="w", pady=(16, 0))

        self.progress = ttk.Progressbar(
            page,
            mode="indeterminate",
            style="Setup.Horizontal.TProgressbar",
            length=420,
        )
        self.progress.pack(fill="x", pady=(18, 0))
        self.status = tk.StringVar(value="Ready to install")
        ttk.Label(page, textvariable=self.status, style="Status.TLabel").pack(
            anchor="w", pady=(10, 0)
        )
        self.install_button = ttk.Button(
            page,
            text="Install D4C Mic Boost V.2",
            style="Install.TButton",
            command=self.install,
        )
        self.install_button.pack(anchor="e", pady=(17, 0))
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._check_result)

    def install(self):
        if self.is_installing:
            return
        self.is_installing = True
        self.install_button.configure(state="disabled")
        self.status.set("Installing app and creating shortcuts…")
        self.progress.start(10)
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self):
        try:
            source_exe = resource_path(f"{APP_NAME}.exe")
            source_uninstaller = resource_path("Uninstall-D4CMic.ps1")
            if not source_exe.is_file():
                raise FileNotFoundError(f"Setup payload is missing: {source_exe}")
            if not source_uninstaller.is_file():
                raise FileNotFoundError(f"Uninstaller payload is missing: {source_uninstaller}")

            install_dir = (
                Path(os.environ["LOCALAPPDATA"])
                / "Programs"
                / APP_NAME
            )
            install_dir.mkdir(parents=True, exist_ok=True)
            installed_exe = install_dir / f"{APP_NAME}.exe"
            shutil.copy2(source_exe, installed_exe)
            installed_uninstaller = install_dir / "Uninstall-D4CMic.ps1"
            shutil.copy2(source_uninstaller, installed_uninstaller)
            create_shortcuts(install_dir)
            self.results.put((True, str(installed_exe)))
        except Exception as error:
            self.results.put((False, str(error)))

    def _check_result(self):
        try:
            succeeded, detail = self.results.get_nowait()
        except queue.Empty:
            if self.root.winfo_exists():
                self.root.after(100, self._check_result)
            return

        self.progress.stop()
        self.is_installing = False
        if succeeded:
            self.status.set("Installed successfully · Desktop shortcut is ready")
            self.driver_warning.configure(
                text="In Discord, choose CABLE Output (VB-Audio Virtual Cable) "
                "as the input device.",
                foreground=ACCENT,
            )
            self.install_button.configure(text="Launch D4C Mic Boost V.2", state="normal")
            self.install_button.configure(
                command=lambda path=detail: self.launch_installed(path)
            )
        else:
            self.status.set("Installation failed")
            self.install_button.configure(state="normal")
            self.driver_warning.configure(
                text=detail,
                foreground="#ff697c",
            )

    def launch_installed(self, path):
        try:
            subprocess.Popen([path], cwd=str(Path(path).parent))
            self.root.destroy()
        except OSError as error:
            self.status.set(f"Could not launch the installed app: {error}")

    def close(self):
        if self.is_installing:
            self.status.set("Please wait for installation to finish")
            return
        self.root.destroy()


def main():
    root = tk.Tk()
    SetupWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
