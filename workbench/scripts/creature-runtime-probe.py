"""Bounded real game consumers and fresh-process component restoration.

Only disposable .artifacts projects/save roots are admitted. This is a controlled
fixture, not natural selection, a balance test or a personal-save migration.
"""
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
root, output = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
assert ".artifacts" in root.parts and ".artifacts" in output.parts and root != REPO
output.mkdir(parents=True, exist_ok=True)
os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYGAME_HIDE_SUPPORT_PROMPT="1")
sys.path[:0] = [str(root / "roguelike"), str(REPO / "tools/critical_fix_regressions/tests")]
import pygame
pygame.init()
pygame.display.set_mode((1,1))
os.chdir(root / "roguelike")
import config
config.DEBUG_MODE = False
from test_effect_persistence import load_data, make_engine
from engine.creature_factory import CreatureFactory
from engine.creature_abilities import process_abilities
from engine.effect_lifecycle import creature_id
from engine.save_manager import _serialize_entity, _deserialize_entities
from components.ai import AIState, _monster_attack_entity
from world.local_map import LocalMap, make_tile


def component_values(a):
    return dict(name=a.name, hp=a.fighter.hp, max_hp=a.fighter.max_hp, armour=a.fighter.effective_av,
                sight=a.perception.sight_radius, dark=a.perception.sees_in_dark, wander=a.ai.wander_radius,
                stable_id=creature_id(a), ai=type(a.ai).__name__)


def phase():
    with contextlib.redirect_stdout(io.StringIO()), patch("engine.save_manager.SAVE_DIR", output / "saves"):
        data = load_data(); engine = make_engine(data); engine.debug = None; engine.rng = random.Random(164)
        if "--restore" in sys.argv:
            row = json.loads((output / "injured.json").read_text(encoding="utf-8"))
            old = json.loads((output / "saved-values.json").read_text(encoding="utf-8"))
            restored = _deserialize_entities([row], engine)[0]
            fresh = CreatureFactory(data).spawn("barrow_wight", 13, 12)
            assert component_values(restored) == old, (component_values(restored), old)
            assert fresh.name == "W5F fresh Wight" and fresh.fighter.hp == fresh.fighter.max_hp == 41
            assert fresh.fighter.effective_av == 9 and fresh.perception.sight_radius == 2
            assert not fresh.perception.sees_in_dark and fresh.ai.wander_radius == 3
            definition = data.entities[creature_id(restored)]
            assert definition["description"] == "W5F current definition prose" and definition["damage_dice"] == "1d1"
            assert definition["damage_bonus"] == 4 and definition["speed"] == 1.25 and definition["pursuit_timeout"] == 2
            engine.entities = [engine.player, restored]; engine.local_map.tiles["visible"][:] = True
            things = engine.look_mode._get_things_at(engine, restored.x, restored.y)
            assert next(t for t in things if t["type"] == "creature")["description"] == definition["description"]
            before = engine.player.corruption.value; engine._advance_turn()
            assert abs(engine.player.corruption.value - before - 0.005) < 1e-9
            assert any(e.type == "pulse" for e in engine.visual_events.get_active())
            assert any("W5F tests thee" in m.text for m in engine.log.messages)
            return dict(restored=old, fresh=component_values(fresh), current_definition={k:definition[k] for k in ("description","damage_dice","damage_bonus","attack_verb","speed","pursuit_timeout")},
                        ability_corruption_delta=engine.player.corruption.value-before, pulse=True,
                        route="fresh process → DataLoader → _deserialize_entities → LookMode → Engine._advance_turn / actual AI attack and wight dispatch")

        actor = CreatureFactory(data).spawn("barrow_wight", 13, 12); actor.fighter.hp = 7
        assert actor.name == "Barrow Wight" and actor.fighter.max_hp == 20, "Use a fresh disposable fixture"
        saved = component_values(actor)
        (output / "injured.json").write_text(json.dumps(_serialize_entity(actor)), encoding="utf-8")
        (output / "saved-values.json").write_text(json.dumps(saved), encoding="utf-8")
        wight_path = root / "roguelike/data/entities/creatures/barrow_wight.json"
        wight = json.loads(wight_path.read_bytes())
        wight.update(name="W5F fresh Wight", description="W5F current definition prose", base_hp=41, armour_value=9,
                     damage_dice="1d1", damage_bonus=4, attack_verb="W5F tests thee", speed=1.25, pursuit_timeout=2, wander_radius=3)
        wight["fighter"]["max_hp"] = 41; wight["perception"].update(sight_radius=2, sees_in_dark=False)
        wight_path.write_text(json.dumps(wight), encoding="utf-8")
        restored_process = subprocess.run([sys.executable, "-X", "utf8", "-B", __file__, str(root), str(output), "--restore"],
                                          capture_output=True, text=True, timeout=40, creationflags=0x08000000 if os.name == "nt" else 0)
        assert restored_process.returncode == 0, restored_process.stderr
        restored_receipt = json.loads(restored_process.stdout.strip().splitlines()[-1])

        # A saved ordinary variant sharing its template's presentation tile.
        template = copy.deepcopy(data.entities["hollow_revenant"])
        template["callout_sounds"] = {"on_attack":{"text":"W5F inherited literal", "color":[160,140,120]}}
        (root / "roguelike/data/entities/creatures/hollow_revenant.json").write_text(json.dumps(template),encoding="utf-8")
        variant = copy.deepcopy(template)
        variant.update(id="w5f_probe_variant", name="W5F ordinary", description="W5F own description", speed=1.25,
                       pursuit_timeout=2, damage_dice="1d1", damage_bonus=4, attack_verb="W5F strikes thee")
        path = root / "roguelike/data/entities/creatures/w5f_probe_variant.json"; path.write_text(json.dumps(variant), encoding="utf-8")
        data = load_data(); engine = make_engine(data); engine.debug = None; engine.rng = random.Random(164)
        actor = engine.creature_factory.spawn(variant["id"], 13, 12); engine.entities.append(actor)
        # Distinct tile-linked negative control: it must never supply this actor's prose/callout/details.
        data.entities["hollow_revenant"] = {**data.entities["hollow_revenant"], "description":"WRONG TEMPLATE", "speed":0.1,
                                          "pursuit_timeout":99, "callout_sounds":{"on_attack":{"text":"WRONG CALLOUT"}}}
        engine.local_map.tiles["visible"][:] = True; engine.local_map.tiles["explored"][:] = True
        visible = next(t for t in engine.look_mode._get_things_at(engine, 13, 12) if t["type"] == "creature")
        assert visible["description"] == variant["description"]
        actor.last_known_x, actor.last_known_y = 13, 12; engine.local_map.tiles["visible"][13,12] = False
        ghost = next(t for t in engine.look_mode._get_things_at(engine, 13, 12) if t["type"] == "creature")
        assert ghost["description"].startswith(variant["description"])
        engine.local_map.tiles["visible"][:] = True
        engine.creature_knowledge[variant["id"]] = {"revealed_weaknesses":["W5F own knowledge"], "revealed_strengths":[]}
        engine.creature_knowledge["hollow_revenant"] = {"revealed_weaknesses":["WRONG KNOWLEDGE"]}
        rendered = []
        class Font:
            def __init__(self, font): self.font = font
            def __getattr__(self, name): return getattr(self.font, name)
            def render(self, text, *args, **kwargs): rendered.append(text); return self.font.render(text, *args, **kwargs)
        from rendering.ui_registry import UIRegistry
        engine.ui_registry = UIRegistry(); engine.ui_registry.load()
        engine.display.init(); engine.player.true_sight = True
        look = engine.look_mode; look.init(engine.display)
        look._font_small = Font(look._font_small)
        look.cursor_x, look.cursor_y = 13, 12; look.examine_index = len(look._get_things_at(engine,13,12))-1
        frame = pygame.Surface((1280,720)); look.render_examine_popup(frame,engine)
        assert any("faster than you" in s for s in rendered), rendered
        assert "Weak to: W5F own knowledge" in rendered and not any("WRONG" in s for s in rendered)
        pygame.image.save(frame, str(output / "variant-look.png"))

        actor.ai.state = AIState.WANDERING; engine.player.dodge_chance = 0
        from engine.combat import resolve_attack
        hp = engine.player.fighter.hp
        with patch("engine.combat.resolve_attack", wraps=resolve_attack) as observed_attack:
            engine._advance_turn()
        assert observed_attack.call_args.kwargs["weapon"]["damage_dice"] == "1d1"
        assert observed_attack.call_args.kwargs["weapon"]["damage_bonus"] == 4
        assert engine.player.fighter.hp < hp and any("W5F strikes thee" in m.text for m in engine.log.messages)
        assert abs(actor.ai.move_accumulator - 0.25) < 1e-9
        callouts = [c["text"] for c in engine._pending_callouts]
        assert variant["callout_sounds"]["on_attack"]["text"] in callouts and "WRONG CALLOUT" not in callouts
        # Ordinary engine phase and real resolver; the observer above delegates unchanged.
        normal_damage = hp - engine.player.fighter.hp

        engine.player.x, engine.player.y = 60, 35
        actor.ai.state = AIState.HUNTING; actor.ai.pursuit_turns_without_contact = 1
        actor._last_known_px, actor._last_known_py = 30, 20
        actor.ai._update_state(actor,engine.local_map,engine.player,1,engine=engine)
        assert actor.ai.state == AIState.WANDERING and actor._last_known_px is None
        actor.ai.state = AIState.HUNTING; actor.ai.pursuit_turns_without_contact = 1; actor.ai.move_accumulator = 0
        actor._last_known_px, actor._last_known_py = 30, 20; actor.ai.target_x, actor.ai.target_y = 30,20
        offmap = LocalMap(); offmap.tiles[:] = make_tile("grass",True,True)
        engine.save_manager.cache.store_submap("w5f_offmap",offmap,[])
        engine.entities = [engine.player]; engine._live_pursuers = [(actor,0,0,"w5f_offmap")]
        engine._tick_live_pursuers()
        assert actor.ai.state == AIState.WANDERING and actor.ai.pursuit_turns_without_contact == 2
        assert abs(actor.ai.move_accumulator - 0.25) < 1e-9

        lurker = engine.creature_factory.spawn("stone_lurker",5,5)
        process_abilities(lurker,engine); assert lurker.tile == "rock" and creature_id(lurker) == "stone_lurker"
        engine.player.x,engine.player.y = 6,5; process_abilities(lurker,engine)
        assert lurker.tile == "stone_lurker" and lurker._ambush_ready
        # Matching tile cannot inherit the wight's ID-bound dispatch.
        clone = copy.deepcopy(data.entities["barrow_wight"]); clone["id"] = "w5f_no_binding"
        data.entities[clone["id"]] = clone; unbound = engine.creature_factory.spawn(clone["id"],7,5)
        before = engine.player.corruption.value; process_abilities(unbound,engine); assert engine.player.corruption.value == before
        return dict(passed=True, pid=os.getpid(), restore=restored_receipt,
                    variant=dict(id=variant["id"], tile=actor.tile, definition_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                 visible_description=visible["description"], ghost_description=ghost["description"], rendered_details=rendered,
                                 callouts=callouts, controlled_damage=normal_damage, active_timeout=True, offmap_timeout=True, speed_accumulator=actor.ai.move_accumulator),
                    disguised_special_identity=True, identical_tile_no_special_binding=True,
                    limits="Controlled production routes with seeded RNG and disposable inputs; no natural selection or balance claim. Save format/restoration unchanged.")


result = phase()
(output / ("restore-result.json" if "--restore" in sys.argv else "runtime-result.json")).write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result))
