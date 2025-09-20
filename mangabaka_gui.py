# Standard library
import io
import json
import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, Iterable, List, Optional

# Third-party
import requests
from PIL import Image, ImageTk

# Optional third-party
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

def env(name: str, default: Optional[str]=None, required: bool=False) -> str:
    v = os.getenv(name, default)
    if required and not v:
        raise RuntimeError(f"Missing env: {name}")
    return v or ""

def load_env():
    if load_dotenv:
        load_dotenv()

BASE = env("MANGABAKA_BASE", "https://api.mangabaka.dev").rstrip("/")

WATCHLIST_FILE = env("WATCHLIST_FILE", "watchlist.json")

# --- API helpers ------------------------------------------------------------
def search_series_paged(
    q: str,
    *,
    page_start: int = 1,
    page_limit: int = 50,
    max_pages: int = 1,
    sort_by: Optional[str] = None,
) -> Iterable[Dict[str, Any]]:
    """Yield series search results across pages."""
    params = {"q": q, "page": page_start, "limit": min(page_limit, 50)}
    if sort_by:
        params["sort_by"] = sort_by

    pages_fetched = 0
    while True:
        r = requests.get(f"{BASE}/v1/series/search", params=params, timeout=30)
        r.raise_for_status()
        js = r.json()

        items = js.get("data") or js.get("results") or []
        for it in items:
            yield it

        pages_fetched += 1
        # stop if we hit our page cap or there weren't a full page of results
        if pages_fetched >= max_pages or len(items) < params["limit"]:
            break
        params["page"] += 1

def series_title(s: Dict[str, Any]) -> str:
    titles = s.get("titles") or s.get("secondary_titles") or {}
    # MangaBaka sample schema often has `title` + `secondary_titles`
    # Try common fields conservatively
    en = None
    if isinstance(titles, dict):
        en = titles.get("en")
        if isinstance(en, list) and en:
            en = en[0].get("title") if isinstance(en[0], dict) else en[0]
        elif isinstance(en, dict):
            en = en.get("title")
    return s.get("title") or en or "(no title)"

def get_cover_url(series: dict) -> str | None:
    cover = series.get("cover") or {}
    return cover.get("small") or cover.get("default") or cover.get("raw")


# --- Cover Image helpers ------------------------------------------------------
IMG_CACHE_DIR = ".img_cache"
os.makedirs(IMG_CACHE_DIR, exist_ok=True)

def _cache_path(url: str) -> str:
    import hashlib
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return os.path.join(IMG_CACHE_DIR, f"{h}.bin")

def fetch_thumbnail_tk(url: str, max_size=(320, 320)) -> ImageTk.PhotoImage | None:
    try:
        path = _cache_path(url)
        if os.path.exists(path):
            data = open(path, "rb").read()
        else:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            data = r.content
            with open(path, "wb") as f:
                f.write(data)
        img = Image.open(io.BytesIO(data))
        img.thumbnail(max_size)  # in-place, keeps aspect ratio
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def prune_cache(max_size_mb=20):
    total = 0
    files = []
    for f in os.scandir(".img_cache"):
        if f.is_file():
            size = os.path.getsize(f.path)
            total += size
            files.append((f.path, size, f.stat().st_mtime))
    if total > max_size_mb * 1024 * 1024:
        # sort by oldest first
        files.sort(key=lambda x: x[2])
        while total > max_size_mb * 1024 * 1024 and files:
            path, size, _ = files.pop(0)
            os.remove(path)
            total -= size

# --- Watchlist helpers ------------------------------------------------------
def load_watchlist() -> List[Dict[str, Any]]:
    if WATCHLIST_FILE.exists():
        try:
            return json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []

def save_watchlist(items: List[Dict[str, Any]]) -> None:
    WATCHLIST_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")

def add_to_watchlist(series: Dict[str, Any]) -> None:
    wl = load_watchlist()
    sid = series.get("id")
    if any(str(x.get("id")) == str(sid) for x in wl):
        messagebox.showinfo("Watchlist", "Already in watchlist.")
        return
    wl.append({"id": sid, "title": series_title(series)})
    save_watchlist(wl)
    messagebox.showinfo("Watchlist", f"Added: {sid} - {series_title(series)}")

# --- GUI app ----------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MangaBaka Search (very rudimentary)")
        self.geometry("700x480")

        self.query_var = tk.StringVar()
        self.pages_var = tk.IntVar(value=1)
        self.sort_var = tk.StringVar(value="relevance_desc")

        # Top controls
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Query:").grid(row=0, column=0, sticky="w")
        q_entry = ttk.Entry(top, textvariable=self.query_var, width=40)
        q_entry.grid(row=0, column=1, padx=6, sticky="w")
        q_entry.bind("<Return>", lambda e: self.start_search())

        ttk.Label(top, text="Pages:").grid(row=0, column=2, padx=(12,4), sticky="e")
        pages_spin = ttk.Spinbox(top, from_=1, to=10, textvariable=self.pages_var, width=5)
        pages_spin.grid(row=0, column=3, sticky="w")

        ttk.Label(top, text="Sort:").grid(row=0, column=4, padx=(12,4), sticky="e")
        sort_combo = ttk.Combobox(top, textvariable=self.sort_var, width=18, values=[
            "relevance_desc", "popularity_desc", "name_asc", "name_desc",
            "chapters_desc", "volumes_desc", "published_year_desc",
            "published_year_asc", "latest", "random"
        ])
        sort_combo.grid(row=0, column=5, sticky="w")
        sort_combo.state(["readonly"])

        self.search_btn = ttk.Button(top, text="Search", command=self.start_search)
        self.search_btn.grid(row=0, column=6, padx=10)

        # Results list
        mid = ttk.Frame(self, padding=(10,0))
        mid.pack(fill="both", expand=True)

        self.results = tk.Listbox(mid, height=18)
        self.results.pack(side="left", fill="both", expand=True)
        # ... in __init__ after you create self.results ...
        self.results.bind("<<ListboxSelect>>", self.on_select)

        # Right-side detail area
        right = ttk.Frame(mid, padding=(10, 0))
        right.pack(side="right", fill="y")

        self.cover_label = ttk.Label(right, text="(no image)", anchor="center")
        self.cover_label.pack(pady=6)

        # Keep a reference to prevent GC of PhotoImage
        self._cover_tk = None

        sb = ttk.Scrollbar(mid, orient="vertical", command=self.results.yview)
        sb.pack(side="right", fill="y")
        self.results.configure(yscrollcommand=sb.set)

        # Bottom bar
        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill="x")

        self.add_btn = ttk.Button(bottom, text="Add to watchlist", command=self.add_selected)
        self.add_btn.pack(side="left")

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(bottom, textvariable=self.status_var).pack(side="right")

        # Backing store for current search results (parallel to listbox rows)
        self.current_rows: List[Dict[str, Any]] = []

    def start_search(self):
        q = self.query_var.get().strip()
        if not q:
            messagebox.showwarning("Search", "Enter a query.")
            return
        self.status_var.set("Searching...")
        self.search_btn.config(state="disabled")
        self.results.delete(0, "end")
        self.current_rows.clear()
        t = threading.Thread(target=self._search_thread, args=(q, self.pages_var.get(), self.sort_var.get()), daemon=True)
        t.start()

    def _search_thread(self, q: str, pages: int, sort_by: str):
        try:
            count = 0
            for item in search_series_paged(q, page_limit=50, max_pages=pages, sort_by=sort_by):
                self.current_rows.append(item)
                sid = item.get("id")
                title = series_title(item)
                authors_raw = item.get("authors") or []
                authors = ", ".join(authors_raw)

                artists_raw = item.get("artists") or []
                artists = ", ".join(artists_raw)

                self.results.insert("end", f"{sid} — {title} - {authors} - {artists}")
                count += 1
            self._set_status(f"Done. {count} result(s).")
        except Exception as e:
            self._set_status(f"Error: {e}")
        finally:
            self.search_btn.config(state="normal")

    def _set_status(self, msg: str):
        # Tkinter updates must run on main thread
        self.after(0, lambda: self.status_var.set(msg))

    def add_selected(self):
        idx = self.results.curselection()
        if not idx:
            messagebox.showinfo("Watchlist", "Select a row first.")
            return
        series = self.current_rows[idx[0]]
        add_to_watchlist(series)

    def on_select(self, *_):
        sel = self.results.curselection()
        if not sel: return
        series = self.current_rows[sel[0]]

        cover_url = get_cover_url(series)
        if not cover_url:
            self.cover_label.config(text="(no image)")
            self._cover_tk = None
            return

        def worker():
            tkimg = fetch_thumbnail_tk(cover_url, max_size=(360, 360))

            def update():
                if tkimg:
                    self._cover_tk = tkimg  # keep a reference!
                    self.cover_label.config(image=self._cover_tk, text="")
                else:
                    self.cover_label.config(text="(image failed)")

            self.after(0, update)

        import threading
        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    prune_cache(max_size_mb=20)
    App().mainloop()
