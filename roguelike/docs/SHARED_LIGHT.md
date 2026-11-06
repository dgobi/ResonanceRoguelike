# Shared light and tactical visibility (SYS-2)

Light is a property of the current scene. Terrain, supported decor and the exact
carried, lit offhand source illuminate finite, obstructed circles. A target cell
is lit when it receives one of those sources or scene ambient is at least 0.1.
Sources do not need to be visible to the player. Walls and sight-blocking decor
stop their footprints; overlapping lights do not extend each other's reach.

Mechanical radius is an inclusive Euclidean distance in tiles, at most 40.
Terrain/decor `light_emit` accepts integral 1–40 tile reach; zero/absent is off.
The historical terrain `campfire_lit` value 0.7 explicitly means five tiles.
Unsupported fractional values do not produce unlimited light. Cosmetic color,
falloff and flicker change presentation only. Rendering does not spend fuel,
advance AI, sample gameplay RNG or change the illumination decision.

The player still needs personal direct line of sight. Existing near/moon vision
remains; emitted light can extend it to 40 tiles before final fog/wraith limits.
Ambient moonlight does not grant that extension. Debug reveal and remembered
terrain never count as observation. Eligible ordinary AI checks the particular
target's lit cell, then its own range, obstruction, concealment and existing
darkvision/near-range rules. Extinguishing removes fresh visual evidence; it does
not erase a creature's memory, hearing or existing response state.

Underground ambient comes from the actual submap's declared zone type, without
surface daylight. Missing/ambiguous submap context falls back to dark. Surface
day/moon and passive terrain memory policies remain. Queries never repair scene
identity. Scene transitions and restoration rebuild this derived view; neither
illumination masks nor the cache are saved.

## Carrying and using a light

Use the ordinary inventory action to light/extinguish a torch or lantern. Lighting
claims the offhand. Equipping the Ward or another offhand object releases the
source; two same-ID torches retain separate ownership and spent fuel. Dropping or
consuming the exact source releases it. A dropped light is an ordinary unlit floor
item; floor-source, refill and shutter systems are outside this feature.

An active carried source spends one fuel count per charged phase, including its
activation phase. Expiry removes its light and burning availability before that
phase's AI sight. Inspection, rendering, rejected use and F5/F9 are free. The
existing burning keyword still determines held heat; illumination does not grant
stationary-fire suitability or change SYS-1 preparation rules.

Newly constructed and restored supported items retain an effective
`held_light: {version: 1, radius: N}` in their item state, alongside copied visual
settings, burn duration and spent count. Editing a definition affects later
construction; owned saved lights retain their settings. Genuine old items gain
their historical mechanical `light_radius`, never the old decorative radius
(canonical torch and lantern both resolve to six). Missing/nonpositive mechanical
reach remains zero. Historical null/zero fuel keeps the existing 600-phase default.
Malformed new state is rejected before installation. An exhausted restored owner
stays exhausted and cannot emit or supply burning heat.

## Author a variant in Workbench

Open an ordinary nonstackable `equip_light` tool such as `tallow_torch` or
`oil_lantern`, then **Save as new variant**. Set name, description, existing tile,
mass, **Mechanical light reach (tiles)** (1–40) and **Held fuel (charged phases)**
(1–10,000).
The supported cosmetic controls are falloff (0.25–4) and flicker. Visual radius,
color, heat provision, use binding, offhand role, consumption identity and other
metadata stay protected, including through Raw Source and recovery.

Validate, review/apply, and reopen the saved item. Place its saved ID in a saved
room or supported loot pool. **Test latest saved version** captures that source;
**Reset current test** retains the earlier immutable capture. A parked item draft
does not affect another room. Publication alone does not add an acquisition route.

`watch_lantern` is the ordinary example: radius 9, 420 charged phases, 0.8 kg,
trading greater reach for shorter endurance and greater mass than the old lantern.
New tool-shed C stock can contain it; stock is finite and not guaranteed. Existing
worlds/containers are not retroactively restocked. `short_rushlight` (radius 6,
five phases, 0.1 kg) is a deliberately short-lived Test-room reuse example in
`sys2_light_room`, not a new general supply route.

The normally selected `barrow_lamplit_store` offers a held-light approach and a
fixed campfire pool with a free offhand for the Ward. An existing observation-averse
watcher responds only to actual direct observation. Cover and the pool edge still
matter; the optional readable note grants no flags. The encounter, existing grave
material, equipment and changed place state use ordinary acquisition/save rules.
These examples establish local usefulness, not global balance or unaided discovery.
