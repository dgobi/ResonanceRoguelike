# engine/palette.py
# Single source of truth for all colours in the project.
# Import semantic aliases into game code — not raw palette names
# unless the meaning is unambiguous.
#
# All values are AAP-64 canonical RGB tuples.

# ── Voids and Depths ──────────────────────────────────────────────────────────
VOID_BLACK        = (  6,   6,   8)   # #060608 — deepest bg
DEEP_NOTHING      = ( 20,  16,  19)   # #141013 — near-void
BLOOD_CELLAR      = ( 59,  23,  37)   # #3b1725 — ancient dark
DRIED_BLOOD       = (115,  23,  45)   # #73172d — old wound
FRESH_WOUND       = (180,  32,  42)   # #b4202a — bright red
EMBER_GLOW        = (223,  62,  35)   # #df3e23 — hot coal
FORGE_FIRE        = (250, 106,  10)   # #fa6a0a — orange flame
BELL_BRASS        = (249, 163,  27)   # #f9a31b — old brass
RESONANCE_GOLD    = (255, 213,  65)   # #ffd541 — charged gold
DISCHARGE_FLASH   = (255, 252,  64)   # #fffc40 — bell light

# ── Living and Growing ────────────────────────────────────────────────────────
PALE_GROWTH       = (214, 242, 100)   # #d6f264 — new leaf
LIVING_GREEN      = (156, 219,  67)   # #9cdb43 — fresh growth
VERDANT           = ( 89, 193,  53)   # #59c135 — pure life
DEEP_VERDANT      = ( 20, 160,  46)   # #14a02e — forest floor
OLD_GROWTH        = ( 26, 122,  62)   # #1a7a3e — ancient tree
MOSS_DARK         = ( 36,  82,  59)   # #24523b — wet moss
ABYSS_GREEN       = ( 18,  32,  32)   # #122020 — void-green

# ── Waters and Resonance ──────────────────────────────────────────────────────
DEEP_STONE_BLUE   = ( 20,  52, 100)   # #143464 — cold depth
LAPIS             = ( 40,  92, 196)   # #285cc4 — old stone blue
CLEAR_WATER       = ( 36, 159, 222)   # #249fde — open sky
COLDBELL_LIGHT    = ( 32, 214, 199)   # #20d6c7 — bell-teal
PALE_RESONANCE    = (166, 252, 219)   # #a6fcdb — resonance wash

# ── Lights and Bones ──────────────────────────────────────────────────────────
TRUE_WHITE        = (255, 255, 255)   # #ffffff — pure
BONE_PALE         = (254, 243, 192)   # #fef3c0 — old bone
SKIN_LIGHT        = (250, 214, 184)   # #fad6b8 — living skin
FLESH_WOUND       = (245, 160, 151)   # #f5a097 — wound pink
CORRUPTED_FLESH   = (232, 106, 115)   # #e86a73 — changed skin

# ── Corruption and Resonance Blooms ───────────────────────────────────────────
RESONANCE_BLOOM   = (188,  74, 155)   # #bc4a9b — discharge
VOID_PURPLE       = (121,  58, 128)   # #793a80 — deep ritual
DEEP_PURPLE       = ( 64,  51,  83)   # #403353 — dark ritual
MIDNIGHT_DEEP     = ( 36,  34,  52)   # #242234 — near-black

# ── Ash and Char ──────────────────────────────────────────────────────────────
CHAR_BLACK        = ( 34,  28,  26)   # #221c1a — cold ash
ASH_DARK          = ( 50,  43,  40)   # #322b28 — dark ash
RUST_BROWN        = (113,  65,  59)   # #71413b — old rust
EARTH_TONE        = (187, 117,  71)   # #bb7547 — dry earth
OLD_GOLD          = (219, 164,  99)   # #dba463 — tarnished
PALE_STONE        = (244, 210, 156)   # #f4d29c — worn stone

# ── Mists and Shadows ─────────────────────────────────────────────────────────
FROST_WHITE       = (218, 224, 234)   # #dae0ea — cold light
MIST_GREY         = (179, 185, 209)   # #b3b9d1 — morning mist
SLATE_MID         = (139, 147, 175)   # #8b93af — slate face
STONE_BLUE        = (109, 117, 141)   # #6d758d — wet stone
SLATE_DARK        = ( 74,  84,  98)   # #4a5462 — deep slate
DUNGEON_SHADOW    = ( 51,  57,  65)   # #333941 — dungeon dark

# ── Blood and Rose ────────────────────────────────────────────────────────────
BLOOD_DARK        = ( 66,  36,  51)   # #422433 — dried deep
DRIED_ROSE        = ( 91,  49,  56)   # #5b3138 — old wound
BLOOD_STONE       = (142,  82,  82)   # #8e5252 — stained
DUSTY_ROSE        = (186, 117, 106)   # #ba756a — faded wound
PALE_FLESH        = (233, 181, 163)   # #e9b5a3 — bloodless

# ── Spirits and Wraiths ───────────────────────────────────────────────────────
GHOST_WHITE       = (227, 230, 255)   # #e3e6ff — spirit light
SPIRIT_BLUE       = (185, 191, 251)   # #b9bffb — hollow glow
HOLLOW_BLUE       = (132, 155, 228)   # #849be4 — revenant
STEEL_WATER       = ( 88, 141, 190)   # #588dbe — cold steel
TEAL_DEEP         = ( 71, 125, 133)   # #477d85 — bog water

# ── Deep Forest ───────────────────────────────────────────────────────────────
FOREST_DEEP       = ( 35, 103,  78)   # #23674e — ancient wood
VERDANT_MID       = ( 50, 132, 100)   # #328464 — living path
LIFE_GREEN        = ( 93, 175, 141)   # #5daf8d — renewal
PALE_LIFE         = (146, 220, 186)   # #92dcba — faint life
RESONANCE_PALE    = (205, 247, 226)   # #cdf7e2 — washed clean

# ── Parchment and Age ─────────────────────────────────────────────────────────
OLD_PARCHMENT     = (228, 210, 170)   # #e4d2aa — found text
WORN_STONE        = (199, 176, 139)   # #c7b08b — ancient wall
AGED_WOOD         = (160, 134,  98)   # #a08662 — old timber
EARTH_BROWN       = (121, 103,  85)   # #796755 — turned earth
DEEP_EARTH        = ( 90,  78,  68)   # #5a4e44 — soil
SOIL_BLACK        = ( 66,  57,  52)   # #423934 — dark ground

# =============================================================================
# Semantic aliases — import these into game code
# =============================================================================

# ── UI / Structure ─────────────────────────────────────────────────────────────
UI_BACKGROUND       = VOID_BLACK
UI_PANEL_DARK       = MIDNIGHT_DEEP
UI_PANEL_MID        = DUNGEON_SHADOW
UI_BORDER           = DEEP_STONE_BLUE
UI_TEXT_BRIGHT      = FROST_WHITE
UI_TEXT_MID         = SLATE_MID
UI_TEXT_DIM         = SLATE_DARK
UI_TEXT_ACCENT      = OLD_GOLD
UI_TEXT_DANGER      = FRESH_WOUND

# ── Combat ─────────────────────────────────────────────────────────────────────
COMBAT_OUTGOING     = HOLLOW_BLUE      # player deals damage
COMBAT_INCOMING     = DUSTY_ROSE       # player takes damage
COMBAT_DEFLECT      = SLATE_DARK       # no damage
COMBAT_CRIT         = RESONANCE_GOLD   # critical hit callout
COMBAT_CRIT_DANGER  = FRESH_WOUND      # creature crit on player

# ── Resonance and Corruption ───────────────────────────────────────────────────
RESONANCE_LOW       = SLATE_MID
RESONANCE_MID       = STEEL_WATER
RESONANCE_HIGH      = DUSTY_ROSE
RESONANCE_CRITICAL  = BLOOD_STONE
CORRUPTION_COLOUR   = VOID_PURPLE
BELL_COLOUR         = OLD_GOLD
DISCHARGE_COLOUR    = RESONANCE_GOLD

# ── Deep Tongue ────────────────────────────────────────────────────────────────
DEEP_TONGUE_COLOUR  = (162, 120, 218)  # legible purple — glyphs and translations

# ── Status Effects ─────────────────────────────────────────────────────────────
STATUS_CHILL        = HOLLOW_BLUE
STATUS_THORNS       = OLD_GROWTH
STATUS_CORRUPTION   = VOID_PURPLE

# ── Messages ───────────────────────────────────────────────────────────────────
MSG_DEFAULT         = FROST_WHITE
MSG_COMBAT_OUT      = HOLLOW_BLUE
MSG_COMBAT_IN       = DUSTY_ROSE
MSG_SYSTEM          = SLATE_MID
MSG_LORE            = OLD_PARCHMENT
MSG_DANGER          = FRESH_WOUND
MSG_ANCIENT         = VOID_PURPLE
MSG_RESONANCE       = TEAL_DEEP

# ── Terrain ────────────────────────────────────────────────────────────────────
TERRAIN_WALL        = STEEL_WATER
TERRAIN_FLOOR       = TEAL_DEEP
TERRAIN_GRASS       = LIFE_GREEN
TERRAIN_TREE        = FOREST_DEEP
TERRAIN_WATER       = COLDBELL_LIGHT
TERRAIN_ROAD        = WORN_STONE
TERRAIN_RIVER       = COLDBELL_LIGHT

# ── Overmap ────────────────────────────────────────────────────────────────────
OVERMAP_RIVER       = COLDBELL_LIGHT
OVERMAP_ROAD_PRI    = AGED_WOOD
OVERMAP_ROAD_SEC    = EARTH_BROWN
OVERMAP_CAPITAL     = BLOOD_STONE
OVERMAP_VUKH        = RESONANCE_GOLD
OVERMAP_TOWN        = DUSTY_ROSE

# ── Biome overmap colours ──────────────────────────────────────────────────────
BIOME_FOREST        = FOREST_DEEP
BIOME_PLAINS        = LIFE_GREEN
BIOME_HEATH         = EARTH_TONE
BIOME_SWAMP         = MOSS_DARK
BIOME_MOUNTAIN      = SLATE_MID
BIOME_DEEP_MOUNTAIN = STONE_BLUE
BIOME_DROWNED_WOOD  = TEAL_DEEP
BIOME_ASH_WASTES    = ASH_DARK
BIOME_CAPITAL       = BLOOD_STONE
BIOME_TOWN          = DUSTY_ROSE

# ── Weather ────────────────────────────────────────────────────────────────────
WEATHER_RAIN        = STEEL_WATER
WEATHER_STORM       = DEEP_PURPLE
WEATHER_STORM_GLYPH = VOID_PURPLE
WEATHER_FOG         = FROST_WHITE
WEATHER_FOG_FORGET  = GHOST_WHITE
WEATHER_SNOW        = BONE_PALE
WEATHER_EDGE_PULSE  = DEEP_PURPLE
