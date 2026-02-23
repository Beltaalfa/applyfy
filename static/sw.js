/* Service Worker Applyfy Painel - PWA installável */
const CACHE = 'applyfy-v1';

self.addEventListener('install', function(e) {
  self.skipWaiting();
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(keys.filter(function(k) { return k !== CACHE; }).map(function(k) { return caches.delete(k); }));
    }).then(function() { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function(e) {
  /* network-first: sempre tenta rede; fallback para cache só em falha */
  if (e.request.url.match(/\/api\//)) return;
  e.respondWith(
    fetch(e.request).catch(function() {
      return caches.match(e.request).then(function(c) { return c || caches.match('/'); });
    })
  );
});
