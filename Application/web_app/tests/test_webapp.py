import json
from pathlib import Path
import sys
import unittest

APP = Path(__file__).resolve().parents[2]
WEB_APP = APP / "web_app"
sys.path.insert(0, str(WEB_APP))
sys.path.insert(0, str(APP))

from run_webapp import PredictionStabilizer, SETTINGS, draw_landmarks
from dual_isl_v1.pilot import PilotModel
from dual_isl_v1.sentences import compose_english


class WebAppModelTests(unittest.TestCase):
    def test_loads_existing_phase2_model_and_labels(self):
        model = PilotModel(APP / "phase2" / "pilot_model.npz")
        self.assertEqual(list(model.labels), SETTINGS["model_labels"])
        self.assertEqual(len(model.labels), 8)

    def test_settings_are_well_formed_and_match_real_labels(self):
        loaded = json.loads((WEB_APP / "settings.json").read_text(encoding="utf-8"))
        model = PilotModel(APP / "phase2" / "pilot_model.npz")
        self.assertEqual(tuple(loaded["model_labels"]), model.labels)
        self.assertEqual(loaded["camera_stream_url"], "http://192.168.0.105/stream")

    def test_prediction_stabilization_requires_matching_windows_and_threshold(self):
        stable = PredictionStabilizer(3, 0.25)
        self.assertFalse(stable.observe("HELLO", 0.5))
        self.assertFalse(stable.observe("HELLO", 0.5))
        self.assertTrue(stable.observe("HELLO", 0.5))
        stable.reset()
        self.assertFalse(stable.observe("GO", 0.5))
        self.assertFalse(stable.observe("GO", 0.1))
        self.assertFalse(stable.observe("GO", 0.5))
        stable.reset()
        stable.observe("GO", 0.5)
        stable.observe("HELLO", 0.5)
        self.assertFalse(stable.observe("GO", 0.5))

    def test_landmark_overlay_is_preview_only_and_handles_empty_results(self):
        import numpy as np
        from types import SimpleNamespace
        frame = np.zeros((32, 48, 3), dtype=np.uint8)
        original = frame.copy()
        result = SimpleNamespace(hand_landmarks=[], pose_landmarks=[])
        overlay = draw_landmarks(frame, result, result)
        self.assertTrue(np.array_equal(frame, original))
        self.assertTrue(np.array_equal(overlay, original))

    def test_landmark_overlay_draws_detected_hand_without_mutating_source(self):
        import numpy as np
        from types import SimpleNamespace
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        original = frame.copy()
        hand = [SimpleNamespace(x=.2 + i * .01, y=.3 + i * .01) for i in range(21)]
        result = SimpleNamespace(hand_landmarks=[hand], pose_landmarks=[])
        overlay = draw_landmarks(frame, result, result)
        self.assertTrue(np.array_equal(frame, original))
        self.assertGreater(int(overlay.sum()), 0)


class SentenceRuleTests(unittest.TestCase):
    def test_documented_sentence_examples(self):
        cases = {
            ("HELLO",): "Hello!",
            ("THANK_YOU",): "Thank you.",
            ("WHERE", "YOU", "GO"): "Where are you going?",
            ("YOU", "WHERE", "GO"): "Where are you going?",
            ("I", "TOMORROW", "SCHOOL", "GO"): "I will go to school tomorrow.",
        }
        for labels, expected in cases.items():
            with self.subTest(labels=labels):
                self.assertEqual(compose_english(list(labels)), expected)

    def test_unsupported_sequence_does_not_make_sentence(self):
        self.assertIsNone(compose_english(["GO", "HELLO", "SCHOOL"]))


if __name__ == "__main__":
    unittest.main()
