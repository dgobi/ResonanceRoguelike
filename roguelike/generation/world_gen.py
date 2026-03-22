# generation/world_gen.py
from __future__ import annotations
import random
from world.world_map import (
    WorldMap, Chunk, RegionType,
    ConnectorType,
)
from world.name_gen import assign_chunk_name

# Probability of a submap existing per surface biome (by region_type.value string)
SUBMAP_WEIGHTS: dict[str, float] = {
    "plains":   0.06,
    "forest":   0.10,
    "swamp":    0.12,
    "heath":    0.15,
    "mountain": 0.18,
    "town":     0.0,
}

# Submap type distribution per surface biome
SUBMAP_TYPES: dict[str, dict[str, int]] = {
    "plains":   {"barrow": 3, "vault": 1},
    "forest":   {"barrow": 2, "cave": 2, "vault": 1},
    "swamp":    {"barrow": 1, "cave": 2, "vault": 1},
    "heath":    {"barrow": 4, "cave": 1},
    "mountain": {"cave": 4, "vault": 2, "barrow": 1},
}

# Zone compositions per submap type
SUBMAP_ZONES: dict[str, list] = {
    "barrow": [("barrow", 0.5), ("vault", 0.3), ("undercroft", 0.2)],
    "cave":   [("vault", 0.4), ("highstone", 0.3), ("dead_ground", 0.3)],
    "vault":  [("vault", 0.4), ("undercroft", 0.3), ("warped_place", 0.3)],
}


BIOME_WEIGHTS = {
    RegionType.PLAINS:   25,
    RegionType.FOREST:   30,
    RegionType.SWAMP:    10,
    RegionType.HEATH:    25,
}

MIN_TOWN_SPACING = 6

# Zone compositions per surface region type
REGION_ZONES = {
    RegionType.PLAINS: [
        ("heath",    0.6),
        ("deepwood", 0.1),
    ],
    RegionType.FOREST: [
        ("deepwood", 0.6),
        ("briarwood", 0.3),
        ("mere",     0.1),
    ],
    RegionType.SWAMP: [
        ("mere",     0.7),
        ("deepwood", 0.2),
        ("dead_ground", 0.1),
    ],
    RegionType.HEATH: [
        ("heath",    0.8),
        ("highstone",0.2),
    ],
    RegionType.MOUNTAIN: [
        ("highstone",0.7),
        ("barrow",   0.2),
        ("vault",    0.1),
    ],
    RegionType.TOWN: [
        ("hearth",   0.45),
        ("market",   0.20),
        ("sanctum",  0.15),
        ("gate_ward",0.10),
        ("pale_quarter", 0.05),
        ("undercroft",0.05),
    ],
}


def generate_world(
    width: int,
    height: int,
    seed: int | None = None,
) -> WorldMap:
    rng   = random.Random(seed)
    world = WorldMap(width, height)

    # --- Pass 1: Base biomes ---
    biome_pool    = list(BIOME_WEIGHTS.keys())
    biome_weights = list(BIOME_WEIGHTS.values())

    for wx in range(width):
        for wy in range(height):
            region_type = rng.choices(biome_pool, weights=biome_weights, k=1)[0]
            chunk = Chunk(
                wx=wx, wy=wy,
                region_type=region_type,
                seed=rng.randint(0, 999999),
                zones=list(REGION_ZONES.get(region_type, [("heath", 1.0)])),
            )
            world.set(chunk)

    # Smooth pass
    for _ in range(3):
        for wx in range(width):
            for wy in range(height):
                if rng.random() < 0.4:
                    neighbour_types = []
                    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nb = world.get(wx + dx, wy + dy)
                        if nb and nb.region_type in BIOME_WEIGHTS:
                            neighbour_types.append(nb.region_type)
                    if neighbour_types:
                        majority = max(set(neighbour_types),
                                       key=neighbour_types.count)
                        chunk = world.get(wx, wy)
                        if chunk:
                            chunk.region_type = majority
                            chunk.zones = list(
                                REGION_ZONES.get(majority, [("heath", 1.0)])
                            )

    # --- Pass 2: Towns ---
    placed_towns: list[tuple[int, int]] = []
    n_towns = (width * height) // 40

    def min_dist(ax, ay, positions):
        if not positions:
            return float("inf")
        return min(abs(ax-px)+abs(ay-py) for px,py in positions)

    attempts = 0
    while len(placed_towns) < n_towns and attempts < 10000:
        attempts += 1
        wx = rng.randint(1, width  - 2)
        wy = rng.randint(1, height - 2)
        if min_dist(wx, wy, placed_towns) >= MIN_TOWN_SPACING:
            chunk = world.get(wx, wy)
            if chunk:
                chunk.region_type = RegionType.TOWN
                chunk.zones = list(REGION_ZONES[RegionType.TOWN])
                chunk.seed  = rng.randint(0, 999999)
                placed_towns.append((wx, wy))

    # --- Pass 3: Rivers ---
    n_rivers = (width * height) // 200
    for _ in range(n_rivers):
        _place_river(world, rng, width, height)

    # --- Pass 4: Roads between towns ---
    _place_roads(world, rng, placed_towns)

    # --- Pass 5: Name every chunk ---
    for chunk in world.chunks.values():
        chunk.name, chunk.name_register = assign_chunk_name(
            chunk.region_type.value, chunk.seed
        )

    # --- Pass 7: SubMap assignment ---
    # Per-biome probability from SUBMAP_WEIGHTS; type from SUBMAP_TYPES.
    from world.name_gen import assign_chunk_name as _name_chunk
    for (wx, wy), chunk in world.chunks.items():
        biome       = chunk.region_type.value
        chance      = SUBMAP_WEIGHTS.get(biome, 0.0)
        if chance <= 0.0:
            continue
        submap_rng  = random.Random(chunk.seed ^ 0xABCD1234)
        if submap_rng.random() >= chance:
            continue
        types_map   = SUBMAP_TYPES.get(biome, {"barrow": 1})
        types       = list(types_map.keys())
        wts         = list(types_map.values())
        stype       = submap_rng.choices(types, weights=wts, k=1)[0]
        sseed       = submap_rng.randint(0, 999999)
        sname, _    = _name_chunk("dungeon", sseed)
        chunk.add_submap(stype, sname, sseed)

    # --- Pass 8: Starting Location ---
    # Force the world centre chunk to FOREST with a single hand-crafted lab SubMap.
    # Surface generates normally via forest generator; _place_submap_entrance()
    # stamps a sunken_ruin entrance into the interior.
    centre_wx = width  // 2
    centre_wy = height // 2
    start_chunk = world.get(centre_wx, centre_wy)
    if start_chunk:
        start_chunk.region_type = RegionType.FOREST
        start_chunk.zones = list(REGION_ZONES.get(RegionType.FOREST, []))
        start_chunk.submaps = []
        from world.world_map import SubMap
        start_sub = SubMap(
            submap_id   = f"sub_{centre_wx}_{centre_wy}_0",
            submap_type = "laboratory",
            name        = "Vrath Sketh",
            seed        = (seed or 0) ^ 0x0AB1,
            layout_id   = "starting_lab",
        )
        start_chunk.submaps = [start_sub]
        start_chunk.name = "the waking forest"
        start_chunk.name_register = "common"

    # --- Pass 9: WorldMyth ---
    from world.world_myth import generate_world_myth
    from world import name_gen

    # Use chunks with submaps as candidate loci; fall back to any explored chunk
    submap_chunks = [
        (wx, wy) for (wx, wy), chunk in world.chunks.items()
        if chunk.submaps
    ]
    cx, cy = width // 2, height // 2
    submap_chunks.sort(key=lambda p: abs(p[0] - cx) + abs(p[1] - cy))

    myth = generate_world_myth(seed, submap_chunks, name_gen)

    locus_chunk = world.get(myth.locus_wx, myth.locus_wy)
    if locus_chunk:
        locus_chunk.is_locus = True
        locus_chunk.name     = myth.locus_name

    world.myth = myth
    return world


def _place_river(
    world: WorldMap,
    rng: random.Random,
    width: int,
    height: int,
) -> None:
    """
    Trace a river from a random highland/edge source to a swamp/edge sink.
    At each chunk boundary it crosses, stamp matching EdgeConnectors
    on both sides so local generators know where to carve water.
    """
    # Start at a random edge or highland chunk
    x = rng.randint(0, width  - 1)
    y = rng.randint(0, height - 1)

    river_id = f"river_{x}_{y}"
    # Rivers meander — pick a dominant flow direction
    # with some random drift
    flow_dx = rng.choice([-1, 0, 1])
    flow_dy = rng.choice([-1, 0, 1])
    if flow_dx == 0 and flow_dy == 0:
        flow_dy = 1

    position = round(rng.uniform(0.2, 0.8), 2)
    max_length = rng.randint(8, 25)

    for _ in range(max_length):
        if not world.in_bounds(x, y):
            break

        chunk = world.get(x, y)
        if not chunk:
            break

        # Bias toward swamp/plains as river flows
        if chunk.region_type not in (RegionType.MOUNTAIN,):
            if "mere" not in [z[0] for z in chunk.zones]:
                chunk.zones.append(("mere", 0.2))

        # Determine exit edge and stamp connectors
        next_x, next_y, exit_edge, entry_edge = _flow_step(
            x, y, flow_dx, flow_dy, rng
        )

        # Stamp exit connector on current chunk
        chunk.add_connector(exit_edge, ConnectorType.RIVER,
                            position, river_id)

        # Stamp entry connector on next chunk
        next_chunk = world.get(next_x, next_y)
        if next_chunk:
            next_chunk.add_connector(entry_edge, ConnectorType.RIVER,
                                     position, river_id)

        x, y = next_x, next_y

        # Small drift
        if rng.random() < 0.3:
            flow_dx = max(-1, min(1, flow_dx + rng.randint(-1, 1)))
            flow_dy = max(-1, min(1, flow_dy + rng.randint(-1, 1)))
            if flow_dx == 0 and flow_dy == 0:
                flow_dy = 1


def _flow_step(
    x: int, y: int,
    dx: int, dy: int,
    rng: random.Random,
) -> tuple[int, int, str, str]:
    """
    Given current position and flow direction, return
    (next_x, next_y, exit_edge, entry_edge).
    """
    OPPOSITE = {"north": "south", "south": "north",
                "east": "west",   "west": "east"}

    if abs(dx) >= abs(dy):
        if dx > 0:
            exit_edge = "east"
        else:
            exit_edge = "west"
    else:
        if dy > 0:
            exit_edge = "south"
        else:
            exit_edge = "north"

    offsets = {"north": (0,-1), "south": (0,1),
               "east":  (1, 0), "west": (-1,0)}
    ox, oy = offsets[exit_edge]
    return x + ox, y + oy, exit_edge, OPPOSITE[exit_edge]


def _place_roads(
    world: WorldMap,
    rng: random.Random,
    towns: list[tuple[int, int]],
) -> None:
    """
    Connect towns with roads using a simple pathfinding approach.
    Stamp EdgeConnectors at every chunk boundary the road crosses.
    """
    if len(towns) < 2:
        return

    road_id_counter = [0]

    def connect(ax, ay, bx, by):
        road_id = f"road_{road_id_counter[0]}"
        road_id_counter[0] += 1

        x, y = ax, ay
        while (x, y) != (bx, by):
            chunk = world.get(x, y)
            if not chunk:
                break

            # Step toward target — prefer straight lines
            dx = 0 if bx == x else (1 if bx > x else -1)
            dy = 0 if by == y else (1 if by > y else -1)

            # Roads prefer cardinal movement
            if dx != 0 and dy != 0:
                if rng.random() < 0.5:
                    dy = 0
                else:
                    dx = 0

            next_x, next_y, exit_edge, entry_edge = _flow_step(
                x, y, dx, dy, rng
            )

            position = 0.5  # roads cross at midpoint
            chunk.add_connector(exit_edge, ConnectorType.ROAD,
                                position, road_id)
            next_chunk = world.get(next_x, next_y)
            if next_chunk:
                next_chunk.add_connector(entry_edge, ConnectorType.ROAD,
                                         position, road_id)
            x, y = next_x, next_y

    # Connect each town to the nearest town
    for i, (ax, ay) in enumerate(towns):
        if i + 1 < len(towns):
            connect(ax, ay, towns[i+1][0], towns[i+1][1])