from typing import Dict, Any, List, Optional
from ..core.config import WATCHLIST_PATH
from ..storage.json_store import load_json, save_json
from ..core.utils import to_int, now_utc_iso

def load_watchlist() -> List[Dict[str, Any]]:
    return load_json(WATCHLIST_PATH, [])

def save_watchlist(items: List[Dict[str, Any]]):
    save_json(WATCHLIST_PATH, items)

def pick_cover(series: Dict[str, Any]) -> Optional[str]:
    cov = series.get("cover") or {}
    return cov.get("small") or cov.get("default") or cov.get("raw")

def derive_last_chapter_at(series_full: Dict[str, Any]) -> Optional[str]:
    if series_full.get("last_updated_at"): return series_full["last_updated_at"]
    src = series_full.get("source") or {}
    for k in ("anilist","my_anime_list","anime_news_network","manga_updates","kitsu","shikimori","mangadex"):
        ts = (src.get(k) or {}).get("last_updated_at")
        if ts: return ts
    return None

def normalize_series_min(series: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": series.get("id"),
        "title": series.get("title"),
        "total_chapters": to_int(series.get("total_chapters")),
        "has_anime": bool(series.get("has_anime")) if series.get("has_anime") is not None else None,
        "status": series.get("status"),
        "type": series.get("type"),
        "content_rating": series.get("content_rating"),
        "cover": pick_cover(series),
        "last_updated_at": series.get("last_updated_at"),
        "state": series.get("state"),
        "merged_with": series.get("merged_with"),
    }

def annotate_unread(it: Dict[str, Any]) -> Dict[str, Any]:
    total = to_int(it.get("total_chapters")) or 0
    last  = to_int(it.get("last_read")) or 0
    unread = max(total - last, 0)
    return {**it, "total_chapters": total or None, "last_read": last or 0,
            "unread": unread, "is_behind": unread > 0}

def set_last_checked(it: Dict[str, Any]):
    it["last_checked"] = now_utc_iso()
