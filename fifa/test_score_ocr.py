import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from score_ocr import (crop_rectangle, find_digit_pairs, parse_score,
                           positive_seconds, sample, tesseract_command)


class FakeFrame:
    def __init__(self, size=(16, 8), image=None):
        image = image or Image.new("RGB", size, "black")
        self.size = image.size
        self.rgb = image.tobytes()


class FakeCapture:
    def __init__(self, size=(16, 8), image=None):
        self.rectangle = None
        self.size = size
        self.image = image

    def grab(self, rectangle):
        self.rectangle = rectangle
        return FakeFrame(self.size, self.image)


class ScoreOcrTests(unittest.TestCase):
    def test_bundle_uses_its_own_ocr_engine_and_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tesseract").touch()
            (root / "tessdata").mkdir()
            (root / "tessdata" / "eng.traineddata").touch()
            with patch("score_ocr.sys.frozen", True, create=True), \
                 patch("score_ocr.sys._MEIPASS", directory, create=True), \
                 patch("score_ocr.sys.platform", "linux"):
                executable, environment = tesseract_command()
                self.assertEqual(executable, str(root / "tesseract"))
                self.assertEqual(environment["TESSDATA_PREFIX"], str(root / "tessdata"))
                (root / "tesseract").unlink()
                with self.assertRaises(RuntimeError):
                    tesseract_command()

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

    def test_parse_score_rejects_non_score_text(self):
        self.assertEqual(parse_score("1\n2"), [1, 2])
        self.assertEqual(parse_score("10\n 3"), [10, 3])
        for text in ["", "1", "1\n", "1\n\n2", "83:20\n1", "1\n2\n3", "A\n1", "123\n1"]:
            with self.subTest(text=text):
                self.assertIsNone(parse_score(text))

    def test_sample_saves_crop_and_logs_raw_ocr_without_serial(self):
        with tempfile.TemporaryDirectory() as directory:
            capture = FakeCapture()
            rectangle = {"left": 0, "top": 0, "width": 16, "height": 8}
            with patch("score_ocr.read_crop", return_value="TEAM A 2 - 1 TEAM B"):
                result = sample(capture, rectangle, Path(directory), raw_ocr=True)
            self.assertEqual(capture.rectangle, rectangle)
            self.assertEqual(result["ocr"], "TEAM A 2 - 1 TEAM B")
            with Image.open(result["crop"]) as image:
                self.assertEqual(image.size, (16, 8))
            self.assertEqual(Path(result["crop"]).name, "latest.png")

    def test_auto_finds_moved_digits_and_rejects_unknown_image(self):
        from PIL import ImageDraw

        image = Image.new("RGB", (600, 180), "black")
        self.assertEqual(find_digit_pairs(image), [])
        with tempfile.TemporaryDirectory() as directory:
            with patch("score_ocr.read_crop") as reader:
                result = sample(FakeCapture(image=image), {"left": 0, "top": 0,
                                "width": 600, "height": 180}, Path(directory))
            self.assertIsNone(result["score"])
            self.assertIsNone(result["digit_boxes"])
            reader.assert_not_called()

        for x, y, gap in [(240, 65, 50), (275, 78, 28)]:
            with self.subTest(position=(x, y)):
                image = Image.new("RGB", (600, 180), "black")
                draw = ImageDraw.Draw(image)
                draw.rectangle((x - 12, y - 9, x + 20, y + gap + 34), fill="white")
                draw.rectangle((x, y, x + 7, y + 21), fill="black")
                draw.rectangle((x, y + gap, x + 7, y + gap + 21), fill="black")
                expected = ((x, y, x + 8, y + 22),
                            (x, y + gap, x + 8, y + gap + 22))
                self.assertIn(expected, find_digit_pairs(image))
                with tempfile.TemporaryDirectory() as directory:
                    with patch("score_ocr.read_crop", side_effect=["1", "3"]):
                        result = sample(FakeCapture(image=image), {"left": 0, "top": 0,
                                        "width": 600, "height": 180}, Path(directory))
                    self.assertEqual(result["score"], [1, 3])
                    self.assertEqual(result["digit_boxes"], [list(box) for box in expected])

    def test_sample_reads_only_score_region_when_configured(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("score_ocr.read_crop", side_effect=["1", "2"]) as reader:
                result = sample(FakeCapture((16, 24)), {"left": 0, "top": 0, "width": 16,
                                                       "height": 24}, Path(directory),
                                score_crop=(4, 2, 8, 20))
            self.assertEqual(result["score"], [1, 2])
            self.assertEqual(result["score_ocr"], "1\n2")
            self.assertNotIn("ocr", result)
            self.assertEqual([call.args[0].size for call in reader.call_args_list],
                             [(8, 6), (8, 6)])
            self.assertTrue(all(call.kwargs["score"] for call in reader.call_args_list))


if __name__ == "__main__":
    unittest.main()
