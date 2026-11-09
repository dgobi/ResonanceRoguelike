# Creatures, AI and population

For isolated learning, use [Start creating](#learning-path) and its complete GUIDE-1 examples. The older authoring recipes below describe intentional production content edits; do not install them merely to run a lesson.

Use `roguelike/data/entities/creatures/` for creature definitions. A creature's identity, appearance, basic combat data and existing AI selection can be authored here. Its spawn route, special abilities and some town population rules live elsewhere.

## Safest first edit: tune a shipped creature

For the Briar Lurker, open `briar_lurker.json`. Its current `base_hp` is `12`, `armour_value` is `3`, and ordinary damage is `1d4` with `damage_bonus: 0`. Change `base_hp` to `14` for a small durability increase without changing attack damage.

Use `base_hp`: the factory gives it precedence over `fighter.max_hp`. Use the top-level damage and armour fields for current combat; historical `fighter.power` and `fighter.defense` are not substitutes for the ordinary dice/armour system. Keep the definition `id` stable. A creature's visible tile can change while its `_creature_id` remains the same, and saves/effects depend on that distinction.

Test a new spawn. Loading a previously saved lurker restores its recorded health and combat state rather than automatically applying every new factory default.

## Tutorial: add an ordinary new creature

The following is a new tutorial definition using existing appearance and basic wandering AI. It does not invent a custom ability. Save it as `roguelike/data/entities/creatures/owner_road_scavenger.json`:

```json
{
  "id": "owner_road_scavenger",
  "name": "Road Scavenger",
  "description": "A hungry traveller watching the verge.",
  "tile": "highland_bandit",
  "base_hp": 10,
  "armour_value": 1,
  "body_id": "body_player",
  "limbs": [
    {"id": "head", "size": 1, "damage_multiplier": 1.5},
    {"id": "torso", "size": 4, "damage_multiplier": 1.0},
    {"id": "limbs", "size": 3, "damage_multiplier": 0.8}
  ],
  "damage_dice": "1d4",
  "damage_bonus": 0,
  "essence_modifiers": {"Severance": 1.2, "Binding": 1.0},
  "ai_type": "wandering",
  "wander_radius": 6,
  "pursuit_timeout": 12,
  "can_cross_chunks": true,
  "speed": 0.75,
  "perception": {
    "sight_radius": 6,
    "hearing_radius": 4,
    "sees_in_dark": false,
    "faction": "hostile",
    "hostile_to": ["player"]
  }
}
```

Inline `limbs` provide valid weighted hit locations; no separate new body file is needed. The borrowed `highland_bandit` tile deliberately reuses existing art. Replace it with a properly registered tile when you have the new asset.

### Register a wilderness appearance

Add this entry to the existing `creatures` array in `roguelike/data/zones/wilderness/briarwood.json`:

```json
{"id": "owner_road_scavenger", "chance": 0.2}
```

This makes the creature eligible when the actual scene's zone is `briarwood`. It does not establish a global 20% spawn rate or populate every forest. Zone assignment is part of world generation, and current planned scenes also reject reserved/blocked population cells.

For a predictable isolated authoring check, first verify the factory independently:

```powershell
& $ResonancePython -m json.tool roguelike/data/entities/creatures/owner_road_scavenger.json
& $ResonancePython -c "import sys; sys.path.insert(0, 'roguelike'); from engine.data_loader import DataLoader; from engine.creature_factory import CreatureFactory; d=DataLoader('roguelike/data'); a=CreatureFactory(d).spawn('owner_road_scavenger', 5, 5); assert a is not None and a.fighter.max_hp == 10 and a._creature_id == 'owner_road_scavenger'; print(a.name, type(a.ai).__name__, a.fighter.max_hp)"
```

Expect `Road Scavenger WanderingAI 10`. This does not prove spawning or pursuit. Then inspect a fresh scene with the actual eligible zone and exercise movement, attack, death and reload if the change affects those paths. Avoid changing permanent pool probabilities solely to make an ad hoc observation and forgetting to restore them.

## Wilderness probability is not weighted selection

Despite an old docstring describing weights, `CreatureFactory.spawn_for_zone` currently walks the zone's entries in order. Each entry independently passes or fails its `chance` check (default `0.3`). For an accepted entry, it tries up to 20 positions and creates at most one actor. It stops when `max_count` actors have been created; current surface callers pass a cap of three per zone.

Consequences:

- `weight` in a zone creature entry is not consumed by this function.
- Earlier successful entries can fill the cap before later ones are considered.
- `chance: 1.0` guarantees the probability check, not a legal placement.
- `spawn_zones` on the creature itself does not register it in a zone pool.
- Multiple zones can each contribute population; this is not one global scene cap.

Town population uses `DISTRICT_CREATURES` and `DISTRICT_DENSITY` in `generation/town_gen.py`, through `_compute_creature_spawns`. Its pool algorithm is different. Editing a wilderness zone does not change those district tables.

## Supported AI controls

| Field | Current role |
|---|---|
| `ai_type` | Legacy `wandering`, `ambush`, `fleeing`, `circling`, or current validated `composite`; do not rely on legacy fallback as validation |
| `wander_radius` | Passed to the chosen AI class and tied to its home position |
| `perception.sight_radius` | Detection distance used by perception |
| `perception.hearing_radius` | Hearing distance |
| `perception.sees_in_dark` | Existing darkness behavior |
| `perception.faction`, `.hostile_to` | Faction/hostility inputs |
| `speed` | Per-turn accumulator rate: below one skips some action opportunities; above one can produce extra opportunities |
| `pursuit_timeout` | Existing cross-scene pursuit timeout lookup |
| `can_cross_chunks` | Permission considered by the implemented boundary-pursuit logic |
| `can_swim` | Used in the zone spawning restriction for terrain marked not creature-passable; do not assume it supplies a complete new swimming AI |

The nested historical `ai.alert_memory` block is not a replacement for the current profile. Composite creatures use validated behavior profiles, senses and admitted abilities/attachments; [L05](#L05) gives a complete local territorial example. Effective profile and decision state have explicit saved identity. `can_use_stairs` and `can_cross_chunks` remain separate authored boundaries. New AI class names require implementation/registration. A legacy special ability can depend on an exact creature ID; cloning descriptive data does not transfer it. Use admitted attachments or implement the new dispatch deliberately.

Global concealment/pursuit controls in `data/ai_config.json` are a separate layer. Change them only when deliberately tuning those behaviors across creatures.

## Butchery and remains

A creature may declare `butcher_yield` containing `decay_turns` and a `tiers` array. Each tier uses `min_cutting_tier` and `yields` entries with `item_id`, `quantity_min`, `quantity_max`. Use `briar_lurker.json` as a full example.

SYS-5 captures finite remains identity and yield recipe at creation; current source changes do not rewrite an owned corpse's recipe. Scavenging can strip flesh while leaving non-flesh yields. Butchery checks exact current floor ownership and equipped cutting, stages outputs, and commits corpse removal only with the supported result transaction. Stale ownership rejects free; insufficient cutting is a paid attempt. Work and phase ownership matter across active/hot scenes and saves. The older source-creature lookup remains an explicit legacy route, not a reason to flatten every remains record into today's definition.

The Bone Reader perk allows all yield tiers to qualify, but the selected tier's quantities are still rolled between minimum and maximum. Its description's “always maximum yield” is stronger than the current consumer. Do not balance a recipe around a guaranteed maximum merely because the perk text says so.

Corpse timers are set during creature death. The current floor-object decay loop ticks the active scene's floor objects. A `decay_turns` field added to an ordinary food definition is not automatically copied by `ItemFactory` and does not implement general inventory food spoilage. Broader decay/catch-up behavior remains a separate design/implementation concern.

## Useful checks after a creature change

Check default HP/armour with a new spawn, its exact AI class, collision and detection, ordinary attack damage, active ability behavior when applicable, death/remains, and save/reload identity. If you add a new spawn reference, also confirm it is reached by an active generator; successful factory creation alone does not establish that.

## Source bindings

- [Creature factory and zone loop](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/creature_factory.py)
- [AI behavior and pursuit](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/components/ai.py)
- [AI speed scheduling](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/ai_system.py)
- [Town population tables and consumer](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/generation/town_gen.py)
- [Planned-scene population restrictions](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/generation/planned_scene.py)
- [Working creature and butchery declaration](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/data/entities/creatures/briar_lurker.json)
- [Butchery and corpse-decay consumers](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/engine.py)
