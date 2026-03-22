# Define the Category in decor.py

The DECOR_TABLE acts as a lookup. If a tile's terrain name exists here, the renderer will intercept it and roll for a variant.

Action: Open rendering/decor.py and add your new category key.
Python

DECOR_TABLE = {
    "grass": [(None, 85), ("grass", 15)],
    
    # NEW CATEGORY EXAMPLE:
    "statue": [
        ("statue_warrior", 40), # 40% chance
        ("statue_mage", 40),    # 40% chance
        (None, 20)              # 20% chance the tile is empty/void
    ]
}

    Key: Must match the string you will use in your generator (e.g., "statue").

    Values: A list of tuples (sprite_name, weight).

    Void Space: Use None as a sprite name to create "mostly void" areas (useful for grass or debris).

# Populate Assets in sprite_map.json

The "Specific Names" you invented in Step 1 (e.g., "statue_warrior") must now be mapped to actual pixel coordinates so the SpriteRegistry can load them.

Action: Open data/sprites/sprite_map.json and add entries to the "tiles" object.
JSON

"tiles": {
    "statue_warrior": {
      "sheet": "objects",
      "col": 12,
      "row": 4
    },
    "statue_mage": {
      "sheet": "objects",
      "col": 13,
      "row": 4
    }
}