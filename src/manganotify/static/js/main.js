// Entry point – wire everything
import "./api.js"; // just to ensure early fetch helpers in cache
import { initSettings } from "./settings.js";
import {wireSearchBox, applyLayout, search, loadWatchlist, selectTab} from "./ui.js";
import { initNotifications, loadNotifications } from "./notifications-ui.js";
import { state, MIN_QUERY_LEN } from "./state.js";
import { $ } from "./ui.js";

console.log("[MN] main.js loaded", import.meta.url);

queueMicrotask(async () => {
  try{
    initSettings();
    wireSearchBox();
    applyLayout(state.layout);
    initNotifications();
    // main.js
    const ENABLE_SHORTCUTS = false;
    if (ENABLE_SHORTCUTS) {
      const { initKeyboard } = await import("/keyboard.js");
      initKeyboard({
        focusSearch: () => document.getElementById("q")?.focus(),
        refreshWatchlist: () => loadWatchlist(),
        openSettings: () => openSettings(),
        toggleTheme: () => document.getElementById("theme")?.click(),
        selectTab: (name) => selectTab(name)
      });
    }

    // initial data
    await loadWatchlist();
    await loadNotifications();

    // if there is a query in URL, run a search immediately
    const qinit = $("#q")?.value.trim() || "";
    if(qinit.length >= MIN_QUERY_LEN){ state.q = qinit; state.page = 1; search(); }

    console.log("[MN] bootstrap complete");
  }catch(e){
    console.error("[MN] bootstrap failed:", e);
  }
});
