# engine/debug.py
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.engine import Engine



class DebugOverlay:
    """
    Debug tools. Only active when config.DEBUG_MODE = True.
    All F-key handlers live here.
    The engine checks debug.handle_key() before normal input.
    """

    def __init__(self) -> None:
        self.show_overlay:           bool = False
        self.show_fov_viz:           bool = False
        self.show_submap_highlights: bool = False
        self._font: pygame.font.Font | None = None
        self._input_mode:    str  = ""
        self._input_buffer:  str  = ""
        self._input_prompt:  str  = ""

    def init(self) -> None:
        self._font = pygame.font.SysFont("monospace", 13)

    # ------------------------------------------------------------------ #
    #  Key handling — returns True if the key was consumed
    # ------------------------------------------------------------------ #

    def handle_key(self, key: int, engine: Engine) -> bool:
        """
        Handle a keypress. Returns True if consumed by debug system.
        Call this BEFORE normal input handling.
        """
        if self._input_mode:
            return self._handle_input(key, engine)

        if key == pygame.K_F1:
            self.show_overlay = not self.show_overlay
            return True

        if key == pygame.K_F2:
            self.show_fov_viz = not self.show_fov_viz
            return True

        if key == pygame.K_F3:
            self._reveal_local_map(engine)
            return True

        if key == pygame.K_F4:
            self._reveal_world_map_submaps(engine)
            return True

        if key == pygame.K_F5:
            self._teleport_to_nearest_submap(engine)
            return True

        if key == pygame.K_F6:
            self._start_input(
                "set_time",
                "Set hour (0-23): "
            )
            return True

        if key == pygame.K_F7:
            self._start_input(
                "set_values",
                "Set values — hunger,thirst,corruption (0.0-1.0 each, e.g. 0.5,0.8,0.3): "
            )
            return True

        if key == pygame.K_F8:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_SHIFT:
                engine.player_invincible = not engine.player_invincible
                state = "ON" if engine.player_invincible else "OFF"
                engine.log.add(f"[DEBUG] Invincibility {state}.", (150, 150, 100))
            else:
                self._force_regen(engine)
            return True

        if key == pygame.K_F9:
            self._dump_state(engine)
            return True

        if key == pygame.K_F10:
            self._start_input(
                "teleport",
                "Teleport to chunk wx,wy (e.g. 3,7): "
            )
            return True
        
        if key == pygame.K_F11:
            import shutil
            from pathlib import Path
            save_path = Path("saves")
            if save_path.exists():
                shutil.rmtree(save_path)
            engine.log.add(
                "[DEBUG] Save data cleared. Wipe complete.",
                (200, 80, 80),
            )
            return True
        
        if key == pygame.K_F12:
            self._start_input(
                "remap_tile",
                "Remap tile: tile_id sheet col row (e.g. floor obj 0 15): "
            )
            return True

        if key == pygame.K_BACKQUOTE:
            self._start_input("debug_cmd", "Debug> ")
            return True

        return False

    # ------------------------------------------------------------------ #
    #  Text input handling for commands that need parameters
    # ------------------------------------------------------------------ #

    def _start_input(self, mode: str, prompt: str) -> None:
        self._input_mode   = mode
        self._input_buffer = ""
        self._input_prompt = prompt

    def _handle_input(self, key: int, engine: Engine) -> bool:
        if key == pygame.K_ESCAPE:
            self._input_mode   = ""
            self._input_buffer = ""
            return True

        if key == pygame.K_RETURN:
            self._execute_input(engine)
            self._input_mode   = ""
            self._input_buffer = ""
            return True

        if key == pygame.K_BACKSPACE:
            self._input_buffer = self._input_buffer[:-1]
            return True

        # Append printable characters
        char = self._key_to_char(key)
        if char:
            self._input_buffer += char
        return True

    def _execute_input(self, engine: Engine) -> None:
        buf = self._input_buffer.strip()

        if self._input_mode == "teleport":
            try:
                parts = buf.split(",")
                wx, wy = int(parts[0].strip()), int(parts[1].strip())
                if engine.world_map.in_bounds(wx, wy):
                    from generation.region_gen import generate_region
                    from config import MAP_WIDTH, MAP_HEIGHT
                    chunk = engine.world_map.get(wx, wy)
                    if chunk:
                        new_map, (sx, sy) = generate_region(
                            chunk, MAP_WIDTH, MAP_HEIGHT,
                            engine.data.terrain
                        )
                        sx, sy = engine._find_walkable_near(new_map, sx, sy)
                        engine.player.x  = sx
                        engine.player.y  = sy
                        engine.local_map = new_map
                        engine.world_x   = wx
                        engine.world_y   = wy
                        engine.world_map.mark_explored_radius(wx, wy, radius=2)
                        chunk.visited    = True
                        engine.entities  = [engine.player]
                        engine._update_fov()
                        engine.log.add(
                            f"[DEBUG] Teleported to chunk ({wx},{wy}).",
                            (150, 150, 100)
                        )
                else:
                    engine.log.add(
                        f"[DEBUG] Chunk ({wx},{wy}) out of bounds.",
                        (200, 80, 80)
                    )
            except Exception as e:
                engine.log.add(f"[DEBUG] Teleport failed: {e}", (200, 80, 80))

        elif self._input_mode == "set_time":
            try:
                hour = float(buf)
                hour = max(0.0, min(23.9, hour))
                from engine.world_time import TURNS_PER_HOUR, TURNS_PER_DAY
                current_day_start = (engine.world_time.turn
                                     // TURNS_PER_DAY) * TURNS_PER_DAY
                engine.world_time.turn = (current_day_start
                                          + int(hour * TURNS_PER_HOUR))
                engine._update_fov()
                engine.log.add(
                    f"[DEBUG] Time set to {engine.world_time.time_string}.",
                    (150, 150, 100)
                )
            except Exception as e:
                engine.log.add(f"[DEBUG] Set time failed: {e}", (200, 80, 80))

        elif self._input_mode == "set_values":
            try:
                parts  = buf.split(",")
                hunger = float(parts[0].strip())
                thirst = float(parts[1].strip())
                corrupt= float(parts[2].strip())

                needs = getattr(engine.player, "needs", None)
                corr  = getattr(engine.player, "corruption", None)

                if needs:
                    needs.hunger = max(0.0, min(1.0, hunger))
                    needs.thirst = max(0.0, min(1.0, thirst))
                if corr:
                    corr.value   = max(0.0, min(1.0, corrupt))

                engine._update_fov()
                engine.log.add(
                    f"[DEBUG] Set hunger={hunger:.2f} "
                    f"thirst={thirst:.2f} corruption={corrupt:.2f}.",
                    (150, 150, 100)
                )
            except Exception as e:
                engine.log.add(
                    f"[DEBUG] Set values failed: {e}", (200, 80, 80)
                )

        elif self._input_mode == "debug_cmd":
            parts = buf.strip().split()
            if not parts:
                pass
            elif parts[0] == "spawn_creature" and len(parts) > 1:
                creature_id = parts[1]
                px, py = engine.player.x, engine.player.y
                spawned = False
                for dx, dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]:
                    tx, ty = px + dx, py + dy
                    if (engine.local_map.in_bounds(tx, ty)
                            and engine.local_map.walkable[tx, ty]):
                        creature = engine.creature_factory.spawn(creature_id, tx, ty)
                        if creature:
                            engine.entities.append(creature)
                            engine.log.add(
                                f"[DEBUG] Spawned {creature_id} at ({tx},{ty}).",
                                (150, 150, 100),
                            )
                        else:
                            engine.log.add(
                                f"[DEBUG] Unknown creature: {creature_id}.",
                                (200, 80, 80),
                            )
                        spawned = True
                        break
                if not spawned:
                    engine.log.add("[DEBUG] No adjacent walkable tile.", (200, 80, 80))

            elif parts[0] == "spawn_item" and len(parts) > 1:
                item_id = parts[1]
                px, py  = engine.player.x, engine.player.y
                item    = engine.item_factory.create(item_id, px, py)
                if item:
                    engine.entities.append(item)
                    engine.log.add(
                        f"[DEBUG] Spawned {item_id} at ({px},{py}).",
                        (150, 150, 100),
                    )
                else:
                    engine.log.add(
                        f"[DEBUG] Unknown item: {item_id}.",
                        (200, 80, 80),
                    )
            else:
                engine.log.add(
                    f"[DEBUG] Unknown command '{parts[0]}'. "
                    "Use: spawn_creature <id>  spawn_item <id>",
                    (200, 80, 80),
                )

        elif self._input_mode == "remap_tile":
            try:
                parts    = buf.split()
                tile_id  = parts[0]
                sheet_id = parts[1]
                col      = int(parts[2])
                row      = int(parts[3])
                sr       = getattr(engine, "sprite_registry", None)
                if sr:
                    sr.remap(tile_id, sheet_id, col, row)
                    engine.log.add(
                        f"[DEBUG] Remapped {tile_id} → {sheet_id} "
                        f"({col},{row})",
                        (150, 150, 100),
                    )
                else:
                    engine.log.add(
                        "[DEBUG] No sprite registry loaded.",
                        (200, 80, 80),
                    )
            except Exception as e:
                engine.log.add(f"[DEBUG] Remap failed: {e}", (200, 80, 80))

    @staticmethod
    def _key_to_char(key: int) -> str:
        """Convert pygame key code to character for text input."""
        if pygame.K_a <= key <= pygame.K_z:
            return chr(key)
        if pygame.K_0 <= key <= pygame.K_9:
            return chr(key)
        if key == pygame.K_PERIOD:
            return "."
        if key == pygame.K_COMMA:
            return ","
        if key == pygame.K_MINUS or key == pygame.K_UNDERSCORE:
            return "_"
        if key == pygame.K_SPACE:
            return " "
        return ""

    # ------------------------------------------------------------------ #
    #  Actions
    # ------------------------------------------------------------------ #

    def _reveal_local_map(self, engine: Engine) -> None:
        engine.local_map.tiles["explored"][:] = True
        engine.log.add("[DEBUG] Local map revealed.", (150, 150, 100))

    def _reveal_world_map_submaps(self, engine: Engine) -> None:
        for chunk in engine.world_map.chunks.values():
            chunk.explored = True
        self.show_submap_highlights = not self.show_submap_highlights
        from engine.engine import GameMode
        engine.mode = GameMode.OVERMAP
        engine.overmap_cursor_x = engine.world_x
        engine.overmap_cursor_y = engine.world_y
        engine.overmap_cam_x    = engine.world_x
        engine.overmap_cam_y    = engine.world_y
        status = "on" if self.show_submap_highlights else "off"
        engine.log.add(
            f"[DEBUG] World map revealed. SubMap highlights {status}.",
            (150, 150, 100),
        )

    def _teleport_to_nearest_submap(self, engine: Engine) -> None:
        """Teleport to the nearest chunk that has a SubMap entry."""
        from config import MAP_WIDTH, MAP_HEIGHT

        candidates = []
        for (wx, wy), chunk in engine.world_map.chunks.items():
            if chunk.submaps:
                dist = abs(wx - engine.world_x) + abs(wy - engine.world_y)
                candidates.append((dist, wx, wy, chunk))

        if not candidates:
            engine.log.add("[DEBUG] No submaps found in world.", (200, 80, 80))
            return

        candidates.sort()
        _, wx, wy, chunk = candidates[0]

        from generation.region_gen import generate_region
        local_map, _ = generate_region(
            chunk, MAP_WIDTH, MAP_HEIGHT, engine.data.terrain
        )

        # Place player near the submap entrance if a submap_link exists
        spawn_x, spawn_y = MAP_WIDTH // 2, MAP_HEIGHT // 2
        if local_map.submap_links:
            # Use first registered stairs_down tile
            sx, sy = next(iter(local_map.submap_links))
            spawn_x, spawn_y = engine._find_walkable_near(local_map, sx, sy)
        else:
            spawn_x, spawn_y = engine._find_walkable_near(
                local_map, MAP_WIDTH // 2, MAP_HEIGHT // 2
            )

        engine.world_x       = wx
        engine.world_y       = wy
        engine.local_map     = local_map
        engine.entities      = [engine.player]
        engine.player.x      = spawn_x
        engine.player.y      = spawn_y
        chunk.visited        = True
        engine.world_map.mark_explored_radius(wx, wy, radius=2)
        engine._update_fov()
        name = chunk.submaps[0].name if chunk.submaps[0].name else chunk.submaps[0].submap_type
        engine.log.add(
            f"[DEBUG] Teleported to submap chunk ({wx},{wy}): {name}",
            (150, 150, 100),
        )

    def _force_regen(self, engine: Engine) -> None:
        from generation.region_gen import generate_region
        from config import MAP_WIDTH, MAP_HEIGHT
        chunk = engine.world_map.get(engine.world_x, engine.world_y)
        if chunk:
            chunk.seed += 1   # increment seed for different layout
            new_map, (sx, sy) = generate_region(
                chunk, MAP_WIDTH, MAP_HEIGHT, engine.data.terrain
            )
            sx, sy = engine._find_walkable_near(new_map, sx, sy)
            engine.player.x  = sx
            engine.player.y  = sy
            engine.local_map = new_map
            engine.entities  = [engine.player]
            engine._update_fov()
            engine.log.add(
                f"[DEBUG] Chunk regenerated (seed {chunk.seed}).",
                (150, 150, 100)
            )

    def _dump_state(self, engine: Engine) -> None:
        chunk = engine.world_map.get(engine.world_x, engine.world_y)
        needs = getattr(engine.player, "needs", None)
        corr  = getattr(engine.player, "corruption", None)

        print("\n=== DEBUG STATE DUMP ===")
        print(f"World pos:    ({engine.world_x}, {engine.world_y})")
        print(f"Local pos:    ({engine.player.x}, {engine.player.y})")
        print(f"Region type:  {chunk.region_type.value if chunk else 'N/A'}")
        print(f"Zones:        {chunk.zones if chunk else 'N/A'}")
        print(f"Edges:        {chunk.edges if chunk else 'N/A'}")
        print(f"Turn:         {engine.world_time.turn}")
        print(f"Time:         {engine.world_time.time_string}")
        print(f"Moon:         {engine.world_time.moon_phase_name}")
        print(f"Sun:          {engine.world_time.sun_intensity:.3f}")
        print(f"Moon int:     {engine.world_time.moon_intensity:.3f}")
        if needs:
            print(f"Hunger:       {needs.hunger:.4f} ({needs.hunger_state})")
            print(f"Thirst:       {needs.thirst:.4f} ({needs.thirst_state})")
        if corr:
            print(f"Corruption:   {corr.value:.4f} ({corr.state})")
        lm = engine.local_map.light_map
        px, py = engine.player.x, engine.player.y
        print(f"Light at @:   {lm[px, py]}")
        print(f"Entities:     {len(engine.entities)}")
        print(f"Explored:     {engine.local_map.tiles['explored'].sum()} tiles")
        print(f"Submap ID:    {engine.current_submap_id or 'surface'}")
        if chunk and chunk.submaps:
            print(f"Submaps ({len(chunk.submaps)}):")
            for sm in chunk.submaps:
                print(f"  [{sm.submap_id}] type={sm.submap_type}"
                      f" layout={sm.layout_id or 'bsp'}"
                      f" generated={sm.generated}"
                      f" entry=({sm.entry_x},{sm.entry_y})"
                      f" depth={sm.depth}")
        myth = engine.world_myth
        if myth:
            print(f"WorldMyth:")
            print(f"  Age:       {myth.age_name}")
            print(f"  Sundering: {myth.sundering_epithet}")
            print(f"  Shape:     {myth.myth_shape}")
            print(f"  God:       {myth.prominent_god}")
            print(f"  Locus:     {myth.locus_name} at ({myth.locus_wx},{myth.locus_wy})")
            print(f"  Factions:  {myth.faction_a} vs {myth.faction_b}")
        print("========================\n")
        engine.log.add("[DEBUG] State dumped to console.", (150, 150, 100))

    # ------------------------------------------------------------------ #
    #  Overlay rendering
    # ------------------------------------------------------------------ #

    def render(
        self,
        screen:  pygame.Surface,
        engine:  Engine,
    ) -> None:
        """Render all active debug visuals onto screen."""
        if self.show_fov_viz:
            self._render_fov_viz(screen, engine)

        if self.show_overlay:
            self._render_overlay(screen, engine)

        if self._input_mode:
            self._render_input_prompt(screen)

    @staticmethod
    def _draw_rune_sigil(surf: pygame.Surface, cx: int, cy: int, size: int = 32) -> None:
        """Draw the debug registry sigil — asymmetric angular rune."""
        import math
        s = size / 32
        col_dim    = (30, 48, 80)
        col_mid    = (40, 72, 128)
        col_bright = (72, 120, 184)
        # Outer circle
        pygame.draw.circle(surf, col_dim, (cx, cy), int(30 * s), 1)
        # Inner dashed circle
        for i in range(24):
            if i % 3 == 2:
                continue
            a  = (i / 24) * 2 * math.pi
            px = int(cx + 20 * s * math.cos(a))
            py = int(cy + 20 * s * math.sin(a))
            pygame.draw.circle(surf, col_dim, (px, py), 1)
        # Vertical spine
        pygame.draw.line(surf, col_mid, (cx, int(cy - 28 * s)), (cx, int(cy + 28 * s)), 1)
        # Upper left arm
        pygame.draw.line(surf, col_mid, (cx, int(cy - 14 * s)), (int(cx - 20 * s), cy), 1)
        # Upper right arm (shorter)
        pygame.draw.line(surf, col_mid, (cx, int(cy - 14 * s)), (int(cx + 16 * s), int(cy - 6 * s)), 1)
        # Lower arm
        pygame.draw.line(surf, col_mid, (cx, int(cy + 12 * s)), (int(cx - 18 * s), int(cy + 20 * s)), 1)
        # Cross bar (offset from centre)
        pygame.draw.line(surf, col_dim, (int(cx - 14 * s), int(cy - 2 * s)), (int(cx + 16 * s), int(cy + 3 * s)), 1)
        # Tick marks
        pygame.draw.line(surf, col_mid, (int(cx - 4 * s), int(cy - 10 * s)), (cx, int(cy - 10 * s)), 1)
        pygame.draw.line(surf, col_mid, (int(cx - 4 * s), int(cy + 2 * s)),  (cx, int(cy + 2 * s)),  1)
        pygame.draw.line(surf, col_mid, (int(cx - 4 * s), int(cy + 14 * s)), (int(cx + 4 * s), int(cy + 14 * s)), 1)
        # Node dots
        pygame.draw.circle(surf, col_bright, (cx, int(cy - 28 * s)), 3)
        pygame.draw.circle(surf, col_mid,    (cx, int(cy - 14 * s)), 2)
        pygame.draw.circle(surf, col_mid,    (int(cx - 20 * s), cy), 2)
        pygame.draw.circle(surf, col_mid,    (cx, int(cy + 12 * s)), 2)
        # Bright accent lines
        pygame.draw.line(surf, col_bright, (cx, int(cy - 28 * s)), (cx, int(cy - 14 * s)), 2)
        pygame.draw.line(surf, col_bright, (cx, int(cy - 14 * s)), (int(cx - 20 * s), cy), 1)

    def _render_overlay(
        self,
        screen: pygame.Surface,
        engine: Engine,
    ) -> None:
        # Font access — prefer engine display fonts, fall back to monospace
        display   = getattr(engine, "display", None)
        fn_small  = getattr(display, "font_ui_small",      None) or self._font
        fn_bold   = getattr(display, "font_ui_bold",       None) or self._font
        fn_blarge = getattr(display, "font_ui_bold_large", None) or fn_bold
        if not fn_small:
            return

        sw, sh   = screen.get_width(), screen.get_height()
        VOID     = (7, 12, 29)
        STEEL    = (40, 96, 128)
        DIM      = (68, 99, 116)
        BRIGHT   = (140, 200, 200)
        RED_DIM  = (145, 58, 82)
        GREEN    = (93, 167, 93)
        SECTION  = (72, 120, 184)
        pad      = 14
        lh       = 16   # small line height
        sh_lh    = 18   # section heading height

        # Full-screen panel
        panel = pygame.Surface((sw, sh), pygame.SRCALPHA)
        panel.fill((*VOID, 230))
        pygame.draw.rect(panel, STEEL, (0, 0, sw, sh), 2)
        screen.blit(panel, (0, 0))

        # ── Header strip ────────────────────────────────────────────────
        SIG_CX, SIG_CY, SIG_R = 44, 44, 32
        self._draw_rune_sigil(screen, SIG_CX, SIG_CY, SIG_R)
        pygame.draw.line(screen, STEEL, (SIG_CX * 2 + 4, 0), (SIG_CX * 2 + 4, 88), 1)

        title = fn_blarge.render("DEBUG REGISTRY", True, STEEL)
        screen.blit(title, (SIG_CX * 2 + 14, pad))
        sub   = fn_small.render("engine/debug.py  ·  DEBUG_MODE = True", True, DIM)
        screen.blit(sub, (SIG_CX * 2 + 14, pad + 26))

        # Invincibility indicator
        inv   = getattr(engine, "player_invincible", False)
        dot_x = sw - pad - 8
        dot_y = pad + 8
        pygame.draw.circle(screen, GREEN if inv else (50, 60, 70), (dot_x, dot_y), 6)
        pygame.draw.circle(screen, STEEL, (dot_x, dot_y), 6, 1)
        inv_label = fn_small.render("INVINCIBLE" if inv else "mortal", True, GREEN if inv else DIM)
        screen.blit(inv_label, (dot_x - inv_label.get_width() - 10, dot_y - 6))

        header_h = 88
        pygame.draw.line(screen, STEEL, (0, header_h), (sw, header_h), 1)

        # ── Two-column key grid ──────────────────────────────────────────
        col_w   = (sw - pad * 3) // 2
        col1_x  = pad
        col2_x  = pad * 2 + col_w
        y1 = header_h + pad
        y2 = header_h + pad

        def draw_section(x: int, y: int, heading: str, rows: list[tuple[str, str]]) -> int:
            h = fn_bold.render(heading, True, SECTION)
            screen.blit(h, (x, y))
            y += sh_lh
            for key, desc in rows:
                k_surf = fn_small.render(key, True, BRIGHT)
                d_surf = fn_small.render(desc, True, DIM)
                screen.blit(k_surf, (x, y))
                screen.blit(d_surf, (x + 80, y))
                y += lh
            return y + 6

        y1 = draw_section(col1_x, y1, "NAVIGATION", [
            ("F2",        "FOV visualization overlay"),
            ("F3",        "Reveal full local map"),
            ("F4",        "SubMap highlights on overmap"),
            ("F10",       "Teleport to chunk coords"),
        ])
        y1 = draw_section(col1_x, y1, "INSPECTION", [
            ("F1",        "Toggle this overlay"),
            ("F9",        "Full state dump to terminal"),
            ("F12",       "Remap sprite tile at runtime"),
            ("Shift+F8",  "Toggle invincibility"),
        ])

        y2 = draw_section(col2_x, y2, "WORLD & TIME", [
            ("F5",        "Teleport to nearest SubMap"),
            ("F6",        "Set world time (0-23)"),
            ("F7",        "Set needs / corruption"),
            ("F8",        "Force chunk regeneration"),
        ])
        # Destructive section in red tint
        dest_y = y2
        h = fn_bold.render("DESTRUCTIVE", True, RED_DIM)
        screen.blit(h, (col2_x, dest_y))
        dest_y += sh_lh
        k = fn_small.render("F11", True, (188, 89, 96))
        d = fn_small.render("Wipe entire saves/ directory", True, (145, 80, 80))
        screen.blit(k, (col2_x, dest_y))
        screen.blit(d, (col2_x + 80, dest_y))
        dest_y += lh

        content_bottom = max(y1, dest_y) + pad

        # ── Console section ──────────────────────────────────────────────
        pygame.draw.line(screen, STEEL, (0, content_bottom), (sw, content_bottom), 1)
        cy = content_bottom + pad

        h = fn_bold.render("DEBUG CONSOLE", True, SECTION)
        screen.blit(h, (pad, cy))
        trig = fn_small.render("trigger: ` (backtick)", True, DIM)
        screen.blit(trig, (pad + h.get_width() + 20, cy + 2))
        cy += sh_lh

        cmds = [
            ("spawn_creature <id>", "Spawns creature on nearest adjacent walkable tile"),
            ("spawn_item <id>",     "Drops item at player's current position"),
        ]
        for cmd, desc in cmds:
            c = fn_small.render(cmd, True, BRIGHT)
            d_surf = fn_small.render(f"— {desc}", True, DIM)
            screen.blit(c,      (pad + 12, cy))
            screen.blit(d_surf, (pad + 12 + c.get_width() + 8, cy))
            cy += lh

        ids_c = fn_small.render(
            "creature IDs: bog_wraith  barrow_wight  hollow_knight  hollow_revenant  "
            "grave_thing  heath_stalker  briar_lurker  stone_lurker  plague_crow  highland_bandit",
            True, (50, 70, 90),
        )
        screen.blit(ids_c, (pad + 12, cy))
        cy += lh
        ids_i = fn_small.render(
            "item IDs: crude_blade  heavy_blade  binding_knife  dissolution_blade  "
            "leather_jack  leather_cap  tallow_torch  oil_lantern  crow_jerky  water_flask  moist_pebble",
            True, (50, 70, 90),
        )
        screen.blit(ids_i, (pad + 12, cy))
        cy += lh + pad

        # ── Footer status bar ────────────────────────────────────────────
        footer_y = sh - lh - pad - 4
        pygame.draw.line(screen, STEEL, (0, footer_y - 6), (sw, footer_y - 6), 1)

        chunk       = engine.world_map.get(engine.world_x, engine.world_y)
        corr        = getattr(engine.player, "corruption", None)
        submap_label = engine.current_submap_id or "surface"
        region_label = chunk.region_type.value if chunk else "?"
        corr_label   = corr.state if corr else "?"

        footer = fn_small.render(
            f"mode: {engine.mode.value}  |  submap: {submap_label}  |  "
            f"chunk: ({engine.world_x},{engine.world_y}) {region_label}  |  "
            f"corruption: {corr_label}  |  turn: {engine.world_time.turn}",
            True, DIM,
        )
        screen.blit(footer, (pad, footer_y))

    def _render_fov_viz(
        self,
        screen: pygame.Surface,
        engine: Engine,
    ) -> None:
        """Tint visible tiles green, FOV boundary cyan."""
        from engine.engine import GameMode
        if engine.mode != GameMode.LOCAL:
            return

        tw = engine.display.tile_width
        th = engine.display.tile_height

        # We need a viewport rect — approximate from screen and panel
        from config import STATUS_BAR_H, MSG_PANEL_W
        viewport_w = screen.get_width() - MSG_PANEL_W
        viewport_h = screen.get_height() - STATUS_BAR_H

        cam_x = engine.player.x - (viewport_w // tw) // 2
        cam_y = engine.player.y - (viewport_h // th) // 2
        cam_x = max(0, min(cam_x, engine.local_map.width  - viewport_w // tw))
        cam_y = max(0, min(cam_y, engine.local_map.height - viewport_h // th))

        tiles_x = viewport_w // tw + 2
        tiles_y = viewport_h // th + 2

        viz_surf = pygame.Surface((viewport_w, viewport_h), pygame.SRCALPHA)

        for tx in range(tiles_x):
            for ty in range(tiles_y):
                mx = tx + cam_x
                my = ty + cam_y
                if not engine.local_map.in_bounds(mx, my):
                    continue
                if engine.local_map.tiles[mx, my]["visible"]:
                    px_x = tx * tw
                    px_y = ty * th
                    pygame.draw.rect(
                        viz_surf, (0, 255, 0, 40),
                        (px_x, px_y, tw, th)
                    )

        screen.blit(viz_surf, (0, 0))

    def _render_input_prompt(self, screen: pygame.Surface) -> None:
        if not self._font:
            return
        text = f"{self._input_prompt}{self._input_buffer}_"
        surf = self._font.render(text, True, (255, 220, 80))
        bg   = pygame.Surface(
            (surf.get_width() + 12, surf.get_height() + 8),
            pygame.SRCALPHA
        )
        bg.fill((10, 8, 16, 230))
        y = screen.get_height() // 2
        screen.blit(bg,  (10, y))
        screen.blit(surf, (16, y + 4))