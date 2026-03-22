# rendering/decor.py
import random

# Format: "terrain_name": [(sprite_key, weight), ...]
# Use None for "Void" (don't render anything)
DECOR_TABLE = {
    "grass": [
        (None, 85),          # 85% Empty/Void
        ("grass", 10) # 10% Standard
    ],
    "tree": [
        ("tree", 100) 
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