# logic/quest_chains.py
from core.models import Quest
from typing import List, Dict, Set

def build_quest_chains(quests: List[Quest]) -> List[List[Quest]]:
    """
    Groups quests into chains based on PrevQuestId, NextQuestId, and NextQuestInChain.
    """
    quest_map = {q.entry: q for q in quests}
    
    # Adjacency list: parent -> [children]
    graph: Dict[int, List[int]] = {q.entry: [] for q in quests}
    # Track incoming edges to find roots (start of chains)
    incoming_count = {q.entry: 0 for q in quests}

    for q in quests:
        # NextQuestId (deprecated in some cores but used)
        if q.next_quest_id != 0 and q.next_quest_id in quest_map:
            graph[q.entry].append(q.next_quest_id)
            incoming_count[q.next_quest_id] += 1
            
        # NextQuestInChain (Mangos TBC specific)
        if q.next_quest_in_chain != 0 and q.next_quest_in_chain in quest_map:
            graph[q.entry].append(q.next_quest_in_chain)
            incoming_count[q.next_quest_in_chain] += 1
            
        # PrevQuestId (Backlink)
        if q.prev_quest_id != 0 and q.prev_quest_id in quest_map:
            # Prev implies Parent -> Current
            graph[q.prev_quest_id].append(q.entry)
            incoming_count[q.entry] += 1

    chains: List[List[Quest]] = []
    visited: Set[int] = set()

    def dfs(current_id: int, current_chain: List[Quest]):
        visited.add(current_id)
        current_chain.append(quest_map[current_id])
        
        children = graph[current_id]
        # Sort children by ID to be deterministic
        children.sort()
        
        for child_id in children:
            if child_id not in visited:
                dfs(child_id, current_chain)

    # 1. Start with nodes having 0 incoming edges (Roots)
    for q_id in incoming_count:
        if incoming_count[q_id] == 0:
            if q_id not in visited:
                new_chain = []
                dfs(q_id, new_chain)
                if new_chain:
                    chains.append(new_chain)

    # 2. Handle cycles or isolated loops (nodes that have incoming edges but weren't visited from a root)
    for q_id in quest_map:
        if q_id not in visited:
            new_chain = []
            dfs(q_id, new_chain)
            if new_chain:
                chains.append(new_chain)

    # Sort chains by min_level of the first quest
    chains.sort(key=lambda c: (c[0].min_level, c[0].entry))
    
    return chains