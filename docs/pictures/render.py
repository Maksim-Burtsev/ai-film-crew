"""Render the README pictures to PNG with headless Chrome or Chromium (set $CHROME if it isn't found).

Usage: python3 docs/pictures/render.py      (from the repo root; writes docs/img/ and .claude-plugin/icon.png)
The pictures are drawn in pictures.py; fonts come from Google Fonts, so rendering needs a network connection.
"""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pictures  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=Golos+Text:'
         'wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700;800&display=swap">')
JOBS = (  # (output, drawing, width, height, scale)
    ("docs/img/crew.png", pictures.hero_crew, 880, 744, 2),
    ("docs/img/product-size.png", pictures.prop_overlay, 880, 510, 2),
    ("docs/img/scene-set.png", pictures.set_couch, 880, 500, 2),
    ("docs/img/recurring-cast.png", pictures.cast_rank, 880, 528, 2),
    ("docs/img/blind-review.png", pictures.test_why, 880, 470, 2),
    ("docs/img/sound-mix.png", pictures.sound_cards, 880, 702, 2),
    ("docs/img/social-preview.png", pictures.social, 1280, 640, 1),
    (".claude-plugin/icon.png", pictures.icon, 512, 512, 2),
)


def chrome():
    for c in (os.environ.get("CHROME"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser")):
        if c and Path(c).exists():
            return c
    sys.exit("no Chrome or Chromium found: set $CHROME")


def main():
    exe = chrome()
    with tempfile.TemporaryDirectory() as tmp:
        for out, draw, w, h, scale in JOBS:
            page = Path(tmp) / "p.html"
            page.write_text(f'<!doctype html><meta charset="utf-8">{FONTS}<style>body{{margin:0}}svg{{display:block;'
                            f'width:{w}px;height:{h}px}}</style>{draw()}')
            dest = ROOT / out
            dest.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=6000",
                            f"--force-device-scale-factor={scale}", f"--window-size={max(w, 500)},{h}",
                            "--default-background-color=00000000", f"--screenshot={dest}", page.as_uri()],
                           check=True, capture_output=True)
            print(out)


if __name__ == "__main__":
    main()
