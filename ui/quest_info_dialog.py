# ui/quest_info_dialog.py
import tkinter as tk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from typing import Dict

class QuestInfoDialog(ttkb.Toplevel):
    def __init__(self, master, title: str, data: Dict[str, str]):
        super().__init__(master)
        self.title(f"Инфо: {title}")
        self.geometry("600x500")
        self.transient(master)
        
        main_frame = ttkb.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttkb.Label(main_frame, text=title, font=("Segoe UI Bold", 14), bootstyle=INFO).pack(anchor=tk.W, pady=(0, 10))
        
        # Цели
        ttkb.Label(main_frame, text="Цели:", font=("Segoe UI Bold", 11)).pack(anchor=tk.W)
        obj_text = tk.Text(main_frame, height=5, font=("Segoe UI", 10), wrap=tk.WORD, padx=5, pady=5)
        obj_text.insert(tk.END, data.get('objectives', 'Нет целей'))
        obj_text.config(state=tk.DISABLED)
        obj_text.pack(fill=tk.X, pady=(0, 15))
        
        # Описание
        ttkb.Label(main_frame, text="Описание:", font=("Segoe UI Bold", 11)).pack(anchor=tk.W)
        det_text = tk.Text(main_frame, font=("Segoe UI", 10), wrap=tk.WORD, padx=5, pady=5)
        det_text.insert(tk.END, data.get('details', 'Нет описания'))
        det_text.config(state=tk.DISABLED)
        det_text.pack(fill=tk.BOTH, expand=True)
        
        btn_close = ttkb.Button(main_frame, text="Закрыть", command=self.destroy, bootstyle=SECONDARY)
        btn_close.pack(pady=10)
        
        self.bind("<Escape>", lambda e: self.destroy())
