#!/usr/bin/env python3
"""Capture the top-left scoreboard crop and log its raw OCR text. No serial I/O."""

import argparse
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import time
from datetime import datetime, timezone


def positive_seconds(value):
    try:
        seconds = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("interval must be a positive number") from error
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("interval must be a finite positive number")
    return seconds


def crop_rectangle(monitor, crop):
    if crop is None:
        # Start broad; narrow this to the scoreboard for better OCR accuracy.
        width = max(1, int(monitor["width"] * 0.35))
        height = max(1, int(monitor["height"] * 0.18))
        x, y = 0, 0
    else:
        x, y, width, height = crop
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ValueError("crop must be X>=0 Y>=0 WIDTH>0 HEIGHT>0")
    if x + width > monitor["width"] or y + height > monitor["height"]:
        raise ValueError("crop extends outside the selected monitor")
    return {"left": monitor["left"] + x, "top": monitor["top"] + y,
            "width": width, "height": height}


def read_crop(image):
    from PIL import ImageOps

    enhanced = ImageOps.autocontrast(ImageOps.grayscale(image))
    enhanced = enhanced.resize((enhanced.width * 2, enhanced.height * 2))
    data = io.BytesIO()
    enhanced.save(data, format="PNG")
    result = subprocess.run(
        ["tesseract", "stdin", "stdout", "--psm", "6"],
        input=data.getvalue(), capture_output=True, check=True,
    )
    return result.stdout.decode("utf-8", errors="replace").strip()


def sample(sct, rectangle, output_dir, save_all=False):
    from PIL import Image

    frame = sct.grab(rectangle)
    image = Image.frombytes("RGB", frame.size, frame.rgb)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    name = (datetime.now(timezone.utc).strftime("crop_%Y%m%dT%H%M%S_%fZ.png")
            if save_all else "latest.png")
    crop_path = output_dir / name
    image.save(crop_path)
    text = read_crop(image)
    return {"time": timestamp, "crop": str(crop_path), "ocr": text}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=positive_seconds, default=1.0,
                        help="seconds between captures (default: 1)")
    parser.add_argument("--monitor", type=int, default=1,
                        help="mss monitor index, starting at 1 (default: 1)")
    parser.add_argument("--crop", type=int, nargs=4, metavar=("X", "Y", "WIDTH", "HEIGHT"),
                        help="crop in pixels relative to selected monitor; default: top-left 35%% x 18%%")
    parser.add_argument("--output-dir", type=Path, default=Path("run/fifa-ocr"),
                        help="directory for crops and readings.jsonl (default: run/fifa-ocr)")
    parser.add_argument("--save-all", action="store_true",
                        help="save every crop instead of overwriting latest.png (can use much disk space)")
    parser.add_argument("--once", action="store_true", help="take one sample and exit")
    args = parser.parse_args()

    if shutil.which("tesseract") is None:
        parser.error("tesseract is required; use the project nix dev shell")
    try:
        import mss
        import PIL  # noqa: F401 - check dependency before entering capture loop
    except ImportError:
        parser.error("mss and Pillow are required; use the project nix dev shell")

    try:
        with mss.mss() as sct:
            if args.monitor < 1 or args.monitor >= len(sct.monitors):
                parser.error(f"monitor must be between 1 and {len(sct.monitors) - 1}")
            rectangle = crop_rectangle(sct.monitors[args.monitor], args.crop)
            args.output_dir.mkdir(parents=True, exist_ok=True)
            print(f"Capturing monitor {args.monitor} at {rectangle}; press Ctrl+C to stop", flush=True)
            with (args.output_dir / "readings.jsonl").open("a", encoding="utf-8") as log:
                next_sample = time.monotonic()
                while True:
                    entry = sample(sct, rectangle, args.output_dir, args.save_all)
                    line = json.dumps(entry, ensure_ascii=False)
                    print(line, flush=True)
                    log.write(line + "\n")
                    log.flush()
                    if args.once:
                        break
                    next_sample = max(next_sample + args.interval, time.monotonic())
                    time.sleep(max(0, next_sample - time.monotonic()))
    except ValueError as error:
        parser.error(str(error))
    except (subprocess.CalledProcessError, OSError) as error:
        parser.exit(1, f"capture/OCR failed: {error}\n")
    except KeyboardInterrupt:
        print("\nStopped")


if __name__ == "__main__":
    main()
