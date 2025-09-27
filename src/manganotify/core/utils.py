from datetime import datetime, timezone

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def to_int(v):
    if v is None: return None
    try:
        s = str(v).strip()
        if s == "": return None
        return int(float(s)) if "." in s else int(s)
    except Exception:
        return None

def to_bool_or_none(v):
    if v is None: return None
    if isinstance(v, bool): return v
    s = str(v).strip().lower()
    if s in {"1","true","yes","on"}: return True
    if s in {"0","false","no","off"}: return False
    return None

def str_eq(a, b: str | None) -> bool:
    if not b: return True
    return (a is not None) and (str(a).lower() == str(b).lower())
