/* Offline support.
 *
 * There is no reception in Zion, Bryce, Antelope, Monument Valley or much of
 * the Grand Canyon — exactly where the itinerary is needed. Everything the
 * page needs is precached on first visit.
 *
 * Two strategies, on purpose:
 *   shell + art  cache-first, because they rarely change and must open instantly
 *   data/*.json  network-first, because the sync job rewrites them 3x a day
 *                and a stale expense total is worse than a slow one
 *
 * Bump CACHE when the shell changes; old caches are dropped on activate.
 */
const CACHE = "grand-circle-v4";

const DAY_NUMS = ["05","06","07","08","09","10","11","12","13","14","15","16","17","18","19","20"];

const SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icons/apple-touch-icon.png",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/favicon-32.png",
  "./data/days.json",
  "./data/tasks.json",
  "./data/expenses.json",
  "./data/places.json",
  "./data/packing.json",
  "./data/flights.json",
  "./data/emergency.json",
  // real day photos (what the page actually renders) ...
  ...DAY_NUMS.map(d => `./images/day-2026-08-${d}.webp`),
  // ...and the generated SVGs kept as the fallback if a day has no photo yet
  ...DAY_NUMS.map(d => `./images/day-2026-08-${d}.svg`)
];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE)
      // addAll is all-or-nothing; one 404 would leave the site with no cache
      .then(c => Promise.allSettled(SHELL.map(u => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("message", e => {
  if (e.data === "skipWaiting") self.skipWaiting();
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  /* Open-Meteo and Google Maps are never cached here — the page keeps its own
     copy of the last forecast in localStorage, and map tiles are not ours. */
  if (url.origin !== self.location.origin) return;

  /* The page itself is network-first. Serving it cache-first meant every
     deploy stayed invisible until a second reload, and a browser could sit on
     a stale layout indefinitely — which is exactly what happened with the
     two-column pager fix. Offline still falls back to the cached copy. */
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req)
        .then(res => {
          const forReq = res.clone(), forIndex = res.clone();
          caches.open(CACHE).then(c => {
            c.put(req, forReq);
            // GitHub Pages serves the directory URL, so normalise it too
            c.put("./index.html", forIndex);
          });
          return res;
        })
        .catch(() => caches.match(req).then(hit => hit || caches.match("./index.html")))
    );
    return;
  }

  if (url.pathname.includes("/data/")) {
    e.respondWith(
      fetch(req)
        .then(res => {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  e.respondWith(
    caches.match(req).then(hit => hit || fetch(req).then(res => {
      if (res.ok && res.type === "basic") {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(req, copy));
      }
      return res;
    }).catch(() => caches.match("./index.html")))
  );
});
