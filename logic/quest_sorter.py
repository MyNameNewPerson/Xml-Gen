# logic/quest_sorter.py
import heapq
from typing import List, Dict, Set, DefaultDict
from collections import defaultdict
from core.models import Quest
from core.logger import get_logger

logger = get_logger(__name__)

def sort_quests_with_dependencies(quests: List[Quest]) -> List[Quest]:
    """
    Сортирует список квестов так, чтобы преквесты всегда шли ПЕРЕД следующими квестами.
    Использует топологическую сортировку с приоритетной очередью по уровню.
    """
    if not quests:
        return []

    # 1. Создаем карту для быстрого доступа по ID
    quest_map = {q.entry: q for q in quests}
    selected_ids = set(quest_map.keys())

    # 2. Строим граф зависимостей (Adjacency List)
    graph: DefaultDict[int, List[int]] = defaultdict(list)
    in_degree: Dict[int, int] = {q_id: 0 for q_id in selected_ids}

    for q in quests:
        parent_id = q.prev_quest_id
        if parent_id > 0 and parent_id in selected_ids:
            graph[parent_id].append(q.entry)
            in_degree[q.entry] += 1

    # 3. Инициализируем приоритетную очередь квестами без зависимостей
    # Сортируем по (MinLevel, QuestLevel, entry) для детерминированности
    priority_queue = []
    for q_id, degree in in_degree.items():
        if degree == 0:
            q = quest_map[q_id]
            heapq.heappush(priority_queue, (q.min_level, q.quest_level, q.entry))

    sorted_result = []

    # 4. Алгоритм Кана с приоритетной очередью
    while priority_queue:
        min_lvl, q_lvl, current_id = heapq.heappop(priority_queue)
        sorted_result.append(quest_map[current_id])

        if current_id in graph:
            for child_id in graph[current_id]:
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    child = quest_map[child_id]
                    heapq.heappush(priority_queue, (child.min_level, child.quest_level, child.entry))

    # 5. Проверка на циклические зависимости
    if len(sorted_result) != len(quests):
        logger.warning("Обнаружен цикл в зависимостях квестов! Используем запасной вариант сортировки.")
        processed_ids = set(q.entry for q in sorted_result)
        leftovers = [q for q in quests if q.entry not in processed_ids]
        leftovers.sort(key=lambda x: (x.min_level, x.quest_level))
        sorted_result.extend(leftovers)

    logger.info("Квесты успешно отсортированы по уровню и цепочкам.")
    return sorted_result
