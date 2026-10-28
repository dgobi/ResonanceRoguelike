"""Production proportional-font contract, resources and atomic initialization.

No authoring dependencies. pygame.font renders; FreeType checks the selected
bytes' character map because SDL_ttf metrics can report a missing-glyph box.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import stat
import warnings

PROFILE = "roguelike/data/display/typography.json"
CONTRACT = "game-typography-1"
# field: (label, default resource, nominal size, functional symbols, examples)
ROLES = {
    "font_ui_large": ("Headings", "Junicode.ttf", 22, "", "Reader and menu headings"),
    "font_ui_normal": ("Ordinary prose", "Junicode.ttf", 18, "—", "Reader prose/footer and several menus"),
    "font_ui_small": ("Small details", "Junicode.ttf", 16, "≥—·•", "Perk requirements, inventory and map details"),
    "font_ui_tiny": ("Message log", "Junicode.ttf", 14, "↑→×−›", "Message log, combat formulae and HUD"),
    "font_ui_italic": ("Italic role", "Junicode-Italic.ttf", 18, "", "Italic menu and lexicon text; chosen face replaces the role without synthesis"),
    "font_ui_bold": ("Bold role", "Junicode-Bold.ttf", 18, "—", "Inventory, perk and lexicon titles; chosen face replaces the role without synthesis"),
    "font_ui_bold_large": ("Large bold role", "Junicode-Bold.ttf", 22, "", "Prominent menu text; chosen face replaces the role without synthesis"),
    "font_deep": ("Known Deep Tongue", "Junicode-Italic.ttf", 18, "—", "Known proportional Deep Tongue text; unknown-language glyphs are generated separately"),
    "font_callout_damage": ("Damage callout", "Junicode-Bold.ttf", 13, "", "Floating damage numbers; small alias"),
    "font_callout_status": ("Status callout", "Junicode-Bold.ttf", 12, "", "Floating status effects"),
    "font_callout_creature": ("Creature callout", "Junicode-Bold.ttf", 11, "", "Creature sounds; tiny alias"),
    "font_callout_crit": ("Critical callout", "Junicode-Bold.ttf", 18, "", "Critical hit numbers"),
    "font_callout_levelup": ("Level-up callout", "Junicode-Bold.ttf", 21, "", "Level and perk-point announcements"),
}
ASCII = "".join(chr(c) for c in range(32, 127))
# Existing default gaps, never promoted to blocking requirements.
OPTIONAL = {"font_ui_normal": "✓", "font_ui_tiny": "○●", "font_ui_small": "☁ϟ"}
MAX_FONT_BYTES = 16 * 1024 * 1024
MAX_FONTS = 64


class TypographyError(ValueError):
    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        super().__init__("; ".join(f"{d['field']}: {d['message']}" for d in diagnostics if d["severity"] == "error"))


def diagnostic(field, message, severity="error", code="TYPOGRAPHY"):
    return dict(severity=severity, code=code, field=field, path=PROFILE, asset="game_typography",
                message=message, correction="Choose a usable project TTF for this role; saved changes apply at next game initialization.")


def defaults():
    return dict(id="game_typography", version=1, **{key:role[1] for key, role in ROLES.items()})


def shape_diagnostics(raw):
    if not isinstance(raw, dict): return [diagnostic("", "Expected one version-1 typography object.")]
    errors = []
    if raw.get("id") != "game_typography": errors.append(diagnostic("id", "Identity must be game_typography."))
    if type(raw.get("version")) is not int or raw["version"] != 1: errors.append(diagnostic("version", "Only version 1 is supported."))
    for key in ROLES:
        if not isinstance(raw.get(key), str): errors.append(diagnostic(key, "Every role requires a TTF basename string."))
    return errors


def no_links(path):
    """Inspect every lexical ancestor, including Windows junction/reparse points."""
    path = Path(os.path.abspath(path))
    for part in reversed((path, *path.parents)):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Linked/reparse resource is refused: {part}")
    return path


def resource(root, basename):
    if (not isinstance(basename, str) or not 1 <= len(basename) <= 128 or basename[-4:] != ".ttf"
            or basename.strip() != basename or any(c in basename for c in '/\\:')
            or any(ord(c) < 32 for c in basename) or basename in (".", "..")):
        raise ValueError("Expected an exact project .ttf basename, without path components.")
    folder = no_links(Path(root) / "roguelike/assets/Fonts")
    path = no_links(folder / basename)
    # Windows lookups are case insensitive; the published contract is not.
    names = []
    for index, entry in enumerate(folder.iterdir()):
        if index >= 256: raise ValueError("Font directory exceeds 256 entries.")
        names.append(entry.name)
    if path.name not in names:
        raise ValueError(f"Font basename does not exactly match a project resource: {basename}")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_FONT_BYTES:
        raise ValueError(f"Not a regular bounded TTF resource: {basename}")
    with path.open("rb") as stream: payload = stream.read(MAX_FONT_BYTES + 1)
    if not 0 < len(payload) <= MAX_FONT_BYTES: raise ValueError(f"Font resource exceeds bound: {basename}")
    return path, payload


def discover_resources(root):
    folder = no_links(Path(root) / "roguelike/assets/Fonts")
    rows = []
    for index, path in enumerate(folder.iterdir()):
        if index >= 256: raise ValueError("Font directory exceeds 256 entries.")
        if path.suffix == ".ttf":
            try:
                resolved, payload = resource(root, path.name)
                rows.append(dict(id=path.name, label=path.stem.replace("-", " "), sha256=hashlib.sha256(payload).hexdigest()))
            except (OSError, ValueError): continue
            if len(rows) > MAX_FONTS: raise ValueError("Font directory exceeds 64 TTF resources.")
    return sorted(rows, key=lambda row: row["id"])


def load_candidate(root, raw):
    """Resolve a complete candidate before the caller installs any font object."""
    import pygame
    import pygame.freetype
    diagnostics = shape_diagnostics(raw)
    if diagnostics: raise TypographyError(diagnostics)
    pygame.font.init(); pygame.freetype.init()
    fonts, coverage, resolved, cached = {}, {}, [], {}
    for key, (label, _, size, symbols, _) in ROLES.items():
        name = raw[key]
        try:
            if name not in cached:
                path, payload = resource(root, name)
                probe = pygame.freetype.Font(io.BytesIO(payload), size=18, ucs4=True)
                cached[name] = (path, payload, probe)
            path, payload, probe = cached[name]
            missing = [c for c, metric in zip(ASCII + symbols, probe.get_metrics(ASCII + symbols)) if metric is None]
            if missing:
                diagnostics.append(diagnostic(key, f"{name} lacks required characters: " + " ".join(f"{c!r} U+{ord(c):04X}" for c in missing), code="FONT_GLYPHS"))
            optional = OPTIONAL.get(key, "")
            gaps = [c for c, m in zip(optional, probe.get_metrics(optional)) if m is None] if optional else []
            if gaps: diagnostics.append(diagnostic(key, f"Bounded optional/decorative glyph gaps: {''.join(gaps)}. These are pre-existing default limitations, not a universal Unicode guarantee.", "warning", "FONT_OPTIONAL_GLYPHS"))
            fonts[key] = pygame.font.Font(io.BytesIO(payload), size)
            coverage[key] = probe
            resolved.append(dict(role=key, label=label, requested=name, resolved=path.relative_to(root).as_posix(),
                                 sha256=hashlib.sha256(payload).hexdigest(), size=size, fallback=False))
        except (OSError, ValueError, RuntimeError, pygame.error) as error:
            diagnostics.append(diagnostic(key, f"{name!r}: {error}", code="FONT_RESOURCE"))
    if any(d["severity"] == "error" for d in diagnostics): raise TypographyError(diagnostics)
    return dict(fonts=fonts, coverage=coverage, roles=resolved, diagnostics=diagnostics, fallback=False)


def read_profile(path):
    path = no_links(path)
    if path.stat().st_size > 1024 * 1024: raise ValueError("Typography profile exceeds 1 MiB.")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError(f"Duplicate key: {key}")
            result[key] = value
        return result
    def constant(value): raise ValueError(f"Invalid JSON constant: {value}")
    return json.loads(path.read_bytes().decode("utf-8-sig"), object_pairs_hook=unique, parse_constant=constant)


def initialize(root, candidate=None):
    """Candidate preview is strict. Saved invalid profiles fall back as a whole."""
    root = Path(root)
    if candidate is not None: return load_candidate(root, candidate)
    path = root / PROFILE
    try:
        raw = read_profile(path) if os.path.lexists(path) else defaults()
        loaded = load_candidate(root, raw)
        loaded["basis"] = "saved profile" if path.exists() else "absent profile / defaults"
        loaded["profile_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        return loaded
    except (OSError, ValueError) as error:
        message = f"Typography {path}: {error}. Using the complete known-default assignment; repair the profile in Workbench."
        warnings.warn(message, RuntimeWarning, stacklevel=2)
        try: loaded = load_candidate(root, defaults())
        except (OSError, ValueError) as default_error:
            raise RuntimeError(f"Cannot initialize default typography: {default_error}") from default_error
        loaded.update(fallback=True, basis="invalid saved profile / complete defaults", profile_sha256=None)
        for role in loaded["roles"]:
            role["requested"] = raw.get(role["role"]) if isinstance(locals().get("raw"), dict) else None
            role["fallback"] = True
        loaded["diagnostics"].insert(0, diagnostic("", message, "warning", "FONT_FALLBACK"))
        return loaded
