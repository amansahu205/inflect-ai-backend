"""
Validate Snowflake tables vs local data (implementation lives under backend/).
Run from repo root: python scripts/setup/validate_all_tables.py
"""

from __future__ import annotations

import runpy
from pathlib import Path

_IMPL = (
    Path(__file__).resolve().parents[2]
    / "backend"
    / "scripts"
    / "setup"
    / "validate_all_tables.py"
)

if __name__ == "__main__":
    runpy.run_path(str(_IMPL), run_name="__main__")
