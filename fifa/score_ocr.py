#!/usr/bin/env python3
"""Capture the top-left HUD and log tentative scores. No serial I/O."""

import argparse
import io
import json
import math
import re
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


def read_crop(image, score=False):
    from PIL import ImageOps

    if score:
        # Ignore the panel border and use the high-contrast black-on-white digit.
        image = image.crop((3, 2, image.width - 3, image.height - 2))
        enhanced = ImageOps.grayscale(image).point(lambda value: 255 if value > 170 else 0)
    else:
        enhanced = ImageOps.autocontrast(ImageOps.grayscale(image))
    scale = 4 if score else 2
    enhanced = enhanced.resize((enhanced.width * scale, enhanced.height * scale))
    data = io.BytesIO()
    enhanced.save(data, format="PNG")
    command = ["tesseract", "stdin", "stdout", "--psm", "10" if score else "6"]
    if score:
        command.extend(["-c", "tessedit_char_whitelist=0123456789"])
    result = subprocess.run(command, input=data.getvalue(), capture_output=True, check=True)
    return result.stdout.decode("utf-8", errors="replace").strip()


def parse_score(text):
    if not re.fullmatch(r"[0-9]{1,2}[ \t]*\n[ \t]*[0-9]{1,2}", text):
        return None
    return [int(value.strip()) for value in text.splitlines()]


def find_digit_pairs(image):
    """Find vertically aligned dark glyphs inside bright HUD panels.

    Search a broad upper-left region. This does not depend on a team name,
    panel width, or an exact score position. OCR must still validate the pair.
    """
    pixels = image.convert("RGB").load()
    left, right = int(image.width * .25), min(image.width, int(image.width * .65))
    top, bottom = int(image.height * .25), min(image.height, int(image.height * .97))
    seen = set()
    glyphs = []

    def white(x, y):
        if not (0 <= x < image.width and 0 <= y < image.height):
            return False
        red, green, blue = pixels[x, y]
        return min(red, green, blue) > 205 and max(red, green, blue) - min(red, green, blue) < 55

    for y in range(top, bottom):
        for x in range(left, right):
            if (x, y) in seen or max(pixels[x, y]) > 145:
                continue
            seen.add((x, y))
            queue = [(x, y)]
            points = []
            while queue:
                current_x, current_y = queue.pop()
                points.append((current_x, current_y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    next_x, next_y = current_x + dx, current_y + dy
                    if (left <= next_x < right and top <= next_y < bottom and
                            (next_x, next_y) not in seen and
                            max(pixels[next_x, next_y]) <= 145):
                        seen.add((next_x, next_y))
                        queue.append((next_x, next_y))
            x1 = min(point[0] for point in points)
            y1 = min(point[1] for point in points)
            x2 = max(point[0] for point in points) + 1
            y2 = max(point[1] for point in points) + 1
            if not (4 <= x2 - x1 <= 25 and 12 <= y2 - y1 <= 36 and len(points) > 20):
                continue
            if sum(white(x1 - 4, row) and white(x2 + 4, row)
                   for row in range(y1, y2)) < .65 * (y2 - y1):
                continue
            glyphs.append((x1, y1, x2, y2))

    pairs = [(upper, lower) for upper in glyphs for lower in glyphs
             if 6 <= lower[1] - upper[3] <= 55 and
             abs(upper[0] + upper[2] - lower[0] - lower[2]) <= 16]
    # The score is normally to the right of the team names and match clock.
    return sorted(pairs, key=lambda pair: pair[0][0] + pair[1][0], reverse=True)


def read_digit(image, box):
    x1, y1, x2, y2 = box
    return read_crop(image.crop((x1 - 8, y1 - 6, x2 + 8, y2 + 2)), score=True)


def sample(sct, rectangle, output_dir, save_all=False, score_crop=None, raw_ocr=False):
    from PIL import Image

    frame = sct.grab(rectangle)
    image = Image.frombytes("RGB", frame.size, frame.rgb)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    name = (datetime.now(timezone.utc).strftime("crop_%Y%m%dT%H%M%S_%fZ.png")
            if save_all else "latest.png")
    crop_path = output_dir / name
    image.save(crop_path)
    entry = {"time": timestamp, "crop": str(crop_path)}
    if raw_ocr:
        entry["ocr"] = read_crop(image)
    else:
        entry["score_ocr"] = ""
        entry["score"] = None
        entry["digit_boxes"] = None
        if score_crop is None:
            for upper, lower in find_digit_pairs(image):
                text = read_digit(image, upper) + "\n" + read_digit(image, lower)
                if parse_score(text) is not None:
                    entry["score_ocr"] = text
                    entry["score"] = parse_score(text)
                    entry["digit_boxes"] = [list(upper), list(lower)]
                    break
        else:
            x, y, width, height = score_crop
            region = image.crop((x, y, x + width, y + height))
            midpoint = height // 2
            upper = region.crop((0, 0, width, midpoint - 4))
            lower = region.crop((0, midpoint + 4, width, height))
            entry["score_ocr"] = read_crop(upper, score=True) + "\n" + read_crop(lower, score=True)
            entry["score"] = parse_score(entry["score_ocr"])
            entry["digit_boxes"] = None
        # This is only an OCR candidate, not a verified goal or a relay command.
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=positive_seconds, default=1.0,
                        help="seconds between captures (default: 1)")
    parser.add_argument("--monitor", type=int, default=1,
                        help="mss monitor index, starting at 1 (default: 1)")
    parser.add_argument("--crop", type=int, nargs=4, metavar=("X", "Y", "WIDTH", "HEIGHT"),
                        help="crop in pixels relative to selected monitor; default: top-left 35%% x 18%%")
    parser.add_argument("--score-crop", type=int, nargs=4, metavar=("X", "Y", "WIDTH", "HEIGHT"),
                        help="override automatic digit detection with a manual score crop")
    parser.add_argument("--raw-ocr", action="store_true",
                        help="OCR the whole captured image as text instead of detecting a score")
    parser.add_argument("--output-dir", type=Path, default=Path("run/fifa-ocr"),
                        help="directory for crops and readings.jsonl (default: run/fifa-ocr)")
    parser.add_argument("--save-all", action="store_true",
                        help="save every crop instead of overwriting latest.png (can use much disk space)")
    parser.add_argument("--once", action="store_true", help="take one sample and exit")
    args = parser.parse_args()

    if args.raw_ocr and args.score_crop is not None:
        parser.error("--raw-ocr and --score-crop cannot be combined")
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
            if args.score_crop is not None:
                try:
                    crop_rectangle({"left": 0, "top": 0, "width": rectangle["width"],
                                    "height": rectangle["height"]}, args.score_crop)
                    if args.score_crop[2] <= 6 or args.score_crop[3] <= 10:
                        raise ValueError("score crop must be wider than 6 and taller than 10 pixels")
                except ValueError as error:
                    parser.error(f"score crop: {error}")
            args.output_dir.mkdir(parents=True, exist_ok=True)
            print(f"Capturing monitor {args.monitor} at {rectangle}; press Ctrl+C to stop", flush=True)
            with (args.output_dir / "readings.jsonl").open("a", encoding="utf-8") as log:
                next_sample = time.monotonic()
                while True:
                    entry = sample(sct, rectangle, args.output_dir, args.save_all,
                                   args.score_crop, args.raw_ocr)
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
