"""
Ana ekran: sol/sağ bölünmüş panel.

Sol: varsayılan / yeni çalışan / çalışan detay (günlük) / düzenle / geçmiş ödemeler.
Sağ: çalışan listesi, haftalık toplam, YENİ ÇALIŞAN EKLE, GEÇMİŞ ÖDEMELER, TÜM HAFTAYI SIFIRLA, KALDIR.
"""
import datetime
from tkinter import messagebox

import customtkinter as ctk

from database import (
    DAY_KEYS,
    add_employee,
    add_missing_for_day,
    clear_payment_history,
    fetch_active_employees,
    fetch_payment_history,
    get_employee,
    insert_payment,
    mark_as_paid,
    remove_employee,
    reset_all_missing_hours,
    reset_missing_hours,
    set_actual_paid,
    set_day_missing,
    update_employee,
)

FONT = 20
FONT_BIG = 24
FONT_TITLE = 28

DAY_NAMES = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]

MONTH_TR = {
    1: "Ocak",
    2: "Şubat",
    3: "Mart",
    4: "Nisan",
    5: "Mayıs",
    6: "Haziran",
    7: "Temmuz",
    8: "Ağustos",
    9: "Eylül",
    10: "Ekim",
    11: "Kasım",
    12: "Aralık",
}


def _format_history_header(ts_text: str) -> str:
    dt = None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(ts_text, fmt)
            break
        except ValueError:
            continue
    if not dt:
        return f"====== {ts_text} İşlemleri ======"
    day = f"{dt.day:02d}"
    month = MONTH_TR.get(dt.month, str(dt.month))
    year = dt.year
    if " " in ts_text:
        return f"====== {day} {month} {year} - Saat: {dt.hour:02d}:{dt.minute:02d} İşlemleri ======"
    return f"====== {day} {month} {year} İşlemleri ======"


def _missing_summary_for_days(day_values):
    parts = []
    labels = ["Pzt", "Sal", "Çar", "Per", "Cum"]
    for i, v in enumerate(day_values):
        h = int(v) if v else 0
        if h > 0:
            parts.append(f"{labels[i]}: -{h} saat")
    return ", ".join(parts) if parts else "Yok"


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.master = master
        self.selected_employee_id = None

        # split widths ~60/40
        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=1)

        self.left_panel = ctk.CTkFrame(self, fg_color=("gray90", "gray17"))
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=0)

        self.right_panel = ctk.CTkFrame(self, fg_color=("gray92", "gray14"))
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=0)
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.right_panel,
            text="ÇALIŞANLAR",
            font=ctk.CTkFont(family="Arial", size=FONT_BIG),
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=12)

        self.scroll_frame = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        self.total_weekly_label = ctk.CTkLabel(
            self.right_panel,
            text="",
            font=ctk.CTkFont(family="Arial", size=22, weight="bold"),
        )
        self.total_weekly_label.grid(row=2, column=0, sticky="ew", padx=12, pady=8)

        ctk.CTkButton(
            self.right_panel,
            text="YENİ ÇALIŞAN EKLE",
            font=ctk.CTkFont(family="Arial", size=FONT_BIG),
            height=70,
            fg_color="green",
            hover_color="darkgreen",
            command=self._show_add_employee,
        ).grid(row=3, column=0, sticky="ew", padx=12, pady=6)

        ctk.CTkButton(
            self.right_panel,
            text="GEÇMİŞ ÖDEMELER",
            font=ctk.CTkFont(family="Arial", size=FONT_BIG),
            height=60,
            command=self._show_payment_history,
        ).grid(row=4, column=0, sticky="ew", padx=12, pady=6)

        ctk.CTkButton(
            self.right_panel,
            text="TÜM HAFTAYI SIFIRLA (Yeni Hafta)",
            font=ctk.CTkFont(family="Arial", size=FONT_BIG),
            height=70,
            fg_color="#8B0000",
            hover_color="#5C0000",
            command=self._on_global_reset,
        ).grid(row=5, column=0, sticky="ew", padx=12, pady=12)

        self.font = ctk.CTkFont(family="Arial", size=FONT)
        self.font_big = ctk.CTkFont(family="Arial", size=FONT_BIG)
        self.font_title = ctk.CTkFont(family="Arial", size=FONT_TITLE)
        self.font_list_name = ctk.CTkFont(family="Arial", size=22, weight="bold")
        self.font_list_detail = ctk.CTkFont(family="Arial", size=16)
        self.font_day_status = ctk.CTkFont(family="Arial", size=16)

        self._refresh_employee_list()
        self._show_default_view()

    def _clear_left(self):
        for w in self.left_panel.winfo_children():
            w.destroy()

    def _show_default_view(self):
        self._clear_left()
        self.selected_employee_id = None
        ctk.CTkLabel(
            self.left_panel,
            text="İşlem yapmak için sağdan bir kişi seçin.",
            font=self.font_title,
        ).place(relx=0.5, rely=0.5, anchor="center")

    def _on_global_reset(self):
        if not messagebox.askyesno(
            "Onay",
            "Tüm çalışanların saat kesintileri sıfırlanacak. Emin misiniz?",
            parent=self.winfo_toplevel(),
        ):
            return

        # Önce kontrol: actual_paid net maaşı aşan çalışan var mı?
        employees = fetch_active_employees()
        problem_list = []
        for row in employees:
            _id, name, _phone, base_salary, _a = row[:5]
            day_vals = [float(row[i] or 0) for i in range(5, 10)]
            actual_paid_val = row[11] if len(row) > 11 else None
            if actual_paid_val is None:
                continue
            total_missing = sum(day_vals)
            hourly = (base_salary or 0) / 50
            net_paid = max(0, (base_salary or 0) - total_missing * hourly)
            if float(actual_paid_val) > net_paid + 0.009:
                problem_list.append(
                    f"  • {name}: Elden Ödenen {actual_paid_val:,.2f} ₺ > Net {net_paid:,.2f} ₺"
                )

        if problem_list:
            problem_str = "\n".join(problem_list)
            messagebox.showerror(
                "Hata — Sıfırlama İptal Edildi",
                f"Aşağıdaki çalışanların elden ödenen tutarı hesaplanan net maaşından fazla!\n"
                f"Lütfen önce bu kişileri düzeltin:\n\n{problem_str}\n\n"
                f"Sıfırlama yapılmadı.",
                parent=self.winfo_toplevel(),
            )
            return

        batch_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for row in employees:
            _id, name, _phone, base_salary, _a = row[:5]
            day_vals = [float(row[i] or 0) for i in range(5, 10)]
            actual_paid_val = row[11] if len(row) > 11 else None
            total_missing = sum(day_vals)
            hourly = (base_salary or 0) / 50
            net_paid = max(0, (base_salary or 0) - total_missing * hourly)
            insert_payment(name, batch_ts, base_salary or 0, net_paid, _missing_summary_for_days(day_vals), actual_paid_val)
        reset_all_missing_hours()
        self._refresh_employee_list()
        if self.selected_employee_id:
            self._show_employee_detail(self.selected_employee_id)

    def _show_add_employee(self):
        self._clear_left()
        self.selected_employee_id = None
        main = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=32, pady=32)

        ctk.CTkLabel(main, text="Yeni Çalışan", font=self.font_title).pack(anchor="w", pady=(0, 20))
        ctk.CTkLabel(main, text="Ad Soyad", font=self.font).pack(anchor="w", pady=(0, 4))
        entry_name = ctk.CTkEntry(main, height=48, font=self.font)
        entry_name.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(main, text="Telefon", font=self.font).pack(anchor="w", pady=(0, 4))
        entry_phone = ctk.CTkEntry(main, height=48, font=self.font)
        entry_phone.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(main, text="Haftalık Maaş (TL)", font=self.font).pack(anchor="w", pady=(0, 4))
        entry_salary = ctk.CTkEntry(main, height=48, font=self.font, placeholder_text="Örn: 2500")
        entry_salary.pack(fill="x", pady=(0, 24))
        err = ctk.CTkLabel(main, text="", font=self.font, text_color="red")
        err.pack(anchor="w", pady=(0, 8))

        def save():
            name = entry_name.get().strip()
            salary_str = entry_salary.get().strip()
            if not name:
                err.configure(text="Ad Soyad boş bırakılamaz.")
                return
            if not salary_str:
                err.configure(text="Haftalık maaş boş bırakılamaz.")
                return
            try:
                salary = float(salary_str.replace(",", "."))
                if salary < 0:
                    raise ValueError()
            except ValueError:
                err.configure(text="Geçerli bir maaş girin.")
                return
            err.configure(text="")
            add_employee(name, entry_phone.get().strip(), salary)
            self._refresh_employee_list()
            self._show_default_view()

        btn_f = ctk.CTkFrame(main, fg_color="transparent")
        btn_f.pack(fill="x", pady=16)
        ctk.CTkButton(
            btn_f, text="KAYDET", font=self.font_big, height=60,
            fg_color="green", hover_color="darkgreen", command=save,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            btn_f, text="İPTAL", font=self.font_big, height=60,
            fg_color="red", hover_color="darkred", command=self._show_default_view,
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))

    def _show_employee_detail(self, employee_id):
        self.selected_employee_id = employee_id
        row = get_employee(employee_id)
        if not row:
            self._show_default_view()
            return
        _id, name, _phone, weekly_salary, _a = row[:5]
        day_vals = [float(row[i] or 0) for i in range(5, 10)]
        is_paid = int(row[10]) if len(row) > 10 else 0
        actual_paid_db = row[11] if len(row) > 11 else None
        weekly_salary = weekly_salary or 0

        self._clear_left()
        # ScrollableFrame so all days (including Cuma) are reachable
        scroll_main = ctk.CTkScrollableFrame(self.left_panel, fg_color="transparent")
        scroll_main.pack(fill="both", expand=True)
        main = ctk.CTkFrame(scroll_main, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=18, pady=16)

        def total_missing():
            return sum(day_vals)

        def hourly():
            return weekly_salary / 50

        def net():
            return max(0, weekly_salary - total_missing() * hourly())

        ctk.CTkLabel(main, text="Çalışan", font=self.font).pack(anchor="w", pady=(0, 4))
        top_row = ctk.CTkFrame(main, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 8))
        top_row.grid_columnconfigure(0, weight=1)
        top_row.grid_columnconfigure(1, weight=0)
        ctk.CTkLabel(top_row, text=name, font=self.font_big, anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            top_row, text="KİŞİYİ DÜZENLE", font=self.font_day_status, height=40,
            command=lambda: self._show_edit_employee(employee_id),
        ).grid(row=0, column=1, sticky="e", padx=(12, 0))

        ctk.CTkLabel(main, text="Haftalık Maaş (Taban)", font=self.font).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(main, text=f"{weekly_salary:,.2f} ₺", font=self.font_big).pack(anchor="w", pady=(0, 6))
        net_lbl = ctk.CTkLabel(main, text="", font=ctk.CTkFont(family="Arial", size=FONT_TITLE), text_color="green")
        net_lbl.pack(anchor="w", pady=(0, 4))
        deduction_lbl = ctk.CTkLabel(main, text="", font=self.font_big, text_color="red")
        deduction_lbl.pack(anchor="w", pady=(0, 6))

        # --- Elden ödenen tutar alanı ---
        actual_frame = ctk.CTkFrame(main, fg_color=("gray85", "gray22"), corner_radius=8)
        actual_frame.pack(fill="x", pady=(0, 10))
        actual_inner = ctk.CTkFrame(actual_frame, fg_color="transparent")
        actual_inner.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(
            actual_inner,
            text="Bu Hafta Elden Ödenen Tutar (₺):",
            font=self.font,
            anchor="w",
        ).pack(anchor="w", pady=(0, 4))
        actual_entry_row = ctk.CTkFrame(actual_inner, fg_color="transparent")
        actual_entry_row.pack(fill="x")
        actual_entry = ctk.CTkEntry(
            actual_entry_row,
            height=48,
            font=self.font_big,
            placeholder_text="Net maaştan fazla olamaz",
        )
        actual_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        if actual_paid_db is not None:
            actual_entry.insert(0, f"{actual_paid_db:,.2f}".replace(",", ""))
        actual_err_lbl = ctk.CTkLabel(actual_inner, text="", font=self.font_day_status, text_color="red")
        actual_err_lbl.pack(anchor="w", pady=(4, 0))

        def _save_actual_paid():
            raw = actual_entry.get().strip().replace(",", ".")
            if not raw:
                # Boş bırakılırsa kaydı temizle (ödeme girilmemiş sayılır)
                set_actual_paid(employee_id, None)
                actual_err_lbl.configure(text="")
                self._refresh_employee_list()
                return
            try:
                val = float(raw)
                if val < 0:
                    raise ValueError()
                if val > net():
                    actual_err_lbl.configure(text=f"⚠ Net maaştan ({net():,.2f} ₺) fazla olamaz!")
                    return
            except ValueError:
                actual_err_lbl.configure(text="Geçerli bir tutar girin.")
                return
            actual_err_lbl.configure(text="")
            set_actual_paid(employee_id, val)
            self._refresh_employee_list()

        ctk.CTkButton(
            actual_entry_row,
            text="KAYDET",
            font=self.font,
            width=100,
            height=48,
            fg_color="green",
            hover_color="darkgreen",
            command=_save_actual_paid,
        ).pack(side="left")

        def refresh_money():
            n = net()
            net_lbl.configure(text=f"ÖDENECEK NET MAAŞ: {n:,.2f} ₺")
            deduction = max(0.0, weekly_salary - n)
            deduction_lbl.configure(text=f"Bu Haftaki Toplam Kesinti: {deduction:,.2f} ₺")
            # Eğer kayıtlı actual_paid yeni net'ten fazlaysa uyar
            try:
                raw = actual_entry.get().strip().replace(",", ".")
                if raw:
                    val = float(raw)
                    if val > n:
                        actual_err_lbl.configure(text=f"⚠ Net maaştan ({n:,.2f} ₺) fazla olamaz!")
                    else:
                        actual_err_lbl.configure(text="")
            except Exception:
                pass

        refresh_money()

        ctk.CTkLabel(main, text="Günlük devamsızlık (Pzt–Cum):", font=self.font).pack(anchor="w", pady=(6, 4))
        status_lbls = []

        def _update_status(idx):
            h = float(day_vals[idx] or 0)
            if h > 0:
                status_lbls[idx].configure(text=f"{DAY_NAMES[idx]}: {int(h)} Saat Eksik", text_color="red")
            else:
                status_lbls[idx].configure(text=f"{DAY_NAMES[idx]}: Tam Geldi", text_color="green")

        def day_add(dk, idx, hours):
            # Bir günde max 10 saat eksik olabilir
            current = float(day_vals[idx] or 0)
            new_val = min(10.0, current + hours)
            if new_val == current:
                return  # Zaten max, değişiklik yok
            set_day_missing(employee_id, dk, new_val)
            day_vals[idx] = new_val
            _update_status(idx)
            refresh_money()
            self._refresh_employee_list()

        def day_sub_one(dk, idx):
            # DB'den taze oku — UI ile kayma olmasın
            fresh = get_employee(employee_id)
            if fresh:
                day_vals[idx] = float(fresh[5 + idx] or 0)
            new_val = max(0.0, float(day_vals[idx]) - 1.0)
            set_day_missing(employee_id, dk, new_val)
            day_vals[idx] = new_val
            _update_status(idx)
            refresh_money()
            self._refresh_employee_list()

        def day_reset(dk, idx):
            set_day_missing(employee_id, dk, 0)
            day_vals[idx] = 0
            _update_status(idx)
            refresh_money()
            self._refresh_employee_list()

        for day_index, day_name in enumerate(DAY_NAMES):
            day_key = DAY_KEYS[day_index]
            day_f = ctk.CTkFrame(main, fg_color=("gray85", "gray20"), corner_radius=8)
            day_f.pack(fill="x", pady=2)
            inner = ctk.CTkFrame(day_f, fg_color="transparent")
            inner.pack(fill="x", padx=10, pady=3)

            status_lbl = ctk.CTkLabel(inner, text="", font=self.font_day_status, anchor="w")
            status_lbl.pack(anchor="w", pady=(0, 2))
            status_lbls.append(status_lbl)
            _update_status(day_index)

            btn_row = ctk.CTkFrame(inner, fg_color="transparent")
            btn_row.pack(fill="x")
            for c in range(5):
                btn_row.grid_columnconfigure(c, weight=1)

            ctk.CTkButton(
                btn_row, text="-1 Saat", font=self.font_day_status, height=38, width=72,
                fg_color="red", hover_color="darkred",
                command=lambda dk=day_key, idx=day_index: day_add(dk, idx, 1),
            ).grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=1)
            ctk.CTkButton(
                btn_row, text="Yarım Gün (-5)", font=self.font_day_status, height=38,
                fg_color="red", hover_color="darkred",
                command=lambda dk=day_key, idx=day_index: day_add(dk, idx, 5),
            ).grid(row=0, column=1, sticky="ew", padx=4, pady=1)
            ctk.CTkButton(
                btn_row, text="Tam Gün (-10)", font=self.font_day_status, height=38,
                fg_color="red", hover_color="darkred",
                command=lambda dk=day_key, idx=day_index: day_add(dk, idx, 10),
            ).grid(row=0, column=2, sticky="ew", padx=4, pady=1)
            ctk.CTkButton(
                btn_row, text="+1 Saat", font=self.font_day_status, height=38, width=72,
                fg_color="green", hover_color="darkgreen",
                command=lambda dk=day_key, idx=day_index: day_sub_one(dk, idx),
            ).grid(row=0, column=3, sticky="ew", padx=4, pady=1)
            ctk.CTkButton(
                btn_row, text="Sıfırla", font=self.font_day_status, height=38,
                fg_color="#1f6aa5", hover_color="#144870",
                command=lambda dk=day_key, idx=day_index: day_reset(dk, idx),
            ).grid(row=0, column=4, sticky="ew", padx=(4, 0), pady=1)

        def _toggle_paid():
            current = get_employee(employee_id)
            current_paid = int(current[10]) if current and len(current) > 10 else 0
            if current_paid == 1:
                if not messagebox.askyesno(
                    "Onay",
                    f"{name} adlı çalışanın ödeme işareti GERİ ALINACAK.\nEmin misiniz?",
                    parent=self.winfo_toplevel(),
                ):
                    return
                mark_as_paid(employee_id, 0)
            else:
                mark_as_paid(employee_id, 1)
            self._refresh_employee_list()
            self._show_employee_detail(employee_id)

        if is_paid:
            pay_btn_text = "✅ ÖDENDİ — Geri Al"
            pay_btn_color = "#5a7a5a"
            pay_btn_hover = "#4a6a4a"
        else:
            pay_btn_text = "MAAŞI ÖDENDİ (İşaretle)"
            pay_btn_color = "#1f6aa5"
            pay_btn_hover = "#144870"

        ctk.CTkButton(
            main,
            text=pay_btn_text,
            font=self.font_big,
            height=62,
            fg_color=pay_btn_color,
            hover_color=pay_btn_hover,
            command=_toggle_paid,
        ).pack(fill="x", pady=12)

    def _show_edit_employee(self, employee_id):
        row = get_employee(employee_id)
        if not row:
            self._show_default_view()
            return
        _id, name, phone, weekly_salary, _a = row[:5]

        self._clear_left()
        main = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=32, pady=32)

        ctk.CTkLabel(main, text="Çalışan Düzenle", font=self.font_title).pack(anchor="w", pady=(0, 20))
        ctk.CTkLabel(main, text="Ad Soyad", font=self.font).pack(anchor="w", pady=(0, 4))
        entry_name = ctk.CTkEntry(main, height=48, font=self.font)
        entry_name.pack(fill="x", pady=(0, 16))
        entry_name.insert(0, name or "")
        ctk.CTkLabel(main, text="Telefon", font=self.font).pack(anchor="w", pady=(0, 4))
        entry_phone = ctk.CTkEntry(main, height=48, font=self.font)
        entry_phone.pack(fill="x", pady=(0, 16))
        entry_phone.insert(0, phone or "")
        ctk.CTkLabel(main, text="Haftalık Maaş (TL)", font=self.font).pack(anchor="w", pady=(0, 4))
        entry_salary = ctk.CTkEntry(main, height=48, font=self.font)
        entry_salary.pack(fill="x", pady=(0, 24))
        entry_salary.insert(0, str(int(weekly_salary)) if weekly_salary is not None else "")
        err = ctk.CTkLabel(main, text="", font=self.font, text_color="red")
        err.pack(anchor="w", pady=(0, 8))

        def save():
            n = entry_name.get().strip()
            s = entry_salary.get().strip()
            if not n:
                err.configure(text="Ad Soyad boş bırakılamaz.")
                return
            if not s:
                err.configure(text="Haftalık maaş boş bırakılamaz.")
                return
            try:
                sal = float(s.replace(",", "."))
                if sal < 0:
                    raise ValueError()
            except ValueError:
                err.configure(text="Geçerli bir maaş girin.")
                return
            err.configure(text="")
            update_employee(employee_id, n, entry_phone.get().strip(), sal)
            self._refresh_employee_list()
            self._show_employee_detail(employee_id)

        btn_f = ctk.CTkFrame(main, fg_color="transparent")
        btn_f.pack(fill="x", pady=16)
        ctk.CTkButton(
            btn_f, text="KAYDET", font=self.font_big, height=60,
            fg_color="green", hover_color="darkgreen", command=save,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            btn_f, text="İPTAL", font=self.font_big, height=60,
            fg_color="red", hover_color="darkred", command=lambda: self._show_employee_detail(employee_id),
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))

    def _on_clear_history(self):
        if not messagebox.askyesno(
            "Onay",
            "Tüm geçmiş ödeme kayıtları silinecek. Emin misiniz?",
            parent=self.winfo_toplevel(),
        ):
            return
        clear_payment_history()
        self._show_payment_history()

    def _show_payment_history(self):
        self._clear_left()
        self.selected_employee_id = None
        main = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=32, pady=32)

        ctk.CTkLabel(main, text="Geçmiş Ödemeler", font=self.font_title).pack(anchor="w", pady=(0, 16))
        ctk.CTkButton(
            main,
            text="🗑️ Geçmiş Verileri Sil",
            font=self.font_big,
            height=56,
            fg_color="#8B0000",
            hover_color="#5C0000",
            command=self._on_clear_history,
        ).pack(anchor="w", pady=(0, 16))

        scroll = ctk.CTkScrollableFrame(main, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        records = fetch_payment_history()
        font_row = ctk.CTkFont(family="Arial", size=18)
        last_ts = None
        batch_total = 0.0

        for r in records:
            _id, emp_name, payment_date, _base_salary, net_paid, missing_summary, actual_paid_h = r
            if payment_date != last_ts:
                if last_ts is not None:
                    ctk.CTkLabel(
                        scroll,
                        text=f"💰 Bu İşlemde Toplam Ödenen: {batch_total:,.2f} ₺",
                        font=ctk.CTkFont(family="Arial", size=20, weight="bold"),
                        text_color="green",
                        anchor="w",
                    ).pack(anchor="w", fill="x", pady=(6, 14))
                    batch_total = 0.0

                last_ts = payment_date
                header_frame = ctk.CTkFrame(scroll, fg_color="#1f6aa5", corner_radius=8)
                header_frame.pack(fill="x", pady=(10, 6))
                ctk.CTkLabel(
                    header_frame,
                    text=_format_history_header(payment_date),
                    font=ctk.CTkFont(family="Arial", size=20, weight="bold"),
                    text_color="white",
                ).pack(anchor="w", padx=12, pady=10)

            batch_total += float(actual_paid_h if actual_paid_h is not None else (net_paid or 0))
            # Build row text
            actual_part = ""
            if actual_paid_h is not None:
                diff = float(net_paid or 0) - float(actual_paid_h)
                if diff > 0.009:
                    actual_part = f" | Elden Ödenen: {actual_paid_h:,.2f} ₺ | ⚠ Eksik Ödeme: -{diff:,.2f} ₺"
                else:
                    actual_part = f" | Elden Ödenen: {actual_paid_h:,.2f} ₺ ✓"
            text = f"{emp_name} | Net Hesaplanan: {net_paid:,.2f} ₺{actual_part} | Detay: {missing_summary or 'Yok'}"
            text_color = "orange" if actual_paid_h is not None and (float(net_paid or 0) - float(actual_paid_h)) > 0.009 else None
            ctk.CTkLabel(scroll, text=text, font=font_row, anchor="w", justify="left", wraplength=560, text_color=text_color).pack(
                anchor="w", fill="x", pady=6
            )

        if last_ts is not None:
            ctk.CTkLabel(
                scroll,
                text=f"💰 Bu İşlemde Toplam Ödenen: {batch_total:,.2f} ₺",
                font=ctk.CTkFont(family="Arial", size=20, weight="bold"),
                text_color="green",
                anchor="w",
            ).pack(anchor="w", fill="x", pady=(6, 14))

    def _on_remove_employee(self, emp_id: int):
        if not messagebox.askyesno(
            "Onay",
            "Bu çalışanı silmek istediğinize emin misiniz? (Geçmiş ödeme kayıtları silinmez)",
            parent=self.winfo_toplevel(),
        ):
            return
        remove_employee(emp_id)
        if self.selected_employee_id == emp_id:
            self._show_default_view()
        self._refresh_employee_list()

    def _refresh_employee_list(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        employees = fetch_active_employees()
        grand_total = 0.0

        for row in employees:
            emp_id, name, _phone, weekly_salary, _a = row[:5]
            day_vals = [float(row[i] or 0) for i in range(5, 10)]
            is_paid = int(row[10]) if len(row) > 10 else 0
            actual_paid_val = row[11] if len(row) > 11 else None
            total_missing = sum(day_vals)
            weekly_salary = weekly_salary or 0
            hourly = weekly_salary / 50
            deduction = total_missing * hourly
            net_salary = max(0, weekly_salary - deduction)
            grand_total += net_salary

            # missing display
            m = int(total_missing)
            full_days = m // 10
            remainder = m % 10
            half_days = remainder // 5
            hours_rem = remainder % 5
            total_days = full_days + (0.5 if half_days == 1 else 0)
            eksik_text = "Yok" if total_missing == 0 else f"{total_days} Gün, {hours_rem} Saat"

            # Card styling based on is_paid
            if is_paid:
                card_color = ("#d6ead6", "#2a3d2a")
                name_color = "#808080"
                detail_color = "#808080"
                sel_btn_text = "ÖDENDİ ✅"
                sel_btn_color = "#5a7a5a"
                sel_btn_hover = "#4a6a4a"
            else:
                card_color = ("gray88", "gray18")
                name_color = None
                detail_color = "orange" if total_missing > 0 else None
                sel_btn_text = "SEÇ"
                sel_btn_color = "#1f6aa5"
                sel_btn_hover = "#144870"

            # Card frame
            card = ctk.CTkFrame(self.scroll_frame, fg_color=card_color, corner_radius=10)
            card.pack(fill="x", pady=5, padx=2)

            content_row = ctk.CTkFrame(card, fg_color="transparent")
            content_row.pack(fill="x", padx=12, pady=10)

            left_block = ctk.CTkFrame(content_row, fg_color="transparent", cursor="hand2")
            left_block.pack(side="left", fill="both", expand=True)

            name_lbl = ctk.CTkLabel(
                left_block, text=name, font=self.font_list_name, anchor="w",
                text_color=name_color if name_color else ("gray14", "gray84"),
            )
            name_lbl.pack(anchor="w")

            detail_lbl = ctk.CTkLabel(
                left_block,
                text=f"Taban: {weekly_salary:,.2f} ₺  |  Net: {net_salary:,.2f} ₺  |  Eksik: {eksik_text}",
                font=self.font_list_detail, anchor="w", text_color=detail_color,
            )
            detail_lbl.pack(anchor="w")

            # Show actual_paid difference if set (0 is a valid entry meaning nothing paid)
            if actual_paid_val is not None:
                diff = net_salary - actual_paid_val
                if diff > 0.009:
                    diff_color = "orange"
                    diff_text = f"Elden Ödenen: {actual_paid_val:,.2f} ₺  |  Eksik Ödeme: -{diff:,.2f} ₺"
                else:
                    diff_color = "green"
                    diff_text = f"Elden Ödenen: {actual_paid_val:,.2f} ₺  ✓ Tam Ödendi"
                ctk.CTkLabel(
                    left_block, text=diff_text, font=self.font_list_detail,
                    anchor="w", text_color=diff_color,
                ).pack(anchor="w")

            def select_emp(eid):
                return lambda e=None: self._show_employee_detail(eid)

            sel = select_emp(emp_id)
            card.bind("<Button-1>", sel)
            content_row.bind("<Button-1>", sel)
            left_block.bind("<Button-1>", sel)
            name_lbl.bind("<Button-1>", sel)
            detail_lbl.bind("<Button-1>", sel)

            btn_box = ctk.CTkFrame(content_row, fg_color="transparent")
            btn_box.pack(side="right", padx=(8, 0))
            ctk.CTkButton(
                btn_box,
                text=sel_btn_text,
                font=self.font,
                width=100,
                height=48,
                fg_color=sel_btn_color,
                hover_color=sel_btn_hover,
                command=lambda eid=emp_id: self._show_employee_detail(eid),
            ).pack(side="left", padx=(0, 6))
            ctk.CTkButton(
                btn_box,
                text="KALDIR",
                font=self.font,
                width=100,
                height=48,
                fg_color="#8B0000",
                hover_color="#5C0000",
                command=lambda eid=emp_id: self._on_remove_employee(eid),
            ).pack(side="left")

        self.total_weekly_label.configure(text=f"💰 BU HAFTA TOPLAM ÖDENECEK: {grand_total:,.2f} ₺")