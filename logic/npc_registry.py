# logic/npc_registry.py
from typing import Set, Dict, Any, List

class NPCRegistry:
    """Глобальный реестр для дедупликации NPC при экспорте в XML."""
    def __init__(self):
        self.seen_ids: Set[int] = set()
        self.npcs: List[Dict[str, Any]] = []

    def add_npc(self, npc_data: Dict[str, Any]) -> bool:
        npc_id = int(npc_data.get('Id', npc_data.get('entry', 0)))
        if npc_id == 0 or npc_id in self.seen_ids:
            return False
        
        self.seen_ids.add(npc_id)
        # Приводим к единому формату для WRobot XML
        formatted_npc = {
            'Id': npc_id,
            'Name': npc_data.get('Name', npc_data.get('name', 'Unknown')),
            'Type': npc_data.get('Type', 'None'),
            'X': npc_data.get('X', npc_data.get('position_x', 0)),
            'Y': npc_data.get('Y', npc_data.get('position_y', 0)),
            'Z': npc_data.get('Z', npc_data.get('position_z', 0)),
            'Map': npc_data.get('Map', npc_data.get('map', 1))
        }
        self.npcs.append(formatted_npc)
        return True

    def get_all(self) -> List[Dict[str, Any]]:
        return self.npcs
