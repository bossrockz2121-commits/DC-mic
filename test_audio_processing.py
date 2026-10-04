import unittest

import numpy as np

from mic_boost import (
    APP_TITLE,
    MAX_GAIN_DB,
    LIMITER_CEILING,
    LIMITER_THRESHOLD,
    STREAM_ATTEMPTS,
    VoiceProcessor,
    process_audio,
)


class ProcessAudioTests(unittest.TestCase):
    def test_release_name_and_version(self):
        self.assertEqual(APP_TITLE, "D4C Mic Boost V.2")

    def test_stream_prefers_low_latency_then_falls_back(self):
        self.assertEqual(STREAM_ATTEMPTS[0], (128, "low"))
        self.assertEqual(STREAM_ATTEMPTS[1], (256, "low"))
        self.assertEqual(STREAM_ATTEMPTS[2], (0, "low"))
        self.assertEqual(STREAM_ATTEMPTS[-1], (0, "high"))
        self.assertEqual(len(STREAM_ATTEMPTS), len(set(STREAM_ATTEMPTS)))

    def test_gain_increases_quiet_signal(self):
        source = np.full((4, 1), 0.1, dtype=np.float32)
        result = process_audio(source, 2.0)
        np.testing.assert_allclose(result, 0.2)

    def test_stereo_input_is_downmixed(self):
        source = np.array([[0.2, 0.4], [-0.2, 0.0]], dtype=np.float32)
        result = process_audio(source, 1.0)
        np.testing.assert_allclose(result, [0.3, -0.1])

    def test_limiter_keeps_peaks_below_full_scale(self):
        source = np.array([[1.0], [-1.0], [0.2]], dtype=np.float32)
        result = process_audio(source, 10.0)
        self.assertTrue(np.all(np.abs(result) <= 1.0))
        self.assertGreater(result[0], LIMITER_THRESHOLD)
        self.assertAlmostEqual(result[0], -result[1])

    def test_below_threshold_audio_is_not_limited(self):
        source = np.array([[0.2], [-0.2]], dtype=np.float32)
        result = process_audio(source, 1.0)
        np.testing.assert_allclose(result, [0.2, -0.2])

    def test_adaptive_leveling_lifts_quiet_voice(self):
        processor = VoiceProcessor(48000)
        source = np.full((480, 1), 0.01, dtype=np.float32)
        result = None
        for _ in range(100):
            result, input_rms, _, output_rms, _ = processor.process(source, 1.0)
        self.assertAlmostEqual(input_rms, 0.01, places=5)
        self.assertGreater(output_rms, 0.12)
        self.assertLess(output_rms, 0.2)
        self.assertTrue(np.all(np.abs(result) <= 1.0))

    def test_maximum_manual_gain_is_loud_and_limited(self):
        self.assertEqual(MAX_GAIN_DB, 48)
        processor = VoiceProcessor(48000)
        source = np.full((480, 1), 0.5, dtype=np.float32)
        result, _, _, _, output_peak = processor.process(source, 10 ** (48 / 20))
        self.assertLessEqual(output_peak, LIMITER_CEILING)
        self.assertGreater(output_peak, 0.9)
        self.assertLessEqual(float(np.max(np.abs(result))), LIMITER_CEILING)

    def test_stronger_presets_raise_speech_level_without_digital_clipping(self):
        rate = 48000
        source = (
            0.1
            * np.sin(2 * np.pi * 440 * np.arange(480, dtype=np.float32) / rate)
        ).astype(np.float32)[:, np.newaxis]

        def settled_output(gain_db):
            processor = VoiceProcessor(rate)
            output = None
            for _ in range(100):
                output, _, _, _, _ = processor.process(
                    source, 10 ** (gain_db / 20)
                )
            return output

        clear = settled_output(18)
        recommended = settled_output(30)
        maximum = settled_output(48)
        clear_rms = float(np.sqrt(np.mean(clear * clear)))
        recommended_rms = float(np.sqrt(np.mean(recommended * recommended)))
        maximum_rms = float(np.sqrt(np.mean(maximum * maximum)))
        self.assertLess(clear_rms, recommended_rms)
        self.assertLess(recommended_rms, maximum_rms)
        for signal in (clear, recommended, maximum):
            self.assertTrue(np.all(np.isfinite(signal)))
            self.assertLessEqual(float(np.max(np.abs(signal))), LIMITER_CEILING)

    def test_voice_processor_supports_stereo_input(self):
        processor = VoiceProcessor(48000)
        source = np.array([[0.2, 0.4], [-0.2, 0.0]], dtype=np.float32)
        result, input_rms, input_peak, _, output_peak = processor.process(source, 1.0)
        self.assertEqual(result.shape, (2,))
        self.assertGreater(input_rms, 0)
        self.assertAlmostEqual(input_peak, 0.3)
        self.assertGreater(output_peak, 0)


if __name__ == "__main__":
    unittest.main()
