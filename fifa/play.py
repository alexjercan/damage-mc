#!/usr/bin/env python3
"""Monitor FIFA scores; optionally pulse the opposing Arduino channel after a goal."""

import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import signal
import shutil
import subprocess
import time

from score_ocr import crop_rectangle, positive_seconds, sample


class ScoreTracker:
    def __init__(self, confirmations=2):
        self.confirmations = confirmations
        self.pending = None
        self.count = 0
        self.baseline = None

    def observe(self, score):
        if score is None:
            self.pending = None
            self.count = 0
            return None
        current = tuple(score)
        if current == self.pending:
            self.count += 1
        else:
            self.pending, self.count = current, 1
        if self.count < self.confirmations or current == self.baseline:
            return None
        previous, self.baseline = self.baseline, current
        if previous is None:
            return None  # First stable reading establishes the match baseline.
        changes = [new - old for old, new in zip(previous, current)]
        return changes.index(1) if sorted(changes) == [0, 1] else None


def send_target(connection, channel, level):
    """Keep only one command outstanding; an ACK 0 means the target was reached."""
    for attempt in range(3):
        if connection.write(bytes((channel, level))) != 2:
            raise RuntimeError("incomplete serial write; physical level is unknown")
        connection.flush()
        ack = connection.read(1)
        if ack == b"\x00":
            return
        if ack == b"\x01":
            time.sleep(0.1)
            continue
        if not ack:
            raise RuntimeError("Arduino ACK timeout; physical level is unknown")
        raise RuntimeError(f"unexpected Arduino ACK {ack!r}; physical level is unknown")
    raise RuntimeError("Arduino rejected target three times; physical level is unknown")


def pulse_channel(connection, channel, level, pulse_ms, stopping=lambda: False):
    send_target(connection, channel, level)
    try:
        # Start the pulse only after the target is reached. Ctrl+C can shorten it.
        deadline = time.monotonic() + pulse_ms / 1000
        while not stopping() and time.monotonic() < deadline:
            time.sleep(min(0.1, deadline - time.monotonic()))
    finally:
        send_target(connection, channel, 0)


def pulse_milliseconds(value):
    try:
        milliseconds = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("pulse must be an integer number of milliseconds") from error
    if not 0 <= milliseconds <= 60000:
        raise argparse.ArgumentTypeError("pulse must be between 0 and 60000 ms")
    return milliseconds


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", nargs="?", help="Arduino serial port, e.g. /dev/ttyACM0 (omit with -n)")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="log OCR and confirmed goals without opening a serial port")
    parser.add_argument("--pulse", type=pulse_milliseconds, default=1000,
                        help="milliseconds at level after ACK (default: 1000)")
    parser.add_argument("--level", type=int, default=25,
                        help="target level after a goal (default: 25; range 1-50)")
    parser.add_argument("--top-channel", type=int, default=0,
                        help="top team device channel (default: 0=P1)")
    parser.add_argument("--bottom-channel", type=int, default=1,
                        help="bottom team device channel (default: 1=P2)")
    parser.add_argument("--interval", type=positive_seconds, default=0.5,
                        help="seconds between samples (default: 0.5)")
    parser.add_argument("--monitor", type=int, default=1)
    parser.add_argument("--crop", type=int, nargs=4, metavar=("X", "Y", "WIDTH", "HEIGHT"),
                        default=(0, 0, 600, 180), help="top-left HUD region (default: 0 0 600 180)")
    parser.add_argument("--score-crop", type=int, nargs=4, metavar=("X", "Y", "WIDTH", "HEIGHT"),
                        help="override automatic score detection with a manual score crop")
    parser.add_argument("--raw-ocr", action="store_true",
                        help="OCR whole crop as text (dry-run only; disables goal detection)")
    parser.add_argument("--once", action="store_true", help="capture once and exit (dry-run only)")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="directory for crops and readings.jsonl (default: run/fifa-play or run/fifa-ocr)")
    parser.add_argument("--save-all", action="store_true", help="save each capture, not just latest.png")
    args = parser.parse_args(argv)
    if args.dry_run:
        if args.port is not None:
            parser.error("omit the serial port with --dry-run")
    elif args.port is None:
        parser.error("a serial port is required unless --dry-run is set")
    if not args.dry_run and (args.once or args.raw_ocr):
        parser.error("--once and --raw-ocr require --dry-run")
    if args.raw_ocr and args.score_crop is not None:
        parser.error("--raw-ocr and --score-crop cannot be combined")
    if args.output_dir is None:
        args.output_dir = Path("run/fifa-ocr" if args.dry_run else "run/fifa-play")
    if not 1 <= args.level <= 50:
        parser.error("--level must be between 1 and 50")
    if sorted((args.top_channel, args.bottom_channel)) != [0, 1]:
        parser.error("top and bottom channels must be different and each be 0 or 1")
    if shutil.which("tesseract") is None:
        parser.error("tesseract is required; use the project nix dev shell")
    try:
        import mss
        import PIL  # noqa: F401 - required by sample()
    except ImportError:
        parser.error("mss and Pillow are required; use the project nix dev shell")
    if not args.dry_run:
        try:
            import serial
        except ImportError:
            parser.error("pyserial is required; use the project nix dev shell")
    tracker = ScoreTracker()
    stop = False

    def request_stop(_signum, _frame):
        nonlocal stop
        stop = True

    try:
        with mss.mss() as sct:
            if args.monitor < 1 or args.monitor >= len(sct.monitors):
                parser.error(f"monitor must be between 1 and {len(sct.monitors) - 1}")
            rectangle = crop_rectangle(sct.monitors[args.monitor], args.crop)
            if args.score_crop is not None:
                crop_rectangle({"left": 0, "top": 0, "width": rectangle["width"],
                                "height": rectangle["height"]}, args.score_crop)
                if args.score_crop[2] <= 6 or args.score_crop[3] <= 10:
                    parser.error("score crop must be wider than 6 and taller than 10 pixels")
            args.output_dir.mkdir(parents=True, exist_ok=True)
            # Dry-run never imports serial or opens the port.
            connection_context = (nullcontext(None) if args.dry_run else
                                  serial.Serial(args.port, baudrate=9600, timeout=10, write_timeout=2))
            with connection_context as connection:
                if not args.dry_run:
                    # Port opening commonly resets the board. Its physical level MUST be zero.
                    time.sleep(2)
                    print("Assuming both physical channels start at level 0. Press Ctrl+C to stop.", flush=True)
                else:
                    print(f"Dry run: capturing monitor {args.monitor} at {rectangle}; no serial I/O.", flush=True)
                previous_handler = signal.signal(signal.SIGINT, request_stop)
                try:
                    with (args.output_dir / "readings.jsonl").open("a", encoding="utf-8") as log:
                        while not stop:
                            started = time.monotonic()
                            entry = sample(sct, rectangle, args.output_dir, args.save_all,
                                           args.score_crop, args.raw_ocr)
                            scorer = tracker.observe(entry.get("score"))
                            entry["confirmed_score"] = list(tracker.baseline) if tracker.baseline else None
                            if scorer is not None:
                                channel = (args.bottom_channel, args.top_channel)[scorer]
                                entry["goal"] = {"scorer": "top" if scorer == 0 else "bottom",
                                                 "target_channel": channel, "level": args.level}
                            line = json.dumps(entry, ensure_ascii=False)
                            print(line, flush=True)
                            log.write(line + "\n")
                            log.flush()
                            if scorer is not None and not args.dry_run:
                                pulse_channel(connection, channel, args.level, args.pulse, lambda: stop)
                                print(f"P{channel + 1} returned to level 0", flush=True)
                            if args.once:
                                break
                            if not stop:
                                time.sleep(max(0, args.interval - (time.monotonic() - started)))
                finally:
                    signal.signal(signal.SIGINT, previous_handler)
    except (ValueError, subprocess.CalledProcessError, OSError, RuntimeError) as error:
        suffix = (" Check the device's physical level before reconnecting." if not args.dry_run else "")
        parser.exit(1, f"Stopped: {error}.{suffix}\n")


if __name__ == "__main__":
    main()
