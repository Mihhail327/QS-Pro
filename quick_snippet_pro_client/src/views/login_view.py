import flet as ft
from src.components.custom_input import CustomInput
from src.api.auth_api import AuthAPI

class LoginView:
    @staticmethod
    async def get_view(page: ft.Page) -> ft.View:
        
        username_input = CustomInput(
            label="ИДЕНТИФИКАТОР / ЛОГИН",
            hint_text="Введите ваш никнейм..."
        )
        
        password_input = CustomInput(
            label="КРИПТО-ПАРОЛЬ",
            password=True,
            can_reveal_password=True,
            hint_text="••••••••••••"
        )

        # Универсальная функция для железного вызова модальных окон
        async def show_system_dialog(title: str, text: str, color: str):
            def close_click(e):
                dialog.open = False
                page.update()

            dialog = ft.AlertDialog(
                title=ft.Text(title, color=color, weight=ft.FontWeight.BOLD),
                content=ft.Text(text),
                actions=[ft.TextButton("ОК", on_click=close_click)],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            # Принудительно пушим в оверлей и открываем, чтобы Flet точно его отрендерил
            page.dialog = dialog # type: ignore
            dialog.open = True
            page.update()

        # Обработчик регистрации
        async def register_click(e):
            await show_system_dialog(
                "РЕГИСТРАЦИЯ", 
                "Для создания нового крипто-профиля обратитесь к администратору RellixCore или воспользуйтесь Web-панелью.", 
                "teal400"
            )

        # 🎯 Исправленная боевая функция клика
        async def login_click(e):
            # Проверка пустых полей теперь 100% вызовет окно
            if not username_input.value or not password_input.value:
                await show_system_dialog(
                    "СИСТЕМНЫЙ СБОЙ", 
                    "Ошибка: Идентификатор и крипто-пароль не могут быть пустыми!", 
                    "red400"
                )
                return
            
            # Включаем прелоадер
            login_btn.disabled = True
            login_btn.content = ft.ProgressRing(width=20, height=20, color="#070a13")
            page.update()
            
            # Отправляем асинхронный запрос
            auth_data = await AuthAPI.login(username_input.value, password_input.value)
            
            # Возвращаем кнопку в исходное состояние
            login_btn.disabled = False
            login_btn.content = ft.Text("ИНИЦИИРОВАТЬ ВХОД", weight=ft.FontWeight.BOLD)
            page.update()
            
            if auth_data is not None:
                # Если бэкенд вернул токен
                setattr(page, "user_token", auth_data.get("access_token"))
                
                await show_system_dialog(
                    "ДОСТУП РАЗРЕШЕН", 
                    f"Добро пожаловать в систему, {username_input.value}!", 
                    "green400"
                )
                # Здесь позже будет переход: await page.push_route("/dashboard")
            else:
                # Если пришла ошибка сети, HTML или неверный пароль
                await show_system_dialog(
                    "ОТКАЗ В ДОСТУПЕ", 
                    "Неверные учетные данные, либо шлюз RellixCore вернул некорректный ответ.", 
                    "red400"
                )

        # Создаем кнопку входа
        login_btn = ft.ElevatedButton(
            content=ft.Text("ИНИЦИИРОВАТЬ ВХОД", weight=ft.FontWeight.BOLD),
            color="#070a13",
            bgcolor="teal400",
            width=280,
            height=45,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=login_click
        )

        form_body = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("ВХОД В ТЕРМИНАЛ", size=24, weight=ft.FontWeight.BOLD, color="teal400"),
                    ft.Text("Авторизация экосистемы QuickSnippet Pro", size=12, color="grey500"),
                    ft.Container(height=30),
                    
                    username_input,
                    ft.Container(height=10),
                    password_input,
                    ft.Container(height=25),
                    
                    login_btn,
                    
                    ft.Container(height=15),
                    
                    # 🎯 Вешаем триггер на кнопку регистрации
                    ft.TextButton(
                        "Создать новый крипто-профиль (Регистрация)",
                        style=ft.ButtonStyle(color="teal600"),
                        on_click=register_click
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            width=320,
            alignment=ft.Alignment(0, 0)
        )

        return ft.View(
            route="/login",
            controls=[
                ft.Container(
                    content=form_body,
                    alignment=ft.Alignment(0, 0),
                    expand=True
                )
            ], 
            padding=0,
            bgcolor="#070a13"
        )