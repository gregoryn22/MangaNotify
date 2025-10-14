import json
import logging
import sys
from datetime import UTC, datetime


def now_utc_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


def setup_logging(level: str = "INFO", fmt: str = "plain") -> None:
    lvl = getattr(logging, str(level).upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(lvl)
    # remove default handlers
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
    root.addHandler(handler)


def to_int(v):
    if v is None:
        return None
    try:
        s = str(v).strip()
        if s == "":
            return None
        return int(float(s)) if "." in s else int(s)
    except Exception:
        return None


def to_bool_or_none(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"1", "true", "yes", "on"}:
        return True
    if s in {"0", "false", "no", "off"}:
        return False
    return None


def str_eq(a, b: str | None) -> bool:
    if not b:
        return True
    return (a is not None) and (str(a).lower() == str(b).lower())
