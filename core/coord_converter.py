# core/coord_converter.py
from core.logger import get_logger

logger = get_logger(__name__)

# Данные из WorldMapArea.dbc для TBC 2.4.3
# Формат: ZoneID: {'map': MapID, 'left': Y_max, 'right': Y_min, 'top': X_max, 'bottom': X_min}
# Координаты WoW: X - Север(+)/Юг(-), Y - Запад(+)/Восток(-)
# MapID: 0=Azeroth(EK), 1=Kalimdor, 530=Outland

ZONE_DIMENSIONS = {
    # ========================================================
    #                EASTERN KINGDOMS (Map 0)
    # ========================================================
    1:    {'map': 0, 'left': -4266.67, 'right': -6400.0, 'top': 2133.33, 'bottom': -533.33},    # Dun Morogh
    3:    {'map': 0, 'left': -5866.67, 'right': -7466.67, 'top': -2666.67, 'bottom': -4266.67}, # Badlands
    4:    {'map': 0, 'left': -10133.33, 'right': -12800.0, 'top': -2666.67, 'bottom': -5333.33},# Blasted Lands
    8:    {'map': 0, 'left': -9066.67, 'right': -11200.0, 'top': -2133.33, 'bottom': -4266.67}, # Swamp of Sorrows
    10:   {'map': 0, 'left': -9066.67, 'right': -11733.33, 'top': -533.33, 'bottom': -3200.0},  # Duskwood
    11:   {'map': 0, 'left': -2133.33, 'right': -4800.0, 'top': 533.33, 'bottom': -2133.33},    # Wetlands
    12:   {'map': 0, 'left': -8000.0, 'right': -10666.67, 'top': 533.33, 'bottom': -2133.33},   # Elwynn Forest
    28:   {'map': 0, 'left': 533.33, 'right': -2133.33, 'top': 3200.0, 'bottom': 533.33},       # Western Plaguelands
    33:   {'map': 0, 'left': -10666.67, 'right': -15466.67, 'top': 533.33, 'bottom': -4266.67}, # Stranglethorn Vale
    36:   {'map': 0, 'left': 533.33, 'right': -1066.67, 'top': 1066.67, 'bottom': -533.33},     # Alterac Mountains
    38:   {'map': 0, 'left': -4266.67, 'right': -6400.0, 'top': -2133.33, 'bottom': -4266.67},  # Loch Modan
    40:   {'map': 0, 'left': -9600.0, 'right': -12266.67, 'top': -533.33, 'bottom': -3200.0},   # Westfall
    41:   {'map': 0, 'left': -10133.33, 'right': -11200.0, 'top': -1600.0, 'bottom': -2666.67}, # Deadwind Pass
    44:   {'map': 0, 'left': -8533.33, 'right': -10133.33, 'top': -533.33, 'bottom': -2133.33}, # Redridge Mountains
    45:   {'map': 0, 'left': -533.33, 'right': -2666.67, 'top': 533.33, 'bottom': -1600.0},     # Arathi Highlands
    46:   {'map': 0, 'left': -6400.0, 'right': -8533.33, 'top': -533.33, 'bottom': -2666.67},   # Burning Steppes
    47:   {'map': 0, 'left': 2133.33, 'right': -1066.67, 'top': 2133.33, 'bottom': -1066.67},   # The Hinterlands
    51:   {'map': 0, 'left': -6400.0, 'right': -8000.0, 'top': -533.33, 'bottom': -2133.33},    # Searing Gorge
    85:   {'map': 0, 'left': 3200.0, 'right': 533.33, 'top': 2666.67, 'bottom': 0.0},           # Tirisfal Glades
    130:  {'map': 0, 'left': 1600.0, 'right': -1066.67, 'top': 2133.33, 'bottom': -533.33},     # Silverpine Forest
    139:  {'map': 0, 'left': 5866.67, 'right': 1600.0, 'top': 3733.33, 'bottom': -533.33},      # Eastern Plaguelands
    267:  {'map': 0, 'left': 533.33, 'right': -1600.0, 'top': 533.33, 'bottom': -1600.0},       # Hillsbrad Foothills
    # Города и стартовые зоны (EK)
    1497: {'map': 0, 'left': 2185.0, 'right': 1515.0, 'top': 475.0, 'bottom': -107.0},          # Undercity
    1519: {'map': 0, 'left': -8430.0, 'right': -9300.0, 'top': 1300.0, 'bottom': 320.0},        # Stormwind City
    1537: {'map': 0, 'left': -4533.33, 'right': -5333.33, 'top': -533.33, 'bottom': -1333.33},  # Ironforge
    
    # Стартовые зоны Blood Elf (Map 530 - технически Outland map ID, но находятся в Азероте)
    3430: {'map': 530, 'left': 11733.33, 'right': 6400.0, 'top': 14400.0, 'bottom': 9066.67},   # Eversong Woods
    3433: {'map': 530, 'left': 8533.33, 'right': 5333.33, 'top': 10666.67, 'bottom': 5333.33},  # Ghostlands
    3487: {'map': 530, 'left': 10026.7, 'right': 9360.0, 'top': 10666.7, 'bottom': 10000.0},    # Silvermoon City
    4080: {'map': 530, 'left': 13066.67, 'right': 12533.33, 'top': 13066.67, 'bottom': 12533.33}, # Isle of Quel'Danas (2.4)

    # ========================================================
    #                    KALIMDOR (Map 1)
    # ========================================================
    14:   {'map': 1, 'left': 426.67, 'right': -2773.33, 'top': 1600.0, 'bottom': -1600.0},      # Durotar
    15:   {'map': 1, 'left': -2133.33, 'right': -5866.67, 'top': -2666.67, 'bottom': -6400.0},  # Dustwallow Marsh
    16:   {'map': 1, 'left': -2133.33, 'right': -5333.33, 'top': 4800.0, 'bottom': 1600.0},     # Azshara
    17:   {'map': 1, 'left': 1600.0, 'right': -4266.67, 'top': 2933.33, 'bottom': -2933.33},    # The Barrens
    141:  {'map': 1, 'left': 10666.67, 'right': 8533.33, 'top': 12266.67, 'bottom': 10133.33},  # Teldrassil
    148:  {'map': 1, 'left': 8533.33, 'right': 5333.33, 'top': 8533.33, 'bottom': 5333.33},     # Darkshore
    188:  {'map': 1, 'left': 1200.0, 'right': 600.0, 'top': 11000.0, 'bottom': 10200.0},        # Shadowglen (Corrected)
    215:  {'map': 1, 'left': -533.33, 'right': -4266.67, 'top': 1066.67, 'bottom': -2666.67},   # Mulgore
    331:  {'map': 1, 'left': 4800.0, 'right': 1066.67, 'top': 4266.67, 'bottom': 533.33},       # Ashenvale
    357:  {'map': 1, 'left': -2133.33, 'right': -6933.33, 'top': 2133.33, 'bottom': -2666.67},  # Feralas
    361:  {'map': 1, 'left': 4800.0, 'right': 2666.67, 'top': 7466.67, 'bottom': 5333.33},      # Felwood
    400:  {'map': 1, 'left': -4266.67, 'right': -6933.33, 'top': -2666.67, 'bottom': -5333.33}, # Thousand Needles
    405:  {'map': 1, 'left': -533.33, 'right': -3200.0, 'top': 2133.33, 'bottom': -533.33},     # Desolace
    406:  {'map': 1, 'left': 1600.0, 'right': -1066.67, 'top': 3200.0, 'bottom': 533.33},       # Stonetalon Mountains
    440:  {'map': 1, 'left': -5866.67, 'right': -9066.67, 'top': -2666.67, 'bottom': -5866.67}, # Tanaris
    490:  {'map': 1, 'left': -6400.0, 'right': -8533.33, 'top': -533.33, 'bottom': -2666.67},   # Un'Goro Crater
    493:  {'map': 1, 'left': 8533.33, 'right': 6400.0, 'top': 8533.33, 'bottom': 6400.0},       # Moonglade
    618:  {'map': 1, 'left': 8000.0, 'right': 3733.33, 'top': 6933.33, 'bottom': 2666.67},      # Winterspring
    1377: {'map': 1, 'left': -6400.0, 'right': -9600.0, 'top': -2666.67, 'bottom': -5866.67},   # Silithus
    # Города (Kalimdor)
    1637: {'map': 1, 'left': 2133.33, 'right': 1066.67, 'top': -4266.67, 'bottom': -5333.33},   # Orgrimmar
    1638: {'map': 1, 'left': -1066.67, 'right': -1600.0, 'top': -2133.33, 'bottom': -2666.67},  # Thunder Bluff
    1657: {'map': 1, 'left': 10186.7, 'right': 9653.33, 'top': 12800.0, 'bottom': 12266.7},     # Darnassus
    
    # Стартовые зоны Draenei (Map 530)
    3524: {'map': 530, 'left': -2666.67, 'right': -6400.0, 'top': 12800.0, 'bottom': 9066.67},  # Azuremyst Isle
    3525: {'map': 530, 'left': -1066.67, 'right': -4266.67, 'top': 14933.33, 'bottom': 11733.3}, # Bloodmyst Isle
    3557: {'map': 530, 'left': -3650.0, 'right': -4200.0, 'top': 11350.0, 'bottom': 10800.0},   # The Exodar

    # ========================================================
    #                    OUTLAND (Map 530)
    # ========================================================
    3483: {'map': 530, 'left': 4266.67, 'right': -1333.33, 'top': 5440.0, 'bottom': -160.0},    # Hellfire Peninsula
    3518: {'map': 530, 'left': -1600.0, 'right': -6400.0, 'top': 3413.33, 'bottom': -1386.67},  # Nagrand
    3519: {'map': 530, 'left': -853.33, 'right': -5120.0, 'top': 6080.0, 'bottom': 1280.0},     # Terokkar Forest
    3520: {'map': 530, 'left': -1600.0, 'right': -6133.33, 'top': 1066.67, 'bottom': -3466.67}, # Shadowmoon Valley
    3521: {'map': 530, 'left': 1066.67, 'right': -3733.33, 'top': 8746.67, 'bottom': 3946.67},  # Zangarmarsh
    3522: {'map': 530, 'left': 4266.67, 'right': -1600.0, 'top': 9813.33, 'bottom': 4213.33},   # Blade's Edge Mountains
    3523: {'map': 530, 'left': 6240.0, 'right': 1440.0, 'top': 5866.67, 'bottom': 1066.67},     # Netherstorm
    3703: {'map': 530, 'left': -1725.0, 'right': -2035.0, 'top': 5585.0, 'bottom': 5275.0},     # Shattrath City
}

def get_zone_dimensions(zone_id: int):
    return ZONE_DIMENSIONS.get(zone_id)

def is_coords_in_bounds(zone_id: int, x: float, y: float) -> bool:
    """
    Проверяет, попадают ли мировые координаты в границы указанной зоны.
    Если зоны нет в базе, возвращаем True (не можем проверить, считаем верным).
    """
    dims = ZONE_DIMENSIONS.get(zone_id)
    if not dims:
        return True

    # WoW X (Vertical): Top > Bottom
    # WoW Y (Horizontal): Left > Right
    
    # Проверка X (между Bottom и Top)
    # Добавляем небольшой буфер (100), чтобы не терять точки на границах, но не цеплять соседей
    min_x = min(dims['bottom'], dims['top']) - 100 
    max_x = max(dims['bottom'], dims['top']) + 100
    valid_x = min_x <= x <= max_x

    # Проверка Y (между Right и Left)
    min_y = min(dims['right'], dims['left']) - 100
    max_y = max(dims['right'], dims['left']) + 100
    valid_y = min_y <= y <= max_y

    return valid_x and valid_y

def questie_to_world_coords(zone_id: int, q_x: float, q_y: float):
    """
    Конвертирует координаты Questie (0-100) в World Coords (X, Y, Z=0)
    Questie X = Горизонталь (WoW Y)
    Questie Y = Вертикаль (WoW X)
    """
    dims = ZONE_DIMENSIONS.get(zone_id)
    if not dims:
        # Если зоны нет в базе, возвращаем None. 
        return None

    # Questie X/Y - это проценты (0-100)
    # WoW Y (Горизонталь) идет от Left (+) к Right (-)
    # WoW X (Вертикаль) идет от Top (+) к Bottom (-)
    
    width = dims['left'] - dims['right']
    height = dims['top'] - dims['bottom']
    
    world_y = dims['left'] - (width * q_x / 100.0)
    world_x = dims['top'] - (height * q_y / 100.0)
    
    return {
        'position_x': world_x,
        'position_y': world_y,
        'position_z': 0.0, # Z не известен в Questie
        'map': dims['map']
    }