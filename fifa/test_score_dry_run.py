import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from score_dry_run import crop_rectangle, positive_seconds, sample


class FakeFrame:
    def __init__(self):
        image = Image.new("RGB", (16, 8), "black")
        self.size = image.size
        self.rgb = image.tobytes()


class FakeCapture:
    def __init__(self):
        self.rectangle = None

    def grab(self, rectangle):
        self.rectangle = rectangle
        return FakeFrame()


class ScoreDryRunTests(unittest.TestCase):
    def test_crop_uses_monitor_origin_and_validates_bounds(self):
        monitor = {"left": 1920, "top": -100, "width": 1000, "height": 500}
        self.assertEqual(crop_rectangle(monitor, (10, 20, 200, 80)),
                         {"left": 1930, "top": -80, "width": 200, "height": 80})
        self.assertEqual(crop_rectangle(monitor, None)["width"], 350)
        for crop in [(-1, 0, 10, 10), (0, 0, 0, 10), (990, 0, 20, 10)]:
            with self.subTest(crop=crop), self.assertRaises(ValueError):
                crop_rectangle(monitor, crop)

    def test_interval_must_be_positive_and_finite(self):
        self.assertEqual(positive_seconds("0.5"), 0.5)
        for value in ["0", "-1", "nan", "inf", "not-a-number"]:
            with self.subTest(value=value), self.assertRaises(Exception):
                positive_seconds(value)

    def test_sample_saves_crop_and_logs_raw_ocr_without_serial(self):
        with tempfile.TemporaryDirectory() as directory:
            capture = FakeCapture()
            rectangle = {"left": 0, "top": 0, "width": 16, "height": 8}
            with patch("score_dry_run.read_crop", return_value="TEAM A 2 - 1 TEAM B"):
                result = sample(capture, rectangle, Path(directory))
            self.assertEqual(capture.rectangle, rectangle)
            self.assertEqual(result["ocr"], "TEAM A 2 - 1 TEAM B")
            with Image.open(result["crop"]) as image:
                self.assertEqual(image.size, (16, 8))
            self.assertEqual(Path(result["crop"]).name, "latest.png")


if __name__ == "__main__":
    unittest.main()
