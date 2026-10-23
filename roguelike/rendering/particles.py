# rendering/particles.py
"""
Particle and overlay visual effects system.
Pure rendering layer — no game state, no save state, no simulation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import pygame
import math
import random
import time
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    pass


# ------------------------------------------------------------------ #
#  Core data structures
# ------------------------------------------------------------------ #

@dataclass
class Particle:
    # Position: world-space (tile coords, float) OR
    #           screen-space (viewport-relative pixel coords, float)
    x: float
    y: float
    vx: float              # velocity x per second
    vy: float              # velocity y per second
    lifetime: float        # seconds remaining
    max_lifetime: float    # total lifetime at spawn
    r: int
    g: int
    b: int
    alpha: int             # 0-255
    size: float            # radius in pixels
    space: str             # "world" or "screen"
    shape: str             # "circle" | "streak" | "ring" | "square"
    # Ring-specific:
    ring_radius: float     = 0.0      # current radius (tiles)
    ring_max_radius: float = 0.0      # max radius before fade
    ring_width: int        = 1        # pixel width
    # Pool tag for two-pool cap system: "ambient" or "combat"
    pool: str              = "combat"

    @property
    def life_fraction(self) -> float:
        """0.0 = just spawned, 1.0 = dead."""
        if self.max_lifetime <= 0:
            return 1.0
        return 1.0 - (self.lifetime / self.max_lifetime)


@dataclass
class ParticleEmitter:
    """
    Emits particles of a given type at a rate.
    Screen-space emitters use viewport-relative positions.
    """
    emitter_id: str
    x: float
    y: float
    space: str              # "world" | "screen"
    particle_type: str
    active: bool   = True
    rate: float    = 0.0    # particles per second (0 = manual)
    _accumulator: float = field(default=0.0, repr=False)
    _last_emit: float   = field(default=0.0, repr=False)


# ------------------------------------------------------------------ #
#  ParticleSystem
# ------------------------------------------------------------------ #

class ParticleSystem:
    """
    Manages all active particles and emitters.
    Updated every frame (real-time delta, not turn-based).
    Drawn as the final pass in the render pipeline, before popups.

    Two-pool cap system:
      ambient pool (sparkles, flames, smoke, embers): max 200
      combat pool  (blood, burst, rings, callout):    max 150
      Total hard cap: 350
    """

    AMBIENT_CAP = 200
    COMBAT_CAP  = 150
    MAX_PARTICLES = AMBIENT_CAP + COMBAT_CAP

    def __init__(self) -> None:
        self.particles:   list[Particle]            = []
        self.emitters:    dict[str, ParticleEmitter] = {}
        self._last_frame:  float                    = time.monotonic()
        # Per-pool counts — recalculated each update() for accuracy
        self._ambient_count: int = 0
        self._combat_count:  int = 0
        # Shared scratch surface — avoids per-particle allocations in draw()
        self._scratch: "pygame.Surface | None"  = None
        self._scratch_size: tuple[int, int]     = (0, 0)

    # ── Emitter management ─────────────────────────────────────────

    def add_emitter(self, emitter: ParticleEmitter) -> None:
        self.emitters[emitter.emitter_id] = emitter

    def remove_emitter(self, emitter_id: str) -> None:
        self.emitters.pop(emitter_id, None)

    def set_emitter_active(self, emitter_id: str, active: bool) -> None:
        if emitter_id in self.emitters:
            self.emitters[emitter_id].active = active

    # ── Manual one-shot emission ───────────────────────────────────

    def _pool_count(self, pool: str) -> int:
        """Return cached pool count (refreshed each update())."""
        return self._ambient_count if pool == "ambient" else self._combat_count

    def _pool_cap(self, pool: str) -> int:
        """Return the cap for a given pool."""
        return self.AMBIENT_CAP if pool == "ambient" else self.COMBAT_CAP

    def _recount_pools(self) -> None:
        """Recount pool sizes from the particle list."""
        a = c = 0
        for p in self.particles:
            if p.pool == "ambient":
                a += 1
            else:
                c += 1
        self._ambient_count = a
        self._combat_count  = c

    def emit(self, particle: Particle) -> None:
        """Directly add a particle. Respects pool cap."""
        if particle.pool == "ambient":
            if self._ambient_count >= self.AMBIENT_CAP:
                return
            self._ambient_count += 1
        else:
            if self._combat_count >= self.COMBAT_CAP:
                return
            self._combat_count += 1
        self.particles.append(particle)

    def emit_burst(self, particles: list[Particle]) -> None:
        """Add multiple particles at once. Respects pool caps."""
        if not particles:
            return
        pool = particles[0].pool
        if pool == "ambient":
            remaining = max(0, self.AMBIENT_CAP - self._ambient_count)
        else:
            remaining = max(0, self.COMBAT_CAP - self._combat_count)
        added = particles[:remaining]
        for p in added:
            self.particles.append(p)
        if pool == "ambient":
            self._ambient_count += len(added)
        else:
            self._combat_count += len(added)

    def clear(self) -> None:
        """Remove all active particles and emitters."""
        self.particles.clear()
        self.emitters.clear()
        self._ambient_count = 0
        self._combat_count  = 0

    # ── Update (call every frame) ──────────────────────────────────

    def update(self, dt: float, viewport_w: int, viewport_h: int,
               zoom: int, scroll_x: int = 0, scroll_y: int = 0) -> None:
        """
        dt: seconds since last frame.
        viewport_w/h: game map area in pixels.
        zoom: current zoom level (tiles to pixels).
        """
        # Emit from active emitters
        for emitter in self.emitters.values():
            if not emitter.active or emitter.rate <= 0:
                continue
            emitter._accumulator += emitter.rate * dt
            while emitter._accumulator >= 1.0:
                emitter._accumulator -= 1.0
                p = _make_particle(emitter, viewport_w, viewport_h, zoom)
                if p and len(self.particles) < self.MAX_PARTICLES:
                    self.particles.append(p)

        # Update particles
        alive = []
        for p in self.particles:
            p.lifetime -= dt
            if p.lifetime <= 0:
                continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            # Square particles (screen-space blood) fall with gravity in px/s²
            if p.shape == "square":
                p.vy += 220.0 * dt
            # Ring expansion
            if p.shape == "ring":
                expansion_rate = (p.ring_max_radius / p.max_lifetime
                                  if p.max_lifetime > 0 else 0)
                p.ring_radius += expansion_rate * dt
            # Fade alpha
            frac = p.life_fraction
            if p.shape == "ring":
                if frac < 0.3:
                    p.alpha = int(255 * (frac / 0.3) * 0.6)
                else:
                    p.alpha = int(255 * (1.0 - frac) * 0.6)
            elif p.shape == "sparkle":
                pass  # alpha stores max alpha; draw() computes from life_fraction
            else:
                p.alpha = int(255 * (1.0 - frac))
            # Cull off-screen screen-space particles
            if p.space == "screen":
                if (p.x < -60 or p.x > viewport_w + 60 or
                        p.y < -60 or p.y > viewport_h + 60):
                    continue
            alive.append(p)
        self.particles = alive
        # Hard cap: if update() grew the list past MAX_PARTICLES, trim oldest first.
        if len(self.particles) > self.MAX_PARTICLES:
            self.particles = self.particles[-self.MAX_PARTICLES:]
        # Refresh pool counts after pruning dead particles
        self._recount_pools()

    # ── Draw ──────────────────────────────────────────────────────

    def draw(self, surf: pygame.Surface,
             tile_w: int, tile_h: int,
             map_origin_x: int, map_origin_y: int,
             cam_x: int = 0,
             cam_y: int = 0,
             viewport_w: int = 0,
             viewport_h: int = 0) -> None:
        """
        surf: the game surface (full screen surface).
        tile_w/h: pixel size of one tile (after zoom).
        map_origin_x/y: viewport top-left in screen pixels (viewport.x + shake_x,
                         viewport.y + shake_y). Does NOT include camera tile offset.
        cam_x/y: camera tile offset — subtracted from world-space particle positions
                 so that the particle tracks with the camera correctly.
        viewport_w/h: pixel dimensions of the game viewport (for world-space culling).

        World-space formula: screen_x = map_origin_x + (p.x - cam_x) * tile_w
        Screen-space formula: screen_x = map_origin_x + p.x

        Uses a single shared scratch surface — zero per-particle allocations.
        """
        # Always clear scratch first — prevents sprite accumulation across frames.
        # Must happen before the early-return guard; a dirty scratch from a
        # prior frame must never survive to the next draw call.
        surf_w, surf_h = surf.get_size()
        if self._scratch is None or self._scratch_size != (surf_w, surf_h):
            self._scratch = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
            self._scratch_size = (surf_w, surf_h)
        self._scratch.fill((0, 0, 0, 0))

        if not self.particles:
            return

        _bounds = pygame.Rect(0, 0, surf_w, surf_h)

        _vp_x1 = map_origin_x
        _vp_y1 = map_origin_y
        _vp_x2 = map_origin_x + viewport_w if viewport_w > 0 else surf_w
        _vp_y2 = map_origin_y + viewport_h if viewport_h > 0 else surf_h

        for p in self.particles:
            if p.space == "world":
                sx = int(map_origin_x + (p.x - cam_x) * tile_w)
                sy = int(map_origin_y + (p.y - cam_y) * tile_h)
                # Cull world-space particles that are far outside the viewport
                if sx < _vp_x1 - 100 or sx > _vp_x2 + 100:
                    continue
                if sy < _vp_y1 - 100 or sy > _vp_y2 + 100:
                    continue
            else:
                # Screen-space: p.x/y hold absolute screen pixel coordinates.
                # Do NOT add map_origin — that would double-count viewport.x.
                sx = int(p.x)
                sy = int(p.y)

            color = (p.r, p.g, p.b, p.alpha)

            if p.shape == "circle":
                _draw_circle_to(self._scratch, color, sx, sy, max(1, int(p.size)))

            elif p.shape == "streak":
                length = max(2, int(p.size))
                vlen = math.sqrt(p.vx ** 2 + p.vy ** 2)
                if vlen > 0:
                    ndx = p.vx / vlen
                    ndy = p.vy / vlen
                    ex = int(sx + ndx * length)
                    ey = int(sy + ndy * length)
                    pygame.draw.line(self._scratch, color, (sx, sy), (ex, ey), 1)

            elif p.shape == "ring":
                radius_px = int(p.ring_radius * tile_w)
                if radius_px > 0:
                    pygame.draw.circle(self._scratch, color, (sx, sy),
                                       radius_px, p.ring_width)

            elif p.shape == "square":
                # Filled rectangle — pixel-art blood/burst aesthetic.
                # Use clip() not clamp_ip() — clamp snaps off-screen rects to the
                # screen edge, causing stray pixels at the viewport corner.
                half = max(1, int(p.size))
                rect = pygame.Rect(sx - half, sy - half, half * 2, half * 2)
                visible = rect.clip(_bounds)
                if visible.width > 0 and visible.height > 0:
                    self._scratch.fill((p.r, p.g, p.b, p.alpha), visible)

            elif p.shape == "sparkle":
                # alpha stores max alpha; derive current alpha from life_fraction
                frac  = p.life_fraction
                max_a = p.alpha
                if frac < 0.35:
                    cur_a = int(max_a * frac / 0.35)
                elif frac < 0.60:
                    cur_a = max_a
                else:
                    cur_a = int(max_a * (1.0 - (frac - 0.60) / 0.40))
                cur_a = max(0, min(255, cur_a))
                arm = max(1, int(p.size))
                sc = (p.r, p.g, p.b, cur_a)
                pygame.draw.line(self._scratch, sc, (sx - arm, sy), (sx + arm, sy), 1)
                pygame.draw.line(self._scratch, sc, (sx, sy - arm), (sx, sy + arm), 1)

        surf.blit(self._scratch, (0, 0))


# ------------------------------------------------------------------ #
#  Drawing helpers
# ------------------------------------------------------------------ #

def _draw_circle_to(
        surf: pygame.Surface,
        color: tuple,
        cx: int,
        cy: int,
        radius: int,
) -> None:
    """Draw a circle with alpha directly onto surf (no sub-surface allocation)."""
    if radius <= 0:
        return
    pygame.draw.circle(surf, color, (cx, cy), radius)


# ------------------------------------------------------------------ #
#  Particle factories
# ------------------------------------------------------------------ #

def make_rain_particle(
        viewport_w: int,
        viewport_h: int,
        intensity: float,
        rng: random.Random,
) -> Particle:
    """
    intensity: 0.0-1.0 (light_rain=0.35, heavy_rain=0.75, storm=1.0)
    Screen-space. Viewport-relative coordinates.
    """
    x = rng.uniform(-20, viewport_w + 20)
    y = rng.uniform(-30, -5)

    speed = rng.uniform(400, 600) * max(0.3, intensity)
    vx = speed * 0.15
    vy = speed

    size = rng.uniform(4, 10) * max(0.3, intensity)

    if intensity >= 0.95:
        r = rng.randint(160, 200)
        g = 160
        b = rng.randint(200, 240)
    else:
        v = rng.randint(180, 240)
        r, g, b = v - 20, v - 10, v

    lifetime = rng.uniform(0.3, 0.8)
    return Particle(
        x=x, y=y, vx=vx, vy=vy,
        lifetime=lifetime, max_lifetime=lifetime,
        r=r, g=g, b=b, alpha=180,
        size=size, space="screen", shape="streak",
    )


def make_sprint_streaks(
        world_x: float,
        world_y: float,
        dx: int,
        dy: int,
        color: tuple[int, int, int],
        rng: random.Random,
) -> list[Particle]:
    """World-space speed-line streaks for sprint bonus step.
    4-6 short-lived streaks angled in movement direction."""
    r, g, b = color
    n = rng.randint(4, 6)
    particles = []
    for _ in range(n):
        # Scatter origin slightly around tile centre
        ox = rng.uniform(-0.3, 0.3)
        oy = rng.uniform(-0.3, 0.3)
        # Velocity opposite to movement (trails behind)
        speed = rng.uniform(1.5, 3.0)
        vx = -dx * speed + rng.uniform(-0.3, 0.3)
        vy = -dy * speed + rng.uniform(-0.3, 0.3)
        lt = rng.uniform(0.08, 0.15)  # ~5-9 frames at 60fps
        particles.append(Particle(
            x=world_x + 0.5 + ox,
            y=world_y + 0.5 + oy,
            vx=vx, vy=vy,
            lifetime=lt, max_lifetime=lt,
            r=r, g=g, b=b, alpha=100,
            size=rng.uniform(2.0, 4.0),
            space="world", shape="streak",
            pool="combat",
        ))
    return particles


def make_fog_patch(
        viewport_w: int,
        viewport_h: int,
        rng: random.Random,
        fog_type: str = "fog",
) -> Particle:
    """
    fog_type: "fog" | "forgetting_fog"
    Large soft circles drifting slowly. Screen-space.
    """
    side = rng.randint(0, 3)
    if side == 0:
        x, y = rng.uniform(0, viewport_w), -60.0
    elif side == 1:
        x, y = viewport_w + 60.0, rng.uniform(0, viewport_h)
    elif side == 2:
        x, y = rng.uniform(0, viewport_w), viewport_h + 60.0
    else:
        x, y = -60.0, rng.uniform(0, viewport_h)

    if rng.random() < 0.4:
        x = rng.uniform(-50, viewport_w + 50)
        y = rng.uniform(-50, viewport_h + 50)

    vx = rng.uniform(-15, 15)
    vy = rng.uniform(-8, 8)
    size = rng.uniform(40, 120)

    if fog_type == "forgetting_fog":
        r, g, b = 230, 235, 255
        alpha   = rng.randint(30, 70)
        lifetime = rng.uniform(8, 16)
    else:
        r, g, b = 220, 225, 230
        alpha   = rng.randint(20, 55)
        lifetime = rng.uniform(6, 14)

    return Particle(
        x=x, y=y, vx=vx, vy=vy,
        lifetime=lifetime, max_lifetime=lifetime,
        r=r, g=g, b=b, alpha=alpha,
        size=size, space="screen", shape="circle",
    )


def make_bone_snow_particle(
        viewport_w: int,
        viewport_h: int,
        rng: random.Random,
) -> Particle:
    """
    Slower than rain. Slightly larger. Off-white.
    Erratic horizontal drift — unsettling.
    """
    x = rng.uniform(-20, viewport_w + 20)
    y = rng.uniform(-20, -2)

    vx = rng.uniform(-30, 60)
    vy = rng.uniform(40, 90)

    v    = rng.randint(200, 235)
    r, g, b = v, v - 5, v - 15

    size     = rng.uniform(2, 5)
    lifetime = rng.uniform(2.0, 5.0)

    return Particle(
        x=x, y=y, vx=vx, vy=vy,
        lifetime=lifetime, max_lifetime=lifetime,
        r=r, g=g, b=b, alpha=200,
        size=size, space="screen", shape="circle",
    )


def make_waystone_ring(
        tile_x: float,
        tile_y: float,
        rng: random.Random,
) -> Particle:
    """
    Expanding ring centred on waystone tile.
    World-space. Cold grey-blue.
    """
    return Particle(
        x=tile_x + 0.5,
        y=tile_y + 0.5,
        vx=0.0, vy=0.0,
        lifetime=2.5, max_lifetime=2.5,
        r=90, g=110, b=130,
        alpha=0,
        size=1.0,
        space="world", shape="ring",
        ring_radius=0.0,
        ring_max_radius=4.5,
        ring_width=1,
        pool="ambient",
    )


def make_discharge_ring(
        tile_x: float,
        tile_y: float,
        bell_type: str,
) -> Particle:
    """
    Fast expanding ring from bell discharge.
    Intact: gold, large. Cracked: dusty rose, smaller.
    """
    if bell_type == "intact":
        r, g, b  = 226, 181, 112   # old_gold
        max_r    = 18.0
        lifetime = 1.2
        width    = 2
    else:
        r, g, b  = 188, 89, 96    # dusty_rose
        max_r    = 10.0
        lifetime = 0.8
        width    = 1

    return Particle(
        x=tile_x + 0.5, y=tile_y + 0.5,
        vx=0.0, vy=0.0,
        lifetime=lifetime, max_lifetime=lifetime,
        r=r, g=g, b=b, alpha=200,
        size=1.0, space="world", shape="ring",
        ring_radius=0.0,
        ring_max_radius=max_r,
        ring_width=width,
    )


def make_sparkle(
        world_x: float,
        world_y: float,
        color:   tuple[int, int, int],
        rng:     random.Random,
) -> Particle:
    """
    World-space sparkle at tile centre.
    alpha stores max alpha — draw() computes current alpha from life_fraction.
    Fade-in first 35%, hold to 60%, fade-out last 40%.
    """
    r, g, b = color
    lt = rng.uniform(0.4, 0.9)
    # Slight scatter so sparkles don't all appear at exact tile centre
    ox = rng.uniform(-0.3, 0.3)
    oy = rng.uniform(-0.3, 0.3)
    return Particle(
        x=world_x + 0.5 + ox,
        y=world_y + 0.5 + oy,
        vx=0.0, vy=0.0,
        lifetime=lt, max_lifetime=lt,
        r=r, g=g, b=b,
        alpha=rng.randint(160, 240),   # stored as max alpha
        size=rng.uniform(1.5, 3.5),
        space="world", shape="sparkle",
        pool="ambient",
    )


# ------------------------------------------------------------------ #
#  Ember particle factory (campfire_lit and future fire tiles)
# ------------------------------------------------------------------ #

def make_ember_particles(
        screen_x: float,
        screen_y: float,
        rng:      random.Random,
) -> list[Particle]:
    """
    1-2 screen-space square particles rising from a fire tile.
    screen_x/y: centre of the tile in absolute screen pixels.
    Gravity (220 px/s²) counters the upward velocity, giving a brief arc.
    """
    count = rng.randint(1, 2)
    result = []
    for _ in range(count):
        col = rng.choice((OLD_GOLD, EMBER_GLOW))
        lt = rng.uniform(0.4, 0.7)
        result.append(Particle(
            x=screen_x + rng.uniform(-4, 4),
            y=screen_y + rng.uniform(-2, 2),
            vx=rng.uniform(-8.0, 8.0),
            vy=rng.uniform(-70.0, -90.0),   # upward; gravity pulls back
            lifetime=lt, max_lifetime=lt,
            r=col[0], g=col[1], b=col[2],
            alpha=200,
            size=rng.uniform(1.5, 2.5),
            space="screen", shape="square",
            pool="ambient",
        ))
    return result


# ------------------------------------------------------------------ #
#  Tiered flame particle factories
# ------------------------------------------------------------------ #

def make_flame_low_particles(
        screen_x: float,
        screen_y: float,
        rng:      random.Random,
) -> list[Particle]:
    """
    Small flicker: candles, stub torches. 1 particle per 4 frames.
    Uses dim amber (EARTH_TONE) and forge orange (FORGE_FIRE).
    """
    col = rng.choice((EARTH_TONE, FORGE_FIRE))
    lt  = rng.uniform(0.25, 0.45)
    return [Particle(
        x=screen_x + rng.uniform(-2, 2),
        y=screen_y + rng.uniform(-1, 1),
        vx=rng.uniform(-4.0, 4.0),
        vy=rng.uniform(-45.0, -60.0),
        lifetime=lt, max_lifetime=lt,
        r=col[0], g=col[1], b=col[2],
        alpha=180,
        size=rng.uniform(1.0, 2.0),
        space="screen", shape="square",
        pool="ambient",
    )]


def make_flame_med_particles(
        screen_x: float,
        screen_y: float,
        rng:      random.Random,
) -> list[Particle]:
    """
    Medium fire: campfire_lit. 1-2 particles per 3 frames.
    Uses OLD_GOLD and EMBER_GLOW.
    """
    count = rng.randint(1, 2)
    result = []
    for _ in range(count):
        col = rng.choice((OLD_GOLD, EMBER_GLOW))
        lt  = rng.uniform(0.4, 0.7)
        result.append(Particle(
            x=screen_x + rng.uniform(-5, 5),
            y=screen_y + rng.uniform(-2, 2),
            vx=rng.uniform(-8.0, 8.0),
            vy=rng.uniform(-70.0, -90.0),
            lifetime=lt, max_lifetime=lt,
            r=col[0], g=col[1], b=col[2],
            alpha=200,
            size=rng.uniform(1.5, 2.5),
            space="screen", shape="square",
            pool="ambient",
        ))
    return result


def make_flame_high_particles(
        screen_x: float,
        screen_y: float,
        rng:      random.Random,
) -> list[Particle]:
    """
    Large fire: bonfire, burning terrain. 2-3 particles per 2 frames.
    Uses FORGE_FIRE, BELL_BRASS, RESONANCE_GOLD for a roaring palette.
    """
    count = rng.randint(2, 3)
    result = []
    for _ in range(count):
        col = rng.choice((FORGE_FIRE, BELL_BRASS, RESONANCE_GOLD))
        lt  = rng.uniform(0.5, 0.8)
        result.append(Particle(
            x=screen_x + rng.uniform(-8, 8),
            y=screen_y + rng.uniform(-3, 3),
            vx=rng.uniform(-12.0, 12.0),
            vy=rng.uniform(-90.0, -120.0),
            lifetime=lt, max_lifetime=lt,
            r=col[0], g=col[1], b=col[2],
            alpha=220,
            size=rng.uniform(2.0, 3.5),
            space="screen", shape="square",
            pool="ambient",
        ))
    return result


def make_smoke_incense_particles(
        screen_x: float,
        screen_y: float,
        rng:      random.Random,
) -> list[Particle]:
    """
    Thin drifting smoke: incense burners, smouldering embers.
    1 particle per 5 frames. SLATE_MID fading to DUNGEON_SHADOW.
    """
    col = rng.choice((SLATE_MID, DUNGEON_SHADOW))
    lt  = rng.uniform(0.8, 1.4)
    ox  = rng.uniform(-3, 3)
    return [Particle(
        x=screen_x + ox,
        y=screen_y + rng.uniform(-2, 0),
        vx=rng.uniform(-3.0, 3.0),
        vy=rng.uniform(-30.0, -50.0),
        lifetime=lt, max_lifetime=lt,
        r=col[0], g=col[1], b=col[2],
        alpha=120,
        size=rng.uniform(1.5, 2.5),
        space="screen", shape="circle",
        pool="ambient",
    )]


# ------------------------------------------------------------------ #
#  Blood / fluid particle factories
# ------------------------------------------------------------------ #

BLOOD_COLORS: dict[str, tuple[int, int, int] | None] = {
    "red":       DRIED_BLOOD,
    "bone_dust": BONE_PALE,
    "ectoplasm": COLDBELL_LIGHT,
    "ichor":     DEEP_PURPLE,
    "verdigris": VERDANT_MID,
    "none":      None,
}


def make_blood_particles(
        screen_x: int,
        screen_y: int,
        color: tuple,
        attacker_screen_x: int,
        attacker_screen_y: int,
        count: int = 10,
        speed_range: tuple[float, float] = (80.0, 260.0),
        size_range:  tuple[float, float] = (2.0, 4.5),
        lifetime_range: tuple[float, float] = (0.35, 0.75),
) -> list[Particle]:
    """
    Screen-space burst of square pixels spraying away from the attacker.
    color: (r, g, b) tuple — resolve from BLOOD_COLORS before calling.
    Spray is a directional cone (~±50°) in the impact direction.
    Squares fall with gravity (update loop applies vy bias via shape="square").
    Returns empty list if color is None.
    Optional params allow crit hits to use wider speed/size/lifetime ranges.
    """
    if color is None:
        return []
    r, g, b = color

    rng = random.Random()

    # Impact direction: from attacker toward defender
    impact_dx = screen_x - attacker_screen_x
    impact_dy = screen_y - attacker_screen_y
    impact_len = math.sqrt(impact_dx ** 2 + impact_dy ** 2)
    if impact_len < 1:
        base_angle = rng.uniform(0, 2 * math.pi)
    else:
        base_angle = math.atan2(impact_dy / impact_len,
                                impact_dx / impact_len)

    SPREAD = math.radians(50)   # ±50° cone
    smin, smax = speed_range
    zmin, zmax = size_range
    lmin, lmax = lifetime_range

    particles = []
    for i in range(count):
        angle = base_angle + rng.uniform(-SPREAD, SPREAD)
        speed = rng.uniform(smin, smax)
        if i < 3:
            speed *= 1.8   # fast outlier drops
        lt = rng.uniform(lmin, lmax)
        particles.append(Particle(
            x=float(screen_x) + rng.uniform(-3, 3),
            y=float(screen_y) + rng.uniform(-3, 3),
            vx=math.cos(angle) * speed,
            vy=math.sin(angle) * speed,
            lifetime=lt, max_lifetime=lt,
            r=r, g=g, b=b, alpha=240,
            size=rng.uniform(zmin, zmax),
            space="screen", shape="square",
        ))
    return particles


def make_crit_impact_sparkles(
        screen_x: int,
        screen_y: int,
        blood_color: tuple[int, int, int],
        count: int = 5,
) -> list[Particle]:
    """
    Brief impact flash sparkles on a critical hit.
    Brightened version of the blood colour — very short lifetime.
    shape="sparkle" so they cross-flash rather than fall.
    """
    rng = random.Random()
    r, g, b = blood_color
    particles = []
    for _ in range(count):
        lt = rng.uniform(0.15, 0.35)
        particles.append(Particle(
            x=float(screen_x) + rng.uniform(-4, 4),
            y=float(screen_y) + rng.uniform(-4, 4),
            vx=rng.uniform(-15, 15),
            vy=rng.uniform(-15, 15),
            lifetime=lt, max_lifetime=lt,
            r=min(255, r + 80),
            g=min(255, g + 80),
            b=min(255, b + 80),
            alpha=240,
            size=rng.uniform(3.0, 5.5),
            space="screen", shape="sparkle",
        ))
    return particles


def make_resonance_ripple(
    wx: float,
    wy: float,
    rng: "random.Random | None" = None,
) -> list[Particle]:
    """Expanding ring of dim dots from waystone/bell.  Pool: ambient."""
    import math as _m
    particles = []
    for i in range(8):
        angle = (i / 8) * _m.tau
        particles.append(Particle(
            x=wx + 0.5,
            y=wy + 0.5,
            vx=_m.cos(angle) * 0.033,
            vy=_m.sin(angle) * 0.033,
            lifetime=1.5,
            max_lifetime=1.5,
            r=DEEP_TONGUE_COLOUR[0],
            g=DEEP_TONGUE_COLOUR[1],
            b=DEEP_TONGUE_COLOUR[2],
            alpha=120,
            size=1.0,
            space="world",
            shape="circle",
            pool="ambient",
        ))
    return particles


def make_ground_mist(
    wx: float,
    wy: float,
    rng: "random.Random",
) -> Particle:
    """Slow horizontal mist particle at terrain level.  Pool: ambient."""
    return Particle(
        x=wx + rng.uniform(0, 1),
        y=wy + rng.uniform(0.6, 1.0),
        vx=rng.uniform(0.005, 0.015) * rng.choice([-1, 1]),
        vy=rng.uniform(-0.002, 0.002),
        lifetime=rng.uniform(3.0, 5.0),
        max_lifetime=5.0,
        r=GROUND_MIST[0],
        g=GROUND_MIST[1],
        b=GROUND_MIST[2],
        alpha=60,
        size=rng.uniform(1.5, 2.5),
        space="world",
        shape="circle",
        pool="ambient",
    )


def make_dust_mote(
    wx: float,
    wy: float,
    rng: "random.Random",
) -> Particle:
    """Slow upward dust mote in abandoned building interiors.  Pool: ambient."""
    return Particle(
        x=wx + rng.uniform(0, 1),
        y=wy + rng.uniform(0, 1),
        vx=rng.uniform(-0.003, 0.003),
        vy=-rng.uniform(0.005, 0.012),
        lifetime=rng.uniform(2.0, 3.0),
        max_lifetime=3.0,
        r=DUST_MOTE[0],
        g=DUST_MOTE[1],
        b=DUST_MOTE[2],
        alpha=50,
        size=1.0,
        space="world",
        shape="circle",
        pool="ambient",
    )


def make_corruption_wisp(
    wx: float,
    wy: float,
    exposure: float,
    rng: "random.Random",
) -> Particle:
    """Dark purple wisp orbiting the player.  Pool: ambient.

    Orbit speed and alpha scale with resonance_exposure (0.5–1.5).
    """
    import math as _m
    angle = rng.uniform(0, _m.tau)
    orbit_r = 1.5
    speed = 0.02 + (exposure - 0.5) * 0.04  # faster at higher exposure
    alpha = int(40 + (exposure - 0.5) * 100)
    alpha = min(160, max(40, alpha))
    return Particle(
        x=wx + 0.5 + orbit_r * _m.cos(angle),
        y=wy + 0.5 + orbit_r * _m.sin(angle),
        vx=-_m.sin(angle) * speed,
        vy=_m.cos(angle) * speed,
        lifetime=rng.uniform(1.0, 1.8),
        max_lifetime=1.8,
        r=CORRUPTION_WISP[0],
        g=CORRUPTION_WISP[1],
        b=CORRUPTION_WISP[2],
        alpha=alpha,
        size=rng.uniform(1.0, 2.0),
        space="world",
        shape="circle",
        pool="ambient",
    )


def _make_particle(
        emitter: ParticleEmitter,
        viewport_w: int,
        viewport_h: int,
        zoom: int,
) -> "Particle | None":
    """Called by ParticleSystem for rate-based emitters."""
    _ = emitter, viewport_w, viewport_h, zoom   # no rate-based emitters currently
    return None


# ------------------------------------------------------------------ #
#  Weather → emitter wiring
# ------------------------------------------------------------------ #

_WEATHER_EMITTER_IDS = frozenset()   # rain/snow use tile-layer overlay in renderer


def update_weather_emitters(engine) -> None:
    """
    Sync particle emitters to current weather state.
    Called once per frame. Preserves emitter accumulators.
    """
    state     = engine.weather.state
    intensity = engine.weather.intensity
    ps        = engine.particle_system

    # Rain, bone_snow — handled by tile-layer overlay in renderer (no emitters)
    # fog / forgetting_fog — handled by vignette overlay only
    # Nothing to do here for weather emitters currently.
    _ = state, intensity, ps  # silence linter


# ------------------------------------------------------------------ #
#  Fog vignette overlay
# ------------------------------------------------------------------ #

_FOG_CACHE_THRESHOLD = 0.02   # rebuild if intensity drifts more than this
_FOG_SCALE           = 4      # work at 1/FOG_SCALE resolution, smoothscale up


def _build_fog_surface(
        w: int,
        h: int,
        intensity: float,
        fog_type: str,
        effective_fov: int = 8,
        tile_w: int = 24,
        tile_h: int = 24,
        centre_x: int = -1,
        centre_y: int = -1,
) -> pygame.Surface:
    """
    Build a smooth radial fog vignette at 1/FOG_SCALE resolution,
    t^2.2 eased, then smoothscale to full size.
    Clear radius matches the player's effective FOV in pixels.
    centre_x/y: player screen pos (viewport-relative pixels).
    Defaults to surface centre if -1.
    """
    sw = max(1, w // _FOG_SCALE)
    sh = max(1, h // _FOG_SCALE)

    if fog_type == "forgetting_fog":
        r_base, g_base, b_base = 227, 230, 255   # GHOST_WHITE — spirit-light blue-white
        fov_shrink = 0.75  # encroaches further than normal fog
    else:
        r_base, g_base, b_base = 218, 224, 234   # FROST_WHITE — cold grey-white
        fov_shrink = 1.0

    # Centre: player screen position scaled to small surface, or fallback to centre
    if centre_x >= 0 and centre_y >= 0:
        cx = centre_x / _FOG_SCALE
        cy = centre_y / _FOG_SCALE
    else:
        cx = sw / 2.0
        cy = sh / 2.0

    # FOV radius in scaled-surface pixels.
    # Multi-segment strength ramp for additive blending.
    # Surface stores premultiplied fog colour (fog_rgb × strength/255) in RGB,
    # no alpha needed — BLEND_RGBA_ADD adds raw RGB channels to destination:
    #   inside s45          → strength 0    (inner area completely unaffected)
    #   s45 → s70           → cubic 0→160  (fog brightens rapidly toward edge)
    #   s70 → s90           → linear 160→230 (dense luminous haze)
    #   beyond s90          → flat 245     (world lost in fog colour)
    fov_px_small = (effective_fov * min(tile_w, tile_h)) / _FOG_SCALE * fov_shrink
    s45 = fov_px_small * 0.45
    s70 = fov_px_small * 0.70
    s90 = fov_px_small * 0.90

    # Plain surface — no SRCALPHA. RGB carries premultiplied fog colour.
    # BLEND_RGBA_ADD ignores per-pixel alpha; strength is baked into RGB.
    small = pygame.Surface((sw, sh))

    try:
        import numpy as np
        xs   = np.arange(sw, dtype=np.float32)
        ys   = np.arange(sh, dtype=np.float32)
        dx   = xs[:, None] - cx
        dy   = ys[None, :] - cy
        dist = np.sqrt(dx * dx + dy * dy)

        # Angular noise — ragged organic boundary instead of perfect circle.
        # Sum of sines at different frequencies; no external library needed.
        angle = np.arctan2(dy, dx)          # (sw, sh) array of angles -π..π
        noise = (
            np.sin(angle * 3.7 + 1.1) * 0.35 +
            np.sin(angle * 7.1 + 2.3) * 0.20 +
            np.sin(angle * 13.3 + 0.7) * 0.10
        )                                   # roughly -0.65 to +0.65
        # Perturb: shrink or expand the effective distance by noise
        pdist = dist / np.maximum(0.001, 1.0 + noise * 0.25)

        # Zone 2: cubic 0→160 over s45..s70
        t2 = np.clip((pdist - s45) / max(0.001, s70 - s45), 0.0, 1.0) ** 3
        # Zone 3: linear 160→230 over s70..s90
        t3 = np.clip((pdist - s70) / max(0.001, s90 - s70), 0.0, 1.0)

        strength = np.where(pdist <= s45,  0.0,
                   np.where(pdist <= s70,  160.0 * t2,
                   np.where(pdist <= s90,  160.0 + 70.0 * t3,
                                           245.0)))
        strength = np.clip(strength * intensity, 0.0, 245.0)

        # Premultiply: baked fog colour = fog_rgb × strength / 255
        pix = pygame.surfarray.pixels3d(small)
        pix[:, :, 0] = np.clip(r_base * strength / 255.0, 0, 255).astype(np.uint8)
        pix[:, :, 1] = np.clip(g_base * strength / 255.0, 0, 255).astype(np.uint8)
        pix[:, :, 2] = np.clip(b_base * strength / 255.0, 0, 255).astype(np.uint8)
        del pix
    except Exception:
        # Pure Python fallback
        for px in range(sw):
            for py in range(sh):
                ddx = px - cx
                ddy = py - cy
                d    = math.sqrt(ddx * ddx + ddy * ddy)
                ang  = math.atan2(ddy, ddx)
                noise_v = (
                    math.sin(ang * 3.7 + 1.1) * 0.35 +
                    math.sin(ang * 7.1 + 2.3) * 0.20 +
                    math.sin(ang * 13.3 + 0.7) * 0.10
                )
                pd = d / max(0.001, 1.0 + noise_v * 0.25)
                if pd <= s45:
                    s = 0.0
                elif pd <= s70:
                    s = 160.0 * min(1.0, (pd - s45) / max(0.001, s70 - s45)) ** 3
                elif pd <= s90:
                    s = 160.0 + 70.0 * min(1.0, (pd - s70) / max(0.001, s90 - s70))
                else:
                    s = 245.0
                s = min(245.0, s * intensity)
                small.set_at((px, py), (
                    int(r_base * s / 255.0),
                    int(g_base * s / 255.0),
                    int(b_base * s / 255.0),
                ))

    return pygame.transform.smoothscale(small, (w, h))


def draw_fog_vignette(
        surf: pygame.Surface,
        intensity: float,
        fog_type: str = "fog",
        rect: "pygame.Rect | None" = None,
        engine=None,
        effective_fov: int = 8,
        tile_w: int = 24,
        tile_h: int = 24,
        centre_x: int = -1,
        centre_y: int = -1,
) -> None:
    """
    Smooth radial fog overlay — transparent at centre (player pos), opaque at edges.
    Clear radius derived from effective_fov × tile pixel size.
    centre_x/y: player screen pos relative to the viewport (not full screen).
    Cached on engine; rebuilds when player moves more than half a tile.
    rect: the viewport area to draw onto (defaults to full surface).
    engine: Engine instance for caching (optional but strongly recommended).
    """
    if rect is None:
        w, h = surf.get_size()
        ox, oy = 0, 0
    else:
        w, h = rect.width, rect.height
        ox, oy = rect.x, rect.y

    if engine is not None:
        cached        = getattr(engine, "_fog_surface",           None)
        cached_intens = getattr(engine, "_fog_surface_intensity", -1.0)
        cached_type   = getattr(engine, "_fog_surface_type",      "")
        cached_size   = getattr(engine, "_fog_surface_size",      (0, 0))
        cached_fov    = getattr(engine, "_fog_surface_fov",       -1)
        cached_cx     = getattr(engine, "_fog_surface_cx",        -1)
        cached_cy     = getattr(engine, "_fog_surface_cy",        -1)

        # Rebuild when player moves more than half a tile (avoids per-frame rebuild)
        centre_moved = (
            abs(centre_x - cached_cx) > tile_w // 2 or
            abs(centre_y - cached_cy) > tile_h // 2
        )

        if (cached is None
                or cached_type != fog_type
                or abs(cached_intens - intensity) > _FOG_CACHE_THRESHOLD
                or cached_size != (w, h)
                or cached_fov != effective_fov
                or centre_moved):
            engine._fog_surface = _build_fog_surface(
                w, h, intensity, fog_type, effective_fov, tile_w, tile_h,
                centre_x, centre_y)
            engine._fog_surface_intensity = intensity
            engine._fog_surface_type      = fog_type
            engine._fog_surface_size      = (w, h)
            engine._fog_surface_fov       = effective_fov
            engine._fog_surface_cx        = centre_x
            engine._fog_surface_cy        = centre_y

        surf.blit(engine._fog_surface, (ox, oy),
                  special_flags=pygame.BLEND_RGBA_ADD)
        return

    # No engine — build each frame (fallback, not ideal)
    surf.blit(_build_fog_surface(w, h, intensity, fog_type,
                                 effective_fov, tile_w, tile_h,
                                 centre_x, centre_y), (ox, oy),
              special_flags=pygame.BLEND_RGBA_ADD)
