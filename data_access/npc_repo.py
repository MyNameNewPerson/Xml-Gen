# data_access/npc_repo.py
from core.db import Database
from core.logger import get_logger
from typing import Optional, Dict, Any, List
from core.coord_converter import is_coords_in_bounds, get_zone_dimensions

logger = get_logger(__name__)

def get_quest_starter_type(db: Database, quest_id: int) -> str:
    # 1. Проверяем NPC
    npc_query = "SELECT id FROM creature_questrelation WHERE quest = %s LIMIT 1"
    if db.execute(npc_query, (quest_id,)): return 'npc'
    # 2. Проверяем Объекты
    go_query = "SELECT id FROM gameobject_questrelation WHERE quest = %s LIMIT 1"
    if db.execute(go_query, (quest_id,)): return 'object'
    # 3. Проверяем Предметы
    item_query = "SELECT entry FROM item_template WHERE startquest = %s LIMIT 1"
    if db.execute(item_query, (quest_id,)): return 'item'
    return 'unknown'

def get_quest_starter_npc(db: Database, quest_id: int) -> Optional[Dict[str, Any]]:
    query = """
    SELECT ct.entry AS entity_id, ct.Name AS entity_name, c.position_x AS x, c.position_y AS y, c.position_z AS z, c.map
    FROM creature_questrelation cq
    JOIN creature c ON cq.id = c.id
    JOIN creature_template ct ON cq.id = ct.entry
    WHERE cq.quest = %s LIMIT 1
    """
    results = db.execute(query, (quest_id,))
    if results:
        res = results[0]
        res['x'], res['y'], res['z'] = float(res['x']), float(res['y']), float(res['z'])
        return res
    return None

def get_quest_ender_npc(db: Database, quest_id: int) -> Optional[Dict[str, Any]]:
    query = """
    SELECT ct.entry AS entity_id, ct.Name AS entity_name, c.position_x AS x, c.position_y AS y, c.position_z AS z, c.map
    FROM creature_involvedrelation cq
    JOIN creature c ON cq.id = c.id
    JOIN creature_template ct ON cq.id = ct.entry
    WHERE cq.quest = %s LIMIT 1
    """
    results = db.execute(query, (quest_id,))
    if results:
        res = results[0]
        res['x'], res['y'], res['z'] = float(res['x']), float(res['y']), float(res['z'])
        return res
    return None

def get_quest_starter_go(db: Database, quest_id: int) -> Optional[Dict[str, Any]]:
    query = """
    SELECT gt.entry AS entity_id, gt.name AS entity_name, g.position_x AS x, g.position_y AS y, g.position_z AS z, g.map
    FROM gameobject_questrelation gq
    JOIN gameobject g ON gq.id = g.id
    JOIN gameobject_template gt ON gq.id = gt.entry
    WHERE gq.quest = %s LIMIT 1
    """
    results = db.execute(query, (quest_id,))
    if results:
        res = results[0]
        res['x'], res['y'], res['z'] = float(res['x']), float(res['y']), float(res['z'])
        return res
    return None

def get_quest_ender_go(db: Database, quest_id: int) -> Optional[Dict[str, Any]]:
    query = """
    SELECT gt.entry AS entity_id, gt.name AS entity_name, g.position_x AS x, g.position_y AS y, g.position_z AS z, g.map
    FROM gameobject_involvedrelation gq
    JOIN gameobject g ON gq.id = g.id
    JOIN gameobject_template gt ON gq.id = gt.entry
    WHERE gq.quest = %s LIMIT 1
    """
    results = db.execute(query, (quest_id,))
    if results:
        res = results[0]
        res['x'], res['y'], res['z'] = float(res['x']), float(res['y']), float(res['z'])
        return res
    return None

def get_zone_vendors(db: Database, zone_id: int) -> List[Dict[str, Any]]:
    dims = get_zone_dimensions(zone_id)
    if not dims: return []
    query = """
    SELECT c.id as entry, ct.Name as name, ct.NpcFlags as npcflag, c.position_x, c.position_y, c.position_z
    FROM creature c JOIN creature_template ct ON c.id = ct.entry
    WHERE c.map = %s AND (ct.NpcFlags & 128 = 128 OR ct.NpcFlags & 4096 = 4096)
    """
    results = db.execute(query, (dims['map'],))
    vendors = []
    seen = set()
    for row in results:
        px, py, pz = float(row['position_x']), float(row['position_y']), float(row['position_z'])
        if is_coords_in_bounds(zone_id, px, py):
            if row['entry'] not in seen:
                flags = row['npcflag']
                t = "VendorRepair" if (flags&128 and flags&4096) else ("Vendor" if flags&128 else "Repair")
                vendors.append({'Id': row['entry'], 'Name': row['name'], 'Type': t, 'X': px, 'Y': py, 'Z': pz})
                seen.add(row['entry'])
    return vendors

def get_continent_flight_masters(db: Database, map_id: int) -> List[Dict[str, Any]]:
    query = """
    SELECT c.id as entry, ct.Name as name, c.position_x, c.position_y, c.position_z
    FROM creature c JOIN creature_template ct ON c.id = ct.entry
    WHERE c.map = %s AND (ct.NpcFlags & 8192 = 8192)
    """
    results = db.execute(query, (map_id,))
    fms = []
    seen = set()
    for row in results:
        if row['entry'] not in seen:
            fms.append({'Id': row['entry'], 'Name': row['name'], 'Type': "FlightMaster", 'X': float(row['position_x']), 'Y': float(row['position_y']), 'Z': float(row['position_z'])})
            seen.add(row['entry'])
    return fms

def get_class_trainers(db: Database, map_id: int) -> List[Dict[str, Any]]:
    """Находит учителей классов на континенте. NPC Flag 16 (0x10) = Trainer."""
    query = """
    SELECT c.id as entry, ct.Name as name, ct.SubName as subname, c.position_x, c.position_y, c.position_z
    FROM creature c JOIN creature_template ct ON c.id = ct.entry
    WHERE c.map = %s AND (ct.NpcFlags & 16 = 16)
    """
    results = db.execute(query, (map_id,))
    trainers = []
    seen = set()
    for row in results:
        if row['entry'] not in seen:
            trainers.append({
                'Id': row['entry'], 'Name': row['name'], 'SubName': row['subname'],
                'Type': "Trainer", 'X': float(row['position_x']), 'Y': float(row['position_y']), 'Z': float(row['position_z'])
            })
            seen.add(row['entry'])
    return trainers
