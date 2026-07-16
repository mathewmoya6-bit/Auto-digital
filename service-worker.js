// ============================================
// AUTO-D KENYA - Service Worker
// ============================================

const CACHE_NAME = 'auto-d-kenya-v3';
const ASSETS = [
  '/dashboard.html',
  '/mileage.html',
  '/instant-value.html',
  '/ownership-cost.html',
  '/full-report.html',
  '/index.html',
  '/manifest.json',
  '/service-worker.js',
  '/icons/icon-72.png',
  '/icons/icon-96.png',
  '/icons/icon-128.png',
  '/icons/icon-144.png',
  '/icons/icon-152.png',
  '/icons/icon-192.png',
  '/icons/icon-384.png',
  '/icons/icon-512.png'
];

// External assets
const EXTERNAL_ASSETS = [
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap',
  'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2'
];

// ============================================
// INSTALL
// ============================================
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[Service Worker] Caching assets');
        return cache.addAll([...ASSETS, ...EXTERNAL_ASSETS]);
      })
      .then(() => {
        console.log('[Service Worker] Installation complete');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[Service Worker] Installation failed:', error);
      })
  );
});

// ============================================
// ACTIVATE
// ============================================
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME) {
              console.log('[Service Worker] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('[Service Worker] Activation complete');
        return self.clients.claim();
      })
  );
});

// ============================================
// FETCH - Offline-first strategy
// ============================================
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Skip cross-origin requests except CDN resources
  if (url.origin !== self.location.origin && 
      !url.origin.includes('cdn.jsdelivr.net') && 
      !url.origin.includes('fonts.googleapis.com') && 
      !url.origin.includes('fonts.gstatic.com') && 
      !url.origin.includes('supabase.co')) {
    return;
  }

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip API requests
  if (url.pathname.includes('/api/')) {
    return;
  }

  event.respondWith(
    caches.match(request)
      .then((cachedResponse) => {
        // Return cached response if available
        if (cachedResponse) {
          console.log('[Service Worker] Serving from cache:', request.url);
          
          // Refresh cache in background for HTML pages
          if (url.pathname.endsWith('.html') || url.pathname === '/' || url.pathname === '/dashboard') {
            fetchAndCache(request);
          }
          
          return cachedResponse;
        }

        // Network fallback
        console.log('[Service Worker] Fetching from network:', request.url);
        return fetchAndCache(request);
      })
      .catch((error) => {
        console.error('[Service Worker] Fetch failed:', error);
        
        // Return offline fallback for HTML pages
        if (request.headers.get('accept').includes('text/html')) {
          return caches.match('/dashboard.html') || new Response(
            `<!DOCTYPE html>
            <html>
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <title>Auto-D Kenya — Offline</title>
              <style>
                body {
                  font-family: 'Inter', sans-serif;
                  background: #0f172a;
                  color: #f8fafc;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  min-height: 100vh;
                  margin: 0;
                  padding: 20px;
                  text-align: center;
                }
                .offline-box {
                  max-width: 400px;
                  padding: 40px;
                  background: #1e293b;
                  border-radius: 12px;
                  border: 1px solid #334155;
                }
                .offline-box .icon { font-size: 48px; margin-bottom: 16px; }
                .offline-box h1 { font-size: 24px; margin-bottom: 8px; }
                .offline-box p { color: #cbd5e1; margin-bottom: 20px; }
                .btn {
                  background: #eab308;
                  color: #0f172a;
                  border: none;
                  padding: 12px 24px;
                  border-radius: 8px;
                  font-weight: 700;
                  cursor: pointer;
                  font-size: 14px;
                }
                .btn:hover { background: #facc15; }
              </style>
            </head>
            <body>
              <div class="offline-box">
                <div class="icon">🚗</div>
                <h1>You're Offline</h1>
                <p>Please check your internet connection to access Auto-D Kenya.</p>
                <button class="btn" onclick="location.reload()">Retry Connection</button>
              </div>
            </body>
            </html>`,
            {
              status: 503,
              statusText: 'Service Unavailable',
              headers: { 'Content-Type': 'text/html' }
            }
          );
        }

        return new Response('Network error occurred', {
          status: 503,
          statusText: 'Service Unavailable'
        });
      })
  );
});

// ============================================
// HELPERS
// ============================================

// Fetch and cache a request
async function fetchAndCache(request) {
  try {
    const networkResponse = await fetch(request);
    
    // Only cache successful responses
    if (networkResponse.status === 200) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
      console.log('[Service Worker] Cached:', request.url);
    }
    
    return networkResponse;
  } catch (error) {
    throw error;
  }
}

// ============================================
// PUSH NOTIFICATIONS
// ============================================
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'Auto-D Kenya';
  const body = data.body || 'New update available for your vehicle!';
  const icon = data.icon || '/icons/icon-192.png';
  
  event.waitUntil(
    self.registration.showNotification(title, {
      body: body,
      icon: icon,
      badge: '/icons/icon-96.png',
      vibrate: [200, 100, 200],
      data: {
        url: data.url || '/dashboard.html'
      }
    })
  );
});

// ============================================
// NOTIFICATION CLICK
// ============================================
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  const url = event.notification.data?.url || '/dashboard.html';
  
  event.waitUntil(
    clients.matchAll({ type: 'window' })
      .then((clientList) => {
        // If a window is already open, focus it
        for (const client of clientList) {
          if (client.url.includes(url) && 'focus' in client) {
            return client.focus();
          }
        }
        // Otherwise, open a new window
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
  );
});

// ============================================
// BACKGROUND SYNC
// ============================================
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-vehicles') {
    event.waitUntil(syncVehicles());
  }
});

async function syncVehicles() {
  try {
    // Attempt to sync any pending vehicle data
    console.log('[Service Worker] Syncing vehicle data...');
    // In production, you would implement actual sync logic here
    return Promise.resolve();
  } catch (error) {
    console.error('[Service Worker] Sync failed:', error);
  }
}
