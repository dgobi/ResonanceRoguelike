> **Arc A status:** Historical source retained below. Creative intent remains a design reference; technical claims need the [current implementation and authority map](owner/STATUS.md). This banner does not resolve open design decisions.

# Creature Reference

Current common-field controls, stable identity, body/reference policy and saved-instance
semantics are documented in [Creature authoring](CREATURE_AUTHORING.md). The
historical reference below is not the current authoring contract.

All creatures are defined in `roguelike/data/entities/creatures/`. Body definitions are in `roguelike/data/bodies/`. Special abilities are implemented in `roguelike/engine/creature_abilities.py`.

---

## Creature Roster

| Creature | Tile | Body | Damage | Key Armor | Essence Vulnerability | Special |
|---|---|---|---|---|---|---|
| Barrow Wight | `barrow_wight` | wight | 1d6+1 | Resonance AV2, Dense Bone AV3 | Binding ×3.0 | Corruption aura |
| Hollow Knight | `hollow_knight` | hollow_knight | 1d8+2 | Fused Plate AV6, Helm AV5 | Severance ×2.5 | Disruption aura |
| Hollow Revenant | `hollow_revenant` | hollow_revenant | 1d4+1 | Resonance Shell AV1 | Severance ×2.5 | — |
| Drowned Revenant | `drowned_revenant` | drowned_revenant | 1d4+1 | Waterlogged AV1 | — | — |
| Grave Thing | `grave_thing` | grave_thing | 1d6 | Compressed Bone AV4 | Revelation ×2.8 | — |
| Heath Stalker | `heath_stalker` | heath_stalker | 1d6 | Sinewy AV2, Lean Muscle AV1 | — | — |
| Briar Lurker | `briar_lurker` | briar_lurker | 1d4 | Dense Thornmass AV3 | Dissolution ×2.0 | Thorn retaliation |
| Stone Lurker | `stone_lurker` | stone_lurker | 1d8+2 | Stone Carapace AV6 | Dissolution ×1.8 | Hibernation ambush |
| Bog Wraith | `bog_wraith` | bog_wraith | 1d4 | Diffuse AV3 (mist) | Binding ×3.0 | FOV drain |
| Plague Crow | `plague_crow` | plague_crow | 1d3 | Feathers AV0 | — | Sickness 30% on hit |
| Highland Bandit | `highland_bandit` | humanoid | 1d6+1 | None | — | — |

---

## Special Abilities

Triggered by `creature_abilities.process_abilities(entity, engine)` each turn.

### Bog Wraith — FOV Drain

The Bog Wraith warps the boundaries of sight.

- **Effect:** Each turn within 8 tiles, reduces the player's effective FOV radius by a gradient amount proportional to distance
- **On death:** Overcorrects — player briefly gains +8 to FOV radius before it normalizes
- **Counter:** Binding-essence weapons deal ×3.0 damage

### Barrow Wight — Corruption Aura

Proximity to the Wight corrodes the spirit.

- **Effect:** +0.005 corruption per turn while within 2 tiles of the player
- **Warning:** Emits a warning message every 20 turns of sustained proximity
- **Compound:** Multiple Wights do not stack the aura, but each checks independently

### Hollow Knight — Resonant Disruption

The Knight's broken essence disrupts the form of attackers.

- **Effect:** Any attacker within 5 tiles rolls attack damage **twice** and takes the **lower** roll
- **Range:** 5-tile radius; the player must be adjacent or near-adjacent to trigger
- **Counter:** Severance-essence weapons deal ×2.5 damage

### Plague Crow — Sickness

The Crow's talons carry decay.

- **Effect:** 30% chance to inflict **Sickness** on a successful hit
- **Sickness mechanics:** Accelerates both hunger and thirst drain rates for 30 turns
- **Stacking:** Multiple sickness applications extend the duration

### Stone Lurker — Hibernation Ambush

The Lurker waits as stone, then strikes.

- **Hibernation:** While dormant, the Lurker appears as a rock tile — visually indistinguishable from terrain
- **Wake trigger:** Player enters within 3 tiles
- **Free attack:** On waking, the Lurker immediately performs one free attack before normal turn order resumes
- **Counter:** Dissolution-essence weapons deal ×1.8 damage

### Briar Lurker — Thorn Retaliation

Strike the briars and they strike back.

- **Effect:** On receiving any melee hit, retaliates with 1–2 thorn hits
- **Thorn mechanics:** Thorn hits always target torso; they are direct hits (bypass all armor layers)
- **Counter:** Dissolution-essence weapons deal ×2.0 damage

---

## Body Definitions

The 12 body definitions are in `roguelike/data/bodies/`. Each defines hit locations with HP pools, hit weights, and impairment thresholds.

### Common Locations by Body Type

**Humanoid** (`humanoid`, `highland_bandit`):

| Location | Size | HP | Impairment at Threshold |
|---|---|---|---|
| head | 10 | 10 | blinded (at 5 HP) |
| torso | 40 | 30 | — |
| left arm | 15 | 12 | left_arm_broken (at 4 HP) |
| right arm | 15 | 12 | right_arm_broken (at 4 HP) |
| left leg | 15 | 14 | left_leg_broken (at 5 HP) |
| right leg | 15 | 14 | right_leg_broken (at 5 HP) |

**Barrow Wight** (`wight`):
Locations: skull, ribcage, left limb, right limb. Higher bone AV across all locations.

**Hollow Knight** (`hollow_knight`):
Locations: helm, torso plate, arms, legs. Highest AV values in the game.

**Bog Wraith** (`bog_wraith`):
Diffuse body — single "form" location with mist-based AV. Cannot be impaired.

**Plague Crow** (`plague_crow`):
Locations: breast, head, wings. Very low HP pools; AV 0 on all.

---

## AI Behavior by Creature Type

All creatures use the standard AI state machine (see [COMPONENTS.md](COMPONENTS.md#ai)), but with different parameters:

| Creature | Sight Radius | Hears in Dark | Wander Radius | Alert Memory | Notes |
|---|---|---|---|---|---|
| Barrow Wight | 8 | yes | 8 | 12 | `sees_in_dark: true` |
| Hollow Knight | 6 | yes | 5 | 8 | Patrols slowly |
| Hollow Revenant | 5 | yes | 10 | 6 | Roams widely |
| Drowned Revenant | 4 | yes | 8 | 4 | Low memory |
| Grave Thing | 4 | no | 3 | 3 | Nearly blind; short range |
| Heath Stalker | 10 | no | 12 | 10 | High sight; roams far |
| Briar Lurker | 3 | no | 2 | 5 | Almost stationary |
| Stone Lurker | 3 | no | 0 | — | Hibernates; no wander |
| Bog Wraith | 6 | yes | 10 | 8 | Floats through rooms |
| Plague Crow | 12 | no | 15 | 6 | Excellent sight; skittish |
| Highland Bandit | 8 | no | 10 | 8 | Human intelligence |

---

## Factions

Faction labels used by `Perception.hostile_to`:

| Faction | Hostile to |
|---|---|
| `player` | — |
| `undead` | `player`, `living` |
| `beast` | `player` |
| `bandit` | `player` |
| `living` | `undead` |

Creatures only attack factions on their `hostile_to` list. Adding new factions requires updating `hostile_to` lists in creature JSON.
