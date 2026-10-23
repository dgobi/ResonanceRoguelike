"""Fixture authoring only; all destructive actions require disposable save roots."""
from pathlib import Path
import shutil
from b1_support import read, dump


def payload_path(sm):
    return sm.checkpoint_path() if hasattr(sm, 'checkpoint_path') else sm.save_path


def flatten_fixture(sm, ev):
    """Build a synthetic legacy-format fixture from a supported checkpoint.

    Used to retain B1 payload rejection/seed-start coverage independently of the
    B3 container-corruption tests. This is not a production migration facility.
    """
    if not hasattr(sm, 'checkpoint_path'):
        return sm.save_path
    slot=sm.save_path.resolve()
    allowed=Path(ev.job['save_root']).resolve()
    assert slot.is_relative_to(allowed) and allowed.is_relative_to(Path(ev.job['run_root']).resolve())
    source=sm.checkpoint_path()
    files={p.relative_to(source):p.read_bytes() for p in source.rglob('*') if p.is_file() and p.name!='manifest.json'}
    # Verified exact disposable slot, single-language recursive deletion.
    shutil.rmtree(slot)
    for name,data in files.items():
        target=slot/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    sm.generation=sm._head_token=None
    return slot


def author_payload(path, value):
    """Reseal intentional semantic fixtures; raw corruption tests never use this."""
    dump(path,value)
    if (Path(path).parent/'manifest.json').exists():
        from b3_cases import reseal
        reseal(Path(path).parent)
