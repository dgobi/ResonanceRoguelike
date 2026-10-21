> **Arc A status:** Historical source retained below. Creative intent remains a design reference; technical claims need the [current implementation and authority map](owner/STATUS.md). This banner does not resolve open design decisions.

# Essence System

Six essences describe the fundamental properties of weapons and the vulnerabilities of creatures. A weapon's essence interacts with a creature's essence profile to scale damage up or down. Nothing in this world is neutral — everything has an essence, even if weak.

See also: [COMBAT.md](COMBAT.md) for the damage formula, [CREATURES.md](CREATURES.md) for the full creature roster.

---

## The Six Essences

### Dissolution

The tendency of forms to come apart. Iron corrodes. Stone weathers. Flesh rots. Dissolution is not destruction — it is the patient unmaking that happens to everything, given time.

Weaponised dissolution accelerates that tendency. A pitted blade does not cut more deeply; it undermines whatever it touches. Armour struck by dissolution weakens. Structure fails.

**Effective against:** Things that hold their form through material mass — carapace, thornmass, physical structures with no inner animating principle.

**Weak against:** Things that are not really "there" in a material sense — diffuse forms, resonance-sustained shells with little physical substance remaining.

**Weapons carrying Dissolution:**
- `crude_blade` — incidental dissolution; poor iron maintenance. Strength 0.2.
- `heavy_blade` — heavier iron, more mass behind the edge. Strength 0.3.
- `dissolution_blade` — the pitting is not rust. Strength 0.5.

---

### Binding

The principle that holds forms in place. The bells were instruments of binding — they tuned the grey stones; the grey stones tuned the people. Generations of accumulated resonance was, in the end, a very thorough act of binding.

A weapon carrying Binding does not merely strike. It fixes, constrains, pins in place what had been drifting. Against forms held together by something diffuse — mist, waterlogged flesh, half-dispersed resonance — Binding is decisive.

**Effective against:** Diffuse or unmoored forms that maintain coherence through drift rather than structure. The Bog Wraith is mist over old water. The Drowned Revenant is barely held together by what soaked into it. Binding finds them where other things pass through.

**Weak against:** Things with strong internal structure that resist being fixed — dense bone, stone, carapace. Binding has nothing to grip.

**Weapons carrying Binding:**
- `binding_knife` — notches cut at calculated intervals; the iron holds something. Strength 0.6.

---

### Quickening

Life-force. Animation. The principle of being alive, moving, changing. Before the discharge, Quickening was what the bells sustained in living things — a resonance of vitality. The hollow have had it purged or inverted. What remains in them is the absence of it.

A weapon carrying Quickening introduces the life-principle directly into something that has rejected or lost it. The result is hostile contact at the most fundamental level.

**Effective against:** The hollow — creatures from which the life-principle has been discharged inward, leaving a transformed thing running on old habit and inverted resonance. The more thoroughly hollow a creature, the more violently it reacts to Quickening.

**Weak against:** Living things in full possession of their vitality. Quickening reinforces rather than damages what is already alive.

**Weapons carrying Quickening:** None currently exist in the world. A weapon of pure Quickening would need to carry enough life to be dangerous — a difficult thing to hold in iron.

---

### Consumption

The taking. Not destruction but transfer — the capacity to feed on, drain from, absorb. The world is full of consumption: the plague crow carries something away from what it touches; old drownings fed on the people who came too close; the barrow fed on whoever was buried in it.

A weapon carrying Consumption does not just deal damage. It takes something away.

**Effective against:** Living things with something left to take — vitality, warmth, function. The more intact a creature's organic or animating substance, the more Consumption can drain from it.

**Weak against:** The fully hollow — creatures from which everything consumable has already been expelled. There is nothing left for Consumption to take from a resonance shell.

**Weapons carrying Consumption:** None currently exist. Weapons of this type would require deliberate construction — a blade that feeds its wielder is not something that happens by accident.

---

### Revelation

The stripping of concealment. The world is layered — everything sits on older things. Revelation does not add anything; it removes what is false. It exposes the truth of a form regardless of what covers it.

The Revelation Lens is ground glass set in tarnished copper, sharpened to a point. What hides inside compressed bone does not hide from this.

**Effective against:** Things that maintain a false surface — bone that conceals inner structure, a creature that disguises itself as rock or terrain, hollow things that still wear the shape of what they were.

**Weak against:** Things that do not hide at all. The Briar Lurker is exactly what it appears to be. Revelation finds nothing to strip.

**Weapons carrying Revelation:**
- `revelation_lens` — ground glass, tarnished copper. What hides inside compressed bone does not hide from this. Strength 0.7.

---

### Severance

The cutting of connection, not of form. The discharge severed the accumulated resonance bonds between bells, stones, and people — violently, all at once. Many of the hollow are the result of that severance going wrong: a connection that was cut but not cleanly, still fraying.

A weapon carrying Severance finds whatever remaining bond sustains a hollow thing and completes the cut.

**Effective against:** Things sustained by resonance connection — the hollow, revenants, wraiths. These forms persist because something still links them to the world. Severance undoes that link. Against a Hollow Knight, it is decisive; there is nothing left of the person, only the connection keeping the armour moving.

**Weak against:** Things that were never connected to anything that could be severed — stone, carapace, creatures of simple predatory biology. Severance passes through them without finding purchase.

**Weapons carrying Severance:**
- `severance_blade` — narrow grey metal, edge ground at an angle that catches nothing. The bindings of the hollow yield before it. Strength 0.6.

---

## Essence Modifier Table

Creature essence profiles are defined in their JSON files under `essence_modifiers`. The modifier is a multiplier applied to damage when the weapon's essence matches — 1.0 is neutral, above 1.0 increases damage, below 1.0 reduces it.

The actual damage scaling:

```
net_modifier = 1.0 + (creature_modifier - 1.0) × weapon_essence_strength
modified_damage = floor(raw_damage × net_modifier)
```

A creature modifier of 3.0 with weapon strength 0.6 → net modifier 2.2 (more than double damage).
A creature modifier of 0.3 with weapon strength 0.5 → net modifier 0.65 (one-third reduction).

### All Creatures — Essence Modifiers

| Creature | Dissolution | Binding | Quickening | Consumption | Revelation | Severance |
|---|---|---|---|---|---|---|
| Barrow Wight | **0.4** | 1.3 | **2.2** | **0.3** | **2.0** | 0.9 |
| Hollow Knight | 0.5 | 0.7 | **1.8** | **0.4** | 1.5 | **2.5** |
| Hollow Revenant | **0.2** | **2.0** | 1.5 | **0.1** | **1.8** | **2.5** |
| Drowned Revenant | 1.4 | **2.2** | 1.6 | 0.5 | 1.3 | **1.8** |
| Grave Thing | 0.7 | 0.8 | 1.2 | 0.6 | **2.8** | 1.0 |
| Heath Stalker | 1.0 | 1.2 | 1.0 | 1.3 | 0.8 | 1.0 |
| Briar Lurker | **2.0** | **0.6** | 1.5 | 1.6 | **0.7** | **1.8** |
| Stone Lurker | **1.8** | **0.5** | 0.8 | **0.3** | 1.6 | 0.7 |
| Bog Wraith | **0.3** | **3.0** | 0.8 | 0.5 | 1.2 | **2.5** |
| Plague Crow | 1.0 | 1.0 | 1.1 | **1.5** | 0.9 | 1.0 |
| Highland Bandit | 1.0 | 1.0 | 1.1 | 1.3 | 1.0 | 1.0 |

Bold values indicate strong vulnerability (≥1.8) or strong resistance (≤0.5).

---

## Design Notes

**Why these six.** The essences map to the world's ontology, not to element systems. Dissolution and Binding are opposites: one breaks, one holds. Quickening and Consumption describe what vitality does (animates, is taken). Revelation and Severance describe operations on truth and connection. Everything in the world can be described in these terms.

**Nothing is neutral.** Weapons without an explicit essence still have one — crude iron carries trace Dissolution from the nature of corroding metal. The starting blades are not inert.

**Essences are not alignments.** Binding is not "good" and Dissolution is not "evil." The bells were instruments of Binding, and the bells ended the world. Revelation exposes false things, which is not always welcome. Severance completes what was left incomplete, which is sometimes mercy and sometimes horror.

**Player has no essence profile.** Creatures attacking the player do not apply essence modifiers. This is intentional — the player's nature is unknown, contested, or in transition.
