"""Capture actual untouched AI-8 alarm saves before AI-9 serializer changes."""
import hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'roguelike')]
from verify_ai_6_play import setup, snapshot
import pygame


def main():
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert revision == 'bc7feaa08910548c2e236fed97c81c627a49fd1b'
    assert not subprocess.check_output(['git','diff','--name-only','HEAD','--','roguelike'],cwd=ROOT,text=True).strip()
    out = ROOT/'evidence/ai-9'
    out.mkdir(parents=True,exist_ok=True)
    records = []
    pygame.init()
    for room, waits, label in [('ai8_alarm_crossing',1,'v5-prepared'),
                               ('ai8_alarm_crossing',2,'v1-investigating'),
                               ('ai8_alarm_reverse',2,'v5-investigating'),
                               ('ai1_skirmisher_room',1,'v1-unattached'),
                               ('ai2_shadow_opening',1,'v2-unattached'),
                               ('ai3_drowsing_opening',1,'v3-unattached')]:
        with tempfile.TemporaryDirectory(prefix='resonance-ai9-baseline-') as temp:
            session = setup(temp, room, out)
            for _ in range(waits): session.key(pygame.K_PERIOD)
            e = session.e
            state = snapshot(e)
            if label == 'v5-prepared':
                assert any(a.ai.responses['prepared'] is not None for a in e.entities[1:])
            elif 'investigating' in label:
                assert any(a.ai.responses['interest'] is not None for a in e.entities[1:])
            else:
                assert all('responses' not in a.ai.snapshot() for a in e.entities[1:] if hasattr(a.ai,'snapshot'))
            e._handle_key(pygame.K_F5)
            assert snapshot(e) == state
            archive = out/('legacy-'+label+'.zip')
            shutil.make_archive(str(archive.with_suffix('')), 'zip', temp)
            records.append(dict(label=label,source_revision=revision,room=room,ordinary_waits=waits,
                config={k:v for k,v in session.config.items() if k!='state_root'},state=state,
                archive=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))
    (out/'legacy-baseline.json').write_text(json.dumps(dict(
        capture='Actual baseline source, ordinary Wait and F5 handlers, disposable room-test roots; no field stripping.',
        records=records),indent=2),encoding='utf8')
    print(json.dumps(dict(passed=True,revision=revision,archives=len(records))))


if __name__ == '__main__': main()
