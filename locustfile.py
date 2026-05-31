import os
import random
import uuid
from locust import HttpUser, task, between

class QuickSnippetProLoadTest(HttpUser):
    """
    Locust load testing script for QuickSnippet Pro.
    Simulates high-load users performing auth, search, creation, and export operations.
    """
    wait_time = between(1, 3)  # Пауза между запросами от 1 до 3 секунд

    def on_start(self):
        """Инициализация виртуального пользователя и регистрация/вход."""
        self.username = f"cyber_load_{uuid.uuid4().hex[:8]}"
        self.password = "Strong_Pass_1337_$"
        self.user_salt = "default_salt"
        self.is_logged_in = False
        
        # 1. Регистрация
        register_payload = {
            "username": self.username,
            "password": self.password,
            "is_dev": "true" if random.random() > 0.5 else "false"
        }
        with self.client.post("/auth/register", data=register_payload, catch_response=True) as response:
            if response.status_code == 200:
                # 2. Вход в Сейф
                login_payload = {
                    "username": self.username,
                    "password": self.password
                }
                with self.client.post("/auth/login", data=login_payload, catch_response=True) as login_resp:
                    if login_resp.status_code == 200:
                        self.is_logged_in = True
                    else:
                        login_resp.failure(f"Login failed: {login_resp.status_code}")
            else:
                response.failure(f"Registration failed: {response.status_code}")

    @task(5)
    def view_workspace(self):
        """Просмотр главной панели (асинхронно HTMX дергает список сниппетов)."""
        if not self.is_logged_in:
            return
        self.client.get("/")
        self.client.get("/snippets/list", headers={"HX-Request": "true"})

    @task(3)
    def search_snippets(self):
        """Симуляция Omni-Search поиска с debounce."""
        if not self.is_logged_in:
            return
        queries = ["#python", "lang:javascript", "секрет", "General"]
        query = random.choice(queries)
        self.client.get(f"/snippets/list?q={query}", headers={"HX-Request": "true"})

    @task(2)
    def create_new_snippet(self):
        """Создание нового сниппета с псевдошифрованием."""
        if not self.is_logged_in:
            return
        
        categories = ["idea", "code", "study", "important"]
        chosen_cat = random.choice(categories)
        
        payload = {
            "category": chosen_cat,
            "content": f"EncryptedBase64PayloadNoise_{uuid.uuid4().hex}",
            "sub_category": random.choice(["Theory", "Drafts", "Archive"]),
            "note": f"EncryptedBase64NoteNoise_{uuid.uuid4().hex}" if random.random() > 0.5 else "",
            "tags": random.choice(["#test #load", "#bench #redis", "#gits #shield"]),
            "parent_snippet_id": "",
            "reminder_at": "2026-06-01T12:00:00" if chosen_cat == "important" else ""
        }
        
        self.client.post("/snippets/create", data=payload, headers={"HX-Request": "true"})

    @task(1)
    def export_archive(self):
        """Экспорт архива (Freedom Protocol - потоковая генерация в RAM)."""
        if not self.is_logged_in:
            return
        self.client.get("/snippets/export")
