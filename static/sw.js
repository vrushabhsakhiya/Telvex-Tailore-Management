const CACHE_NAME = 'talvex-v2';
const ASSETS_TO_CACHE = [
    '/',
    '/static/css/style.css',
    '/static/js/custom_scripts.js',
    '/static/js/ajax_nav.js',
    '/static/manifest.json'
];

// Install Event - Cache Static Assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
});

// Activate Event - Clean old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(keyList.map((key) => {
                if (key !== CACHE_NAME) {
                    return caches.delete(key);
                }
            }));
        })
    );
});

// Fetch Event - Network First, falling back to cache
self.addEventListener('fetch', (event) => {
    // Use Network First strategy for HTML requests to ensure fresh data
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(() => {
                    return caches.match(event.request);
                })
        );
    } else {
        // For other assets (CSS, JS, Images), try cache first, then network
        event.respondWith(
            caches.match(event.request).then((response) => {
                return response || fetch(event.request);
            })
        );
    }
});
