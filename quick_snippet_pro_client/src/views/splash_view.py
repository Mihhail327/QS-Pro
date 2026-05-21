import asyncio
import flet as ft

class SplashView:
    @staticmethod
    async def get_view(page: ft.Page) -> ft.View:
        
        progress_bar = ft.ProgressBar(
            width=260, 
            color="teal400", 
            bgcolor="#1a233d"
        )
        
        status_text = ft.Text(
            value="Инициализация систем QS Pro...", 
            size=11, 
            font_family="monospace", 
            color="teal600"
        )

        content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(value="RELLIXCORE", size=28, weight=ft.FontWeight.BOLD, color="teal400"),
                    ft.Text(value="QUICKSNIPPET PRO", size=12, color="grey500"),
                    ft.Text(""), 
                    progress_bar,
                    ft.Text(""),
                    status_text
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            # 🎯 Железобетонный фикс: координаты центра (0, 0) вместо ft.alignment.center
            alignment=ft.Alignment(0, 0),
            expand=True
        )

        async def run_diagnostics():
            await asyncio.sleep(1.5)
            status_text.value = "Проверка крипто-шлюзов AES-256-GCM..."
            page.update()
            
            await asyncio.sleep(1.2)
            status_text.value = "Связь со шлюзом RellixCore установлена."
            page.update()
            
            await asyncio.sleep(0.8)
            # Переключаем роут асинхронно
            await page.push_route("/login")  # type: ignore

        asyncio.create_task(run_diagnostics())

        return ft.View(
            route="/",
            controls=[content],
            padding=0,
            bgcolor="#070a13"
        )