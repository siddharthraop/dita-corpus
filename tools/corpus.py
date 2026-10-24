"""Shared helpers for the corpus tools: find files, parse them with lxml, resolve references.

Every tool parses DITA *without* loading the DTD. Grammar validation is a separate step
(tools/validate.py, stage 1), so the other tools stay fast and work offline.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
SETS = {
    "tpu": {"map": "tpu/tpu.ditamap", "keys": ["tpu/keys/tpu-keys.ditamap"], "scheme": "tpu/subjects/tpu-scheme.ditamap"},
    "gemma": {"map": "gemma/gemma.ditamap", "keys": ["gemma/keys/gemma-keys.ditamap"], "scheme": "gemma/gemma-scheme.ditamap"},
    "api": {"map": "api/tpu-api.ditamap", "keys": ["api/keys/api-keys.ditamap"], "scheme": None},
}
DITA_EXT = (".dita", ".ditamap", ".ditaval")
SKIP_DIRS = {".git", ".grammar", "build", "_build", "node_modules", "out"}

# No DTD, no network, no entity expansion: safe and fast for every non-grammar check.
PARSER = etree.XMLParser(load_dtd=False, no_network=True, resolve_entities=False, remove_comments=False)


def dita_files(root: Path = ROOT) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name.endswith(DITA_EXT):
                yield Path(dirpath) / name


def set_of(path: Path) -> str:
    rel = path.resolve().relative_to(ROOT)
    return rel.parts[0] if rel.parts else ""


def parse(path: Path) -> etree._ElementTree:
    return etree.parse(str(path), PARSER)


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def split_href(href: str) -> tuple[str, str | None, str | None]:
    """'file.dita#topicid/elemid' -> ('file.dita', 'topicid', 'elemid')."""
    file_part, _, frag = href.partition("#")
    if not frag:
        return file_part, None, None
    topic_id, _, elem_id = frag.partition("/")
    return file_part, topic_id or None, elem_id or None


def is_local(href: str) -> bool:
    return bool(href) and "://" not in href and not href.startswith(("mailto:", "#"))


def keydefs(set_name: str) -> dict[str, str]:
    """All keys defined in a set's key maps, with their text value."""
    out: dict[str, str] = {}
    for km in SETS.get(set_name, {}).get("keys", []):
        p = ROOT / km
        if not p.exists():
            continue
        for kd in parse(p).iter("keydef"):
            text = "".join(kd.itertext()).strip()
            for k in kd.get("keys", "").split():
                out[k] = text
    return out


def scheme_values(set_name: str) -> dict[str, set[str]]:
    """Allowed values per attribute, from the set's subject scheme enumerations."""
    scheme = SETS.get(set_name, {}).get("scheme")
    if not scheme or not (ROOT / scheme).exists():
        return {}
    tree = parse(ROOT / scheme)
    by_key = {sd.get("keys"): sd for sd in tree.iter("subjectdef") if sd.get("keys")}
    allowed: dict[str, set[str]] = {}
    for enum in tree.iter("enumerationdef"):
        att = enum.find("attributedef").get("name")
        ref = enum.find("subjectdef").get("keyref")
        root_def = by_key.get(ref)
        vals = {d.get("keys") for d in root_def.iter("subjectdef") if d is not root_def and d.get("keys")} if root_def is not None else set()
        allowed.setdefault(att, set()).update(vals)
    return allowed


def text_of(el) -> str:
    return " ".join("".join(el.itertext()).split()) if el is not None else ""
