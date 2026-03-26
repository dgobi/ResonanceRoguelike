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
    """

    TARGET_FPS  = 60
    PERF_WINDOW = 30          # frames for rolling average
    SCALE_STEP  = 0.10        # 10% cap adjustment per trigger
    MAX_PARTICLES = 800       # absolute hard ceiling
    _cap: float = 500.0       # current soft cap (adaptive)

    def __init__(self) -> None:
        self.particles:   list[Particle]            = []
        self.emitters:    dict[str, ParticleEmitter] = {}
        self._frame_times: list[float]              = []
        self._last_frame:  float                    = time.monotonic()
        self._cap_cooldown: float                   = 0.0
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

    def emit(self, particle: Particle) -> None:
        """Directly add a particle. Respects cap."""
        if len(self.particles) < int(self._cap):
            self.particles.append(particle)

    def emit_burst(self, particles: list[Particle]) -> None:
        """Add multiple particles at once."""
        remaining = int(self._cap) - len(self.particles)
        for p in particles[:remaining]:
            self.particles.append(p)

    def clear(self) -> None:
        """Remove all active particles and emitters."""
        self.particles.clear()
        self.emitters.clear()

    # ── Update (call every frame) ──────────────────────────────────

    def update(self, dt: float, viewport_w: int, viewport_h: int,
               zoom: int, scroll_x: int = 0, scroll_y: int = 0) -> None:
        """
        dt: seconds since last frame.
        viewport_w/h: game map area in pixels.
        zoom: current zoom level (tiles to pixels).
        """
        self._track_performance(dt)
        self._cap_cooldown = max(0.0, self._cap_cooldown - dt)

        # Emit from active emitters
        for emitter in self.emitters.values():
            if not emitter.active or emitter.rate <= 0:
                continue
            emitter._accumulator += emitter.rate * dt
            while emitter._accumulator >= 1.0:
                emitter._accumulator -= 1.0
                p = _make_particle(emitter, viewport_w, viewport_h, zoom)
                if p and len(self.particles) < int(self._cap):
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

    def _track_performance(self, dt: float) -> None:
        fps = 1.0 / dt if dt > 0 else 999.0
        self._frame_times.append(fps)
        if len(self._frame_times) > self.PERF_WINDOW:
            self._frame_times.pop(0)
        if len(self._frame_times) < self.PERF_WINDOW:
            return
        if self._cap_cooldown > 0:
            return
        avg_fps = sum(self._frame_times) / len(self._frame_times)
        if avg_fps < 50 and self._cap > 100:
            self._cap *= (1.0 - self.SCALE_STEP)
            self._cap_cooldown = 5.0
            print(f"[particles] cap reduced to {self._cap:.0f}"
                  f" (avg {avg_fps:.1f} fps)")
        elif avg_fps > 65 and self._cap < self.MAX_PARTICLES:
            self._cap = min(self.MAX_PARTICLES,
                            self._cap * (1.0 + self.SCALE_STEP))
            self._cap_cooldown = 5.0

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
        if not self.particles:
            return

        # Lazily create / resize scratch surface
        surf_w, surf_h = surf.get_size()
        if self._scratch is None or self._scratch_size != (surf_w, surf_h):
            self._scratch = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
            self._scratch_size = (surf_w, surf_h)
        self._scratch.fill((0, 0, 0, 0))

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
                # Screen-space: viewport-relative coords added to viewport origin
                sx = int(map_origin_x + p.x)
                sy = int(map_origin_y + p.y)

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
    )


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
        r_base, g_base, b_base = 180, 195, 240   # strong blue-white
        max_alpha = 240.0
    else:
        r_base, g_base, b_base = 210, 215, 220
        max_alpha = 200.0

    # Centre: player screen position scaled to small surface, or fallback to centre
    if centre_x >= 0 and centre_y >= 0:
        cx = centre_x / _FOG_SCALE
        cy = centre_y / _FOG_SCALE
    else:
        cx = sw / 2.0
        cy = sh / 2.0

    # max_dist from the chosen centre to the farthest corner
    corners = [
        (0 - cx, 0 - cy),
        (sw - cx, 0 - cy),
        (0 - cx, sh - cy),
        (sw - cx, sh - cy),
    ]
    max_dist = max(math.sqrt(dx * dx + dy * dy) for dx, dy in corners)
    # Clear radius derived from FOV: effective_fov tiles × min tile dimension,
    # scaled down to the small surface space.
    fov_px_small = (effective_fov * min(tile_w, tile_h)) / _FOG_SCALE
    clear_dist = min(fov_px_small, max_dist * 0.95)
    # Forgetting fog encroaches further — smaller clear centre
    if fog_type == "forgetting_fog":
        clear_dist *= 0.75
    denom = max(0.001, max_dist - clear_dist)

    small = pygame.Surface((sw, sh), pygame.SRCALPHA)

    try:
        import numpy as np
        xs   = np.arange(sw, dtype=np.float32)
        ys   = np.arange(sh, dtype=np.float32)
        dx   = xs[:, None] - cx
        dy   = ys[None, :] - cy
        dist = np.sqrt(dx * dx + dy * dy)
        t    = (dist - clear_dist) / denom
        t    = np.clip(t, 0.0, 1.0) ** 2.2
        alpha_arr = (t * max_alpha * intensity).astype(np.uint8)
        pix = pygame.surfarray.pixels3d(small)
        pix[:, :, 0] = r_base
        pix[:, :, 1] = g_base
        pix[:, :, 2] = b_base
        del pix
        a_ch = pygame.surfarray.pixels_alpha(small)
        a_ch[:, :] = alpha_arr
        del a_ch
    except Exception:
        # Pure Python fallback
        for px in range(sw):
            for py in range(sh):
                ddx = px - cx
                ddy = py - cy
                dist = math.sqrt(ddx * ddx + ddy * ddy)
                if dist <= clear_dist:
                    continue
                t = ((dist - clear_dist) / denom) ** 2.2
                t = max(0.0, min(1.0, t))
                small.set_at((px, py),
                             (r_base, g_base, b_base, int(t * max_alpha * intensity)))

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

        surf.blit(engine._fog_surface, (ox, oy))
        return

    # No engine — build each frame (fallback, not ideal)
    surf.blit(_build_fog_surface(w, h, intensity, fog_type,
                                 effective_fov, tile_w, tile_h,
                                 centre_x, centre_y), (ox, oy))
