# ui/zone_panel.py
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from typing import List, Dict, Optional

from core.db import Database
from core.logger import get_logger
from data_access.zones_repo import search_zones_by_name, get_zone_name, ZONE_NAMES
from data_access.quests_repo import get_quests_by_zone, get_objectives_for_quest, get_quest_details
from data_access.npc_repo import get_quest_starter_type 
from logic.faction_filter import get_faction_mask, filter_quests_by_faction
from logic.quest_chains import build_quest_chains
from logic.session_manager import ZoneSession
from logic.quest_sorter import sort_quests_with_dependencies
from logic.vector_parser import parse_vector3_strings
from core.models import Hotspot
from ui.quest_info_dialog import QuestInfoDialog

logger = get_logger(__name__)

class ZonePanel(ttkb.Frame):
    def __init__(self, master, session: ZoneSession, db: Database, **kwargs):
        # Исправлено: убран padding из конструктора Frame, если он вызывал ошибку, 
        # но обычно Frame поддерживает padding. Ошибка была в LabelFrame ниже.
        super().__init__(master, **kwargs)
        self.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.session = session
        self.db = db
        self.quests: List = []
        self.objectives: Dict = {}
        self.check_vars: Dict[str, tk.BooleanVar] = {}
        
        self.create_widgets()
        
        if self.session.zone_id:
            self.zone_combo.set(self.session.zone_name)
            self.faction_var.set(self.session.faction)
            self.load_quests()
        
        self.load_grind_settings()

    def create_widgets(self):
        # --- Панель поиска и фильтров ---
        search_frame = ttkb.Frame(self, padding=5)
        search_frame.pack(fill=tk.X)
        
        ttkb.Label(search_frame, text="Зона:", font=("Segoe UI Bold", 10)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.zone_combo = ttkb.Combobox(search_frame, width=40)
        self.zone_combo['values'] = list(ZONE_NAMES.values())
        self.zone_combo.pack(side=tk.LEFT, padx=5)
        self.zone_combo.bind("<KeyRelease>", self.on_zone_search)
        
        self.faction_var = tk.StringVar(value=self.session.faction)
        ttkb.Radiobutton(search_frame, text="Альянс", variable=self.faction_var, value="alliance", bootstyle=INFO).pack(side=tk.LEFT, padx=10)
        ttkb.Radiobutton(search_frame, text="Орда", variable=self.faction_var, value="horde", bootstyle=DANGER).pack(side=tk.LEFT, padx=5)
        
        load_btn = ttkb.Button(search_frame, text="Загрузить квесты", bootstyle=SUCCESS, command=self.load_quests)
        load_btn.pack(side=tk.LEFT, padx=10)

        # --- Верхняя панель настроек (Гринд + Логистика) ---
        config_parent = ttkb.Frame(self)
        config_parent.pack(fill=tk.X, pady=10)

        # 1. Настройки Гринда
        # ИСПРАВЛЕНО: Убран padding из конструктора LabelFrame
        self.grind_frame = ttkb.LabelFrame(config_parent, text="Настройки Гринда (Фарм мобов)")
        self.grind_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Ряд 1: Моб и Уровни
        g_row1 = ttkb.Frame(self.grind_frame, padding=5)
        g_row1.pack(fill=tk.X)
        
        ttkb.Label(g_row1, text="Mob ID:").pack(side=tk.LEFT)
        self.mob_id_var = tk.StringVar()
        ttkb.Entry(g_row1, textvariable=self.mob_id_var, width=8, bootstyle="secondary").pack(side=tk.LEFT, padx=5)
        
        ttkb.Label(g_row1, text="Имя (опц.):").pack(side=tk.LEFT)
        self.mob_name_var = tk.StringVar()
        ttkb.Entry(g_row1, textvariable=self.mob_name_var, width=15).pack(side=tk.LEFT, padx=5)
        
        ttkb.Label(g_row1, text="Уровни (Min-Max):").pack(side=tk.LEFT, padx=(10, 2))
        self.min_lvl_var = tk.StringVar(value="0")
        ttkb.Entry(g_row1, textvariable=self.min_lvl_var, width=4).pack(side=tk.LEFT)
        ttkb.Label(g_row1, text="-").pack(side=tk.LEFT)
        self.target_lvl_var = tk.StringVar(value="0")
        ttkb.Entry(g_row1, textvariable=self.target_lvl_var, width=4).pack(side=tk.LEFT)
        
        # Ряд 2: Координаты
        g_row2 = ttkb.Frame(self.grind_frame, padding=5)
        g_row2.pack(fill=tk.BOTH, expand=True)
        
        ttkb.Label(g_row2, text="Вставь сюда координаты из WRobot:").pack(anchor=tk.W)
        self.hotspots_text = tk.Text(g_row2, height=5, width=40, font=("Consolas", 8))
        self.hotspots_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=2)
        
        g_btns = ttkb.Frame(g_row2)
        g_btns.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        
        ttkb.Button(g_btns, text="Парсить\nКоординаты", bootstyle=(INFO, OUTLINE), command=self.parse_hotspots).pack(fill=tk.X, pady=2)
        ttkb.Button(g_btns, text="Сохранить\nНастройки", bootstyle=(SUCCESS), command=self.save_grind_settings).pack(fill=tk.X, pady=2)

        # 2. Настройки Логистики
        # ИСПРАВЛЕНО: Убран padding из конструктора LabelFrame
        self.logistics_frame = ttkb.LabelFrame(config_parent, text="Логистика и Навигация")
        self.logistics_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        l_row1 = ttkb.Frame(self.logistics_frame, padding=5)
        l_row1.pack(fill=tk.X)
        
        self.inc_vendors_var = tk.BooleanVar(value=self.session.include_vendors)
        ttkb.Checkbutton(l_row1, text="Вендоры (Ремонт/Еда)", variable=self.inc_vendors_var, bootstyle="round-toggle").pack(anchor=tk.W, pady=2)
        
        self.inc_trainers_var = tk.BooleanVar(value=self.session.include_trainers)
        ttkb.Checkbutton(l_row1, text="Тренеры Класса", variable=self.inc_trainers_var, bootstyle="round-toggle").pack(anchor=tk.W, pady=2)
        
        self.inc_fms_var = tk.BooleanVar(value=self.session.include_flight_masters)
        ttkb.Checkbutton(l_row1, text="Мастера Полетов", variable=self.inc_fms_var, bootstyle="round-toggle").pack(anchor=tk.W, pady=2)

        l_row2 = ttkb.Frame(self.logistics_frame, padding=5)
        l_row2.pack(fill=tk.BOTH, expand=True)
        
        ttkb.Label(l_row2, text="Точки перехода (RunTo):").pack(anchor=tk.W)
        self.run_to_list = tk.Listbox(l_row2, height=3, font=("Segoe UI", 9))
        self.run_to_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        l_btns = ttkb.Frame(l_row2)
        l_btns.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        ttkb.Button(l_btns, text="+", bootstyle=SUCCESS, command=self.add_run_to, width=4).pack(pady=2)
        ttkb.Button(l_btns, text="-", bootstyle=DANGER, command=self.remove_run_to, width=4).pack(pady=2)

        # --- Таблица квестов ---
        tree_frame = ttkb.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttkb.Scrollbar(tree_frame, bootstyle=PRIMARY)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(tree_frame, columns=("Check", "ID", "Level", "Type"), show="tree headings", yscrollcommand=scrollbar.set)
        self.tree.column("#0", width=400, anchor=tk.W)
        self.tree.heading("#0", text="Название квеста (ПКМ - Инфо)")
        self.tree.heading("Check", text="✓")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Level", text="Ур.")
        self.tree.heading("Type", text="Тип")
        
        self.tree.column("Check", width=40, anchor=tk.CENTER)
        self.tree.column("ID", width=60, anchor=tk.CENTER)
        self.tree.column("Level", width=40, anchor=tk.CENTER)
        self.tree.column("Type", width=120, anchor=tk.CENTER)
        
        self.tree.tag_configure("chain", background="#2b2b2b", foreground="#17a2b8", font=("Segoe UI Bold", 10))
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)

    def parse_hotspots(self):
        """Парсит текст из поля ввода и превращает его в XML-вид."""
        raw_text = self.hotspots_text.get("1.0", tk.END)
        hotspots = parse_vector3_strings(raw_text)
        
        if hotspots:
            self.hotspots_text.delete("1.0", tk.END)
            # Выводим обратно в красивом формате, чтобы пользователь видел результат
            for h in hotspots:
                self.hotspots_text.insert(tk.END, f'<Vector3 X="{h.x}" Y="{h.y}" Z="{h.z}" />\n')
            
            # Сразу сохраняем в сессию
            self.session.grind_settings.hotspots = hotspots
            messagebox.showinfo("Успех", f"Найдено и добавлено точек: {len(hotspots)}")
        else:
            messagebox.showwarning("Внимание", "Координаты не найдены.\nВставь текст вида:\nMy Position: -9400.98, -2036.69, 58.38")

    def add_run_to(self):
        dialog = ttkb.Toplevel(self)
        dialog.title("Добавить точку RunTo")
        dialog.geometry("400x250")
        
        ttkb.Label(dialog, text="Название точки:").pack(pady=5)
        name_entry = ttkb.Entry(dialog, width=30)
        name_entry.pack(pady=5)
        name_entry.insert(0, f"RunTo {self.run_to_list.size() + 1}")
        
        ttkb.Label(dialog, text="Координаты (вставь из WRobot):").pack(pady=5)
        coords_entry = ttkb.Entry(dialog, width=40)
        coords_entry.pack(pady=5)
        
        def save():
            raw = coords_entry.get()
            pts = parse_vector3_strings(raw)
            if pts:
                p = pts[0]
                from core.models import RunTo
                rt = RunTo(x=p.x, y=p.y, z=p.z, name=name_entry.get())
                self.session.run_to_points.append(rt)
                self.run_to_list.insert(tk.END, f"{rt.name} ({rt.x:.1f}, {rt.y:.1f}, {rt.z:.1f})")
                dialog.destroy()
            else:
                messagebox.showerror("Ошибка", "Не удалось распознать координаты!")

        ttkb.Button(dialog, text="Добавить", command=save, bootstyle=SUCCESS).pack(pady=10)

    def remove_run_to(self):
        idx = self.run_to_list.curselection()
        if idx:
            self.session.run_to_points.pop(idx[0])
            self.run_to_list.delete(idx[0])

    def save_grind_settings(self):
        try:
            # Сохраняем ID моба
            mid = self.mob_id_var.get().strip()
            self.session.grind_settings.mob_id = int(mid) if mid.isdigit() else 0
            self.session.grind_settings.mob_name = self.mob_name_var.get()
            
            # Сохраняем уровни
            min_l = self.min_lvl_var.get().strip()
            max_l = self.target_lvl_var.get().strip()
            self.session.grind_settings.min_level = int(min_l) if min_l.isdigit() else 0
            self.session.grind_settings.target_level = int(max_l) if max_l.isdigit() else 0
            
            # Сохраняем логистику
            self.session.include_vendors = self.inc_vendors_var.get()
            self.session.include_trainers = self.inc_trainers_var.get()
            self.session.include_flight_masters = self.inc_fms_var.get()

            # Хотспоты уже обновляются в parse_hotspots, но на всякий случай парсим текущий текст
            raw_text = self.hotspots_text.get("1.0", tk.END)
            parsed = parse_vector3_strings(raw_text)
            if parsed:
                self.session.grind_settings.hotspots = parsed
            
            logger.info(f"Settings saved for zone {self.session.zone_id}")
            # Не показываем popup каждый раз, чтобы не бесить, просто лог
        except ValueError:
            messagebox.showerror("Ошибка", "В полях уровней или ID должны быть числа!")

    def load_grind_settings(self):
        gs = self.session.grind_settings
        self.mob_id_var.set(str(gs.mob_id) if gs.mob_id else "")
        self.mob_name_var.set(gs.mob_name if gs.mob_name else "")
        self.min_lvl_var.set(str(gs.min_level))
        self.target_lvl_var.set(str(gs.target_level))
        
        self.hotspots_text.delete("1.0", tk.END)
        for h in gs.hotspots:
            self.hotspots_text.insert(tk.END, f'<Vector3 X="{h.x}" Y="{h.y}" Z="{h.z}" />\n')

        self.inc_vendors_var.set(self.session.include_vendors)
        self.inc_trainers_var.set(self.session.include_trainers)
        self.inc_fms_var.set(self.session.include_flight_masters)

        self.run_to_list.delete(0, tk.END)
        for rt in self.session.run_to_points:
            self.run_to_list.insert(tk.END, f"{rt.name} ({rt.x:.1f}, {rt.y:.1f}, {rt.z:.1f})")

    def on_zone_search(self, event):
        query = self.zone_combo.get().lower()
        if not query:
            self.zone_combo['values'] = list(ZONE_NAMES.values())
            return
        matching = [v for k, v in ZONE_NAMES.items() if query in v.lower()]
        self.zone_combo['values'] = matching

    def load_quests(self):
        zone_input = self.zone_combo.get().strip()
        if not zone_input: return

        zone_id = None
        if zone_input.isdigit():
            zid = int(zone_input)
            if zid in ZONE_NAMES: zone_id = zid
        else:
            for zid, zname in ZONE_NAMES.items():
                if zone_input.lower() == zname.lower():
                    zone_id = zid
                    break
        
        if not zone_id: 
            messagebox.showerror("Ошибка", "Зона не найдена!")
            return
        
        self.session.zone_id = zone_id
        self.session.zone_name = ZONE_NAMES[zone_id]
        self.session.faction = self.faction_var.get()
        
        # Обновляем имя вкладки
        try:
            notebook = self.master
            current_tab = notebook.select()
            notebook.tab(current_tab, text=self.session.zone_name)
        except: pass

        mask = get_faction_mask(self.session.faction)
        try:
            raw_quests = get_quests_by_zone(self.db, zone_id)
            valid_quests = []
            for q in filter_quests_by_faction(raw_quests, mask):
                # Исключаем квесты, начинающиеся с предметов (пока сложно обрабатывать)
                if get_quest_starter_type(self.db, q.entry) != 'item':
                    valid_quests.append(q)
            
            self.quests = valid_quests
            self.objectives = {q.entry: get_objectives_for_quest(self.db, q.entry) for q in valid_quests}
            
            chains = build_quest_chains(valid_quests)
            self.tree.delete(*self.tree.get_children())
            self.check_vars.clear()
            
            for chain in chains:
                if len(chain) == 1:
                    self.add_quest_node("", chain[0])
                else:
                    chain_node = self.tree.insert("", "end", text=f"{chain[0].title} (Цепочка)", values=("☐", "", "", ""), tags=("chain",))
                    self.check_vars[chain_node] = tk.BooleanVar(value=False)
                    for q in chain:
                        self.add_quest_node(chain_node, q)
            self.restore_selection()
        except Exception as e:
            logger.error(f"Error loading quests: {e}")
            messagebox.showerror("Ошибка БД", f"Не удалось загрузить квесты: {e}")

    def add_quest_node(self, parent, q):
        objs = self.objectives.get(q.entry, [])
        type_str = ", ".join(set(o.type for o in objs)) if objs else "Talk"
        node = self.tree.insert(parent, "end", text=q.title, values=("☐", q.entry, q.quest_level, type_str))
        self.check_vars[node] = tk.BooleanVar(value=False)

    def on_tree_click(self, event):
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if item and col == "#1": # Колонка Check
            self.toggle_check(item)

    def on_tree_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item: self.toggle_check(item)

    def toggle_check(self, item):
        if item in self.check_vars:
            var = self.check_vars[item]
            new_val = not var.get()
            var.set(new_val)
            self.tree.set(item, "Check", "☑" if new_val else "☐")
            
            # Если это цепочка, выделяем все дочерние
            if self.tree.tag_has("chain", item):
                for child in self.tree.get_children(item):
                    if child in self.check_vars:
                        self.check_vars[child].set(new_val)
                        self.tree.set(child, "Check", "☑" if new_val else "☐")
            
            self.update_session_selection()

    def update_session_selection(self):
        selected = []
        for node, var in self.check_vars.items():
            if var.get():
                vals = self.tree.item(node, "values")
                if vals and vals[1]: selected.append(int(vals[1]))
        self.session.selected_quest_ids = list(set(selected))

    def restore_selection(self):
        for node, var in self.check_vars.items():
            vals = self.tree.item(node, "values")
            if vals and vals[1] and int(vals[1]) in self.session.selected_quest_ids:
                var.set(True)
                self.tree.set(node, "Check", "☑")

    def on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item: return
        
        vals = self.tree.item(item, "values")
        if not vals or not vals[1]: return
        
        quest_id = int(vals[1])
        title = self.tree.item(item, "text")
        
        data = get_quest_details(self.db, quest_id)
        QuestInfoDialog(self, title, data)
