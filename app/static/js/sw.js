const CACHE_NAME = 'qs-pro-v3-cyber-baroque';

const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/game.js',
    '/static/js/icon-192.png',
    '/static/js/icon-512.png',
    '/manifest.json',
    '/static/js/translations.js',
    '/static/js/offline.js'
];

const DB_NAME = 'qs-pro-db';
const DB_VERSION = 1;

function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        request.onupgradeneeded = (e) => {
            const db = e.target.result;
            if (!db.objectStoreNames.contains('snippets')) {
                db.createObjectStore('snippets', { keyPath: 'id' });
            }
            if (!db.objectStoreNames.contains('sync-queue')) {
                db.createObjectStore('sync-queue', { keyPath: 'id', autoIncrement: true });
            }
        };
        request.onsuccess = (e) => resolve(e.target.result);
        request.onerror = (e) => reject(e.target.error);
    });
}

// Helper to escape HTML tags to prevent XSS
function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// HTML replica of python's render_snippet_cards for offline rendering
function renderOfflineSnippetsHTML(snippets, category = 'all', search_query = '') {
    let filtered = snippets;
    if (category && category !== 'all') {
        filtered = filtered.filter(s => s.category.toLowerCase() === category.toLowerCase());
    }
    
    if (search_query) {
        const q = search_query.toLowerCase();
        if (q.startsWith('#')) {
            filtered = filtered.filter(s => s.tags && s.tags.toLowerCase().includes(q));
        } else if (q.startsWith('lang:')) {
            const lang = q.replace('lang:', '').trim();
            filtered = filtered.filter(s => s.language && s.language.toLowerCase() === lang);
        } else {
            filtered = filtered.filter(s => {
                const target = `${s.content} ${s.note || ''} ${s.tags || ''} ${s.category} ${s.sub_category || ''}`.toLowerCase();
                return target.includes(q);
            });
        }
    }

    if (filtered.length === 0) {
        return "<div class='col-span-full text-center py-24 text-gray-500 font-mono tracking-widest text-base uppercase'>[ OFFLINE ] Архивы пусты... 🕵️‍♂️</div>";
    }

    // Sort by created_at descending (newest first)
    filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    let html = "";
    for (const s of filtered) {
        const accent = ["study", "учеба"].includes(s.category.toLowerCase()) ? "acid" : "electric";
        const shadow = accent === "acid" ? "hover:shadow-[0_0_15px_rgba(57,255,20,0.1)]" : "hover:shadow-neon";
        
        const safe_text = escapeHtml(s.content);
        const safe_note = s.note ? escapeHtml(s.note) : "";
        
        const created_at_str = new Date(s.created_at).toLocaleString();

        const imageHtml = s.image_url ? `
        <div class="mb-5 rounded-xl overflow-hidden border border-gray-800/80">
            <img src="${s.image_url}" class="w-full h-auto object-cover opacity-90 group-hover:opacity-100 transition-all"/>
        </div>` : '';

        const noteHtml = safe_note ? `
        <div class="mt-4 hidden"><p id="note-${s.id}">${safe_note}</p></div>` : '';

        const deleteAttr = String(s.id).startsWith('temp-') 
            ? `@click="alert('Сниппет будет удален после синхронизации сети');"`
            : `hx-delete="/snippets/delete/${s.id}" hx-target="#snippet-{s.id}" hx-swap="outerHTML swap:0.4s"`;

        html += `
        <div id="snippet-${s.id}" class="bg-darkglass/50 backdrop-blur-md border border-gray-800 rounded-2xl p-6 transition-all duration-300 group hover:border-${accent}/50 ${shadow} flex flex-col">
            <div class="flex justify-between items-start mb-5">
                <div class="flex flex-col gap-1.5">
                    <span class="text-xs md:text-sm font-mono text-${accent} uppercase tracking-widest font-bold">${s.category} // ${s.sub_category}</span>
                    <div class="flex gap-1.5 mt-1 text-xs text-gray-400 font-mono">${s.tags || ""}</div>
                </div>
                <div class="flex gap-3">
                    <button @click="viewData = { cat: '${s.category}', sub: '${s.sub_category}', tags: '${s.tags || ''}', image: '${s.image_url || ''}', note: document.getElementById('note-${s.id}') ? document.getElementById('note-${s.id}').innerText : '', text: document.getElementById('code-${s.id}').innerText }; showViewModal = true" 
                            class="opacity-0 group-hover:opacity-100 text-electric hover:text-white transition-all cursor-pointer" title="Развернуть">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/></svg>
                    </button>
                    <button ${deleteAttr} class="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-500 transition-all cursor-pointer">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                    </button>
                </div>
            </div>
            
            ${imageHtml}
            
            <div class="bg-midnight border border-gray-800 rounded-lg p-4 overflow-hidden relative flex-grow">
                <pre id="code-${s.id}" class="text-gray-200 whitespace-pre-wrap text-sm md:text-base font-mono max-h-40 overflow-hidden" style="-webkit-mask-image: linear-gradient(180deg, #000 60%, transparent);">${safe_text}</pre>
            </div>
            
            ${noteHtml}
            
            <div class="mt-5 pt-4 border-t border-gray-800/60 flex justify-between items-center text-xs text-gray-500 font-mono">
                <span>[OFFLINE] ${created_at_str}</span>
            </div>
        </div>
        `;
    }
    return html;
}

// 1. INSTALL
self.addEventListener('install', (event) => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[SW] 🚀 Initializing shell cache...');
            return cache.addAll(STATIC_ASSETS);
        })
    );
});

// 2. ACTIVATE
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME)
                    .map(key => {
                        console.log('[SW] 🗑️ Cleaning old cache:', key);
                        return caches.delete(key);
                    })
            );
        }).then(() => self.clients.claim())
    );
});

// 3. FETCH
self.addEventListener('fetch', (event) => {
    const request = event.request;

    // Security check: Ignore authentication & tokens (strict pass-through to network)
    if (
        request.url.includes('/auth/') || 
        request.url.includes('/login') || 
        request.url.includes('/register') || 
        request.method === 'PUT'
    ) {
        return; 
    }

    // Intercept Snippets GET/POST/DELETE for Local-First Offline Mode
    if (request.url.includes('/snippets/')) {
        // --- 1. GET Snippets List ---
        if (request.method === 'GET' && request.url.includes('/snippets/list')) {
            event.respondWith(
                fetch(request)
                    .then((response) => {
                        // Dynamically update cache when online
                        if (response.status === 200) {
                            const clone = response.clone();
                            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
                        }
                        return response;
                    })
                    .catch(async () => {
                        console.log('[SW] ⚠️ Offline. Fetching snippets list from IndexedDB.');
                        const url = new URL(request.url);
                        const category = url.searchParams.get('category') || 'all';
                        const q = url.searchParams.get('q') || '';
                        
                        try {
                            const db = await openDB();
                            const store = db.transaction('snippets', 'readonly').objectStore('snippets');
                            
                            return new Promise((resolve) => {
                                const req = store.getAll();
                                req.onsuccess = () => {
                                    const html = renderOfflineSnippetsHTML(req.result, category, q);
                                    resolve(new Response(html, {
                                        headers: { 'Content-Type': 'text/html; charset=utf-8' }
                                    }));
                                };
                                req.onerror = () => {
                                    resolve(new Response('Local Database Error', { status: 500 }));
                                };
                            });
                        } catch (err) {
                            return new Response('Offline Mode DB error', { status: 500 });
                        }
                    })
            );
            return;
        }

        // --- 2. POST Snippet Create ---
        if (request.method === 'POST' && request.url.includes('/snippets/create')) {
            event.respondWith(
                fetch(request.clone())
                    .catch(async () => {
                        console.log('[SW] ⚠️ Offline. Intercepting creation and queueing.');
                        try {
                            const formData = await request.clone().formData();
                            const category = formData.get('category');
                            const content = formData.get('content');
                            const sub_category = formData.get('sub_category') || 'General';
                            const note = formData.get('note') || '';
                            const tags = formData.get('tags') || '';
                            const parent_snippet_id = formData.get('parent_snippet_id') || null;
                            const reminder_at = formData.get('reminder_at') || null;

                            // Native image blob extraction
                            const imageFile = formData.get('image');
                            let image_url = null;
                            let imageBlob = null;
                            if (imageFile && imageFile.size > 0) {
                                imageBlob = imageFile;
                                try {
                                    image_url = URL.createObjectURL(imageFile);
                                } catch (e) {
                                    image_url = '/static/js/icon-192.png';
                                }
                            }

                            const db = await openDB();
                            
                            // Save to sync queue
                            const syncTx = db.transaction('sync-queue', 'readwrite');
                            await syncTx.objectStore('sync-queue').put({
                                action: 'create',
                                url: request.url,
                                data: {
                                    category,
                                    content,
                                    sub_category,
                                    note,
                                    tags,
                                    parent_snippet_id,
                                    reminder_at,
                                    image: imageBlob
                                }
                            });

                            // Add to local preview
                            const tempId = 'temp-' + Date.now();
                            const snippetTx = db.transaction('snippets', 'readwrite');
                            await snippetTx.objectStore('snippets').put({
                                id: tempId,
                                category: category.toLowerCase(),
                                sub_category,
                                tags,
                                content,
                                note,
                                image_url,
                                created_at: new Date().toISOString()
                            });

                            // Query local database to render the list with the new temp snippet
                            const readTx = db.transaction('snippets', 'readonly');
                            return new Promise((resolve) => {
                                const req = readTx.objectStore('snippets').getAll();
                                req.onsuccess = () => {
                                    const html = renderOfflineSnippetsHTML(req.result, category, '');
                                    resolve(new Response(html, {
                                        headers: { 'Content-Type': 'text/html; charset=utf-8' }
                                    }));
                                };
                            });
                        } catch (err) {
                            return new Response('<span class="text-red-400">Offline creation error</span>', { status: 500 });
                        }
                    })
            );
            return;
        }

        // --- 3. DELETE Snippet ---
        if (request.method === 'DELETE' && request.url.includes('/snippets/delete/')) {
            event.respondWith(
                fetch(request.clone())
                    .catch(async () => {
                        console.log('[SW] ⚠️ Offline. Intercepting deletion and queueing.');
                        try {
                            const urlParts = request.url.split('/');
                            const snippetIdStr = urlParts[urlParts.length - 1];
                            const snippetId = isNaN(snippetIdStr) ? snippetIdStr : parseInt(snippetIdStr, 10);
                            
                            const db = await openDB();
                            
                            // Queue delete
                            const syncTx = db.transaction('sync-queue', 'readwrite');
                            await syncTx.objectStore('sync-queue').put({
                                action: 'delete',
                                url: request.url,
                                snippetId: snippetId
                            });
                            
                            // Remove locally
                            const snippetTx = db.transaction('snippets', 'readwrite');
                            await snippetTx.objectStore('snippets').delete(snippetId);
                            
                            return new Response('', { status: 200 });
                        } catch (err) {
                            return new Response('Offline deletion error', { status: 500 });
                        }
                    })
            );
            return;
        }
    }

    // Static Assets Fallback (Cache First)
    if (request.method === 'GET') {
        event.respondWith(
            caches.match(request).then((cachedResponse) => {
                return cachedResponse || fetch(request).then((networkResponse) => {
                    if (networkResponse.status === 200 && (request.url.includes('/static/') || request.url.includes('/manifest.json'))) {
                        const clone = networkResponse.clone();
                        caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
                    }
                    return networkResponse;
                }).catch(() => {
                    // Return shell if HTML navigation fails offline
                    if (request.headers.get('Accept').includes('text/html')) {
                        return caches.match('/');
                    }
                });
            })
        );
    }
});