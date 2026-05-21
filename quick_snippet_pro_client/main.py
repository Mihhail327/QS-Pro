import flet as ft
from src.views.splash_view import SplashView
from src.views.login_view import LoginView

async def main(page: ft.Page):
    # Габариты терминала QS Pro
    page.window.width = 420          # type: ignore
    page.window.height = 760         # type: ignore
    page.window.resizable = False    # type: ignore
    page.title = "QuickSnippet Pro // Distributed by RellixCore"
    
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#070a13"
    
    # Реактивный маршрутизатор
    async def route_change(route):
        page.views.clear()
        if page.route == "/":
            page.views.append(await SplashView.get_view(page))
        elif page.route == "/login":
            page.views.append(await LoginView.get_view(page))
        page.update()

    page.on_route_change = route_change
    
    # 🎯 Senior-фикс: Прямой жесткий рендер стартового экрана, чтобы окно не было пустым
    initial_view = await SplashView.get_view(page)
    page.views.append(initial_view)
    page.update()

if __name__ == "__main__":
    ft.run(main)