# FIFA / EA Sports FC score OCR dry run

`score_ocr.py` captures a top-left screen region, finds score-like digits
on bright panels, and runs Tesseract OCR on each candidate. It does **not**
detect goals or use the serial port. Team names can vary, but game modes,
replays, menus, display scales, and HUD layouts can change the results.

Run from the repository root in the Nix development shell:

```fish
nix develop --command fish
python3 fifa/score_ocr.py --interval 1 --monitor 1 --crop 0 0 600 180 --save-all
```

The script searches a broad top-left area for two vertically aligned dark
digits with bright surroundings. It crops around the digits rather than using
fixed HUD coordinates, so both tested FC 26 matches work with the same command
and shifted panels can work too. Logs include `digit_boxes` (pixel coordinates
within the captured image), `score_ocr`, and a tentative `score` (top then
bottom). No detected pair or unreadable digits produce `score: null`.

This is **not** a universal FC score or goal detector. It assumes vertically
stacked dark digits on a light panel. Other fonts, multi-digit scores, HUD
styles, or a scoreboard outside the capture may not work. Other screen text
could also look like scores. Do not use these tentative readings to trigger a
device. `--score-crop X Y WIDTH HEIGHT` remains available for debugging;
`--raw-ocr` restores OCR of the whole captured image. In the saved videos, the
score HUD sometimes disappears during a replay; no crop can read it then.

`--interval` is the number of seconds between samples (default `1`). `--crop`
is `X Y WIDTH HEIGHT` in pixels relative to the selected monitor; without it,
the script captures the top-left 35% of the width and 18% of the height.
`--monitor` selects the display (default `1`, first monitor). Start with a
top-left capture that includes the entire HUD. Use `--once` to take just
one reading. Press Ctrl+C to stop.

Each sample prints a JSON record and appends it to
`run/fifa-ocr/readings.jsonl`. The raw crop is saved as
`run/fifa-ocr/latest.png`, overwritten on each reading. Set `--output-dir PATH`
to change this directory. `--save-all` keeps a separate PNG for every sample;
this can use substantial disk space. Check the image and OCR log before
making any detection rules.

## Arduino goal controller (experimental)

**Only run this with both physical device levels at 0.** Opening the serial
port may reset the Arduino's volatile level counters; it cannot read the
actual physical levels. Wrong initial levels can make a target unsafe. Test
with relays disconnected first. This is not validated with live hardware.

```fish
python3 fifa/play.py /dev/ttyACM0 --pulse 1000 --interval 0.5 --crop 0 0 600 180 --save-all
```

The first score confirmed in two consecutive captures establishes the baseline
without activating anything. Later, if exactly one team's score increases by
one in two consecutive captures, the **opposing** channel receives level 25:
top team goal -> P2 (channel 1); bottom team goal -> P1 (channel 0). The
script waits for Arduino ACK 0 (target reached), holds for `--pulse`
**milliseconds** (default 1000), then sends level 0 and waits for its ACK.
Use `--top-channel` and `--bottom-channel` (0 or 1, distinct) to swap player
mapping, and `--level` (1-50) to change the effect strength. One command is
in flight at a time. Ctrl+C during the hold causes a return to zero after
ACK; a serial error or missing ACK means the physical level is unknown.
Inspect the device before reopening the port. OCR is paused while a pulse
runs, so rapid successive goals may be missed. Jumps, decreased scores,
invalid OCR and the initial baseline do not trigger a pulse. Since the score
HUD may disappear after a goal, this can run late; it is **not** an immediate
goal detector. All captured images and readings are saved under `run/fifa-play`
(`--save-all` retains every image).

Run the scripts' unit tests with
`python3 -m unittest discover -s fifa -p 'test_*.py'`.

The script uses `mss` for screen capture (X11 on this Linux setup), Pillow,
and Tesseract. Some Wayland sessions or protected/full-screen game capture
modes block ordinary screen capture. Test the saved PNG to confirm it shows
the game; a black crop or capture error is not an OCR issue.
