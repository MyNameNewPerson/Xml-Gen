# logic/session_manager.py
import json
import os
from typing import List, Optional
from dataclasses import dataclass, field, asdict
from core.logger import get_logger
from core.models import Hotspot, RunTo

logger = get_logger(__name__)

@dataclass
class GrindSettings:
    mob_id: Optional[int] = None
    mob_name: Optional[str] = ""
    min_level: int = 0
    target_level: int = 0
    hotspots: List[Hotspot] = field(default_factory=list)

@dataclass
class ZoneSession:
    zone_id: int
    zone_name: str
    faction: str = "horde"
    selected_quest_ids: List[int] = field(default_factory=list)
    grind_settings: GrindSettings = field(default_factory=GrindSettings)
    run_to_points: List[RunTo] = field(default_factory=list)
    include_vendors: bool = True
    include_trainers: bool = True
    include_flight_masters: bool = True

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        # Восстановление вложенных объектов
        gs_data = data.get('grind_settings', {})
        hotspots = [Hotspot(**h) for h in gs_data.get('hotspots', [])]
        gs = GrindSettings(
            mob_id=gs_data.get('mob_id'),
            mob_name=gs_data.get('mob_name'),
            min_level=gs_data.get('min_level', 0),
            target_level=gs_data.get('target_level', 0),
            hotspots=hotspots
        )
        
        run_tos = [RunTo(**r) for r in data.get('run_to_points', [])]
        
        return ZoneSession(
            zone_id=data.get('zone_id'),
            zone_name=data.get('zone_name'),
            faction=data.get('faction', 'horde'),
            selected_quest_ids=data.get('selected_quest_ids', []),
            grind_settings=gs,
            run_to_points=run_tos,
            include_vendors=data.get('include_vendors', True),
            include_trainers=data.get('include_trainers', True),
            include_flight_masters=data.get('include_flight_masters', True)
        )

class SessionManager:
    def __init__(self, filepath="project.json"):
        self.filepath = filepath
        self.sessions: List[ZoneSession] = []

    def add_session(self, session: ZoneSession):
        self.sessions.append(session)

    def remove_session(self, index: int):
        if 0 <= index < len(self.sessions):
            self.sessions.pop(index)

    def save(self):
        try:
            data = [s.to_dict() for s in self.sessions]
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Project saved to {self.filepath}")
        except Exception as e:
            logger.error(f"Failed to save project: {e}")

    def load(self) -> List[ZoneSession]:
        if not os.path.exists(self.filepath):
            return []
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.sessions = [ZoneSession.from_dict(s) for s in data]
            logger.info(f"Loaded {len(self.sessions)} sessions.")
            return self.sessions
        except Exception as e:
            logger.error(f"Failed to load project: {e}")
            return []
