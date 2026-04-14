/* 伊丹バス PWA — 最小構成の Service Worker（インストール要件用） */

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

// オフライン用の事前キャッシュは行わず、常にネットワークへ委譲
self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
