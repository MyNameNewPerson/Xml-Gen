# logic/clustering.py
import numpy as np
from sklearn.cluster import DBSCAN
from core.models import FarmZone
from typing import List, Dict

def cluster_spawns(spawns: List[Dict[str, float]]) -> List[FarmZone]:
    if not spawns:
        return []
        
    # Extract coordinates
    coords = np.array([[float(s['position_x']), float(s['position_y'])] for s in spawns])
    
    # DBSCAN: Epsilon distance 80-100 yards is good for WoW hotspots
    dbscan = DBSCAN(eps=80.0, min_samples=3).fit(coords)

    zones = []
    unique_labels = set(dbscan.labels_)
    
    for label in unique_labels:
        if label == -1:  # Noise points
            continue
            
        cluster_indices = np.where(dbscan.labels_ == label)[0]
        cluster_coords = coords[cluster_indices]
        
        # Calculate center
        center = np.mean(cluster_coords, axis=0)
        
        # Calculate Z (average Z of points)
        cluster_z_vals = [float(spawns[i]['position_z']) for i in cluster_indices]
        center_z = np.mean(cluster_z_vals)
        
        # Calculate radius (max dist from center to a point + buffer)
        dists = np.linalg.norm(cluster_coords - center, axis=1)
        radius = np.max(dists) + 15.0
        
        map_id = spawns[0]['map'] # Assume same map for cluster
        
        zones.append(FarmZone(
            map_id=map_id,
            center_x=float(center[0]),
            center_y=float(center[1]),
            center_z=float(center_z),
            radius=float(radius)
        ))

    # If DBSCAN failed to cluster (too few points), return one big zone
    if not zones and spawns:
         center = np.mean(coords, axis=0)
         center_z = np.mean([float(s['position_z']) for s in spawns])
         zones.append(FarmZone(
            map_id=spawns[0]['map'],
            center_x=float(center[0]),
            center_y=float(center[1]),
            center_z=float(center_z),
            radius=50.0
         ))

    return zones