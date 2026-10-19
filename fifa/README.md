# FIFA / EA Sports FC DamageIO controller

A Python controller for EA Sports FC on a PC. `play.py` reads the on-screen
score and sends a level to the *opposing* player's Arduino channel after a
confirmed goal. Use `-n` or `--dry-run` to inspect scores and confirmed goals
without opening a serial port. It uses screen capture, not a game mod. It was tested against saved
FC 26 footage, but not validated with live relay hardware or every HUD layout.

## Install

1. Set up the [shared firmware](../README.md#shared-firmware) and
   [relay wiring](../docs/relay-wiring.md). Use firmware with the two-channel
   v2 serial protocol. Close other serial clients, including Minecraft.
2. For a release build, download the FIFA archive for your PC from the
   [releases](https://github.com/alexjercan/damage-mc/releases) and extract
   the **whole** archive. Linux builds target x86-64 Ubuntu 24.04 and newer
   compatible distributions; Windows builds target x86-64 Windows. Run from a
   terminal in the extracted directory:

   ```fish
   ./damageio-fifa --check-ocr             # Linux
   ./damageio-fifa --dry-run --save-all    # Linux, no Arduino needed
   # On Windows (fish):
   ./damageio-fifa.exe --check-ocr
   ./damageio-fifa.exe --dry-run --save-all
   ```

   The bundle includes Python, its packages, Tesseract, and English OCR data.
   You do not need to install them separately. These bundles are built by the
   tag release workflow; older releases may not have them.

   To run from source instead, install Python 3, Tesseract (with English data),
   `mss`, Pillow, and `pyserial` (only for live mode). The Nix shell provides
   these tools:

   ```fish
   nix develop --command fish
   python3 fifa/play.py --dry-run --save-all
   ```

3. Make sure the game and its top-left score HUD appear in screen captures.
   Test OCR first, with no device connected, using `--dry-run`.

   Check `run/fifa-ocr/latest.png` or the saved crops and the printed `score`.
   If the crop shows a desktop, terminal, or black screen instead of the HUD,
   fix capture or use `--monitor` and `--crop` before enabling relays. Screen
   capture may not work in some Wayland sessions or protected full-screen modes.

## Run and configure

**Only start live mode when both physical device levels are 0.** Opening the
serial port can reset the Arduino's level counters, but it cannot reset or
read the physical device position. Test with relays disconnected first.
Dry-run does not open the port or require a connected Arduino.

For a Linux release bundle, from the extracted directory:

```fish
./damageio-fifa /dev/ttyACM0 --pulse 1000 --interval 0.5 --save-all
```

For a Windows release bundle, use `./damageio-fifa.exe COM3 --pulse 1000`
from a fish terminal and replace `COM3` with your Arduino port. From source,
run `python3 fifa/play.py` instead of the executable.

Replace `/dev/ttyACM0` with your Arduino serial port (for example,
`/dev/ttyUSB0`). The default captured region is `--crop 0 0 600 180`. Top
team is P1 (channel 0); bottom team is P2 (channel 1). A goal for the top
team activates P2, and a goal for the bottom team activates P1. Settings:

```text
--pulse 1000                 Hold at the target for 1000 milliseconds after ACK
--level 25                   Target level (1-50; default 25)
--top-channel 0              Device channel assigned to the top team (0 or 1)
--bottom-channel 1           Device channel assigned to the bottom team (0 or 1)
--interval 0.5               Seconds between captures
--monitor 1                  Screen index, starting at 1
--crop 0 0 600 180           HUD region in pixels relative to that screen
--output-dir run/fifa-play   Crop and JSONL log directory
--save-all                   Keep each crop instead of replacing latest.png
```

The channels must differ. `--pulse` defaults to 1000 ms and accepts 0-60000
ms. The first score seen in two consecutive captures establishes a baseline;
it does not activate the device. A later score confirmed in two consecutive
captures triggers a pulse only if exactly one team's score increased by one.
The script sends the opposing channel to the target, waits for Arduino ACK 0,
holds for `--pulse` milliseconds, then sends level 0 and waits for its ACK.
Press Ctrl+C to stop. During a pulse, OCR pauses, so fast successive goals
may be missed. A missing ACK or serial error leaves the physical position
unknown; inspect the device before reconnecting.

## Inspect and troubleshoot OCR

`play.py --dry-run` prints a JSON record for each frame and writes the same
records to `run/fifa-ocr/readings.jsonl`. The default crop for both modes is
`0 0 600 180`; adjust it with `--crop X Y WIDTH HEIGHT`. Each record includes
`score_ocr`, a *tentative* `score` (top, bottom), and `digit_boxes` within the
captured crop. `confirmed_score` and `goal` use the same rules as live mode,
but dry-run never opens a serial port or activates relays.
Unreadable or hidden score digits produce `score: null`. Without `--save-all`,
`latest.png` is overwritten for each sample; `--save-all` can use much disk
space. Use `--once` for one frame (dry-run only), `--output-dir` to change the
log location, `--score-crop X Y WIDTH HEIGHT` for manual debugging, or
`--raw-ocr` to read the whole crop as text (dry-run only; no goal detection).
The live controller writes similar logs under
`run/fifa-play/`.

OCR assumes two vertically aligned dark score digits on a light panel. New
HUD layouts, multi-digit scores, other screen text, and hidden scoreboards can
produce missing or wrong readings. The HUD may disappear for a goal or replay;
activation can happen much later when it returns. This is not an immediate or
universal goal detector. Confirm the displayed score and crop before use.

Run the unit tests from the repository root:

```fish
python3 -m unittest discover -s fifa -p 'test_*.py'
```
