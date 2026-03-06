"""
Giriş ekranı: sadece şifre.
Başarılı girişte on_success callback'i çağrılır.
"""
import customtkinter as ctk

CORRECT_PASSWORD = "1234"


class LoginScreen(ctk.CTkFrame):
    def __init__(self, parent, on_success=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_success = on_success

        font_large = ctk.CTkFont(family="Arial", size=30)
        font_medium = ctk.CTkFont(family="Arial", size=24)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(expand=True)

        self.password_entry = ctk.CTkEntry(
            inner,
            width=320,
            height=64,
            font=font_medium,
            placeholder_text="Şifre",
            show="*",
        )
        self.password_entry.pack(pady=20)

        ctk.CTkButton(
            inner,
            text="GİRİŞ YAP",
            width=320,
            height=84,
            font=font_large,
            command=self._check_password,
        ).pack(pady=20)

        self.error_label = ctk.CTkLabel(inner, text="", font=font_medium, text_color="red")
        self.error_label.pack(pady=10)

    def _check_password(self):
        if self.password_entry.get().strip() == CORRECT_PASSWORD:
            self.error_label.configure(text="")
            if self.on_success:
                self.on_success()
        else:
            self.error_label.configure(text="Hatalı Şifre!")

