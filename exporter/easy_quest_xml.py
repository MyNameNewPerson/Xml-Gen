# exporter/easy_quest_xml.py
import xml.etree.ElementTree as ET
from xml.dom import minidom
import math
from typing import List, Dict, Any

from core.db import Database
from core.logger import get_logger
from core.models import Quest, Objective
from logic.session_manager import ZoneSession
from data_access.spawns_repo import get_creature_spawns, get_gameobject_spawns
from data_access.npc_repo import (
    get_quest_starter_npc, get_quest_ender_npc, 
    get_quest_starter_go, get_quest_ender_go
)
from logic.clustering import cluster_spawns
from logic.loot_resolver import resolve_loot_to_kills, resolve_loot_to_gos
from logic.npc_registry import NPCRegistry
from core.coord_converter import get_zone_dimensions, is_coords_in_bounds

logger = get_logger(__name__)

def pretty_print_xml(element: ET.Element) -> str:
    rough_string = ET.tostring(element, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent=" ")

def clean_name(text: str) -> str:
    if not text: return "Unknown"
    return "".join(c for c in text if c.isalnum())

def get_distance(x1, y1, x2, y2):
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def is_gameobject(db: Database, entry: int) -> bool:
    if not entry: return False
    query = "SELECT entry FROM gameobject_template WHERE entry = %s"
    results = db.execute(query, (entry,))
    return bool(results)

def determine_quest_type(db: Database, quest: Quest, objectives: List[Objective]) -> str:
    flags = getattr(quest, 'special_flags', 0)
    if flags & 2: return "Exploration"
    if not objectives: return "None"
    
    obj_types = set(o.type for o in objectives)
    if "kill" in obj_types or "loot" in obj_types: return "KillAndLoot"
    if "gather" in obj_types: return "Gatherer"
    return "None"

def get_targets_for_objectives(db: Database, objs: List[Objective]):
    mobs, gos = [], []
    for obj in objs:
        if obj.type == 'kill' and obj.target_id: mobs.append(obj.target_id)
        elif obj.type == 'gather' and obj.target_id: gos.append(obj.target_id)
        elif obj.type == 'loot':
            if obj.target_id and obj.target_id > 0:
                if is_gameobject(db, obj.target_id): gos.append(obj.target_id)
                else: mobs.append(obj.target_id)
            elif obj.item_id:
                gos.extend(resolve_loot_to_gos(db, obj.item_id))
                mobs.extend(resolve_loot_to_kills(db, obj.item_id))
    return list(set(mobs)), list(set(gos))

def get_hotspots(db: Database, quest_id: int, mobs: List[int], gos: List[int]):
    raw_spawns = []
    for tid in gos: raw_spawns.extend(get_gameobject_spawns(db, tid))
    for tid in mobs: raw_spawns.extend(get_creature_spawns(db, tid))
    
    starter = get_quest_starter_npc(db, quest_id) or get_quest_starter_go(db, quest_id)
    if starter and raw_spawns:
        sx, sy, smap = float(starter['x']), float(starter['y']), int(starter['map'])
        valid = [s for s in raw_spawns if int(s['map']) == smap and get_distance(sx, sy, s['position_x'], s['position_y']) <= 3000]
        return cluster_spawns(valid if valid else raw_spawns)
    return cluster_spawns(raw_spawns) if raw_spawns else []

def add_quest_to_xml(easy_quests_node, quest, objs, quest_type, db, xsi_url):
    name = f"{clean_name(quest.title)}{quest.entry}"
    eq = ET.SubElement(easy_quests_node, "EasyQuest")
    ET.SubElement(eq, "Name").text = name
    ET.SubElement(ET.SubElement(eq, "QuestId"), "int").text = str(quest.entry)
    ET.SubElement(eq, "QuestType").text = quest_type
    
    q_class_type = f"{quest_type if quest_type != 'None' else 'KillAndLoot'}EasyQuestClass"
    qc = ET.SubElement(eq, "QuestClass", attrib={f"{{{xsi_url}}}type": q_class_type})
    
    mobs, gos = get_targets_for_objectives(db, objs)
    if mobs:
        et = ET.SubElement(qc, "EntryTarget")
        for m in mobs: ET.SubElement(et, "int").text = str(m)
    if gos:
        eo = ET.SubElement(qc, "EntryIdObjects")
        for g in gos: ET.SubElement(eo, "int").text = str(g)
    
    hs_node = ET.SubElement(qc, "HotSpots")
    hotspots = get_hotspots(db, quest.entry, mobs, gos)
    for h in hotspots:
        # Формат координат: точка вместо запятой
        x_str = f"{h.center_x:.4f}".replace(',', '.')
        y_str = f"{h.center_y:.4f}".replace(',', '.')
        z_str = f"{h.center_z:.4f}".replace(',', '.')
        ET.SubElement(hs_node, "Vector3", X=x_str, Y=y_str, Z=z_str)
    
    ET.SubElement(qc, "IsHotspots").text = "true" if hotspots else "false"
    ET.SubElement(qc, "IsGrinderNotQuest").text = "false"
    
    for i in range(1, 6):
        count = next((o.count for o in objs if o.slot == i), 0)
        ET.SubElement(eq, f"ObjectiveCount{i}").text = str(count)
        ET.SubElement(eq, f"AutoDetectObjectiveCount{i}").text = "true" if count > 0 else "false"
    
    ET.SubElement(eq, "MinLevel").text = "0"
    ET.SubElement(eq, "MaxLevel").text = "100"

def generate_csharp_script(sessions: List[ZoneSession], db: Database) -> str:
    """
    Генерирует C# скрипт для WRobot (TBC 2.4.3), который предотвращает овер-фарм.
    """
    from data_access.quests_repo import get_quests_by_zone, get_objectives_for_quest
    
    lines = []
    lines.append("using System;")
    lines.append("using System.Collections.Generic;")
    lines.append("using System.Threading;")
    lines.append("using wManager.Wow.Helpers;")
    lines.append("using wManager.Wow.ObjectManager;")
    lines.append("using robotManager.Helpful;")
    lines.append("")
    lines.append("public class MyCustomScript")
    lines.append("{")
    lines.append("    public static Dictionary<int, Dictionary<int, int>> QuestMobMap = new Dictionary<int, Dictionary<int, int>>();")
    lines.append("    private static bool _running = true;")
    lines.append("")
    lines.append("    static MyCustomScript()")
    lines.append("    {")
    lines.append("        try")
    lines.append("        {")
    
    processed_quests = set()
    for session in sessions:
        if not session.zone_id: continue
        zone_quests = get_quests_by_zone(db, session.zone_id)
        selected = [q for q in zone_quests if q.entry in session.selected_quest_ids]
        
        for q in selected:
            if q.entry in processed_quests: continue
            processed_quests.add(q.entry)
            
            objs = get_objectives_for_quest(db, q.entry)
            for obj in objs:
                if obj.type == 'kill' and obj.target_id:
                    lines.append(f"            InitQuest({q.entry}, {obj.target_id}, {obj.slot});")

    lines.append("            new Thread(Loop).Start();")
    lines.append("        }")
    lines.append("        catch (Exception e)")
    lines.append("        {")
    lines.append('            Logging.WriteError("SmartKill Script Init Error: " + e.ToString());')
    lines.append("        }")
    lines.append("    }")
    lines.append("")
    lines.append("    public static void InitQuest(int questId, int mobId, int objIndex)")
    lines.append("    {")
    lines.append("        if (!QuestMobMap.ContainsKey(questId))")
    lines.append("        {")
    lines.append("            QuestMobMap.Add(questId, new Dictionary<int, int>());")
    lines.append("        }")
    lines.append("        if (!QuestMobMap[questId].ContainsKey(mobId))")
    lines.append("        {")
    lines.append("            QuestMobMap[questId].Add(mobId, objIndex);")
    lines.append("        }")
    lines.append("    }")
    lines.append("")
    lines.append("    public static void Loop()")
    lines.append("    {")
    lines.append("        while (_running && wManager.wManagerSetting.CurrentSetting.IsStarted)")
    lines.append("        {")
    lines.append("            try")
    lines.append("            {")
    lines.append("                if (Conditions.InGameAndConnectedAndAliveAndProductStartedNotInPause)")
    lines.append("                {")
    lines.append("                    long targetGuid = ObjectManager.Me.Target;")
    lines.append("                    if (targetGuid > 0)")
    lines.append("                    {")
    lines.append("                        WoWUnit target = ObjectManager.GetObjectByGuid(targetGuid) as WoWUnit;")
    lines.append("                        if (target != null && target.IsValid && target.IsAlive)")
    lines.append("                        {")
    lines.append("                            int mobId = target.Entry;")
    lines.append("                            foreach (int qId in QuestMobMap.Keys)")
    lines.append("                            {")
    lines.append("                                if (QuestMobMap[qId].ContainsKey(mobId))")
    lines.append("                                {")
    lines.append("                                    int logIndex = Quest.GetQuestLogIndexByID(qId);")
    lines.append("                                    if (logIndex > 0)")
    lines.append("                                    {")
    lines.append("                                        int objIdx = QuestMobMap[qId][mobId];")
    lines.append('                                        string res = Lua.LuaDoString("return tostring(select(3, GetQuestLogLeaderBoard(" + objIdx + ", " + logIndex + ")))");')
    lines.append('                                        if (res == "true" || res == "1")')
    lines.append("                                        {")
    lines.append("                                            wManager.wManagerSetting.AddBlackList(targetGuid, 5000, true);")
    lines.append("                                            wManager.Wow.Helpers.Fight.StopFight();")
    lines.append("                                            wManager.Wow.Helpers.MovementManager.StopMove();")
    lines.append('                                            Logging.Write("[SmartKill] Blacklisted " + target.Name + " (Objective Complete).");')
    lines.append("                                        }")
    lines.append("                                        break;")
    lines.append("                                    }")
    lines.append("                                }")
    lines.append("                            }")
    lines.append("                        }")
    lines.append("                    }")
    lines.append("                }")
    lines.append("            }")
    lines.append("            catch (Exception e) { Logging.WriteError(\"SmartKill Loop: \" + e.ToString()); }")
    lines.append("            Thread.Sleep(200);")
    lines.append("        }")
    lines.append("    }")
    lines.append("}")
    
    return "\n".join(lines)

def resolve_trainer_type(subname: str) -> str:
    """
    Определяет точный тип тренера для wRobot на основе SubName (подзаголовка NPC).
    wRobot требует точные типы: RogueTrainer, WarriorTrainer и т.д.
    Если тип не найден, возвращает 'None', чтобы избежать краша.
    """
    if not subname: 
        return "None"
    
    s = subname.lower()
    if "rogue" in s: return "RogueTrainer"
    if "warrior" in s: return "WarriorTrainer"
    if "paladin" in s: return "PaladinTrainer"
    if "hunter" in s: return "HunterTrainer"
    if "priest" in s: return "PriestTrainer"
    if "shaman" in s: return "ShamanTrainer"
    if "mage" in s: return "MageTrainer"
    if "warlock" in s: return "WarlockTrainer"
    if "druid" in s: return "DruidTrainer"
    if "demon" in s and "hunter" in s: return "DemonHunterTrainer" # На будущее
    if "death" in s and "knight" in s: return "DeathKnightTrainer" # WotLK
    
    # Можно добавить профессии, если wRobot их поддерживает в этом списке
    # Но для безопасности пока возвращаем None для всего остального
    return "None"

def fetch_npcs_spatially(db: Database, zone_id: int, map_id: int, flag_mask: int, type_name: str) -> List[Dict]:
    """
    Ищет NPC на карте по флагам и проверяет, попадают ли они в границы зоны.
    """
    query = f"""
    SELECT c.id, ct.Name, ct.SubName, c.position_x, c.position_y, c.position_z, ct.NpcFlags
    FROM creature c
    JOIN creature_template ct ON c.id = ct.entry
    WHERE c.map = %s AND (ct.NpcFlags & {flag_mask}) > 0
      AND ct.Name NOT LIKE '[%%]'
    """
    results = db.execute(query, (map_id,))
    valid = []
    for row in results:
        if is_coords_in_bounds(zone_id, float(row['position_x']), float(row['position_y'])):
            
            final_type = type_name
            
            # --- ЛОГИКА ОПРЕДЕЛЕНИЯ ТИПА ---
            if type_name == "Vendor":
                flags = row['NpcFlags']
                if (flags & 4096):
                    final_type = "Repair"
                elif (flags & 128):
                    final_type = "Vendor"
            
            elif type_name == "Trainer":
                # Используем новую функцию для определения класса тренера
                final_type = resolve_trainer_type(row['SubName'])
                if final_type == "None":
                    continue
            
            logger.info(f"Добавлен NPC: {row['Name']} ({final_type}) в зоне {zone_id}")
            
            valid.append({
                'Id': row['id'], 
                'Name': row['Name'], 
                'Type': final_type, 
                'X': row['position_x'], 
                'Y': row['position_y'], 
                'Z': row['position_z'], 
                'Map': map_id
            })
    return valid

def add_grind_to_xml(easy_quests_node, session: ZoneSession, xsi_url):
    gs = session.grind_settings
    if not gs.hotspots and not gs.mob_id: return
    
    name = f"Grind_{clean_name(session.zone_name)}_{gs.target_level}"
    eq = ET.SubElement(easy_quests_node, "EasyQuest")
    ET.SubElement(eq, "Name").text = name
    ET.SubElement(ET.SubElement(eq, "QuestId"), "int").text = "0"
    ET.SubElement(eq, "QuestType").text = "KillAndLoot"
    
    qc = ET.SubElement(eq, "QuestClass", attrib={f"{{{xsi_url}}}type": "KillAndLootEasyQuestClass"})
    
    et = ET.SubElement(qc, "EntryTarget")
    if gs.mob_id:
        ET.SubElement(et, "int").text = str(gs.mob_id)
    
    ET.SubElement(qc, "EntryIdObjects")
    
    hs_node = ET.SubElement(qc, "HotSpots")
    for h in gs.hotspots:
        # Формат координат: точка вместо запятой
        x_str = f"{h.x:.4f}".replace(',', '.')
        y_str = f"{h.y:.4f}".replace(',', '.')
        z_str = f"{h.z:.4f}".replace(',', '.')
        ET.SubElement(hs_node, "Vector3", X=x_str, Y=y_str, Z=z_str)
    
    ET.SubElement(qc, "IsHotspots").text = "true" if gs.hotspots else "false"
    ET.SubElement(qc, "IsGrinderNotQuest").text = "true"
    
    for i in range(1, 6):
        ET.SubElement(eq, f"ObjectiveCount{i}").text = "0"
        ET.SubElement(eq, f"AutoDetectObjectiveCount{i}").text = "false"
    
    can_cond = ET.SubElement(eq, "CanCondition")
    can_cond.text = f"return ObjectManager.Me.Level >= {gs.min_level} && ObjectManager.Me.Level < {gs.target_level};"
    
    ET.SubElement(eq, "MinLevel").text = "0"
    ET.SubElement(eq, "MaxLevel").text = "100"

def get_continent_name_by_map_id(map_id: int) -> str:
    """
    Возвращает имя континента (Kalimdor, Azeroth и т.д.) по ID карты.
    TBC 2.4.3: 0=Azeroth, 1=Kalimdor, 530=Outland, 571=Northrend.
    """
    if map_id == 0: return "Azeroth"
    if map_id == 1: return "Kalimdor"
    if map_id == 530: return "Outland"
    if map_id == 571: return "Northrend"
    return "None"

def generate_easy_quest_xml(sessions: List[ZoneSession], filename: str):
    db = Database()
    registry = NPCRegistry()
    xsi_url = "http://www.w3.org/2001/XMLSchema-instance"
    xsd_url = "http://www.w3.org/2001/XMLSchema"
    ET.register_namespace('xsi', xsi_url)
    ET.register_namespace('xsd', xsd_url)
    
    root = ET.Element("EasyQuestProfile")
    quests_sorted = ET.SubElement(root, "QuestsSorted")
    npc_quest_section = ET.SubElement(root, "NpcQuest")
    npc_section = ET.SubElement(root, "Npc")
    easy_quests_node = ET.SubElement(root, "EasyQuests")
    
    from data_access.quests_repo import get_quests_by_zone, get_objectives_for_quest
    
    added_npc_quests = {} 

    for session in sessions:
        if not session.zone_id: continue
        
        # 1. Загрузка квестов
        zone_quests = get_quests_by_zone(db, session.zone_id)
        selected = [q for q in zone_quests if q.entry in session.selected_quest_ids]
        
        # 2. Обработка квестов
        for q in selected:
            name = f"{clean_name(q.title)}{q.entry}"
            objs = get_objectives_for_quest(db, q.entry)
            q_type = determine_quest_type(db, q, objs)
            
            ET.SubElement(quests_sorted, "QuestsSorted", Action="PickUp", NameClass=name)
            if q_type != "None": ET.SubElement(quests_sorted, "QuestsSorted", Action="Pulse", NameClass=name)
            ET.SubElement(quests_sorted, "QuestsSorted", Action="TurnIn", NameClass=name)
            
            add_quest_to_xml(easy_quests_node, q, objs, q_type, db, xsi_url)
            
            npc_targets = [
                (get_quest_starter_npc(db, q.entry), False, "PickUp"),
                (get_quest_starter_go(db, q.entry), True, "PickUp"),
                (get_quest_ender_npc(db, q.entry), False, "TurnIn"),
                (get_quest_ender_go(db, q.entry), True, "TurnIn")
            ]
            
            for target, is_go, action in npc_targets:
                if not target: continue
                key = (target['entity_id'], is_go)
                if key not in added_npc_quests:
                    nq = ET.SubElement(npc_quest_section, "NPCQuest", Id=str(target['entity_id']), Name=target['entity_name'], GameObject="true" if is_go else "false")
                    ET.SubElement(nq, "PickUpQuests")
                    ET.SubElement(nq, "TurnInQuests")
                    
                    x_str = f"{float(target['x']):.4f}".replace(',', '.')
                    y_str = f"{float(target['y']):.4f}".replace(',', '.')
                    z_str = f"{float(target['z']):.4f}".replace(',', '.')
                    
                    ET.SubElement(nq, "Position", X=x_str, Y=y_str, Z=z_str)
                    added_npc_quests[key] = nq
                
                nq_elem = added_npc_quests[key]
                section = nq_elem.find(f"{action}Quests")
                if section is not None:
                    if not any(child.text == str(q.entry) for child in section.findall("int")):
                        ET.SubElement(section, "int").text = str(q.entry)

        # 3. Гриндинг
        if session.grind_settings.mob_id or session.grind_settings.hotspots:
            grind_name = f"Grind_{clean_name(session.zone_name)}_{session.grind_settings.target_level}"
            ET.SubElement(quests_sorted, "QuestsSorted", Action="Pulse", NameClass=grind_name)
            add_grind_to_xml(easy_quests_node, session, xsi_url)

        # 4. Точки пути
        for rt in session.run_to_points:
            coords_str = f"{rt.x}, {rt.y}, {rt.z}"
            ET.SubElement(quests_sorted, "QuestsSorted", Action="RunTo", NameClass=coords_str)

        # 5. Логистика (Вендоры, Тренеры и т.д.)
        dims = get_zone_dimensions(session.zone_id)
        map_id = dims['map'] if dims else 0
        if selected:
            s_npc = get_quest_starter_npc(db, selected[0].entry)
            if s_npc: map_id = s_npc['map']

        if session.include_trainers:
            # ТЕПЕРЬ здесь будет вызываться логика определения класса (Rogue, Warrior и т.д.)
            for t in fetch_npcs_spatially(db, session.zone_id, map_id, 16, "Trainer"):
                registry.add_npc(t)
        
        if session.include_flight_masters:
            for f in fetch_npcs_spatially(db, session.zone_id, map_id, 8192, "FlightMaster"):
                registry.add_npc(f)

        if session.include_vendors:
            for v in fetch_npcs_spatially(db, session.zone_id, map_id, 128 | 4096, "Vendor"):
                registry.add_npc(v)

    # 6. Финальная выгрузка
    
    # Список ВСЕХ валидных типов. Добавил сюда классовых тренеров.
    valid_wrobot_types = {
        "Vendor", "Repair", "Auctioneer", "Mailbox", "SpiritHealer", "None",
        "RogueTrainer", "WarriorTrainer", "PaladinTrainer", "HunterTrainer",
        "PriestTrainer", "ShamanTrainer", "MageTrainer", "WarlockTrainer", 
        "DruidTrainer", "DeathKnightTrainer"
    }

    for n in registry.get_all():
        npc_node = ET.SubElement(npc_section, "Npc")
        
        pos_x = f"{float(n['X']):.4f}".replace(',', '.')
        pos_y = f"{float(n['Y']):.4f}".replace(',', '.')
        pos_z = f"{float(n['Z']):.4f}".replace(',', '.')
        
        # Атрибут Type="Flying" только у вендоров и ремонтников (как в примере)
        raw_type = n.get('Type', 'None')
        position_attribs = {"X": pos_x, "Y": pos_y, "Z": pos_z}
        if raw_type in ["Vendor", "Repair"]:
             position_attribs["Type"] = "Flying"
             
        ET.SubElement(npc_node, "Position", **position_attribs)
        
        ET.SubElement(npc_node, "Entry").text = str(n['Id'])
        ET.SubElement(npc_node, "Name").text = n['Name'] if n['Name'] else "Unknown Entity"
        ET.SubElement(npc_node, "GossipOption").text = "-1"
        ET.SubElement(npc_node, "Active").text = "true"
        ET.SubElement(npc_node, "Faction").text = "Neutral"
        
        # Проверяем, есть ли наш тип в списке разрешенных.
        # Если это RogueTrainer — он пройдет. Если просто Trainer (не определился класс) — станет None.
        final_xml_type = raw_type if raw_type in valid_wrobot_types else "None"
        ET.SubElement(npc_node, "Type").text = final_xml_type
        
        continent_name = get_continent_name_by_map_id(int(n.get('Map', 0)))
        ET.SubElement(npc_node, "ContinentId").text = continent_name

    xml_str = pretty_print_xml(root).replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="utf-16"?>')
    with open(filename, "w", encoding="utf-16") as f:
        f.write(xml_str)
    db.close()