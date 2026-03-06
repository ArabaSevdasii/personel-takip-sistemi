"""
Personel Takip Sistemi — Ana giriş noktası.
Tek pencere: giriş sonrası split dashboard gösterilir.
"""
import customtkinter as ctk

from dashboard import DashboardView
from login import LoginScreen

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


def main():
    app = ctk.CTk()
    app.title("Personel Takip Sistemi")
    app.geometry("1200x800")
    try:
        app.state("zoomed")  # Windows maximized
    except Exception:
        pass

    def on_login_success():
        for w in app.winfo_children():
            w.destroy()
        DashboardView(app).pack(fill="both", expand=True)

    LoginScreen(app, on_success=on_login_success).pack(fill="both", expand=True)
    app.mainloop()


if __name__ == "__main__":
    main()

