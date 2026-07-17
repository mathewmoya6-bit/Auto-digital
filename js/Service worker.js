// ─── SERVICE WORKER FOR AUTO-D KENYA ──────────────────────────
// This service worker handles offline caching and PWA functionality

const CACHE_NAME = 'auto-d-cache-v1';
const ASSETS = [
  '/',
  '/index.html',
  '/login.html',
  '/signup.html',
  '/dashboard.html',
  '/instant-value.html',
  '/mileage.html',
  '/ownership-cost.html',
  '/assets/auth.js',
  '/assets/supabase-client.js',
  '/assets/supabase.js'
];

// Install event - cache core assets
self.addEventListener('install', function(event) {
  console.log('[Service Worker] Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('[Service Worker] Caching assets...');
        return cache.addAll(ASSETS).catch(function(error) {
          console.error('[Service Worker] Failed to cache:', error);
        });
      })
      .then(function() {
        console.log('[Service Worker] Installation complete');
        return self.skipWaiting();
      })
  );
});

// Activate event - clean old caches
self.addEventListener('activate', function(event) {
  console.log('[Service Worker] Activating...');
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            console.log('[Service Worker] Removing old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
    .then(function() {
      console.log('[Service Worker] Activation complete');
      return self.clients.claim();
    })
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', function(event) {
  var request = event.request;
  var url = new URL(request.url);

  // Skip cross-origin requests (except CDN)
  if (url.origin !== self.location.origin && !url.hostname.includes('cdnjs')) {
    event.respondWith(fetch(request));
    return;
  }

  // Skip non-GET requests
  if (request.method !== 'GET') {
    event.respondWith(fetch(request));
    return;
  }

  // Check if request is for an asset that should be cached
  var shouldCache = ASSETS.some(function(asset) {
    return url.pathname === asset || url.pathname.endsWith('.js') || url.pathname.endsWith('.css');
  });

  if (!shouldCache) {
    event.respondWith(fetch(request));
    return;
  }

  // Try cache first, fallback to network
  event.respondWith(
    caches.match(request).then(function(cachedResponse) {
      if (cachedResponse) {
        console.log('[Service Worker] Serving from cache:', url.pathname);
        return cachedResponse;
      }

      console.log('[Service Worker] Fetching from network:', url.pathname);
      return fetch(request).then(function(networkResponse) {
        // Cache the fetched response for future use
        if (networkResponse && networkResponse.status === 200) {
          var clonedResponse = networkResponse.clone();
          caches.open(CACHE_NAME).then(function(cache) {
            cache.put(request, clonedResponse);
            console.log('[Service Worker] Cached:', url.pathname);
          });
        }
        return networkResponse;
      }).catch(function(error) {
        console.error('[Service Worker] Fetch failed:', error);
        // Return offline fallback if available
        return caches.match('/index.html');
      });
    })
  );
});

// Handle push notifications (optional)
self.addEventListener('push', function(event) {
  var data = event.data ? event.data.text() : 'New update available!';
  var options = {
    body: data,
    icon: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192"%3E%3Crect width="192" height="192" fill="%23eab308" rx="30"/%3E%3Ctext x="96" y="140" font-size="110" text-anchor="middle" fill="%23000"%3E🚗%3C/text%3E%3C/svg%3E',
    badge: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192"%3E%3Crect width="192" height="192" fill="%23eab308" rx="30"/%3E%3Ctext x="96" y="140" font-size="110" text-anchor="middle" fill="%23000"%3E🚗%3C/text%3E%3C/svg%3E',
    vibrate: [200, 100, 200]
  };

  event.waitUntil(
    self.registration.showNotification('Auto-D Kenya', options)
  );
});
