/*
 * Service worker — PWA install and a cache for the app shell.
 *
 * Deliberately narrow. It caches the built shell (HTML, JS, CSS, artwork)
 * so a reopened app paints instantly, and it NEVER caches API responses:
 * coin balances, battle scores and vote counts are the whole game, and a
 * stale one is worse than a spinner. Anything under an API path goes
 * straight to the network, always.
 */
const CACHE = "colafest-shell-v1";
const SHELL = ["/app/", "/app/index.html", "/app/manifest.webmanifest", "/app/icon.svg"];

// Requests that must never be served from cache.
const LIVE_PATHS = [
  "/auth",
  "/users",
  "/avatar",
  "/clothing",
  "/wardrobe",
  "/competitions",
  "/competition-requests",
  "/leaderboard",
  "/notifications",
  "/qr",
  "/config",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  const isLive = LIVE_PATHS.some((path) => url.pathname.startsWith(path));

  if (event.request.method !== "GET" || isLive) {
    return; // straight to the network
  }

  // Cache-first for the shell and the artwork; both are versioned by build
  // hash or replaced wholesale, so a stale copy cannot be wrong for long.
  event.respondWith(
    caches.match(event.request).then(
      (hit) =>
        hit ||
        fetch(event.request).then((response) => {
          if (response.ok && url.origin === self.location.origin) {
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
    )
  );
});
