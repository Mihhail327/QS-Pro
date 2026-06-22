// RellixCore :: Local-First Offline Sync Layer

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

// Parse snippets currently displayed on the page and save to IndexedDB
async function parseAndStoreSnippets() {
    try {
        const db = await openDB();
        const cards = document.querySelectorAll('div[id^="snippet-"]');
        const tx = db.transaction('snippets', 'readwrite');
        const store = tx.objectStore('snippets');
        
        // Keep offline temporary snippets
        const request = store.getAll();
        request.onsuccess = () => {
            const existing = request.result;
            const tempSnippets = existing.filter(s => String(s.id).startsWith('temp-'));
            
            store.clear().onsuccess = () => {
                // Write temporary snippets back
                for (const temp of tempSnippets) {
                    store.put(temp);
                }
                
                // Parse new ones
                cards.forEach(card => {
                    const idStr = card.id.replace('snippet-', '');
                    const id = isNaN(idStr) ? idStr : parseInt(idStr, 10);
                    if (String(id).startsWith('temp-')) return;

                    const headerEl = card.querySelector('span.font-bold') || card.querySelector('span.text-xs');
                    const headerText = headerEl ? headerEl.textContent : '';
                    const [category, sub_category] = headerText.split(' // ').map(s => s.trim());
                    
                    const tagsEl = card.querySelector('div.flex-col div.flex') || card.querySelector('.flex.gap-1\\.5');
                    const tags = tagsEl ? tagsEl.textContent.trim() : '';
                    
                    const codeEl = card.querySelector(`pre[id^="code-"]`);
                    const content = codeEl ? codeEl.textContent : '';
                    
                    const noteEl = card.querySelector(`p[id^="note-"]`);
                    const note = noteEl ? noteEl.textContent : '';
                    
                    const imgEl = card.querySelector('img');
                    const image_url = imgEl ? imgEl.getAttribute('src') : null;
                    
                    const dateEl = card.querySelector('div.mt-5 span') || card.querySelector('div.border-t span');
                    const created_at = dateEl ? dateEl.textContent.trim() : new Date().toISOString();
                    
                    store.put({
                        id,
                        category: category ? category.toLowerCase() : 'all',
                        sub_category: sub_category || 'General',
                        tags,
                        content,
                        note,
                        image_url,
                        created_at
                    });
                });
            };
        };
    } catch (err) {
        console.error('[Offline] Error parsing snippets:', err);
    }
}

// Background sync queue runner
async function syncOfflineQueue() {
    if (!navigator.onLine) return;
    
    try {
        const db = await openDB();
        const tx = db.transaction('sync-queue', 'readonly');
        const store = tx.objectStore('sync-queue');
        
        const req = store.getAll();
        req.onsuccess = async () => {
            const queue = req.result;
            if (queue.length === 0) return;
            
            console.log(`[Offline] Syncing ${queue.length} offline operations...`);
            
            for (const item of queue) {
                try {
                    if (item.action === 'create') {
                        // Recreate form data
                        const formData = new FormData();
                        for (const key in item.data) {
                            if (item.data[key] !== null) {
                                formData.append(key, item.data[key]);
                            }
                        }
                        
                        const res = await fetch(item.url, {
                            method: 'POST',
                            body: formData
                        });
                        
                        if (!res.ok) throw new Error(`Create failed with status ${res.status}`);
                    } else if (item.action === 'delete') {
                        const res = await fetch(item.url, {
                            method: 'DELETE'
                        });
                        if (!res.ok) throw new Error(`Delete failed with status ${res.status}`);
                    }
                    
                    // Remove from queue
                    const delTx = db.transaction('sync-queue', 'readwrite');
                    await delTx.objectStore('sync-queue').delete(item.id);
                } catch (err) {
                    console.error('[Offline] Sync item failed:', err, item);
                    // Stop syncing subsequent items to preserve order
                    break;
                }
            }
            
            // Clean temporary snippets and refresh the page snippets
            const cleanTx = db.transaction('snippets', 'readwrite');
            const cleanStore = cleanTx.objectStore('snippets');
            const cleanReq = cleanStore.getAll();
            cleanReq.onsuccess = () => {
                const all = cleanReq.result;
                const tempIds = all.filter(s => String(s.id).startsWith('temp-')).map(s => s.id);
                const deleteTx = db.transaction('snippets', 'readwrite');
                tempIds.forEach(id => deleteTx.objectStore('snippets').delete(id));
            };
            
            // Trigger HTMX reload of snippets list
            const searchInput = document.querySelector('input[name="q"]');
            if (searchInput) {
                searchInput.dispatchEvent(new Event('keyup'));
            } else {
                location.reload();
            }
        };
    } catch (err) {
        console.error('[Offline] Sync error:', err);
    }
}

// Bind event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Sync queue on network restore
    window.addEventListener('online', syncOfflineQueue);
    
    // Initial sync check
    if (navigator.onLine) {
        syncOfflineQueue();
    }
});

// Intercept HTMX page loads to save snippets
document.body.addEventListener('htmx:afterOnLoad', (event) => {
    if (event.detail.target && event.detail.target.id === 'snippets-list') {
        parseAndStoreSnippets();
    }
});
