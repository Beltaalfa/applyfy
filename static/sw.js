/* Applyfy painel — SW mínimo. Sem fetch handler: não intercepta navegação nem /auth/logout.
 * Não usar clients.claim(): com skipWaiting() o Chrome pode lançar
 * InvalidStateError: "Only the active worker can claim clients" (visto em sw.js:1).
 * bump: applyfy-v5
 */
const CACHE = "applyfy-v5";

self.addEventListener("install", function () {
  self.skipWaiting();
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.map(function (k) {
          return caches.delete(k);
        })
      );
    })
  );
});
