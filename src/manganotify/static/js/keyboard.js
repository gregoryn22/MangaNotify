// static/js/keyboard.js
export function initKeyboard({ focusSearch, refreshWatchlist, openSettings, toggleTheme, selectTab }) {
  const isFormField = (el) =>
    !!el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName));

  window.addEventListener("keydown", (e) => {
    // Let the browser do its thing if we’re in a field *and* no modifier is held
    if (!e.ctrlKey && !e.metaKey) return;
    if (isFormField(e.target)) {
      // Only allow modifier shortcuts to pass; otherwise ignore
      // (we’re already requiring ctrl/meta above)
    }

    // Normalize key (lowercase single-character, named for others)
    const key = (e.key || "").toLowerCase();

    // ---- Shortcuts (choose a tiny, conflict-safe set) ----
    // Cmd/Ctrl + K : focus search (common pattern in web apps)
    if (key === "k") {
      e.preventDefault();
      focusSearch?.();
      return;
    }

    // Cmd/Ctrl + , : open settings (macOS convention; works on Windows too)
    if (key === ",") {
      e.preventDefault();
      openSettings?.();
      return;
    }

    // Cmd/Ctrl + Shift + N : go to Notifications tab (avoid browser conflicts)
    if ((e.shiftKey && key === "n")) {
      e.preventDefault();
      selectTab?.("notif");
      return;
    }

    // Cmd/Ctrl + Alt + T : toggle theme (avoid Ctrl+T = new tab)
    if (e.altKey && key === "t") {
      e.preventDefault();
      toggleTheme?.();
      return;
    }

    // If you ever want a refresh shortcut, pick a non-conflicting one:
    // Cmd/Ctrl + Alt + R (avoid Ctrl+R which reloads the page)
    if (e.altKey && key === "r") {
      e.preventDefault();
      refreshWatchlist?.();
      return;
    }
  });
}
