// ResilientUrban Service Worker for Offline Disaster Resilience
const CACHE_NAME = 'resilient-urban-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/login',
  '/citizen',
  '/admin',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/js/map.js',
  '/static/images/app_icon.png',
  '/manifest.json'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch(() => {});
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
