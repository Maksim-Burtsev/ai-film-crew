import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for skill in ("scene-set", "product-size", "recurring-cast", "blind-review", "sound-mix"):
    sys.path.insert(0, str(ROOT / "skills" / skill / "scripts"))
