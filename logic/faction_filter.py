# logic/faction_filter.py
from core.logger import get_logger
from core.models import Quest
from typing import List

logger = get_logger(__name__)

# Битовые маски рас для TBC (CMaNGOS / MaNGOS)
# Human(1) + Orc(2) + Dwarf(4) + NightElf(8) + Undead(16) + Tauren(32) + 
# Gnome(64) + Troll(128) + BloodElf(512) + Draenei(1024)

ALLIANCE_RACE_MASK = 1101  # Human + Dwarf + NightElf + Gnome + Draenei
HORDE_RACE_MASK    = 690   # Orc + Undead + Tauren + Troll + BloodElf

def get_faction_mask(faction: str) -> int:
    """
    Возвращает маску рас для указанной фракции.
    """
    f = faction.lower().strip()
    if f == 'alliance':
        return ALLIANCE_RACE_MASK
    if f == 'horde':
        return HORDE_RACE_MASK
    
    logger.warning(f"Неизвестная фракция '{faction}' -> фильтрация отключена (маска 0)")
    return 0

def filter_quests_by_faction(quests: List[Quest], mask: int) -> List[Quest]:
    """
    Фильтрует список квестов.
    Если RequiredRaces == 0, квест доступен всем.
    Иначе проверяется пересечение с маской фракции.
    """
    if mask == 0:
        return list(quests)

    filtered = []
    for q in quests:
        # Квест подходит, если требований к расе нет (0) 
        # или есть пересечение битов расы квеста и маски фракции
        if q.required_races == 0 or (q.required_races & mask) != 0:
            filtered.append(q)

    logger.info(f"Фильтрация по фракции: {len(quests)} -> {len(filtered)} квестов (маска {mask})")
    return filtered