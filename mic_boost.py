import math
import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np
import sounddevice as sd


APP_TITLE = "D4C Mic Boost V.2"
SAMPLE_RATES = (48000, 44100, 32000)
STREAM_ATTEMPTS = (
    (128, "low"),
    (256, "low"),
    (0, "low"),
    (256, "high"),
    (0, "high"),
)
MAX_GAIN_DB = 48
DEFAULT_GAIN_DB = 24
LIMITER_THRESHOLD = 0.96
LIMITER_CEILING = 0.985
COMPRESSOR_THRESHOLD = 0.25
COMPRESSOR_RATIO = 3.0
LOUDNESS_TARGET = 0.13
MAX_AUTO_GAIN = 10 ** (24 / 20)
WASAPI = "windows wasapi"

COLORS = {
    "background": "#11141b",
    "surface": "#1a1f29",
    "surface_alt": "#222936",
    "border": "#303947",
    "text": "#f1f4f9",
    "muted": "#a1acbc",
    "accent": "#72e0bb",
    "accent_hover": "#96f0d1",
    "blue": "#87aaff",
    "yellow": "#ffca70",
    "red": "#ff697c",
    "meter_bg": "#303947",
}


def _limit_peaks(audio):
    magnitude = np.abs(audio)
    over = magnitude > LIMITER_THRESHOLD
    if np.any(over):
        excess = (magnitude[over] - LIMITER_THRESHOLD) / (
            LIMITER_CEILING - LIMITER_THRESHOLD
        )
        audio[over] = np.sign(audio[over]) * (
            LIMITER_THRESHOLD + (LIMITER_CEILING - LIMITER_THRESHOLD) * np.tanh(excess)
        )
    return audio


def process_audio(indata, gain):
    """Apply manual gain and a soft peak limiter."""
    mono = np.mean(indata, axis=1, dtype=np.float32) * gain
    return _limit_peaks(mono)


class VoiceProcessor:
    def __init__(self, sample_rate):
        self.sample_rate = sample_rate
        self.level_envelope = 0.0
        self.auto_gain = 1.0

    def process(self, indata, manual_gain):
        mono = np.mean(indata, axis=1, dtype=np.float32)
        input_rms = float(np.sqrt(np.mean(mono * mono)))
        input_peak = float(np.max(np.abs(mono), initial=0.0))

        block_time = len(mono) / self.sample_rate
        envelope_time = 0.035 if input_rms > self.level_envelope else 0.30
        envelope_alpha = 1.0 - math.exp(-block_time / envelope_time)
        self.level_envelope += envelope_alpha * (input_rms - self.level_envelope)

        if self.level_envelope > 1e-6:
            desired_auto_gain = min(
                MAX_AUTO_GAIN, LOUDNESS_TARGET / self.level_envelope
            )
        else:
            desired_auto_gain = MAX_AUTO_GAIN
        gain_time = 0.025 if desired_auto_gain < self.auto_gain else 0.30
        gain_alpha = 1.0 - math.exp(-block_time / gain_time)
        self.auto_gain += gain_alpha * (desired_auto_gain - self.auto_gain)

        audio = mono * (manual_gain * self.auto_gain)
        magnitude = np.abs(audio)
        compressed = magnitude > COMPRESSOR_THRESHOLD
        if np.any(compressed):
            audio[compressed] = np.sign(audio[compressed]) * (
                COMPRESSOR_THRESHOLD
                * np.power(
                    magnitude[compressed] / COMPRESSOR_THRESHOLD,
                    1.0 / COMPRESSOR_RATIO,
                )
            )
        _limit_peaks(audio)

        output_rms = float(np.sqrt(np.mean(audio * audio)))
        output_peak = float(np.max(np.abs(audio), initial=0.0))
        return audio, input_rms, input_peak, output_rms, output_peak


class MicBoostApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("780x1050")
        self.root.minsize(700, 1024)
        self.root.configure(background=COLORS["background"])

        self.devices = []
        self.stream = None
        self.processor = None
        self.gain = 10 ** (DEFAULT_GAIN_DB / 20)
        self.audio_warning = None
        self.status_poll = None
        self.meter_values = (0.0, 0.0, 0.0, 0.0)

        self.input_choice = tk.StringVar()
        self.output_choice = tk.StringVar()
        self.recommended_input = tk.StringVar(value="Searching for microphone…")
        self.recommended_output = tk.StringVar(value="Searching for virtual cable…")
        self.recommended_input_display = tk.StringVar(value="APP MIC  ·  Searching…")
        self.recommended_output_display = tk.StringVar(
            value="TO CABLE  ·  Searching…"
        )
        self.discord_recommendation = tk.StringVar(
            value="IN DISCORD  ·  Input Device = CABLE Output (VB-Audio Virtual Cable)"
        )
        self.gain_text = tk.StringVar(value=f"{DEFAULT_GAIN_DB} dB")
        self.status_text = tk.StringVar(value="READY  ·  Select devices, then start")
        self.input_db_text = tk.StringVar(value="— dB")
        self.output_db_text = tk.StringVar(value="— dB")

        self._configure_styles()
        self._build_ui()
        self.refresh_devices()
        self._poll_audio_status()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            ".",
            background=COLORS["background"],
            foreground=COLORS["text"],
            font=("Segoe UI", 10),
        )
        style.configure("App.TFrame", background=COLORS["background"])
        style.configure("Card.TFrame", background=COLORS["surface"])
        style.configure(
            "Title.TLabel",
            background=COLORS["background"],
            foreground=COLORS["text"],
            font=("Segoe UI Semibold", 25),
        )
        style.configure(
            "Subtitle.TLabel",
            background=COLORS["background"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["text"],
            font=("Segoe UI Semibold", 12),
        )
        style.configure(
            "Field.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "Value.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["accent"],
            font=("Segoe UI Semibold", 13),
        )
        style.configure(
            "Status.TLabel",
            background=COLORS["surface_alt"],
            foreground=COLORS["accent"],
            font=("Segoe UI Semibold", 10),
        )
        style.configure(
            "Hint.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "TCombobox",
            fieldbackground=COLORS["surface_alt"],
            background=COLORS["surface_alt"],
            foreground=COLORS["text"],
            arrowcolor=COLORS["accent"],
            padding=8,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", COLORS["surface_alt"])],
            foreground=[("readonly", COLORS["text"])],
            selectbackground=[("readonly", COLORS["surface_alt"])],
            selectforeground=[("readonly", COLORS["text"])],
        )
        style.configure(
            "TScale",
            background=COLORS["surface"],
            troughcolor=COLORS["surface_alt"],
            sliderlength=22,
        )
        style.configure(
            "Primary.TButton",
            background=COLORS["accent"],
            foreground=COLORS["background"],
            font=("Segoe UI Semibold", 11),
            padding=(20, 10),
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[("active", COLORS["accent_hover"]), ("disabled", COLORS["border"])],
            foreground=[("disabled", COLORS["muted"])],
        )
        style.configure(
            "Secondary.TButton",
            background=COLORS["surface_alt"],
            foreground=COLORS["text"],
            padding=(12, 9),
            borderwidth=0,
        )
        style.map(
            "Secondary.TButton",
            background=[("active", COLORS["border"]), ("disabled", COLORS["surface"])],
            foreground=[("disabled", COLORS["muted"])],
        )

    def _build_ui(self):
        outer = ttk.Frame(self.root, style="App.TFrame", padding=(30, 24))
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="App.TFrame")
        header.pack(fill="x", pady=(0, 20))
        title_row = ttk.Frame(header, style="App.TFrame")
        title_row.pack(anchor="w")
        ttk.Label(title_row, text="D4C MIC BOOST", style="Title.TLabel").pack(side="left")
        ttk.Label(
            title_row,
            text="V.2",
            background=COLORS["background"],
            foreground=COLORS["accent"],
            font=("Segoe UI Semibold", 12),
        ).pack(side="left", padx=(11, 0), pady=(10, 0))
        ttk.Label(
            header,
            text="Strong, consistent microphone audio for Discord",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        recommendation_card = self._card(outer, pady=(0, 14))
        recommendation_header = ttk.Frame(recommendation_card, style="Card.TFrame")
        recommendation_header.pack(fill="x")
        self.apply_recommendation_button = ttk.Button(
            recommendation_header,
            text="Apply recommendation",
            style="Secondary.TButton",
            command=self.apply_recommended_route,
        )
        ttk.Label(
            recommendation_header,
            text="RECOMMENDED ROUTE FOR THIS PC",
            style="CardTitle.TLabel",
        ).pack(side="left")
        ttk.Label(
            recommendation_card,
            textvariable=self.recommended_input_display,
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(10, 3))
        ttk.Label(
            recommendation_card,
            textvariable=self.recommended_output_display,
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(0, 3))
        ttk.Label(
            recommendation_card,
            textvariable=self.discord_recommendation,
            style="Value.TLabel",
        ).pack(anchor="w", pady=(6, 0))
        self.apply_recommendation_button.pack(side="right")
        device_card = self._card(outer)
        ttk.Label(device_card, text="AUDIO ROUTING", style="CardTitle.TLabel").pack(
            anchor="w", pady=(0, 14)
        )
        ttk.Label(device_card, text="MICROPHONE INPUT", style="Field.TLabel").pack(
            anchor="w", pady=(0, 5)
        )
        input_row = ttk.Frame(device_card, style="Card.TFrame")
        input_row.pack(fill="x", pady=(0, 13))
        self.input_menu = ttk.Combobox(
            input_row, textvariable=self.input_choice, state="readonly"
        )
        self.input_menu.pack(side="left", fill="x", expand=True)
        self.refresh_button = ttk.Button(
            input_row, text="Refresh", style="Secondary.TButton", command=self.refresh_devices
        )
        self.refresh_button.pack(side="left", padx=(9, 0))

        ttk.Label(device_card, text="VIRTUAL CABLE OUTPUT", style="Field.TLabel").pack(
            anchor="w", pady=(0, 5)
        )
        self.output_menu = ttk.Combobox(
            device_card, textvariable=self.output_choice, state="readonly"
        )
        self.output_menu.pack(fill="x")
        ttk.Label(
            device_card,
            text="Use CABLE Input here; select CABLE Output as your microphone in Discord.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(9, 0))

        gain_card = self._card(outer, pady=(14, 0))
        gain_header = ttk.Frame(gain_card, style="Card.TFrame")
        gain_header.pack(fill="x")
        ttk.Label(gain_header, text="VOICE BOOST", style="CardTitle.TLabel").pack(
            side="left"
        )
        ttk.Label(gain_header, textvariable=self.gain_text, style="Value.TLabel").pack(
            side="right"
        )
        self.gain_slider = ttk.Scale(
            gain_card,
            from_=0,
            to=MAX_GAIN_DB,
            command=self._set_gain,
        )
        self.gain_slider.set(DEFAULT_GAIN_DB)
        self.gain_slider.pack(fill="x", pady=(12, 5))
        tick_labels = ttk.Frame(gain_card, style="Card.TFrame")
        tick_labels.pack(fill="x")
        for text in ("0 dB", "16 dB", "32 dB", "48 dB MAX"):
            ttk.Label(tick_labels, text=text, style="Field.TLabel").pack(side="left", expand=True)
        presets = ttk.Frame(gain_card, style="Card.TFrame")
        presets.pack(fill="x", pady=(14, 0))
        ttk.Label(presets, text="QUICK SET", style="Field.TLabel").pack(
            side="left", padx=(0, 9)
        )
        for text, gain in (
            ("Clear 18", 18),
            ("Recommended 30", 30),
            ("Strong 42", 42),
            ("Maximum 48", 48),
        ):
            ttk.Button(
                presets,
                text=text,
                style="Secondary.TButton",
                command=lambda value=gain: self.gain_slider.set(value),
            ).pack(side="left", padx=(0, 7))
        ttk.Label(
            gain_card,
            text="Up to +24 dB auto leveling  ·  compression  ·  peak protection",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(11, 0))
        ttk.Label(
            gain_card,
            text="Digital level is peak-limited. More dB can add noise or harshness.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        meter_card = self._card(outer, pady=(14, 0))
        meter_header = ttk.Frame(meter_card, style="Card.TFrame")
        meter_header.pack(fill="x", pady=(0, 10))
        ttk.Label(meter_header, text="LIVE LEVELS", style="CardTitle.TLabel").pack(
            side="left"
        )
        self.clip_indicator = ttk.Label(
            meter_header, text="●  READY", style="Field.TLabel"
        )
        self.clip_indicator.pack(side="right")
        self._create_meter(meter_card, "MIC INPUT · AVG", self.input_db_text)
        self._create_meter(meter_card, "DISCORD OUTPUT · AVG", self.output_db_text)

        controls = ttk.Frame(outer, style="App.TFrame")
        controls.pack(fill="x", pady=(16, 0))
        self.start_button = ttk.Button(
            controls, text="▶   START BOOST", style="Primary.TButton", command=self.start
        )
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(
            controls, text="■   STOP", style="Secondary.TButton", command=self.stop, state="disabled"
        )
        self.stop_button.pack(side="left", padx=(9, 0))
        status_bar = ttk.Frame(outer, style="Card.TFrame", padding=(12, 9))
        status_bar.pack(fill="x", pady=(13, 0))
        ttk.Label(status_bar, textvariable=self.status_text, style="Status.TLabel").pack(
            anchor="w"
        )

    def _card(self, parent, pady=(0, 0)):
        card = ttk.Frame(
            parent,
            style="Card.TFrame",
            padding=(18, 15),
        )
        card.pack(fill="x", pady=pady)
        return card

    def _create_meter(self, parent, title, value_text):
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=(0, 9))
        heading = ttk.Frame(row, style="Card.TFrame")
        heading.pack(fill="x", pady=(0, 5))
        ttk.Label(heading, text=title, style="Field.TLabel").pack(side="left")
        ttk.Label(heading, text="PEAK", style="Field.TLabel").pack(side="right", padx=(0, 5))
        ttk.Label(heading, textvariable=value_text, style="Field.TLabel").pack(side="right")
        meter = tk.Canvas(
            row,
            height=14,
            background=COLORS["meter_bg"],
            highlightthickness=0,
            bd=0,
        )
        meter.pack(fill="x")
        meter.bind("<Configure>", lambda event, canvas=meter: self._draw_meter(canvas, 0.0))
        if not hasattr(self, "meter_canvases"):
            self.meter_canvases = []
        self.meter_canvases.append(meter)

    def _draw_meter(self, canvas, level):
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1:
            return
        canvas.delete("all")
        canvas.create_rectangle(0, 0, width, height, fill=COLORS["meter_bg"], outline="")
        fraction = min(1.0, max(0.0, level))
        if fraction:
            end = int(width * fraction)
            if end:
                color = COLORS["accent"] if fraction < 10 ** (-12 / 20) else COLORS["yellow"]
                if fraction >= 10 ** (-6 / 20):
                    color = COLORS["red"]
                canvas.create_rectangle(0, 0, end, height, fill=color, outline="")
        for db in (-48, -36, -24, -12, -6):
            x = int(width * (10 ** (db / 20)))
            canvas.create_line(x, 0, x, height, fill=COLORS["background"], width=1)

    @staticmethod
    def _db_text(level):
        if level <= 1e-6:
            return "−∞ dB"
        return f"{20 * math.log10(level):.0f} dB"

    @staticmethod
    def _meter_fraction(level):
        if level <= 1e-6:
            return 0.0
        return (20 * math.log10(level) + 60) / 60

    def _set_gain(self, value):
        gain_db = int(round(float(value)))
        self.gain = 10 ** (gain_db / 20)
        self.gain_text.set(f"{gain_db} dB")

    def _select_default(self, devices, preferred_index, preferred_name):
        if not devices:
            return ""
        preferred = next(
            (label for label, _ in devices if preferred_name in label.lower()), None
        )
        if preferred:
            return preferred
        preferred = next(
            (label for label, _ in devices if WASAPI in label.lower()), None
        )
        if preferred:
            return preferred
        preferred = next(
            (label for label, index in devices if index == preferred_index), None
        )
        if preferred:
            return preferred
        return preferred or devices[0][0]

    def apply_recommended_route(self):
        self.input_choice.set(self.recommended_input.get())
        self.output_choice.set(self.recommended_output.get())
        self.status_text.set("RECOMMENDED ROUTE APPLIED  ·  Verify Discord uses CABLE Output")

    def refresh_devices(self):
        try:
            self.devices = sd.query_devices()
            inputs = []
            outputs = []
            default_input, default_output = sd.default.device
            for index, device in enumerate(self.devices):
                host = sd.query_hostapis(device["hostapi"])["name"]
                label = f"{index}: {device['name']}  ·  {host}"
                lower_name = device["name"].lower()
                is_cable_loopback = (
                    "cable output" in lower_name or "vb-audio point" in lower_name
                )
                if device["max_input_channels"] > 0 and not is_cable_loopback:
                    inputs.append((label, index))
                if device["max_output_channels"] > 0:
                    outputs.append((label, index))

            inputs.sort(key=lambda item: WASAPI not in item[0].lower())
            outputs.sort(key=lambda item: WASAPI not in item[0].lower())
            self.input_menu["values"] = [item[0] for item in inputs]
            self.output_menu["values"] = [item[0] for item in outputs]
            recommended_input = self._select_default(
                inputs, default_input, "microphone"
            )
            recommended_output = self._select_default(
                outputs, default_output, "cable input"
            )
            self.recommended_input.set(recommended_input or "No physical microphone detected")
            self.recommended_output.set(
                recommended_output or "No virtual cable output detected"
            )
            self.recommended_input_display.set(
                f"APP MIC  ·  {recommended_input or 'No physical microphone detected'}"
            )
            self.recommended_output_display.set(
                f"TO CABLE  ·  {recommended_output or 'No virtual cable output detected'}"
            )
            self.input_choice.set(recommended_input)
            self.output_choice.set(recommended_output)
            if not outputs or "cable input" not in self.output_choice.get().lower():
                self.status_text.set(
                    f"Found {len(inputs)} mic(s), {len(outputs)} output(s). Install a virtual cable."
                )
            else:
                self.status_text.set(
                    f"READY  ·  {len(inputs)} input(s) and virtual cable detected"
                )
        except Exception as error:
            self.status_text.set("Device scan failed")
            messagebox.showerror("Could not scan audio devices", str(error), parent=self.root)

    def _selected_index(self, label):
        try:
            return int(label.split(":", 1)[0])
        except (ValueError, AttributeError):
            raise ValueError("Select both a microphone input and a virtual cable output.")

    def start(self):
        if self.stream is not None:
            return
        stream = None
        try:
            input_index = self._selected_index(self.input_choice.get())
            output_index = self._selected_index(self.output_choice.get())
            if "cable input" not in self.output_choice.get().lower():
                raise ValueError(
                    "Choose the VB-Audio CABLE Input virtual device for the output. "
                    "Do not choose your speakers."
                )
            if any(
                token in self.input_choice.get().lower()
                for token in ("cable output", "vb-audio point", "stereo mix")
            ):
                raise ValueError(
                    "Choose your physical headset or microphone as the input, "
                    "not a cable or loopback device."
                )
            output_device = self.devices[output_index]
            output_channels = min(2, int(output_device["max_output_channels"]))
            sample_rate = None
            for candidate in SAMPLE_RATES:
                try:
                    sd.check_input_settings(
                        device=input_index, channels=1, samplerate=candidate
                    )
                    sd.check_output_settings(
                        device=output_index,
                        channels=output_channels,
                        samplerate=candidate,
                    )
                    sample_rate = candidate
                    break
                except sd.PortAudioError:
                    continue
            if sample_rate is None:
                raise RuntimeError(
                    "The selected devices do not share a supported sample rate "
                    "(48, 44.1, or 32 kHz)."
                )

            self.processor = VoiceProcessor(sample_rate)

            def audio_callback(indata, outdata, frames, time_info, status):
                if status:
                    self.audio_warning = str(status)
                audio, input_rms, input_peak, output_rms, output_peak = (
                    self.processor.process(indata, self.gain)
                )
                self.meter_values = (input_rms, input_peak, output_rms, output_peak)
                outdata[:] = audio[:, np.newaxis]

            stream_config = None
            last_stream_error = None
            for blocksize, latency in STREAM_ATTEMPTS:
                try:
                    stream = sd.Stream(
                        device=(input_index, output_index),
                        samplerate=sample_rate,
                        channels=(1, output_channels),
                        dtype="float32",
                        blocksize=blocksize,
                        latency=latency,
                        callback=audio_callback,
                    )
                    stream.start()
                    stream_config = (blocksize, latency)
                    break
                except sd.PortAudioError as latency_error:
                    last_stream_error = latency_error
                    if stream is not None:
                        try:
                            stream.close()
                        except sd.PortAudioError as cleanup_error:
                            raise RuntimeError(
                                f"{latency_error}; failed to close low-latency "
                                f"stream: {cleanup_error}"
                            ) from cleanup_error
                        stream = None
            if stream is None:
                raise RuntimeError(
                    "Could not start the mic stream with any supported "
                    f"low-latency buffer: {last_stream_error}"
                )
            self.stream = stream
            blocksize, latency = stream_config
            if blocksize:
                buffer_label = f"{blocksize}-frame buffer (~{blocksize / sample_rate * 1000:.1f} ms)"
            else:
                buffer_label = "device buffer"
            self.status_text.set(
                f"BOOST ACTIVE  ·  {sample_rate // 1000} kHz  ·  "
                f"{latency} latency  ·  {buffer_label}"
            )
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.input_menu.configure(state="disabled")
            self.output_menu.configure(state="disabled")
            self.refresh_button.configure(state="disabled")
            self.apply_recommendation_button.configure(state="disabled")
        except Exception as error:
            if stream is not None:
                try:
                    stream.close()
                except sd.PortAudioError as cleanup_error:
                    error = RuntimeError(f"{error}; stream cleanup failed: {cleanup_error}")
            self.stream = None
            messagebox.showerror("Could not start microphone", str(error), parent=self.root)

    def _poll_audio_status(self):
        if hasattr(self, "meter_canvases"):
            input_rms, input_peak, output_rms, output_peak = self.meter_values
            self.input_db_text.set(self._db_text(input_peak))
            self.output_db_text.set(self._db_text(output_peak))
            self._draw_meter(self.meter_canvases[0], self._meter_fraction(input_rms))
            self._draw_meter(self.meter_canvases[1], self._meter_fraction(output_rms))
            if self.stream is None:
                self.clip_indicator.configure(text="●  READY", foreground=COLORS["muted"])
            elif output_peak >= 0.95:
                self.clip_indicator.configure(
                    text="●  LIMITER ACTIVE", foreground=COLORS["yellow"]
                )
            else:
                self.clip_indicator.configure(text="●  CLEAN", foreground=COLORS["accent"])

        if self.audio_warning and self.stream is not None:
            self.status_text.set(f"AUDIO WARNING  ·  {self.audio_warning}")
            self.audio_warning = None
        self.status_poll = self.root.after(80, self._poll_audio_status)

    def stop(self):
        errors = []
        if self.stream is not None:
            stream, self.stream = self.stream, None
            try:
                stream.stop()
            except sd.PortAudioError as error:
                errors.append(str(error))
            try:
                stream.close()
            except sd.PortAudioError as error:
                errors.append(str(error))
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.input_menu.configure(state="readonly")
        self.output_menu.configure(state="readonly")
        self.refresh_button.configure(state="normal")
        self.apply_recommendation_button.configure(state="normal")
        self.processor = None
        self.meter_values = (0.0, 0.0, 0.0, 0.0)
        self.status_text.set("STOPPED  ·  Set Discord input to CABLE Output")
        if errors:
            messagebox.showerror("Audio stream", "\n".join(errors), parent=self.root)

    def close(self):
        self.stop()
        if self.status_poll is not None:
            self.root.after_cancel(self.status_poll)
        self.root.destroy()


def main():
    root = tk.Tk()
    MicBoostApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
