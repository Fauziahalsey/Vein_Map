const C = 'scan-v4';
const FILES = ['/', '/index.html', '/facilities.json', '/zxing.min.js'];

self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(caches.open(C).then(c => c.addAll(FILES)));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== C).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// network first, cache as the offline fallback
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET' || e.request.url.includes('/api/')) return;
  e.respondWith(
    fetch(e.request)
      .then(res => {
        const copy = res.clone();
        caches.open(C).then(c => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request, {ignoreSearch: true}))
  );
});