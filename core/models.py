# core/models.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Zone:
    id: int
    name: str

@dataclass
class Quest:
    entry: int
    title: str
    min_level: int
    quest_level: int
    zone_or_sort: int
    required_races: int
    prev_quest_id: int = 0
    next_quest_id: int = 0
    next_quest_in_chain: int = 0
    special_flags: int = 0

@dataclass
class Objective:
    quest_id: int
    slot: int
    type: str          # 'kill', 'gather', 'loot', 'unknown'
    target_id: Optional[int] = None
    item_id: Optional[int] = None
    count: int = 1

@dataclass
class FarmZone:
    map_id: int
    center_x: float
    center_y: float
    center_z: float
    radius: float = 80.0

@dataclass
class Hotspot:
    x: float
    y: float
    z: float

@dataclass
class RunTo:
    x: float
    y: float
    z: float
    name: str = "Waypoint"

@dataclass
class GrindSettings:
    mob_id: Optional[int] = None
    mob_name: str = ""
    min_level: int = 0
    target_level: int = 0
    hotspots: List[Hotspot] = field(default_factory=list)
