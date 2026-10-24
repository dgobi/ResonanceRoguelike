"""Source-bound worker: actual production main, disposable save roots only."""
from pathlib import Path
import os
import sys
import traceback
from b1_support import boot, dump, read, hashes
from b2_worker import B2Evidence


def main():
    job = read(sys.argv[1])
    root = Path(__file__).resolve().parents[1]
    game = root / 'roguelike'
    run = Path(job['run_root']).resolve()
    saves = Path(job['save_root']).resolve()
    allowed_roots=(root/'.baseline',root/'evidence/worldgen-g6',root/'evidence/worldgen-g7',root/'evidence/worldgen-g8',root/'evidence/worldgen-g9')
    assert any(run.is_relative_to(base) and run!=base for base in allowed_roots)
    marker=read(run/'disposable-b3.json')
    assert marker=={'kind':'test saves and evidence only','production_source':str(game)}
    assert saves.is_relative_to(run) and not saves.is_relative_to(game)
    assert Path.cwd().resolve() == game.resolve()
    sys.path.insert(0, str(game))
    import engine.save_manager as sm
    sm.SAVE_DIR = saves
    import config
    config.DEBUG_MODE = job.get('debug', False)
    ev = B2Evidence(job)
    ev.record.update(suite=job['suite'], variant=job['variant'])
    try:
        suite = job['suite']
        if suite == 'diagnostic':
            import persistence_diagnostics as pd
            session = Path(job['result']).parent
            pd.prepare = lambda *a, **k: (session, game)
            if job.get('payload'):
                (session / 'lurker.json').write_bytes(Path(job['payload']).read_bytes())
            pd.worker('b3', job['variant'], job['phase'])
            result = read(session / (job['phase'] + '-results.json'))
            for row in result['checks']:
                ev.check('original', row['property'], row['expected'], row['observed'])
            ev.record['checkpoint'] = hashes(saves / 'slot_0')
        elif suite in ('b1', 'b2'):
            if job['scenario'] == 'journey':
                module = __import__(suite + '_journey')
                module.run_journey(ev)
            else:
                module = __import__(suite + ('_format_cases' if job['scenario'] == 'format' else '_cases'))
                callback = module.format_cases if suite == 'b1' and job['scenario'] == 'format' else module.run_case
                boot(lambda e: callback(e, ev), ev)
        elif suite == 'd':
            from d_cases import run_case
            if job['scenario'] == 'journey':
                from d_journey import run_journey
                run_journey(ev)
            else:
                boot(lambda e: run_case(e, ev), ev)
        elif suite == 'c':
            from c_cases import run_case
            if job['scenario'] == 'journey':
                from c_journey import run_journey
                run_journey(ev)
            else:
                boot(lambda e: run_case(e, ev), ev)
        else:
            from b3_cases import run_case, run_journey
            if job['scenario'] == 'journey':
                run_journey(ev)
            elif job['scenario'] == 'initial-fault' and job['phase'] == 'read' and job['variant'] != 'published':
                from b3_cases import first_crash
                first_crash(ev)
            else:
                boot(lambda e: run_case(e, ev), ev)
        ev.bind_sources(game)
        ev.record['completed'] = True
    except BaseException as error:
        ev.record['error'] = repr(error)
        ev.record['traceback'] = traceback.format_exc()
    ev.record['assertion_count'] = len(ev.record['checks'])
    ev.record['passed'] = ev.record['completed'] and bool(ev.record['checks']) and all(c['passed'] for c in ev.record['checks'])
    dump(job['result'], ev.record)
    print({k: ev.record.get(k) for k in ('scenario','phase','completed','passed','assertion_count','error')}, flush=True)
    return 0 if ev.record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
