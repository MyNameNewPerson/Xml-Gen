# data_access/spawns_repo.py
from core.db import Database
from core.logger import get_logger
from typing import List, Dict, Optional
from core.lua_loader import load_questie_data
from core.coord_converter import questie_to_world_coords

logger = get_logger(__name__)

def is_valid_spawn(spawn: Dict[str, float]) -> bool:
    if abs(spawn['position_x']) < 0.1 and abs(spawn['position_y']) < 0.1:
        return False
    return True

def get_spawns_from_questie(entry: int, db_type: str) -> List[Dict[str, float]]:
    questie_data = load_questie_data(db_type)
    entity_data = questie_data.get(entry)
    spawns = []
    if entity_data:
        for point in entity_data:
            world_coords = questie_to_world_coords(point['zone'], point['x'], point['y'])
            if world_coords:
                spawns.append(world_coords)
    return spawns

def get_creature_spawns(db: Database, entry: int, zone_id: Optional[int] = None) -> List[Dict[str, float]]:
    # 1. ЖЕСТКИЙ ПРИОРИТЕТ: Questie
    q_spawns = get_spawns_from_questie(entry, 'npc')
    if q_spawns:
        logger.info(f"NPC {entry}: Координаты взяты из Questie ({len(q_spawns)} точек).")
        return q_spawns

    # 2. ФОЛЛБЕК: База Данных
    logger.warning(f"NPC {entry}: Нет в Questie, ищем в БД...")
    query = "SELECT position_x, position_y, position_z, map FROM creature WHERE id = %s"
    results = db.execute(query, (entry,))
    
    valid_db_spawns = []
    for row in results:
        # !!! КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Конвертируем Decimal в float !!!
        row['position_x'] = float(row['position_x'])
        row['position_y'] = float(row['position_y'])
        row['position_z'] = float(row['position_z'])
        
        if is_valid_spawn(row):
            valid_db_spawns.append(row)
    
    if valid_db_spawns:
        return valid_db_spawns
    return []

def get_gameobject_spawns(db: Database, entry: int, zone_id: Optional[int] = None) -> List[Dict[str, float]]:
    # 1. ЖЕСТКИЙ ПРИОРИТЕТ: Questie
    q_spawns = get_spawns_from_questie(entry, 'object')
    if q_spawns:
        logger.info(f"GO {entry}: Координаты взяты из Questie ({len(q_spawns)} точек).")
        return q_spawns

    # 2. ФОЛЛБЕК: База Данных
    logger.warning(f"GO {entry}: Нет в Questie, ищем в БД...")
    query = "SELECT position_x, position_y, position_z, map FROM gameobject WHERE id = %s"
    results = db.execute(query, (entry,))
    
    valid_db_spawns = []
    for row in results:
        # !!! КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Конвертируем Decimal в float !!!
        row['position_x'] = float(row['position_x'])
        row['position_y'] = float(row['position_y'])
        row['position_z'] = float(row['position_z'])

        if is_valid_spawn(row):
            valid_db_spawns.append(row)
    
    if valid_db_spawns:
        return valid_db_spawns
    return []