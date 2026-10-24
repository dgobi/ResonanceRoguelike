"""One destination boundary for authoring diagnostics and intentional writes.

Resolve aliases before work; revalidate the complete staged set before publishing.
Initializers may create absent files only. A requested catalogue refresh is the
sole replaceable intentional output; it still cannot replace unrelated inputs.
"""
from pathlib import Path
import os


def same_path(a, b):
    a, b = Path(a), Path(b)
    if a.resolve() == b.resolve():
        return True
    try:
        return a.samefile(b)
    except (FileNotFoundError, OSError):
        return False


class Destinations:
    def __init__(self, inputs, roots):
        self.inputs = [(label, Path(path)) for label, path in inputs if path is not None]
        self.roots = [Path(p).resolve() for p in roots]
        # Resolved paths detect symlinks; device/inode identities also detect
        # hard links from an apparently safe artifact directory into installed data.
        self.installed = {}
        for root in self.roots:
            for p in root.rglob('*'):
                if p.is_file():
                    stat = p.stat()
                    self.installed[(stat.st_dev, stat.st_ino)] = p

    def validate(self, outputs):
        for index, (label, path, kind) in enumerate(outputs):
            path = Path(path)
            resolved = path.resolve()
            if any(resolved.is_relative_to(root) for root in self.roots):
                raise ValueError(f'{label} output {path} conflicts with installed game/data input {resolved}')
            if path.exists():
                stat = path.stat()
                installed = self.installed.get((stat.st_dev, stat.st_ino))
                if installed:
                    raise ValueError(f'{label} output {path} aliases installed input {installed}')
            for source_label, source in self.inputs:
                if same_path(path, source):
                    raise ValueError(f'{label} output {path} conflicts with {source_label} input {source}')
            for other_label, other, other_kind in outputs[:index]:
                if same_path(path, other):
                    raise ValueError(f'{label} output {path} conflicts with {other_label} {other_kind} target {other}')

    def publish(self, artifacts):
        self.validate([(label, path, kind) for label, path, kind, content in artifacts])
        for label, path, kind, content in artifacts:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            if kind == 'initializer':
                # Exclusive create also preserves a file created after validation.
                try:
                    with path.open('xb') as stream:
                        stream.write(content)
                except FileExistsError:
                    pass
            else:
                path.write_bytes(content)
