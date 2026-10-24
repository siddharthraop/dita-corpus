#!/usr/bin/env python3
"""List every reuse and filtering mechanism in the source and write build/inventory.json.

    python tools/inventory.py

For each set: every key (its value and how often it is used), every conref (from where, to
what), every profiling value (and on how many elements), and every relationship-table row.

MANIFEST uses this as its "before" picture: after migration to MyST, the number of
substitutions must equal the number of key references, and the number of includes must equal
the number of conrefs. Any difference is content lost in conversion.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import ROOT, SETS, dita_files, keydefs, parse, rel, set_of  # noqa: E402

PROFILE_ATTRS = ("platform", "audience", "product", "otherprops", "deliveryTarget")


def main() -> int:
    inv = {}
    for s in SETS:
        defined = keydefs(s)
        key_uses: Counter = Counter()
        conrefs, reltables = [], []
        profiling: dict[str, Counter] = defaultdict(Counter)
        files = [f for f in dita_files() if set_of(f) == s]
        for f in files:
            root = parse(f).getroot()
            for el in root.iter():
                if not isinstance(el.tag, str):
                    continue
                if el.get("keyref") and el.tag not in ("subjectdef", "subjectref"):
                    key_uses[el.get("keyref").split("/")[0]] += 1
                if el.get("conref"):
                    conrefs.append({"file": rel(f), "element": el.tag, "target": el.get("conref")})
                for a in PROFILE_ATTRS:
                    for v in (el.get(a) or "").split():
                        profiling[a][v] += 1
            for rt in root.iter("reltable"):
                for row in rt.iter("relrow"):
                    reltables.append([[tr.get("href") for tr in cell.iter("topicref")] for cell in row.iter("relcell")])
        inv[s] = {
            "files": len(files),
            "keys": {k: {"value": v, "uses": key_uses.get(k, 0)} for k, v in sorted(defined.items())},
            "keyref_uses": sum(key_uses.values()),
            "conrefs": conrefs,
            "profiling": {a: dict(c) for a, c in profiling.items()},
            "reltable_rows": reltables,
        }
    out = ROOT / "build" / "inventory.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(inv, indent=2), encoding="utf-8")
    for s, d in inv.items():
        print(f"{s:6} {d['files']:4} files  {len(d['keys']):3} keys  {d['keyref_uses']:4} key refs  "
              f"{len(d['conrefs']):3} conrefs  {len(d['reltable_rows']):3} reltable rows  profiling: {d['profiling']}")
    print(f"Wrote {rel(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
