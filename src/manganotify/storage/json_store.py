import json
from pathlib import Path
from typing import Any

def load_json(path: Path, default: Any):
    if path.exists():
        try: return json.loads(path.read_text("utf-8"))
        except Exception: return default
    return default

def save_json(path: Path, data: Any, *, compact=False):
    if compact:
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    else:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
