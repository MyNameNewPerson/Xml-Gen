# core/lua_loader.py
import re
import os
from core.logger import get_logger

logger = get_logger(__name__)

# Кэш для хранения загруженных данных
_QUESTIE_CACHE = {
    'npc': None,
    'object': None
}

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
QUESTIE_PATH = os.path.join(project_root, 'resources', 'questie')

# Индексы данных (Index 6 для NPC, Index 3 для Objects)
NPC_SPAWNS_INDEX = 6  
OBJ_SPAWNS_INDEX = 3  

def smart_split_lua_row(row_content: str) -> list:
    """Разбивает строку элементов, корректно обрабатывая запятые внутри структур."""
    elements = []
    buffer = ""
    brace_level = 0
    in_quote = False
    quote_char = ''
    
    for char in row_content:
        if in_quote:
            buffer += char
            if char == quote_char: in_quote = False
        else:
            if char == '{':
                brace_level += 1
                buffer += char
            elif char == '}':
                brace_level -= 1
                buffer += char
            elif char == '"' or char == "'":
                in_quote = True
                quote_char = char
                buffer += char
            elif char == ',' and brace_level == 0:
                elements.append(buffer.strip())
                buffer = ""
            else:
                buffer += char
    
    if buffer: elements.append(buffer.strip())
    return elements

def parse_spawns_table(content: str) -> list:
    """
    Парсит структуру спавнов.
    Пример: {[141]={{57.81,41.65},},}
    """
    if not content or content == 'nil': return []
    result = []
    
    try:
        # Убираем внешние скобки
        content = content.strip()
        if content.startswith('{') and content.endswith('}'):
            content = content[1:-1]

        # Используем Regex для поиска зон и координат внутри них
        # Ищем паттерн: [ID] = { ... }
        iterator = re.finditer(r'\[(\d+)\]\s*=\s*\{([^}]+)\}', content)
        for match in iterator:
            zone_id = int(match.group(1))
            coords_str = match.group(2)
            
            # Ищем пары координат: {57.81, 41.65}
            pairs = re.findall(r'\{([0-9\.]+),([0-9\.]+)\}', coords_str)
            for x, y in pairs:
                result.append({'zone': zone_id, 'x': float(x), 'y': float(y)})

    except Exception:
        pass
    return result

def load_questie_data(db_type: str) -> dict:
    global _QUESTIE_CACHE
    if _QUESTIE_CACHE[db_type] is not None: return _QUESTIE_CACHE[db_type]

    filename = 'tbcNpcDB.lua' if db_type == 'npc' else 'tbcObjectDB.lua'
    target_index = NPC_SPAWNS_INDEX if db_type == 'npc' else OBJ_SPAWNS_INDEX
    filepath = os.path.join(QUESTIE_PATH, filename)

    if not os.path.exists(filepath):
        logger.warning(f"Файл не найден: {filepath}")
        _QUESTIE_CACHE[db_type] = {}
        return {}

    logger.info(f"Загрузка {filename} (Robust Parser)...")
    data = {}
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # --- ГЛАВНЫЙ ЦИКЛ ПАРСИНГА ---
            # Ищем [ID] = {
            iterator = re.finditer(r'\[(\d+)\]\s*=\s*\{', content)
            
            for match in iterator:
                entry_id = int(match.group(1))
                start_pos = match.end()
                
                # Считаем баланс скобок, чтобы найти конец записи
                current_pos = start_pos
                balance = 1 # Мы уже прошли первую '{'
                
                while balance > 0 and current_pos < len(content):
                    char = content[current_pos]
                    if char == '{': balance += 1
                    elif char == '}': balance -= 1
                    current_pos += 1
                
                # Извлекаем всё содержимое записи NPC
                row_content = content[start_pos : current_pos-1]
                
                # Разбиваем на элементы
                elements = smart_split_lua_row(row_content)
                
                if len(elements) > target_index:
                    spawns_str = elements[target_index]
                    parsed_spawns = parse_spawns_table(spawns_str)
                    
                    if parsed_spawns: 
                        data[entry_id] = parsed_spawns

        logger.info(f"Успешно загружено {len(data)} записей из {filename}")

    except Exception as e:
        logger.error(f"Ошибка парсинга {filename}: {e}")
        return {}

    _QUESTIE_CACHE[db_type] = data
    return data
