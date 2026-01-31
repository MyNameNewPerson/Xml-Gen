# ui/zone_panel.py
import tkinter as tk
from tkinter import ttk, messagebox
import xml.etree.ElementTree as ET
import re
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
        self._loading = False  # Флаг для предотвращения автосохранения при загрузке
        
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
        self.grind_frame = ttkb.LabelFrame(config_parent, text="Настройки Гринда (Цель)")
        self.grind_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Уровни (Min-Max)
        g_row1 = ttkb.Frame(self.grind_frame, padding=5)
        g_row1.pack(fill=tk.X)
        
        ttkb.Label(g_row1, text="Уровни (Min-Max):").pack(side=tk.LEFT)
        self.min_lvl_var = tk.StringVar(value="0")
        self.min_lvl_var.trace_add("write", self.auto_save_levels)
        self.min_lvl_entry = ttkb.Entry(g_row1, textvariable=self.min_lvl_var, width=5)
        self.min_lvl_entry.pack(side=tk.LEFT, padx=2)
        self.enable_text_features(self.min_lvl_entry)
        
        ttkb.Label(g_row1, text="-").pack(side=tk.LEFT)
        self.target_lvl_var = tk.StringVar(value="0")
        self.target_lvl_var.trace_add("write", self.auto_save_levels)
        self.target_lvl_entry = ttkb.Entry(g_row1, textvariable=self.target_lvl_var, width=5)
        self.target_lvl_entry.pack(side=tk.LEFT, padx=2)
        self.enable_text_features(self.target_lvl_entry)
        
        # Поле ввода XML
        ttkb.Label(self.grind_frame, text="Вставь XML NPC (<Npc>...):").pack(anchor=tk.W, padx=5)
        self.grind_input = tk.Text(self.grind_frame, height=4, width=40, font=("Consolas", 8))
        self.grind_input.pack(fill=tk.X, padx=5, pady=2)
        self.enable_text_features(self.grind_input)
        
        # Кнопка и Инфо
        g_bot = ttkb.Frame(self.grind_frame, padding=5)
        g_bot.pack(fill=tk.X)
        ttkb.Button(g_bot, text="Применить цель", bootstyle=INFO, command=self.parse_grind_target).pack(side=tk.LEFT)
        self.grind_info_label = ttkb.Label(g_bot, text="Нет цели", font=("Segoe UI", 8), foreground="gray")
        self.grind_info_label.pack(side=tk.LEFT, padx=10)

        # 2. Настройки Логистики
        self.logistics_frame = ttkb.LabelFrame(config_parent, text="Логистика (RunTo)")
        self.logistics_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        l_row1 = ttkb.Frame(self.logistics_frame, padding=5)
        l_row1.pack(fill=tk.X)
        
        self.inc_vendors_var = tk.BooleanVar(value=self.session.include_vendors)
        self.inc_vendors_var.trace_add("write", lambda *a: setattr(self.session, 'include_vendors', self.inc_vendors_var.get()))
        ttkb.Checkbutton(l_row1, text="Вендоры", variable=self.inc_vendors_var).pack(side=tk.LEFT, padx=2)
        
        self.inc_trainers_var = tk.BooleanVar(value=self.session.include_trainers)
        self.inc_trainers_var.trace_add("write", lambda *a: setattr(self.session, 'include_trainers', self.inc_trainers_var.get()))
        ttkb.Checkbutton(l_row1, text="Тренеры", variable=self.inc_trainers_var).pack(side=tk.LEFT, padx=2)
        
        self.inc_fms_var = tk.BooleanVar(value=self.session.include_flight_masters)
        self.inc_fms_var.trace_add("write", lambda *a: setattr(self.session, 'include_flight_masters', self.inc_fms_var.get()))
        ttkb.Checkbutton(l_row1, text="Полеты", variable=self.inc_fms_var).pack(side=tk.LEFT, padx=2)

        # Список точек
        self.run_to_list = tk.Listbox(self.logistics_frame, height=3, font=("Segoe UI", 9))
        self.run_to_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        # Ввод координат
        l_bot = ttkb.Frame(self.logistics_frame, padding=5)
        l_bot.pack(fill=tk.X)
        ttkb.Label(l_bot, text="Вставь координаты (можно списком):").pack(anchor=tk.W, padx=2)
        
        input_container = ttkb.Frame(l_bot)
        input_container.pack(fill=tk.X, expand=True)
        
        self.run_to_input = tk.Text(input_container, height=3, width=30, font=("Consolas", 8))
        self.run_to_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.enable_text_features(self.run_to_input)
        
        btn_box = ttkb.Frame(input_container)
        btn_box.pack(side=tk.LEFT, fill=tk.Y)
        
        ttkb.Button(btn_box, text="+", width=3, bootstyle=SUCCESS, command=self.add_run_to_from_input).pack(fill=tk.X, pady=1)
        ttkb.Button(btn_box, text="-", width=3, bootstyle=DANGER, command=self.remove_run_to).pack(fill=tk.X, pady=1)
        ttkb.Button(btn_box, text="Clr", width=3, bootstyle=SECONDARY, command=lambda: self.run_to_input.delete("1.0", tk.END)).pack(fill=tk.X, pady=1)

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

    def parse_grind_target(self):
        """Парсит XML NPC и добавляет цель гринда (ID и Hotspot)."""
        text = self.grind_input.get("1.0", tk.END).strip()
        if not text: return
        
        try:
            # Если пользователь вставил просто текст, а не XML
            if not text.startswith("<"):
                messagebox.showwarning("Ошибка", "Ожидается XML формат <Npc>...</Npc>")
                return

            # Оборачиваем в фейковый корень, чтобы распарсить несколько <Npc> подряд
            wrapped_text = f"<Root>{text}</Root>"
            try:
                root = ET.fromstring(wrapped_text)
            except ET.ParseError:
                # Если не получилось, пробуем как есть
                root = ET.fromstring(text)
            
            # Инициализируем список ID, если его нет (для поддержки множества мобов)
            if not hasattr(self.session.grind_settings, 'mob_ids'):
                self.session.grind_settings.mob_ids = set()
                if self.session.grind_settings.mob_id:
                    self.session.grind_settings.mob_ids.add(self.session.grind_settings.mob_id)
            
            # 1. Ищем все Entry (рекурсивно)
            for entry_node in root.findall(".//Entry"):
                new_id = int(entry_node.text)
                self.session.grind_settings.mob_ids.add(new_id)
                self.session.grind_settings.mob_id = new_id # Обновляем последний для UI
            
            # 2. Ищем имя (берем первое попавшееся)
            if not self.session.grind_settings.mob_name:
                name_node = root.find(".//Name")
                if name_node is not None:
                    self.session.grind_settings.mob_name = name_node.text
                
            # 3. Ищем координаты (Vector3 или Position)
            def add_spot(node):
                if node is None: return
                x = float(vec.get("X"))
                y = float(vec.get("Y"))
                z = float(vec.get("Z"))
                from core.models import Hotspot
                
                # Проверяем на дубликаты координат (простое сравнение)
                new_spot = Hotspot(x, y, z)
                exists = False
                for h in self.session.grind_settings.hotspots:
                    if abs(h.x - x) < 1.0 and abs(h.y - y) < 1.0:
                        exists = True
                        break
                
                if not exists:
                    self.session.grind_settings.hotspots.append(new_spot)

            for vec in root.findall(".//Vector3"): add_spot(vec)
            for pos in root.findall(".//Position"): add_spot(pos)

            self.update_grind_ui_info()
            self.grind_input.delete("1.0", tk.END)
            
        except Exception as e:
            logger.error(f"XML Parse Error: {e}")
            messagebox.showerror("Ошибка", f"Неверный формат XML: {e}")

    def add_run_to_from_input(self):
        """Добавляет точку RunTo из строки координат."""
        text = self.run_to_input.get("1.0", tk.END).strip()
        if not text: return
        
        lines = text.split('\n')
        added_count = 0
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            x, y, z = 0.0, 0.0, 0.0
            found = False
            
            # 1. Пробуем XML формат: <Vector3 X="..." ... />
            xml_match = re.search(r'X="([\d\.-]+)"\s+Y="([\d\.-]+)"\s+Z="([\d\.-]+)"', line)
            if xml_match:
                x, y, z = float(xml_match.group(1)), float(xml_match.group(2)), float(xml_match.group(3))
                found = True
            else:
                # 2. Пробуем формат через запятую: 123.45, 67.89, 0.0
                floats = re.findall(r'(-?\d+(?:\.\d+)?)', line)
                if len(floats) >= 3:
                    x, y, z = float(floats[0]), float(floats[1]), float(floats[2])
                    found = True
            
            if found:
                from core.models import RunTo
                name = f"RunTo {len(self.session.run_to_points) + 1}"
                rt = RunTo(x, y, z, name)
                self.session.run_to_points.append(rt)
                self.run_to_list.insert(tk.END, f"{rt.name} ({rt.x:.1f}, {rt.y:.1f}, {rt.z:.1f})")
                added_count += 1
        
        if added_count > 0:
            self.run_to_input.delete("1.0", tk.END)
        else:
            messagebox.showwarning("Ошибка", "Не удалось распознать координаты")

    def remove_run_to(self):
        idx = self.run_to_list.curselection()
        if idx:
            self.session.run_to_points.pop(idx[0])
            self.run_to_list.delete(idx[0])

    def auto_save_levels(self, *args):
        # Если идет программная загрузка данных, не сохраняем (иначе перезапишем нулями)
        if self._loading: return

        # Сохраняем Min Level
        try:
            val = self.min_lvl_var.get().strip()
            if val: self.session.grind_settings.min_level = int(val)
        except ValueError:
            pass
            
        # Сохраняем Max Level
        try:
            val = self.target_lvl_var.get().strip()
            if val: self.session.grind_settings.target_level = int(val)
        except ValueError:
            pass

    def load_grind_settings(self):
        self._loading = True
        try:
            gs = self.session.grind_settings
            
            # Восстанавливаем mob_ids если его нет, но есть mob_id
            if not hasattr(gs, 'mob_ids'):
                gs.mob_ids = set()
                if gs.mob_id:
                    gs.mob_ids.add(gs.mob_id)
            
            self.min_lvl_var.set(str(gs.min_level))
            self.target_lvl_var.set(str(gs.target_level))
        finally:
            self._loading = False
            
        self.update_grind_ui_info()

        self.inc_vendors_var.set(self.session.include_vendors)
        self.inc_trainers_var.set(self.session.include_trainers)
        self.inc_fms_var.set(self.session.include_flight_masters)

        self.run_to_list.delete(0, tk.END)
        for rt in self.session.run_to_points:
            self.run_to_list.insert(tk.END, f"{rt.name} ({rt.x:.1f}, {rt.y:.1f}, {rt.z:.1f})")

    def update_grind_ui_info(self):
        gs = self.session.grind_settings
        # Подсчет ID
        ids_count = 0
        if hasattr(gs, 'mob_ids'):
            ids_count = len(gs.mob_ids)
        elif gs.mob_id:
            ids_count = 1
            
        info = f"IDs: {ids_count}"
        if gs.mob_name: info += f" | {gs.mob_name}"
        if gs.hotspots: info += f" | Точек: {len(gs.hotspots)}"
        self.grind_info_label.config(text=info)

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

    def enable_text_features(self, widget):
        """Включает поддержку горячих клавиш и контекстного меню для виджета."""
        self.setup_text_bindings(widget)
        widget.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Отображает контекстное меню при клике ПКМ."""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: self.perform_copy(event.widget))
        menu.add_command(label="Вставить", command=lambda: self.perform_paste(event.widget))
        menu.add_command(label="Вырезать", command=lambda: self.perform_cut(event.widget))
        menu.add_separator()
        menu.add_command(label="Выделить всё", command=lambda: self.perform_select_all(event.widget))
        menu.tk_popup(event.x_root, event.y_root)

    def setup_text_bindings(self, widget):
        """Добавляет поддержку Ctrl+C, Ctrl+V, Ctrl+X, Ctrl+A."""
        # Стандартные (латиница)
        widget.bind("<Control-a>", self._on_select_all)
        widget.bind("<Control-c>", self._on_copy)
        widget.bind("<Control-v>", self._on_paste)
        widget.bind("<Control-x>", self._on_cut)
        # Русская раскладка (чтобы работало без переключения языка)
        widget.bind("<Control-Cyrillic_ef>", self._on_select_all) # A -> Ф
        widget.bind("<Control-Cyrillic_es>", self._on_copy)       # C -> С
        widget.bind("<Control-Cyrillic_em>", self._on_paste)      # V -> М
        widget.bind("<Control-Cyrillic_che>", self._on_cut)       # X -> Ч

    # --- Обработчики событий (вызывают логику) ---
    def _on_select_all(self, event):
        self.perform_select_all(event.widget)
        return "break"

    def _on_copy(self, event):
        self.perform_copy(event.widget)
        return "break"

    def _on_paste(self, event):
        self.perform_paste(event.widget)
        return "break"

    def _on_cut(self, event):
        self.perform_cut(event.widget)
        return "break"

    # --- Логика операций (работает и для Text, и для Entry) ---
    def perform_select_all(self, widget):
        if isinstance(widget, tk.Text):
            widget.tag_add("sel", "1.0", "end")
        elif isinstance(widget, (tk.Entry, ttk.Entry)):
            widget.selection_range(0, tk.END)

    def perform_copy(self, widget):
        try:
            if isinstance(widget, tk.Text):
                text = widget.get("sel.first", "sel.last")
            elif isinstance(widget, (tk.Entry, ttk.Entry)):
                text = widget.selection_get()
            self.clipboard_clear()
            self.clipboard_append(text)
        except tk.TclError: pass

    def perform_paste(self, widget):
        try:
            text = self.clipboard_get()
            widget.insert("insert", text)
        except tk.TclError: pass

    def perform_cut(self, widget):
        try:
            if isinstance(widget, tk.Text):
                text = widget.get("sel.first", "sel.last")
                widget.delete("sel.first", "sel.last")
            elif isinstance(widget, (tk.Entry, ttk.Entry)):
                text = widget.selection_get()
                widget.delete("sel.first", "sel.last")
            self.clipboard_clear()
            self.clipboard_append(text)
        except tk.TclError: pass
