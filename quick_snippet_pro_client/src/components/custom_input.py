import flet as ft

class CustomInput(ft.TextField):
    def __init__(self, label: str, password: bool = False, can_reveal_password: bool = False, hint_text: str = "", **kwargs):
        # Явно передаем ключевые параметры в конструктор базового класса TextField
        super().__init__(
            label=label,
            password=password,
            can_reveal_password=can_reveal_password,
            hint_text=hint_text,
            border_color="teal700",
            focused_border_color="teal400",
            label_style=ft.TextStyle(color="grey500"),
            cursor_color="teal400",
            color="grey300",
            border_radius=8,
            text_style=ft.TextStyle(font_family="monospace", size=14),
            focused_border_width=2,
            **kwargs
        )