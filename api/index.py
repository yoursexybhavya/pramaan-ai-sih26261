"""Vercel Python entrypoint for the PRAMAAN-AI FastAPI application."""
from pathlib import Path
import sys

APP_ROOT = Path(__file__).resolve().parents[1] / "pramaan-app"
sys.path.insert(0, str(APP_ROOT))

from app.main import app  # noqa: E402
