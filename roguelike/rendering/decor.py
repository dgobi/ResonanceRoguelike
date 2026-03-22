# rendering/decor.py
import random

# Format: "terrain_name": [(sprite_key, weight), ...]
# Use None for "Void" (don't render anything)
DECOR_TABLE = {
    "grass": [
        (None, 60),          
        ("grass_1", 20), 
        ("grass_2", 10),
        ("flower_1", 1),
        ("flower_2", 1),
        ("shroom_1", 1),
        ("shroom_2", 1),
        ("rocks_1", 1),
        ("rocks_2", 1)
    ],
    "tree": [
        ("tree_1", 25),
        ("tree_2", 25),
        ("tree_3", 25),
        ("tree_4", 5) 
    ],
    "gravel": [
        ("gravel_1", 25),
        ("gravel_2", 75)
    ]
}

def get_procedural_key(mx: int, my: int, terrain: str) -> str | None:
    if terrain not in DECOR_TABLE:
        return terrain # Fallback: use terrain name as sprite key
    
    # Deterministic seed based on tile coordinates
    seed = (mx * 374761393) ^ (my * 668265263)
    rng = random.Random(seed)
    
    variants = DECOR_TABLE[terrain]
    total_weight = sum(w for _, w in variants)
    roll = rng.randint(1, total_weight)
    
    cursor = 0
    for key, weight in variants:
        cursor += weight
        if roll <= cursor:
            return key
    return None