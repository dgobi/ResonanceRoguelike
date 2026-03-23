# rendering/decor.py
import random

# Format: "terrain_name": [(sprite_key, weight), ...]
# Use None for "Void" (don't render anything)
DECOR_TABLE = {
    "grass": [
        (None, 60),          
        ("grass_1", 20), 
        ("grass_2", 10),
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
    ],
    "mud": [
        ("mud_1", 25),
        ("mud_2", 25),
        ("mud_3", 25),
        ("mud_4", 25)
    ]
}

# Maps a 'varied_' prefix to actual terrain keys from your tiles.json/terrain_data
FUNCTIONAL_VARIANTS = {
    "varied_grass": [
        ("grass", 95), 
        ("flower_pilgrims_woe", 1), 
        ("flower_murk_violet", 1),
        ("shroom_sulphur_cap", 1),
        ("shroom_prophets_eye", 1)
    ],
    "varied_forest": [
        ("tree_1", 70),
        ("tree_2", 20),
        ("tree_3", 10),
        ("tree_4", 5) 
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

def resolve_functional_variant(terrain: str) -> str:
    """If terrain starts with varied_, pick a random real terrain type."""
    if not terrain.startswith("varied_") or terrain not in FUNCTIONAL_VARIANTS:
        return terrain
    
    variants = FUNCTIONAL_VARIANTS[terrain]
    total_weight = sum(w for _, w in variants)
    roll = random.randint(1, total_weight)
    
    cursor = 0
    for variant_name, weight in variants:
        cursor += weight
        if roll <= cursor:
            return variant_name
    return terrain