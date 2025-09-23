#!/usr/bin/env python3
from __future__ import annotations
import io, json, os, queue, threading, time, tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Dict, List, Optional

import requests
from PIL import Image, ImageTk

from credentials import get_pushover_creds, set_pushover_creds
from pushover import send_pushover

# ----------------------- Config -----------------------
BASE = os.getenv("MANGABAKA_BASE", "https://api.mangabaka.dev").rstrip("/")
WATCHLIST_FILE = os.getenv("WATCHLIST_FILE", "watchlist.json")
PAGE_LIMIT = 50
TIMEOUT_SEC = 20.0
POLL_INTERVAL_SEC = int(os.getenv("WATCH_POLL_MINUTES", "10")) * 60  # default 10 min

# ----------------------- Backend -----------------------
def series_title(s: Dict[str, Any]) -> str:
    t = s.get("title")
    if t: return str(t)
    st = s.get("secondary_titles") or {}
    en = st.get("en")
    if isinstance(en, list) and en:
        first = en[0]
        return (first.get("title") if isinstance(first, dict) else str(first)) or "(no title)"
    return "(no title)"

def search_series_page(q: str, *, start_url: Optional[str] = None, base: str = BASE) -> Dict[str, Any]:
    ses = requests.Session()
    ses.headers.update({"User-Agent": "mangabaka-tk/1.1"})
    if start_url:
        r = ses.get(start_url, timeout=TIMEOUT_SEC)
    else:
        r = ses.get(f"{base}/v1/series/search",
                    params={"q": q, "limit": min(PAGE_LIMIT, 50), "page": 1},
                    timeout=TIMEOUT_SEC)
    r.raise_for_status()
    return r.json()

def get_series(series_id: str | int, *, base: str = BASE) -> Dict[str, Any]:
    r = requests.get(f"{base}/v1/series/{series_id}",
                     headers={"User-Agent": "mangabaka-tk/1.1"}, timeout=TIMEOUT_SEC)
    r.raise_for_status()
    payload = r.json()
    return payload.get("data") or payload

# ----------------------- Watchlist storage -----------------------
def load_watchlist() -> List[Dict[str, Any]]:
    try:
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list): return data
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return []

def save_watchlist(items: List[Dict[str, Any]]) -> None:
    tmp = WATCHLIST_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    os.replace(tmp, WATCHLIST_FILE)

def normalize_total_chapters(v: Any) -> Optional[int]:
    if v is None: return None
    if isinstance(v, (int, float)): return int(v)
    s = str(v).strip()
    return int(s) if s.isdigit() else None

# ----------------------- GUI -----------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        logo = tk.PhotoImage(file="manganotify_logo.png")
        self.iconphoto(True, logo)
        self.title("MangaBaka — Search & Watchlist")
        self.geometry("1060x640")
        self.minsize(980, 560)

        # State
        self.results: list[Dict[str, Any]] = []
        self.next_url: Optional[str] = None
        self.worker_q: "queue.Queue[tuple[str, Any]]" = queue.Queue()
        self.cover_cache: dict[str, ImageTk.PhotoImage] = {}

        # Watchlist state
        self.watch: List[Dict[str, Any]] = load_watchlist()
        self.poll_thread: Optional[threading.Thread] = None
        self.poll_stop = threading.Event()

        self._build_widgets()
        self._poll_worker_queue()
        self._start_poller()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        menubar = tk.Menu(self)
        self.config(menu=menubar)
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Notifications (Pushover)…",
                                  command=lambda: PushoverDialog(self))
        menubar.add_cascade(label="Settings", menu=settings_menu)

    # ---------------- UI Layout ----------------
    def _build_widgets(self):
        # Top bar
        top = ttk.Frame(self, padding=(8, 8))
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.entry = ttk.Entry(top, textvariable=self.search_var, width=44)
        self.entry.pack(side=tk.LEFT, padx=6)
        self.entry.bind("<Return>", lambda e: self.on_search())

        self.btn_search = ttk.Button(top, text="Search", command=self.on_search)
        self.btn_search.pack(side=tk.LEFT)

        self.btn_more = ttk.Button(top, text="Load more", command=self.on_load_more, state=tk.DISABLED)
        self.btn_more.pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(top, textvariable=self.status_var, anchor="e").pack(side=tk.RIGHT)

        # Panes
        main = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Left: results
        left = ttk.Frame(main)
        main.add(left, weight=1)

        self.listbox = tk.Listbox(left, activestyle="dotbox")
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.listbox.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.configure(yscrollcommand=scroll.set)

        # Right: tabs (Details | Watchlist)
        right = ttk.Notebook(main)
        main.add(right, weight=2)

        # Details tab
        details = ttk.Frame(right, padding=(8, 8))
        right.add(details, text="Details")

        self.lbl_title = ttk.Label(details, text="—", font=("TkDefaultFont", 14, "bold"),
                                   wraplength=460, justify="left")
        self.lbl_title.pack(anchor="w", pady=(0, 6))

        self.lbl_meta = ttk.Label(details, text="", justify="left", wraplength=460)
        self.lbl_meta.pack(anchor="w")

        # Buttons row
        btnrow = ttk.Frame(details)
        btnrow.pack(anchor="w", pady=(6, 2))
        self.btn_add_watch = ttk.Button(btnrow, text="➕ Add to Watchlist", command=self.on_add_watch, state=tk.DISABLED)
        self.btn_add_watch.pack(side=tk.LEFT)

        # Body: cover + description
        body = ttk.Frame(details)
        body.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.cover_lbl = ttk.Label(body)
        self.cover_lbl.pack(anchor="w")

        self.desc_txt = tk.Text(body, height=12, wrap="word")
        self.desc_txt.configure(state=tk.DISABLED)
        self.desc_txt.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        # Watchlist tab
        wl = ttk.Frame(right, padding=(8, 8))
        right.add(wl, text="Watchlist")

        wl_top = ttk.Frame(wl)
        wl_top.pack(fill=tk.X)
        self.btn_check_now = ttk.Button(wl_top, text="Check now", command=self.on_check_now)
        self.btn_check_now.pack(side=tk.LEFT)
        ttk.Label(wl_top, text=f"Polling every {POLL_INTERVAL_SEC//60} min").pack(side=tk.LEFT, padx=8)

        self.wl_list = tk.Listbox(wl, activestyle="dotbox", height=12)
        self.wl_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(8, 0))
        wscroll = ttk.Scrollbar(wl, orient=tk.VERTICAL, command=self.wl_list.yview)
        wscroll.pack(side=tk.LEFT, fill=tk.Y, pady=(8, 0))
        self.wl_list.configure(yscrollcommand=wscroll.set)

        wl_btns = ttk.Frame(wl)
        wl_btns.pack(side=tk.LEFT, fill=tk.Y, padx=(8,0), pady=(8,0))
        ttk.Button(wl_btns, text="View", command=self.on_wl_view).pack(fill=tk.X)
        ttk.Button(wl_btns, text="Remove", command=self.on_wl_remove).pack(fill=tk.X, pady=(6,0))

        self._refresh_watchlist_listbox()

    # ---------------- Worker plumbing ----------------
    def run_in_worker(self, fn, *args, **kwargs):
        def task():
            try:
                res = fn(*args, **kwargs)
                self.worker_q.put(("ok", res))
            except Exception as e:
                self.worker_q.put(("err", e))
        threading.Thread(target=task, daemon=True).start()

    def _poll_worker_queue(self):
        try:
            while True:
                kind, payload = self.worker_q.get_nowait()
                if kind == "ok":
                    self._on_worker_success(payload)
                else:
                    self._on_worker_error(payload)
        except queue.Empty:
            pass
        self.after(100, self._poll_worker_queue)

    # ---------------- Actions ----------------
    def on_search(self):
        q = self.search_var.get().strip()
        if not q: return
        self.results.clear()
        self.listbox.delete(0, tk.END)
        self.next_url = None
        self.status_var.set("Searching…")
        self.btn_search.configure(state=tk.DISABLED)
        self.btn_more.configure(state=tk.DISABLED)
        self.btn_add_watch.configure(state=tk.DISABLED)
        self.run_in_worker(search_series_page, q)

    def on_load_more(self):
        if not self.next_url: return
        self.status_var.set("Loading more…")
        self.btn_more.configure(state=tk.DISABLED)
        self.run_in_worker(search_series_page, "", start_url=self.next_url)

    def on_select(self, _evt=None):
        idxs = self.listbox.curselection()
        if not idxs:
            self.btn_add_watch.configure(state=tk.DISABLED)
            return
        item = self.results[idxs[0]]
        sid = item.get("id")
        self.status_var.set(f"Fetching details #{sid}…")
        self.btn_add_watch.configure(state=tk.NORMAL)
        self.run_in_worker(get_series, sid)

    def on_add_watch(self):
        idxs = self.listbox.curselection()
        if not idxs: return
        item = self.results[idxs[0]]
        sid = str(item.get("id"))
        title = series_title(item)
        # avoid dups
        for x in self.watch:
            if str(x.get("id")) == sid:
                messagebox.showinfo("Watchlist", "Already in watchlist.")
                return
        # seed last_total_chapters from current details in right pane if available
        # but safer to fetch fresh
        try:
            s = get_series(sid)
        except Exception:
            s = item
        last = normalize_total_chapters(s.get("total_chapters"))
        self.watch.append({
            "id": sid,
            "title": title,
            "last_total_chapters": last,
            "last_checked": None
        })
        save_watchlist(self.watch)
        self._refresh_watchlist_listbox()
        messagebox.showinfo("Watchlist", f"Added: {sid} — {title}")

    def on_wl_view(self):
        idx = self._wl_selected_index()
        if idx is None: return
        sid = self.watch[idx]["id"]
        self.run_in_worker(get_series, sid)

    def on_wl_remove(self):
        idx = self._wl_selected_index()
        if idx is None: return
        row = self.watch.pop(idx)
        save_watchlist(self.watch)
        self._refresh_watchlist_listbox()
        messagebox.showinfo("Watchlist", f"Removed: {row['id']} — {row['title']}")

    def on_check_now(self):
        # Trigger an immediate poll cycle (non-blocking)
        threading.Thread(target=self._poll_once_safe, daemon=True).start()

    # ---------------- Worker results ----------------
    def _on_worker_success(self, payload):
        # Cover tuple
        if isinstance(payload, tuple) and len(payload) == 3 and payload[0] == "__cover__":
            _, url, photo = payload
            self.cover_cache[url] = photo
            self.cover_lbl.configure(image=photo)
            self.cover_lbl.image = photo
            return

        # Search page
        if isinstance(payload, dict) and "data" in payload and "pagination" in payload:
            page = payload
            data = page.get("data") or []
            pag = page.get("pagination") or {}
            self.next_url = pag.get("next")
            start_index = len(self.results)
            self.results.extend(data)
            for it in data:
                self.listbox.insert(tk.END, f"{it.get('id')} — {series_title(it)}")
            self.status_var.set(f"{len(self.results)} results" + (" (more…)" if self.next_url else ""))
            self.btn_more.configure(state=(tk.NORMAL if self.next_url else tk.DISABLED))
            self.btn_search.configure(state=tk.NORMAL)
            if start_index == 0 and self.results:
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(0)
                self.listbox.event_generate("<<ListboxSelect>>")
            return

        # Assume series dict
        s = payload
        self._show_detail(s)
        self.status_var.set("Ready")

    def _on_worker_error(self, e: Exception):
        self.status_var.set("Error")
        self.btn_search.configure(state=tk.NORMAL)
        self.btn_more.configure(state=(tk.NORMAL if self.next_url else tk.DISABLED))
        messagebox.showerror("Error", str(e))

    # ---------------- Detail rendering ----------------
    def _show_detail(self, s: Dict[str, Any]):
        title = series_title(s)
        kind = s.get("type") or "-"
        year = s.get("year") or "-"
        rating = s.get("rating")
        rating_str = f"{rating:.2f}" if isinstance(rating, (int, float)) else "-"
        authors = ", ".join(s.get("authors") or []) or "-"
        artists = ", ".join(s.get("artists") or []) or "-"
        total_ch = s.get("total_chapters")

        self.lbl_title.configure(text=title)
        meta_lines = [
            f"Type: {kind}    Year: {year}    ⭐ {rating_str}",
            f"Authors: {authors}",
            f"Artists: {artists}",
            f"Total chapters: {total_ch if total_ch is not None else '-'}",
        ]
        self.lbl_meta.configure(text="\n".join(meta_lines))

        # description -> plain text
        desc = (s.get("description") or "").replace("<br>", "\n").replace("<br/>", "\n").replace("<br><br>", "\n\n")
        try:
            import html, re
            desc = re.sub(r"<[^>]+>", "", html.unescape(desc))
        except Exception:
            pass
        self.desc_txt.configure(state=tk.NORMAL)
        self.desc_txt.delete("1.0", tk.END)
        if desc:
            self.desc_txt.insert("1.0", desc.strip())
        self.desc_txt.configure(state=tk.DISABLED)

        # cover
        cover = s.get("cover") or {}
        url = cover.get("default") or cover.get("small") or cover.get("raw")
        self._set_cover(url)

    def _set_cover(self, url: Optional[str]):
        if not url:
            self.cover_lbl.configure(image="", text="(no cover)")
            return
        if url in self.cover_cache:
            photo = self.cover_cache[url]
            self.cover_lbl.configure(image=photo)
            self.cover_lbl.image = photo
            return

        def worker():
            try:
                r = requests.get(url, timeout=TIMEOUT_SEC)
                r.raise_for_status()
                img = Image.open(io.BytesIO(r.content))
                img.thumbnail((360, 360))
                photo = ImageTk.PhotoImage(img)
                self.worker_q.put(("ok", ("__cover__", url, photo)))
            except Exception as e:
                self.worker_q.put(("err", e))
        threading.Thread(target=worker, daemon=True).start()

    # ---------------- Watchlist helpers ----------------
    def _refresh_watchlist_listbox(self):
        self.wl_list.delete(0, tk.END)
        for w in self.watch:
            last = w.get("last_total_chapters")
            txt = f"{w['id']} — {w['title']}"
            if last is not None:
                txt += f"  (last: {last})"
            self.wl_list.insert(tk.END, txt)

    def _wl_selected_index(self) -> Optional[int]:
        sel = self.wl_list.curselection()
        return sel[0] if sel else None

    # ---------------- Poller ----------------
    def _start_poller(self):
        if self.poll_thread and self.poll_thread.is_alive():
            return
        self.poll_stop.clear()
        self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.poll_thread.start()

    def _poll_loop(self):
        # Stagger initial sleep a bit so UI loads
        time.sleep(2.0)
        while not self.poll_stop.is_set():
            self._poll_once_safe()
            # wait interval with early exit
            for _ in range(POLL_INTERVAL_SEC):
                if self.poll_stop.is_set(): break
                time.sleep(1)

    def _poll_once_safe(self):
        if not self.watch:
            return
        # Poll each item; keep modest pacing to be nice to the API
        changed = []
        for w in list(self.watch):
            if self.poll_stop.is_set(): break
            sid = w["id"]
            try:
                s = get_series(sid)
                new_total = normalize_total_chapters(s.get("total_chapters"))
                old_total = normalize_total_chapters(w.get("last_total_chapters"))
                w["last_checked"] = time.strftime("%Y-%m-%d %H:%M:%S")
                if new_total is not None and old_total is not None and new_total > old_total:
                    w["last_total_chapters"] = new_total
                    changed.append((sid, w["title"], old_total, new_total))
                elif old_total is None and new_total is not None:
                    w["last_total_chapters"] = new_total
                # brief delay between calls
                time.sleep(0.3)
            except Exception:
                # ignore individual failures; continue
                time.sleep(0.3)
                continue
        # persist + notify
        save_watchlist(self.watch)
        if changed:
            msg = "\n".join([f"{t} — {o} → {n} (#{sid})" for sid, t, o, n in changed])
            self._notify_ui(f"New chapters detected:\n{msg}")
        # refresh listbox on UI thread
        self.after(0, self._refresh_watchlist_listbox)

    def _notify_ui(self, text: str):
        # existing popup
        def show():
            messagebox.showinfo("Watchlist update", text)

        self.after(0, show)

        # pushover (non-blocking)
        def push():
            try:
                user, token = get_pushover_creds()
                if user and token:
                    send_pushover(text, title="Watchlist update", user_key=user, app_token=token)
            except Exception:
                pass  # avoid crashing the UI on push failure

        threading.Thread(target=push, daemon=True).start()



    # ---------------- Shutdown ----------------
    def _on_close(self):
        self.poll_stop.set()
        self.destroy()

class PushoverDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Pushover Settings")
        self.resizable(False, False)
        self.user_var = tk.StringVar()
        self.token_var = tk.StringVar()

        # prefill from keyring/env
        u, t = get_pushover_creds()
        if u: self.user_var.set(u)
        if t: self.token_var.set(t)

        frm = ttk.Frame(self, padding=12); frm.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frm, text="User Key:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(frm, textvariable=self.user_var, width=48, show="•").grid(row=0, column=1, pady=4)
        ttk.Label(frm, text="App Token:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(frm, textvariable=self.token_var, width=48, show="•").grid(row=1, column=1, pady=4)

        btns = ttk.Frame(frm); btns.grid(row=2, column=0, columnspan=2, pady=(10,0))
        ttk.Button(btns, text="Test", command=self._on_test).pack(side=tk.LEFT)
        ttk.Button(btns, text="Save", command=self._on_save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Close", command=self.destroy).pack(side=tk.LEFT)

    def _on_test(self):
        try:
            send_pushover("✅ Test from MangaNotify", title="Pushover Test",
                          user_key=self.user_var.get().strip(),
                          app_token=self.token_var.get().strip())
            messagebox.showinfo("Pushover", "Test sent!")
        except Exception as e:
            messagebox.showerror("Pushover", f"Test failed:\n{e}")

    def _on_save(self):
        try:
            set_pushover_creds(self.user_var.get().strip(), self.token_var.get().strip())
            messagebox.showinfo("Pushover", "Saved to secure keychain.")
        except Exception as e:
            messagebox.showerror("Pushover", f"Save failed:\n{e}")


# ----------------------- Run -----------------------
if __name__ == "__main__":
    App().mainloop()
