/**
 * Auto-D Kenya — Service Worker
 * ─────────────────────────────────────────────────────────────
 * Strategy:
 *  - App-shell pages & the offline fallback are precached on install.
 *  - HTML navigations: network-first, falling back to cache, then
 *    to offline.html if nothing is cached (keeps content fresh while
 *    still working offline).
 *  - Static assets (css/js/png/svg/fonts): cache-first, falling back
 *    to network, and caching whatever the network returns.
 *  - Old cache versions are cleaned up on activate — bump CACHE_VERSION
 *    whenever you change any precached file so clients pick up updates.
 * ─────────────────────────────────────────────────────────────
 */

'use strict';

var CACHE_VERSION = 'autod-v2';
var STATIC_CACHE = CACHE_VERSION + '-static';

var PRECACHE_URLS = [
    'index.html',
    'login.html',
    'signup.html',
    'dashboard.html',
    'offline.html',
    'site.webmanifest',
    'assets/auth.js',
    'assets/favicon.svg',
    'assets/favicon-32x32.png',
    'assets/apple-touch-icon.png',
    'assets/icon-192.png',
    'assets/icon-512.png'
];

self.addEventListener('install', function (event) {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(function (cache) {
                return cache.addAll(PRECACHE_URLS);
            })
            .then(function () {
                return self.skipWaiting();
            })
    );
});

self.addEventListener('activate', function (event) {
    event.waitUntil(
        caches.keys()
            .then(function (keys) {
                return Promise.all(
                    keys
                        .filter(function (key) { return key.indexOf(CACHE_VERSION) !== 0; })
                        .map(function (key) { return caches.delete(key); })
                );
            })
            .then(function () {
                return self.clients.claim();
            })
    );
});

function isHTMLRequest(request) {
    return request.mode === 'navigate' ||
        (request.headers.get('accept') || '').indexOf('text/html') !== -1;
}

self.addEventListener('fetch', function (event) {
    var request = event.request;

    // Only handle same-origin GET requests; let everything else
    // (CDN fonts/icons, cross-origin API calls) pass straight through.
    if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) {
        return;
    }

    if (isHTMLRequest(request)) {
        event.respondWith(
            fetch(request)
                .then(function (response) {
                    var copy = response.clone();
                    caches.open(STATIC_CACHE).then(function (cache) { cache.put(request, copy); });
                    return response;
                })
                .catch(function () {
                    return caches.match(request).then(function (cached) {
                        return cached || caches.match('offline.html');
                    });
                })
        );
        return;
    }

    event.respondWith(
        caches.match(request).then(function (cached) {
            if (cached) return cached;
            return fetch(request).then(function (response) {
                var copy = response.clone();
                caches.open(STATIC_CACHE).then(function (cache) { cache.put(request, copy); });
                return response;
            });
        })
    );
});
