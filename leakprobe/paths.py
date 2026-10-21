"""Repository paths shared by the package modules."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEMO_DATA = DATA / "demo"
OUTPUTS = ROOT / "outputs"

