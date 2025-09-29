// Shared state & constants
export const MIN_QUERY_LEN = 3;
export const TYPE_DEBOUNCE_MS = 500;

export const state = {
  q: "", page: 1, limit: 20, pagination: null,
  sortBy: localStorage.getItem("mn-sort-by")  || "title",
  sortDir: localStorage.getItem("mn-sort-dir") || "asc",
  unreadOnly: localStorage.getItem("mn-unread-only") === "true",
  showCovers: localStorage.getItem("mn-show-covers") !== "false",
  hideDropped: localStorage.getItem("mn-hide-dropped") === "true",
  autoRefresh: +(localStorage.getItem("mn-auto-refresh") || "0"),
  autoTimer: null,
  lastRefreshTs: null,
  online: navigator.onLine,
  filters: {
    status:        localStorage.getItem("mn-f-status") || "",
    type:          localStorage.getItem("mn-f-type") || "",
    has_anime:     localStorage.getItem("mn-f-has-anime") === "true",
    content_rating:localStorage.getItem("mn-f-cr") || ""
  },
  aborter: null,
  layout: localStorage.getItem("mn-layout") || "stack"
};

// tiny cache just for searches
export const searchCache = new Map();

// datetime helpers
export const dtFormatter = new Intl.DateTimeFormat(undefined, {
  year:"numeric", month:"short", day:"2-digit",
  hour:"2-digit", minute:"2-digit", hour12:false, timeZoneName:"short"
});
