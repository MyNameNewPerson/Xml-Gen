# logic/loot_resolver.py
from core.db import Database
from core.logger import get_logger
from typing import List

logger = get_logger(__name__)

def resolve_loot_to_kills(db: Database, item_id: int) -> List[int]:
    """
    Возвращает список creature_entry, которые дропают item_id.
    """
    query = """
    SELECT DISTINCT entry
    FROM creature_loot_template
    WHERE item = %s
    """
    results = db.execute(query, (item_id,))
    entries = [row['entry'] for row in results]
    
    # Можно добавить логирование для отладки
    if entries:
        logger.info(f"Для item {item_id} найдено {len(entries)} мобов-доноров")
        
    return entries

def resolve_loot_to_gos(db: Database, item_id: int) -> List[int]:
    """
    Возвращает список gameobject_entry, которые дропают item_id.
    """
    query = """
    SELECT DISTINCT entry
    FROM gameobject_loot_template
    WHERE item = %s
    """
    results = db.execute(query, (item_id,))
    entries = [row['entry'] for row in results]
    
    if entries:
        logger.info(f"Для item {item_id} найдено {len(entries)} GO-доноров")
        
    return entries