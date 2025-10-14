from typing import Any

from ..core.config import settings
from ..core.utils import now_utc_iso, to_int
from ..storage.json_store import load_json, save_json


def load_watchlist() -> list[dict[str, Any]]:
    watchlist_path = settings.DATA_DIR / "watchlist.json"
    return load_json(watchlist_path, [])


def save_watchlist(items: list[dict[str, Any]]):
    watchlist_path = settings.DATA_DIR / "watchlist.json"
    save_json(watchlist_path, items)


def pick_cover(series: dict[str, Any]) -> str | None:
    cov = series.get("cover") or {}
    return cov.get("small") or cov.get("default") or cov.get("raw")


def derive_last_chapter_at(series_full: dict[str, Any]) -> str | None:
    if series_full.get("last_updated_at"):
        return series_full["last_updated_at"]
    src = series_full.get("source") or {}
    for k in (
        "anilist",
        "my_anime_list",
        "anime_news_network",
        "manga_updates",
        "kitsu",
        "shikimori",
        "mangadex",
    ):
        ts = (src.get(k) or {}).get("last_updated_at")
        if ts:
            return ts
    return None


def normalize_series_min(series: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": series.get("id"),
        "title": series.get("title"),
        "total_chapters": to_int(series.get("total_chapters")),
        "has_anime": bool(series.get("has_anime"))
        if series.get("has_anime") is not None
        else None,
        "status": series.get("status"),
        "type": series.get("type"),
        "content_rating": series.get("content_rating"),
        "cover": pick_cover(series),
        "last_updated_at": series.get("last_updated_at"),
        "state": series.get("state"),
        "merged_with": series.get("merged_with"),
    }


def annotate_unread(it: dict[str, Any]) -> dict[str, Any]:
    total = to_int(it.get("total_chapters")) or 0
    last = to_int(it.get("last_read")) or 0
    unread = max(total - last, 0)
    return {
        **it,
        "total_chapters": total or None,
        "last_read": last or 0,
        "unread": unread,
        "is_behind": unread > 0,
    }


def set_last_checked(it: dict[str, Any]):
    it["last_checked"] = now_utc_iso()
