# ui/app.py
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from core.db import Database
from core.logger import get_logger
from logic.session_manager import SessionManager, ZoneSession
from ui.zone_panel import ZonePanel
from exporter.easy_quest_xml import generate_easy_quest_xml

logger = get_logger(__name__)

class QuesterApp(ttkb.Window):
    def __init__(self):
        super().__init__(themename="superhero")
        self.title("Quester Profile Generator — CMaNGOS TBC 2.4.3")
        self.geometry("1350x850")
        self.db = Database()
        self.session_manager = SessionManager()
        
        self.setup_styles()
        self.create_widgets()
        self.load_project()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.save_project(show_msg=False)
        self.destroy()

    def setup_styles(self):
        self.style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        self.style.configure("TNotebook.Tab", font=("Segoe UI Bold", 10), padding=[10, 5])

    def create_widgets(self):
        header = ttkb.Frame(self, padding=10, bootstyle=PRIMARY)
        header.pack(fill=tk.X)
        ttkb.Label(header, text="Quester Generator Pro", font=("Segoe UI Bold", 18), bootstyle=LIGHT).pack(side=tk.LEFT, padx=10)
        
        toolbar = ttkb.Frame(self, padding=5)
        toolbar.pack(fill=tk.X)
        
        ttkb.Button(toolbar, text="＋ Добавить зону", bootstyle=SUCCESS, command=self.add_zone_tab).pack(side=tk.LEFT, padx=5)
        ttkb.Button(toolbar, text="💾 Сохранить проект", bootstyle=INFO, command=self.save_project).pack(side=tk.LEFT, padx=5)
        ttkb.Button(toolbar, text="🚀 Генерировать XML", bootstyle=PRIMARY, command=self.generate_xml).pack(side=tk.LEFT, padx=5)
        
        self.notebook = ttkb.Notebook(self, bootstyle=PRIMARY)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttkb.Button(toolbar, text="✖ Удалить вкладку", bootstyle=DANGER, command=self.close_current_tab).pack(side=tk.RIGHT, padx=5)

    def add_zone_tab(self, session: Optional[ZoneSession] = None):
        if session is None:
            session = ZoneSession(zone_id=0, zone_name="Новая зона")
            self.session_manager.add_session(session)
        
        panel = ZonePanel(self.notebook, session, self.db)
        self.notebook.add(panel, text=session.zone_name if session.zone_id else "Новая зона")
        self.notebook.select(panel)
        return panel

    def close_current_tab(self):
        idx = self.notebook.index("current")
        if idx < 0: return
        if messagebox.askyesno("Удаление", "Удалить текущую вкладку из проекта?"):
            self.notebook.forget(idx)
            self.session_manager.remove_session(idx)

    def save_project(self, show_msg=True):
        # Собираем актуальные данные изо всех открытых вкладок
        for tab_id in self.notebook.tabs():
            panel = self.notebook.nametowidget(tab_id)
            if hasattr(panel, 'save_grind_settings'):
                panel.save_grind_settings()
        
        self.session_manager.save()
        if show_msg:
            messagebox.showinfo("Успех", "Проект сохранен в project.json")

    def load_project(self):
        sessions = self.session_manager.load()
        if not sessions:
            self.add_zone_tab()
        else:
            for s in sessions:
                self.add_zone_tab(s)

    def generate_xml(self):
        self.save_project(show_msg=False)
        if not self.session_manager.sessions:
            messagebox.showwarning("Внимание", "Нет зон для генерации!")
            return
        
        filename = "Global_Quester_Profile.xml"
        try:
            generate_easy_quest_xml(self.session_manager.sessions, filename)
            messagebox.showinfo("Успех", f"Профиль сгенерирован: {filename}")
        except Exception as e:
            logger.error(f"Generation error: {e}")
            messagebox.showerror("Ошибка", f"Ошибка при генерации: {e}")

    def destroy(self):
        self.db.close()
        super().destroy()

if __name__ == "__main__":
    app = QuesterApp()
    app.mainloop()
