from typing import List, Optional
from app.models.snippet import Snippet
from app.auth.crypto import decrypt_data
from securitycore import input_sanitizer

def render_snippet_cards(snippets: List[Snippet], salt: str, search_query: Optional[str] = None) -> str:
    if not snippets:
        return _empty_state()

    html = ""
    for s in snippets:
        dec_text = decrypt_data(s.content, salt, s.category) or "[Дешифровка не удалась]"
        dec_note = decrypt_data(s.note, salt, s.category) if s.note else ""
        safe_text = str(input_sanitizer(dec_text))
        safe_note = str(input_sanitizer(dec_note)) if dec_note else ""

        if search_query:
            q = search_query.lower()
            if q.startswith("#"):
                if not s.tags or q not in s.tags.lower():
                    continue
            elif q.startswith("lang:"):
                if not s.language or q.replace("lang:", "").strip() != s.language.lower():
                    continue
            else:
                target = f"{safe_text} {safe_note} {s.tags or ''} {s.category} {s.sub_category or ''}".lower()
                if q not in target:
                    continue

        accent = "acid" if s.category.lower() in ["study", "учеба"] else "electric"
        shadow = "hover:shadow-[0_0_15px_rgba(57,255,20,0.1)]" if accent == "acid" else "hover:shadow-neon"

        html += f"""
        <div id="snippet-{s.id}" class="bg-darkglass/50 backdrop-blur-md border border-gray-800 rounded-2xl p-6 transition-all duration-300 group hover:border-{accent}/50 {shadow} flex flex-col">
            <div class="flex justify-between items-start mb-5">
                <div class="flex flex-col gap-1.5">
                    <span class="text-xs md:text-sm font-mono text-{accent} uppercase tracking-widest font-bold">{s.category} // {s.sub_category}</span>
                    <div class="flex gap-1.5 mt-1 text-xs text-gray-400 font-mono">{s.tags if s.tags else ""}</div>
                </div>
                <div class="flex gap-3">
                    <button @click="viewData = {{ cat: '{s.category}', sub: '{s.sub_category}', tags: '{s.tags or ''}', image: '{s.image_url if s.image_url else ''}', note: document.getElementById('note-{s.id}') ? document.getElementById('note-{s.id}').innerText : '', text: document.getElementById('code-{s.id}').innerText }}; showViewModal = true" 
                            class="opacity-0 group-hover:opacity-100 text-electric hover:text-white transition-all cursor-pointer" title="Развернуть">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/></svg>
                    </button>
                    <button hx-delete="/snippets/delete/{s.id}" hx-target="#snippet-{s.id}" hx-swap="outerHTML swap:0.4s" class="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-500 transition-all cursor-pointer">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                    </button>
                </div>
            </div>
            
            {f'<div class="mb-5 rounded-xl overflow-hidden border border-gray-800/80"><img src="{s.image_url}" class="w-full h-auto object-cover opacity-90 group-hover:opacity-100 transition-all"/></div>' if s.image_url else ''}
            
            <div class="bg-midnight border border-gray-800 rounded-lg p-4 overflow-hidden relative flex-grow">
                <pre id="code-{s.id}" class="text-gray-200 whitespace-pre-wrap text-sm md:text-base font-mono max-h-40 overflow-hidden" style="-webkit-mask-image: linear-gradient(180deg, #000 60%, transparent);">{safe_text}</pre>
            </div>
            
            {f'<div class="mt-4 hidden"><p id="note-{s.id}">{safe_note}</p></div>' if safe_note else ''}
            
            <div class="mt-5 pt-4 border-t border-gray-800/60 flex justify-between items-center text-xs text-gray-500 font-mono">
                <span>{s.created_at.strftime('%d.%m.%Y %H:%M')}</span>
            </div>
        </div>
        """
    return html or _empty_state()

def _empty_state() -> str:
    return "<div class='col-span-full text-center py-24 text-gray-500 font-mono tracking-widest text-base uppercase'>Архивы пусты... 🕵️‍♂️</div>"