// AUTO-D Kenya — Service Worker
// Minimal network-first service worker.
// Provides the service-worker functionality required for PWA/TWA
// without introducing aggressive caching.

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  // Only handle GET requests.
  if (event.request.method !== "GET") {
    return;
  }

  event.respondWith(
    fetch(event.request).catch(() => {
      // Let the browser handle the failed request naturally.
      // No offline cache is configured yet.
      return new Response(
        "AUTO-D is currently offline. Please check your internet connection and try again.",
        {
          status: 503,
          headers: {
            "Content-Type": "text/plain; charset=utf-8"
          }
        }
      );
    })
  );
});
