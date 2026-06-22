const CACHE_NAME = 'qs-pro-v2-cyber-baroque';

// Базовый арсенал: то, что нужно закэшировать при установке
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/game.js',
    '/static/js/icon-192.png',
    '/static/js/icon-512.png',
    '/static/js/manifest.json'
];

// 1. УСТАНОВКА: Прокачиваем кэш
self.addEventListener('install', (event) => {
    self.skipWaiting(); // Заставляем браузер немедленно активировать новый SW
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[SW] 🚀 Инициализация щита: кэшируем ядро');
            return cache.addAll(STATIC_ASSETS);
        })
    );
});

// 2. АКТИВАЦИЯ: Зачистка старых версий (Мусоросборщик)
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME)
                    .map(key => {
                        console.log('[SW] 🗑️ Аннигиляция старого кэша:', key);
                        return caches.delete(key);
                    })
            );
        })
    );
});

// 3. ПЕРЕХВАТ ЗАПРОСОВ: Мозг Саркофага
self.addEventListener('fetch', (event) => {
    const request = event.request;

    // СТРАТЕГИЯ А: Network First (Сначала Сеть, потом Кэш) 
    // Применяем для навигации (HTML) и наших HTMX запросов (/snippets/)
    if (request.headers.get('Accept').includes('text/html') || request.url.includes('/snippets/')) {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    // Если сеть есть и метод GET, сохраняем свежий ответ в кэш для будущих оффлайн сессий
                    if (request.method === 'GET' && response.status === 200) {
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
                    }
                    return response;
                })
                .catch(() => {
                    console.log('[SW] ⚠️ Сеть недоступна. Поднимаем архивы для:', request.url);
                    // Если сети нет, ищем в кэше
                    return caches.match(request).then((cachedResponse) => {
                        if (cachedResponse) return cachedResponse;
                        
                        // Если это был HTMX-запрос, а в кэше пусто, отдаем заглушку
                        if (request.headers.get('HX-Request')) {
                            return new Response(
                                "<div class='col-span-full p-8 border border-red-500/50 bg-red-900/20 rounded-2xl text-center shadow-[0_0_15px_rgba(239,68,68,0.2)]'>" +
                                "<p class='text-red-500 font-mono font-bold tracking-widest uppercase'>[ SYSTEM OFFLINE ]</p>" +
                                "<p class='text-xs text-red-400/70 mt-2 font-mono uppercase'>Связь с сервером утеряна. Невозможно извлечь данные.</p>" +
                                "</div>",
                                { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
                            );
                        }
                    });
                })
        );
        return;
    }

    // СТРАТЕГИЯ Б: Cache First (Сначала Кэш, потом Сеть)
    // Применяем для картинок, CSS, JS, шрифтов
    event.respondWith(
        caches.match(request).then((cachedResponse) => {
            return cachedResponse || fetch(request).then((networkResponse) => {
                // Динамически кэшируем загруженные картинки (например, из Pillow)
                if (request.method === 'GET' && networkResponse.status === 200 && request.url.includes('/static/')) {
                    const clone = networkResponse.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
                }
                return networkResponse;
            });
        })
    );
});