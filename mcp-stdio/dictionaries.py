"""
Closed-list values of the registry columns: the single source of truth.

The lists live in dictionaries.json. server.py validates writes against them,
dashboard.py takes the role levels from them, and tests/test_dictionaries.py
checks that criteria.md and the registry itself do not drift away from them.
"""

import json
from pathlib import Path

_FILE = Path(__file__).parent / "dictionaries.json"

VALUES: dict[str, tuple[str, ...]] = {
    key: tuple(values) for key, values in json.loads(_FILE.read_text(encoding="utf-8")).items()
}
