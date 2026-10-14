/*
 * Service worker — PWA install, and a cache that cannot serve a stale app.
 *
 * Three strategies, because the three kinds of request want different things:
 *
 *   API            never cached. Coin balances, battle scores and vote counts
 *                  are the whole game; a stale one is worse than a spinner.
 *
 *   the HTML shell network first, cache only as an offline fallback. This is
 *                  the one that matters: index.html names the hashed JS
 *                  bundle, so caching it first would pin a returning user to
 *                  whatever build they first opened — every later deploy
 *                  invisible to them until the cache name happened to change.
 *                  That is exactly what happened before this rewrite.
 *
 *   hashed assets  cache first. /app/assets/index-<hash>.js is immutable by
 *                  construction: a new build produces a new filename, so a
 *                  cached copy can never be the wrong one. Artwork under
 *                  /media is versioned by deploy rather than by name, so it
 *                  is revalidated in the background after being served.
 */
const CACHE = "colafest-v2";
const SHELL = ["/app/", "/app/manifest.webmanifest", "/app/icon.svg"];

// Anything under these must always come from the network.
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

// Content-addressed by build hash: safe to serve from cache forever.
const IMMUTABLE = /\/app\/assets\/.+\.[0-9a-zA-Z_-]{8,}\.(js|css)$/;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) =>
      // A shell file that 404s must not abort the whole install and leave the
      // worker permanently uninstalled.
      Promise.allSettled(SHELL.map((path) => cache.add(path)))
    )
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (event.request.method !== "GET") return;
  if (LIVE_PATHS.some((path) => url.pathname.startsWith(path))) return;
  if (url.origin !== self.location.origin) return;

  // The shell: a navigation, or index.html itself.
  const isShell =
    event.request.mode === "navigate" ||
    url.pathname === "/app/" ||
    url.pathname === "/app/index.html";

  if (isShell) {
    event.respondWith(networkFirst(event.request));
    return;
  }

  if (IMMUTABLE.test(url.pathname)) {
    event.respondWith(cacheFirst(event.request, { revalidate: false }));
    return;
  }

  // Artwork and the manifest: fast, but checked in the background.
  event.respondWith(cacheFirst(event.request, { revalidate: true }));
});

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const copy = response.clone();
      caches.open(CACHE).then((cache) => cache.put(request, copy));
    }
    return response;
  } catch {
    // Offline. The cached shell still boots the app, which then shows its own
    // error states for whatever it cannot fetch.
    const cached = await caches.match(request);
    return cached || caches.match("/app/");
  }
}

async function cacheFirst(request, { revalidate }) {
  const cached = await caches.match(request);

  if (cached) {
    if (revalidate) {
      // Refresh in the background; this response is already on its way.
      fetch(request)
        .then((response) => {
          if (response.ok) {
            caches.open(CACHE).then((cache) => cache.put(request, response));
          }
        })
        .catch(() => {});
    }
    return cached;
  }

  const response = await fetch(request);
  if (response.ok) {
    const copy = response.clone();
    caches.open(CACHE).then((cache) => cache.put(request, copy));
  }
  return response;
}
