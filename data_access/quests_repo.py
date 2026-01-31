# data_access/quests_repo.py
from core.db import Database
from core.logger import get_logger
from core.models import Quest, Objective
from typing import List, Dict

logger = get_logger(__name__)

def get_quests_by_zone(db: Database, zone_id: int) -> List[Quest]:
    query = """
    SELECT
        entry,
        Title AS title,
        MinLevel AS min_level,
        QuestLevel AS quest_level,
        ZoneOrSort AS zone_or_sort,
        RequiredRaces AS required_races,
        PrevQuestId AS prev_quest_id,
        NextQuestId AS next_quest_id,
        NextQuestInChain AS next_quest_in_chain,
        SpecialFlags AS special_flags
    FROM quest_template
    WHERE ZoneOrSort = %s
      AND SpecialFlags = 0
      AND SuggestedPlayers = 0
    ORDER BY MinLevel, entry
    """
    results = db.execute(query, (zone_id,))
    quests = [Quest(**row) for row in results]
    logger.info(f"Загружено {len(quests)} квестов для зоны {zone_id}")
    return quests

def get_objectives_for_quest(db: Database, quest_id: int) -> List[Objective]:
    """
    Извлекает цели квеста из quest_template. 
    Логика классификации перенесена из SQL в Python для корректной обработки отрицательных ID (GameObjects).
    """
    query = """
    SELECT
        entry AS quest_id,
        ReqCreatureOrGOId1, ReqCreatureOrGOId2, ReqCreatureOrGOId3, ReqCreatureOrGOId4,
        ReqItemId1, ReqItemId2, ReqItemId3, ReqItemId4,
        ReqCreatureOrGOCount1, ReqCreatureOrGOCount2, ReqCreatureOrGOCount3, ReqCreatureOrGOCount4,
        ReqItemCount1, ReqItemCount2, ReqItemCount3, ReqItemCount4
    FROM quest_template
    WHERE entry = %s
    """
    results = db.execute(query, (quest_id,))
    if not results:
        return []
    
    row = results[0]
    objs = []
    
    for i in range(1, 5):
        target_id = row.get(f'ReqCreatureOrGOId{i}', 0) or 0
        item_id = row.get(f'ReqItemId{i}', 0) or 0
        target_count = row.get(f'ReqCreatureOrGOCount{i}', 0) or 0
        item_count = row.get(f'ReqItemCount{i}', 0) or 0
        
        # Классификация цели
        if item_id > 0:
            # Тип: Loot
            objs.append(Objective(
                quest_id=quest_id,
                slot=i,
                type='loot',
                target_id=abs(target_id) if target_id != 0 else None,
                item_id=item_id,
                count=item_count
            ))
        elif target_id > 0:
            # Тип: Kill (Существо)
            objs.append(Objective(
                quest_id=quest_id,
                slot=i,
                type='kill',
                target_id=target_id,
                item_id=None,
                count=target_count
            ))
        elif target_id < 0:
            # Тип: Gather (Объект)
            objs.append(Objective(
                quest_id=quest_id,
                slot=i,
                type='gather',
                target_id=abs(target_id),
                item_id=None,
                count=target_count
            ))
            
    logger.debug(f"Для квеста {quest_id} найдено {len(objs)} целей")
    return objs

def get_quest_details(db: Database, quest_id: int) -> Dict[str, str]:
    """Извлекает Details и Objectives текст для отображения пользователю."""
    query = "SELECT Details, Objectives FROM quest_template WHERE entry = %s"
    results = db.execute(query, (quest_id,))
    if results:
        return {
            'details': results[0].get('Details', 'Нет описания'),
            'objectives': results[0].get('Objectives', 'Нет целей')
        }
    return {'details': 'Квест не найден', 'objectives': ''}
