"""Entry point for Vercel, which looks for a FastAPI `app` here. Locally, use `python -m uavert serve`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from uavert.api.app import app  # noqa: E402

__all__ = ["app"]
