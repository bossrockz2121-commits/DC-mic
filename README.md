# D4C Mic Boost V.2

A Windows desktop microphone processor with live input/output level meters,
adjustable gain, adaptive voice leveling, compression, and a soft peak limiter.
Audio is processed locally; the app does not record or transmit it.

## Recommended route on this PC

1. Start `D4C Mic Boost V.2.exe`.
2. Click **Apply recommendation**. The best available route detected here is:
   - App microphone input: **Microphone (BH900 PRO) · Windows WASAPI**
   - App virtual-cable output: **CABLE Input (VB-Audio Virtual Cable) · Windows WASAPI**
3. Speak close to the headset microphone. Watch **MIC INPUT** and choose
   **Recommended 30** to begin; use **Strong 42** if the Discord output meter
   remains quiet.
4. Click **START BOOST**.
5. In Discord > **User Settings > Voice & Video**, select
   **CABLE Output (VB-Audio Virtual Cable)** as **Input Device**. Set input
   volume to 100%. Turn off automatic input sensitivity or automatic gain
   control only if it lowers the processed voice; verify with Discord's mic
   test.

The audio path must be:

```text
Microphone (BH900 PRO) -> D4C Mic Boost -> CABLE Input
    -> Discord Input Device: CABLE Output
```

The app needs an installed virtual-cable driver such as VB-Audio Virtual Cable;
the driver is separate from this executable. Selecting the physical headset
directly as Discord input bypasses D4C Mic Boost.

## Gain, plugins and limits

Manual gain is capped at +48 dB; automatic leveling adds up to +24 dB. Voice
compression and the output limiter make quiet speech stronger while keeping the
digital output below the limiter ceiling. **100 dB of software gain is not
possible**: dB SPL measures physical sound pressure, not digital gain. Digital
audio has a hard full-scale limit; pushing beyond it causes clipping, not a
cleaner or reliably louder Discord signal. More gain also boosts room noise.
Use **Maximum 48** sparingly.
If the limiter remains active or the voice sounds harsh, reduce gain. If the
input meter is already near 0 dB, lower the Windows hardware mic level to avoid
distortion before the audio reaches the app.

The first stream attempt uses a 128-frame WASAPI buffer (about 2.7 ms at 48 kHz)
for low monitoring delay. Larger/automatic buffers are tried if the audio device
cannot sustain it; smaller buffers are not always faster in practice if they
cause dropouts.

The 98 DLLs in the supplied `APO-PLUGINS-main` folder are third-party audio
plug-ins for a compatible VST/Equalizer APO host, not microphone drivers. This
app has no VST host, so it deliberately does not load or bundle these unverified
binaries. Loading every effect together is not a usable voice chain: reverb,
chorus, stereo effects and distortion can make speech less intelligible and
add CPU load/latency. D4C uses its tested, built-in low-latency voice processor.

## Build

Requires Python 3.11 and Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --name "D4C Mic Boost V.2" --distpath .\dist-fastest --workpath .\build-fastest mic_boost.py
```

The low-latency executable is written to `dist-fastest\D4C Mic Boost V.2.exe`.

## Shareable per-user setup

Build a standalone setup executable that installs under the current Windows
user's `%LOCALAPPDATA%`, creates Desktop and Start Menu shortcuts, and includes
an uninstaller:

```powershell
.\build_setup.ps1
```

Output: `dist-share\D4C Mic Boost V.2 Setup.exe`. The setup window offers
**Launch** after installation. Share this package using OneDrive, Google Drive
or another file-sharing service; a link to a local
`C:\Users\...` file cannot be downloaded by friends. Recipients need to install
VB-Audio Virtual Cable separately and choose **CABLE Output** in Discord.
Uninstall from **Start > D4C Mic Boost V.2 > Uninstall D4C Mic Boost V.2**.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest
```
