# data_access/zones_repo.py
from core.db import Database
from core.logger import get_logger
from core.models import Zone
from typing import List

logger = get_logger(__name__)

# Hardcoded zone names based on common WoW TBC zones (from DBC or known IDs)
ZONE_NAMES = {
    # ---------- Eastern Kingdoms ----------
    1: 'Dun Morogh',
    3: 'Badlands',
    4: 'Blasted Lands',
    8: 'Swamp of Sorrows',
    10: 'Duskwood',
    11: 'Wetlands',
    12: 'Elwynn Forest',
    14: 'Durotar',
    15: 'Dustwallow Marsh',
    16: 'Azshara',
    17: 'The Barrens',
    19: 'Zul\'Gurub',
    28: 'Western Plaguelands',
    33: 'Stranglethorn Vale',
    36: 'Alterac Mountains',
    38: 'Loch Modan',
    40: 'Westfall',
    41: 'Deadwind Pass',
    44: 'Redridge Mountains',
    45: 'Arathi Highlands',
    47: 'The Hinterlands',
    51: 'Searing Gorge',
    85: 'Tirisfal Glades',
    130: 'Silverpine Forest',
    139: 'Eastern Plaguelands',
    151: 'Designer Island',
    267: 'Hillsbrad Foothills',
    335: 'Dustwallow Bay',
    357: 'Feralas',
    361: 'Felwood',
    400: 'Thousand Needles',
    405: 'Desolace',
    406: 'Stonetalon Mountains',
    440: 'Tanaris',
    490: "Un'Goro Crater",
    618: 'Winterspring',

    # ---------- Kalimdor ----------
    141: 'Teldrassil',
    148: 'Darkshore',
    188: 'Shadowglen',              # стартовая деревня Night Elf
    215: 'Mulgore',
    220: 'Red Cloud Mesa',
    331: 'Ashenvale',
    357: 'Feralas',
    361: 'Felwood',
    405: 'Desolace',
    406: 'Stonetalon Mountains',
    493: 'Moonglade',
    616: 'Hyjal',

    # ---------- TBC: Outland ----------
    3483: 'Hellfire Peninsula',
    3518: 'Nagrand',
    3519: 'Terokkar Forest',
    3520: 'Shadowmoon Valley',
    3521: 'Zangarmarsh',
    3522: "Blade\'s Edge Mountains",
    3523: 'Netherstorm',

    # ---------- TBC: Blood Elf / Draenei старт ----------
    3430: 'Eversong Woods',
    3433: 'Ghostlands',
    3524: 'Azuremyst Isle',
    3525: 'Bloodmyst Isle',

    # ---------- Прочие реально встречающиеся в quest_template ----------
    1377: 'Silithus',
    1497: 'Undercity',
    1519: 'Stormwind City',
    1537: 'Ironforge',
    1637: 'Orgrimmar',
    1638: 'Thunder Bluff',
    1657: 'Darnassus',
    2597: 'Alterac Valley',
    3277: 'Warsong Gulch',
    3358: 'Arathi Basin',
}


def get_all_zone_ids(db: Database) -> List[int]:
    query = "SELECT DISTINCT ZoneOrSort FROM quest_template WHERE ZoneOrSort > 0 ORDER BY ZoneOrSort"
    results = db.execute(query)
    return [row['ZoneOrSort'] for row in results if row['ZoneOrSort'] in ZONE_NAMES]

def get_zone_name(zone_id: int) -> str:
    return ZONE_NAMES.get(zone_id, f"Unknown Zone {zone_id}")

def search_zones_by_name(partial_name: str) -> List[Zone]:
    matching = [Zone(id=k, name=v) for k, v in ZONE_NAMES.items() if partial_name.lower() in v.lower()]
    logger.info(f"Found {len(matching)} zones matching '{partial_name}'")
    return matching