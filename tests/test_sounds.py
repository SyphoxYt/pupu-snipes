"""
Unit tests for the bundled snipe sound library and sound selection.
"""
import os
import tempfile
import unittest
import wave

from pupusnipe.core.sounds import (
    CUSTOM_SOUND_ID,
    SOUND_PRESETS,
    SYSTEM_BEEP_ID,
    SoundManager,
    build_sound,
    generate_sound_library,
    get_preset_file,
    get_preset_label,
)


class TestSoundLibrary(unittest.TestCase):
    def test_all_presets_generate_valid_wav_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            written = generate_sound_library(tmpdir, force=True)
            self.assertEqual(len(written), len(SOUND_PRESETS))
            for preset in SOUND_PRESETS:
                path = written[preset["id"]]
                self.assertTrue(os.path.isfile(path), preset["id"])
                with wave.open(path, "rb") as handle:
                    self.assertEqual(handle.getnchannels(), 1)
                    self.assertEqual(handle.getsampwidth(), 2)
                    self.assertEqual(handle.getframerate(), 44100)
                    frames = handle.readframes(handle.getnframes())
                    self.assertGreater(len(frames), 1000)
                    self.assertTrue(any(byte not in (0, 128, 255) for byte in frames[:2000]))

    def test_bundled_presets_are_present(self):
        for preset in SOUND_PRESETS:
            path = get_preset_file(preset["id"])
            self.assertTrue(path)
            self.assertTrue(os.path.isfile(path), f"Missing bundled sound: {preset['id']}")
            self.assertGreater(os.path.getsize(path), 44)

    def test_synthesis_is_deterministic_and_audible(self):
        first = build_sound("chime")
        second = build_sound("chime")
        self.assertEqual(first, second)
        self.assertGreater(max(abs(sample) for sample in first), 0.5)

    def test_labels_and_unknown_ids(self):
        self.assertIn("Chime", get_preset_label("chime"))
        self.assertIn("System Beep", get_preset_label(SYSTEM_BEEP_ID))
        self.assertIn("Custom", get_preset_label(CUSTOM_SOUND_ID))
        self.assertEqual(get_preset_label("does_not_exist"), "Unknown sound")
        self.assertIsNone(get_preset_file("does_not_exist"))


class TestSoundManager(unittest.TestCase):
    def test_custom_wav_resolution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "my_sound.wav")
            with open(path, "wb") as handle:
                handle.write(b"RIFF")
            manager = SoundManager(preset_id=CUSTOM_SOUND_ID, custom_path=path)
            self.assertEqual(manager.active_file(), path)
            self.assertIn("my_sound.wav", manager.describe())

    def test_missing_custom_wav_is_rejected(self):
        manager = SoundManager(preset_id=CUSTOM_SOUND_ID, custom_path="C:/definitely/missing.wav")
        self.assertIsNone(manager.active_file())
        self.assertIn("no file selected", manager.describe().lower())

    def test_bundled_preset_resolution(self):
        manager = SoundManager(preset_id="vine_boom")
        self.assertEqual(manager.active_file(), get_preset_file("vine_boom"))
        self.assertIn("Vine Boom", manager.describe())

    def test_selection_updates(self):
        manager = SoundManager()
        manager.set_selection(preset_id="rizz", custom_path="C:/sound.wav")
        self.assertEqual(manager.preset_id, "rizz")
        self.assertEqual(manager.custom_path, "C:/sound.wav")


if __name__ == "__main__":
    unittest.main()
