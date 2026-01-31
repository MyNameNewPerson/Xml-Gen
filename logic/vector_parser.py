# logic/vector_parser.py
import re
from typing import List
from core.models import Hotspot

def parse_vector3_strings(text: str) -> List[Hotspot]:
    """
    Извлекает координаты X, Y, Z из различных форматов строк.
    Примеры:
    - <Vector3 X="-9400.988" Y="-2036.693" Z="58.38026" />
    - new Vector3(-9400.988, -2036.693, 58.38026, "None")
    - My Position: -9400.988, -2036.693, 58.38026
    """
    hotspots = []
    
    # 1. Поиск XML формата: X="...", Y="...", Z="..."
    xml_pattern = r'X="(?P<x>[^"]+)"\s+Y="(?P<y>[^"]+)"\s+Z="(?P<z>[^"]+)"'
    for match in re.finditer(xml_pattern, text):
        try:
            hotspots.append(Hotspot(
                x=float(match.group('x').replace(',', '.')),
                y=float(match.group('y').replace(',', '.')),
                z=float(match.group('z').replace(',', '.'))
            ))
        except ValueError: continue

    if hotspots: return hotspots

    # 2. Поиск C# или простого списка через запятую: (-9400.988, -2036.693, 58.38026)
    # Ищем группы по 3 числа
    numbers_pattern = r'(-?\d+(?:[.,]\d+)?)\s*,\s*(-?\d+(?:[.,]\d+)?)\s*,\s*(-?\d+(?:[.,]\d+)?)'
    for match in re.finditer(numbers_pattern, text):
        try:
            hotspots.append(Hotspot(
                x=float(match.group(1).replace(',', '.')),
                y=float(match.group(2).replace(',', '.')),
                z=float(match.group(3).replace(',', '.'))
            ))
        except ValueError: continue

    return hotspots
