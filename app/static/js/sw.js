const CACHE_NAME = 'qs-pro-v1';
// Список файлов, которые приложение сохранит в память телефона
const ASSETS = [
  '/',
  '/static/js/icon-192.png',
  '/static/js/icon-512.png',
  '/static/manifest.json'
];

// Установка: открываем хранилище и записываем туда иконки
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Кэшируем ресурсы');
      return cache.addAll(ASSETS);
    })
  );
});

// Перехват запросов: если иконка уже есть в памяти, не качаем её снова
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});