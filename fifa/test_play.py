import io
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

from play import ScoreTracker, main, pulse_channel, pulse_milliseconds, send_target


class FakeSerial:
    def __init__(self, acks):
        self.acks = iter(acks)
        self.writes = []

    def write(self, payload):
        self.writes.append(payload)
        return len(payload)

    def flush(self):
        pass

    def read(self, size):
        assert size == 1
        return next(self.acks)


class PlayTests(unittest.TestCase):
    def test_confirmed_goal_and_no_duplicate_or_spurious_action(self):
        tracker = ScoreTracker()
        readings = [[0, 0], [0, 0], [0, 0], None, [1, 0], [1, 0], [1, 0],
                    [1, 1], [1, 1], [3, 1], [3, 1], [0, 0], [0, 0],
                    [0, 1], None, [0, 1], [0, 1]]
        events = [tracker.observe(reading) for reading in readings]
        self.assertEqual([(index, event) for index, event in enumerate(events)
                          if event is not None], [(5, 0), (8, 1), (16, 1)])
        self.assertEqual(tracker.baseline, (0, 1))

    def test_transient_ocr_is_not_a_goal(self):
        tracker = ScoreTracker()
        for reading in ([1, 1], [1, 1], [2, 1], None, [1, 1], [1, 1]):
            self.assertIsNone(tracker.observe(reading))

    def test_pulse_waits_for_ack_and_returns_to_zero(self):
        connection = FakeSerial([b"\x00", b"\x00"])
        def check_hold(seconds):
            self.assertEqual(connection.writes, [bytes((1, 25))])
            self.assertLessEqual(seconds, 0.1)
        with patch("play.time.sleep", side_effect=check_hold):
            with patch("play.time.monotonic", side_effect=[0, 0, 0.02, 1]):
                pulse_channel(connection, 1, 25, 1000)
        self.assertEqual(connection.writes, [bytes((1, 25)), bytes((1, 0))])

    def test_interrupted_hold_still_returns_to_zero(self):
        connection = FakeSerial([b"\x00", b"\x00"])
        with patch("play.time.sleep", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                pulse_channel(connection, 0, 25, 1000)
        self.assertEqual(connection.writes, [bytes((0, 25)), bytes((0, 0))])

    def test_reject_retries_and_timeout_stops(self):
        connection = FakeSerial([b"\x01", b"\x00"])
        with patch("play.time.sleep"):
            send_target(connection, 0, 25)
        self.assertEqual(connection.writes, [b"\x00\x19", b"\x00\x19"])
        for ack in (b"", b"\x02"):
            with self.subTest(ack=ack), self.assertRaises(RuntimeError):
                send_target(FakeSerial([ack]), 0, 25)
        with patch("play.time.sleep"):
            with self.assertRaises(RuntimeError):
                send_target(FakeSerial([b"\x01"] * 3), 0, 25)

    def test_dry_run_never_imports_serial_or_sends_targets(self):
        class FakeCapture:
            monitors = [None, {"left": 0, "top": 0, "width": 800, "height": 600}]

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                pass

        with tempfile.TemporaryDirectory() as directory:
            fake_mss = types.SimpleNamespace(mss=FakeCapture)
            entry = {"score": [0, 0], "score_ocr": "0\\n0"}
            with patch.dict(sys.modules, {"mss": fake_mss, "serial": None}):
                with patch("play.shutil.which", return_value="tesseract"):
                    with patch("play.sample", return_value=entry) as sampled:
                        with patch("play.pulse_channel") as pulse:
                            with redirect_stdout(io.StringIO()):
                                main(["-n", "--once", "--output-dir", directory])
            self.assertEqual(sampled.call_count, 1)
            pulse.assert_not_called()

    def test_port_required_only_for_live_mode(self):
        for argv in ([], ["--dry-run", "/dev/ttyUSB0"], ["--once", "/dev/ttyUSB0"],
                     ["--raw-ocr", "/dev/ttyUSB0"]):
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(argv)
                self.assertEqual(raised.exception.code, 2)

    def test_pulse_milliseconds_validation(self):
        self.assertEqual(pulse_milliseconds("2500"), 2500)
        for value in ("-1", "60001", "abc"):
            with self.subTest(value=value), self.assertRaises(Exception):
                pulse_milliseconds(value)


if __name__ == "__main__":
    unittest.main()
