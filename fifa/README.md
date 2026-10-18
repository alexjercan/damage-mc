# FIFA / EA Sports FC score OCR dry run

`score_dry_run.py` captures a configurable top-left screen region and runs
Tesseract OCR on it. It does **not** detect goals or use the serial port. Use it
to collect sample crops and raw OCR text before designing reliable goal
detection. Team names, HUD layout, replays, and menus can change the results.

Run from the repository root in the Nix development shell:

```fish
nix develop --command fish
python3 fifa/score_dry_run.py --interval 1 --monitor 1 --crop 0 0 600 180
```

`--interval` is the number of seconds between samples (default `1`). `--crop`
is `X Y WIDTH HEIGHT` in pixels relative to the selected monitor; without it,
the script captures the top-left 35% of the width and 18% of the height.
`--monitor` selects the display (default `1`, first monitor). Start with a
large region and narrow it after inspecting a crop. Use `--once` to take just
one reading. Press Ctrl+C to stop.

Each sample prints a JSON record and appends it to
`run/fifa-ocr/readings.jsonl`. The raw crop is saved as
`run/fifa-ocr/latest.png`, overwritten on each reading. Set `--output-dir PATH`
to change this directory. `--save-all` keeps a separate PNG for every sample;
this can use substantial disk space. The OCR text is raw, not a confirmed
score. Check the image and OCR log before making any detection rules.

Run the script's unit tests with
`python3 -m unittest discover -s fifa -p 'test_*.py'`.

The script uses `mss` for screen capture (X11 on this Linux setup), Pillow,
and Tesseract. Some Wayland sessions or protected/full-screen game capture
modes block ordinary screen capture. Test the saved PNG to confirm it shows
the game; a black crop or capture error is not an OCR issue.
