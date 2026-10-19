#!/usr/bin/env python3
"""Build a platform-specific, self-contained FIFA CLI directory with PyInstaller."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def tesseract_files():
    override = os.environ.get("TESSERACT_EXE")
    executable = Path(override) if override else Path(shutil.which("tesseract") or "")
    if not executable.is_file():
        raise RuntimeError("install Tesseract or set TESSERACT_EXE to its executable")
    result = subprocess.run([str(executable), "--list-langs"], capture_output=True,
                            text=True, check=True)
    match = re.search(r'"([^"]+)"', result.stdout + result.stderr)
    if not match:
        raise RuntimeError("cannot locate Tesseract's tessdata directory")
    english = Path(match.group(1)) / "eng.traineddata"
    if not english.is_file():
        raise RuntimeError(f"English OCR data missing: {english}")
    return executable, english


def main():
    executable, english = tesseract_files()
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
               "--onedir", "--console", "--name", "damageio-fifa",
               "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"),
               "--specpath", str(ROOT / "build"),
               "--add-binary", f"{executable}{os.pathsep}.",
               "--add-data", f"{english}{os.pathsep}tessdata"]
    # The Windows Tesseract installer keeps its DLLs beside tesseract.exe.
    if sys.platform == "win32":
        for library in executable.parent.glob("*.dll"):
            command.extend(["--add-binary", f"{library}{os.pathsep}."])
    command.append(str(ROOT / "play.py"))
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
