# 🏙️ QuickSnippet Pro

**The Secure Cyber-Baroque Vault**

QuickSnippet Pro — это профессиональный инструмент для безопасного хранения фрагментов кода, заметок и учебных материалов. Система построена на концепции «Саркофага»: данные не просто хранятся, они запечатываются с помощью криптографического ядра.

---

## 🛠 Технический Стек
* **Backend:** FastAPI (Python 3.13)
* **Security:** SecurityCore SDK (Argon2id, AES-256-GCM)
* **Frontend:** Alpine.js + HTMX
* **Database:** PostgreSQL (SQLModel)
* **Infrastructure:** Redis (Cache-Aside), Docker, PWA

## 🔒 Security Features
* **Titanium Shield:** Использование `AES-256-GCM` с динамическим сдвигом ключей (`Key Shifting`) на базе категорий.
* **Integrity Lock:** Автоматическая блокировка сессии при обнаружении попыток подмены данных (SecurityBreachException).
* **Zero-Trust Input:** Входная стерилизация через `nh3` (Rust-sanitizer).
* **Entropy Shield:** Автоматическая защита от слабых паролей (минимум 45 бит).


## 🔗 Архитектура Nexus Links
Система поддерживает построение графа знаний через поле `Nexus Link ID`. Каждый сниппет может быть связан с родительским узлом, создавая иерархические цепочки данных.

---
*Проект поддерживается и разрабатывается в рамках концепции безопасного хранения знаний.*
*Лицензия: MIT*