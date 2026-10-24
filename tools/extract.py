#!/usr/bin/env python3
"""Extract content analytics from the corpus.

    python tools/extract.py      # after tools/validate.py, which writes build/validation.json

Writes:
  build/topics.csv               one row per topic, for a spreadsheet
  build/topics.ndjson            the same rows, ready for `bq load --source_format=NEWLINE_DELIMITED_JSON`
  dashboard/data/metrics.json    the numbers behind the dashboard, with each OKR scored

Topics are read with lxml.etree.iterparse and each top-level block is cleared once counted, so
memory stays flat however large the corpus grows. That is the pattern to use on a 50,000-topic estate.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import ROOT, SETS, dita_files, keydefs, parse, rel, set_of  # noqa: E402

TOPIC_TYPES = {"concept", "reference", "task", "topic"}


def resolved_text(el, keys: dict) -> str:
    """Text of an element with empty <keyword keyref> replaced by the key's value, as a processor would."""
    parts = [el.text or ""]
    for c in el:
        if isinstance(c.tag, str):
            inner = resolved_text(c, keys)
            parts.append(inner or keys.get((c.get("keyref") or "").split("/")[0], ""))
        parts.append(c.tail or "")
    return " ".join("".join(parts).split())


def topic_record(path: Path, keys: dict | None = None) -> dict | None:
    keys = keys or {}
    rec = {"set": set_of(path), "file": rel(path), "type": None, "id": None, "title": "", "shortdesc_words": 0,
           "words": 0, "keyrefs": 0, "conrefs": 0, "xrefs": 0, "tables": 0, "images": 0, "images_with_alt": 0,
           "objects": 0, "objects_with_desc": 0, "steps": 0, "profiled_elements": 0, "platforms": set(),
           "audiences": set(), "products": set(), "revised": None, "source": None, "model_version": None,
           "generated": False, "known_issue": None}
    depth = 0
    for event, el in etree.iterparse(str(path), events=("start", "end"), load_dtd=False, no_network=True,
                                     resolve_entities=False, remove_comments=True):
        if not isinstance(el.tag, str):
            continue
        if event == "start":
            depth += 1
            if depth == 1:
                if el.tag not in TOPIC_TYPES:
                    return None
                rec["type"], rec["id"] = el.tag, el.get("id")
            continue
        tag = el.tag
        if el.get("keyref") and tag not in ("subjectdef", "subjectref"):
            rec["keyrefs"] += 1
        if el.get("conref"):
            rec["conrefs"] += 1
        for att, bucket in (("platform", "platforms"), ("audience", "audiences"), ("product", "products")):
            if el.get(att):
                rec[bucket].update(el.get(att).split())
                rec["profiled_elements"] += 1
        if tag == "xref":
            rec["xrefs"] += 1
        elif tag == "table":
            rec["tables"] += 1
        elif tag == "image":
            rec["images"] += 1
            rec["images_with_alt"] += int(el.find("alt") is not None and bool("".join(el.find("alt").itertext()).strip()))
        elif tag == "object":
            rec["objects"] += 1
            rec["objects_with_desc"] += int(el.find("desc") is not None)
        elif tag == "step":
            rec["steps"] += 1
        elif tag == "revised":
            rec["revised"] = el.get("modified")
        elif tag == "data":
            n, v = el.get("name"), el.get("value")
            if n == "source":
                rec["source"] = v
            elif n == "model-version":
                rec["model_version"] = v
            elif n == "generated":
                rec["generated"] = v == "true"
            elif n == "known-issue":
                rec["known_issue"] = v
        elif tag == "title" and depth == 2:
            rec["title"] = resolved_text(el, keys)
        elif tag == "shortdesc":
            rec["shortdesc_words"] = len("".join(el.itertext()).split())
        if tag in ("p", "li", "entry", "dd", "dt", "cmd", "shortdesc", "title", "note", "codeblock", "propvalue"):
            rec["words"] += len((el.text or "").split()) + sum(len((c.tail or "").split()) for c in el)
        # Free each top-level block (a section, a table, a step list) once it is counted. Its
        # descendants stay intact until then, because their parents read them (an image reads its alt).
        if depth == 3 and el.getparent().tag in ("body", "conbody", "refbody", "taskbody"):
            el.clear(keep_tail=True)
        depth -= 1
    for k in ("platforms", "audiences", "products"):
        rec[k] = sorted(rec[k])
    return rec


def spec_cells() -> tuple[int, int]:
    total = keyed = 0
    for f in dita_files():
        if f.suffix != ".dita":
            continue
        for entry in parse(f).xpath("//table[@outputclass='spec']/tgroup/tbody/row/entry[position() > 1]"):
            text = "".join(entry.itertext())
            if entry.find("keyword") is not None or any(ch.isdigit() for ch in text):
                total += 1
                keyed += int(entry.find(".//keyword[@keyref]") is not None)
    return total, keyed


def generation_builds() -> dict:
    """Topics in each generation's build: shared ones (no @platform) plus that generation's branch."""
    tree = parse(ROOT / SETS["tpu"]["map"])
    shared, per_gen = set(), defaultdict(set)

    def walk(el, platform=None):
        for tr in el:
            if not isinstance(tr.tag, str) or tr.tag not in ("topicref", "topichead"):
                continue
            p = tr.get("platform") or platform
            if tr.get("href") and tr.get("processing-role") != "resource-only":
                (per_gen[p] if p else shared).add(tr.get("href"))
            walk(tr, p)
    walk(tree.getroot())
    gens = sorted(per_gen)
    return {"shared_topics": len(shared), "generations": {g: {"specific": len(per_gen[g]), "total": len(shared) + len(per_gen[g])} for g in gens},
            "reuse_pct": round(100 * len(shared) * len(gens) / sum(len(shared) + len(per_gen[g]) for g in gens), 1) if gens else 0}


def evidence(model: str) -> dict:
    tree = parse(ROOT / SETS["gemma"]["map"])
    packs = {"authority": [0, 0], "downstream": [0, 0], "internal": [0, 0]}
    coverage, gaps, conflicting = Counter(), [], set()
    for row in tree.iter("relrow"):
        cells = row.findall("relcell")
        req = cells[0].find("topicref")
        rid, pack = Path(req.get("href")).stem, req.get("audience")
        refs = [tr for c in cells[1:] for tr in c.findall("topicref") if tr.get("product") == model]
        packs[pack][1] += 1
        if refs:
            packs[pack][0] += 1
        else:
            gaps.append(rid)
        for tr in refs:
            cov = tr.find("topicmeta/data[@name='coverage']").get("value")
            coverage[cov] += 1
            if cov == "conflicting":
                conflicting.add(rid)
    out = {f"{p}_pct": round(100 * c / t, 1) if t else 0 for p, (c, t) in packs.items()}
    out.update({f"{p}_covered": c for p, (c, _) in packs.items()}, **{f"{p}_total": t for p, (_, t) in packs.items()})
    out.update(model=model, coverage=dict(coverage), gaps=gaps, conflicting=len(conflicting), conflicting_ids=sorted(conflicting))
    return out


def api_metrics() -> dict:
    spec = json.loads((ROOT / "sources" / "tpu-api-v2.discovery.json").read_text(encoding="utf-8"))

    def count(r):
        return sum(len(v.get("methods", {})) + count(v.get("resources", {})) for v in r.values())
    methods = count(spec.get("resources", {}))
    have_m = len(list((ROOT / "api" / "topics" / "methods").glob("*.dita")))
    have_s = len(list((ROOT / "api" / "topics" / "schemas").glob("*.dita")))
    return {"revision": spec["revision"], "methods_in_spec": methods, "methods_documented": have_m,
            "methods_documented_pct": round(100 * min(have_m, methods) / methods, 1) if methods else 0,
            "schemas_in_spec": len(spec.get("schemas", {})), "schemas_documented": have_s}


def dig(d, path):
    for p in path.split("."):
        d = d.get(p) if isinstance(d, dict) else None
    return d


def main() -> int:
    today = dt.date.today()
    set_keys = {s: keydefs(s) for s in SETS}
    records = [r for r in (topic_record(f, set_keys[set_of(f)]) for f in dita_files() if f.suffix == ".dita" and set_of(f) in SETS) if r]
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    fields = list(records[0].keys())
    with open(build / "topics.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow({k: ";".join(v) if isinstance(v, list) else v for k, v in r.items()})
    with open(build / "topics.ndjson", "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")

    validation = json.loads((build / "validation.json").read_text()) if (build / "validation.json").exists() else {}
    sources = yaml.safe_load((ROOT / "sources" / "sources.yaml").read_text(encoding="utf-8"))
    ki_files = {w for ki in sources.get("known_issues", []) for w in ki.get("where", [])}
    items = validation.get("items", [])
    typed = [i for i in items if i["rule"] == "SPEC-2"]
    total_cells, keyed_cells = spec_cells()
    keys_defined = {s: keydefs(s) for s in SETS}
    key_usage = validation.get("key_usage", {})
    unused = sum(1 for s, ks in keys_defined.items() for k in ks if not k.startswith("schema-") and not key_usage.get(s, {}).get(k))
    media_total = sum(r["images"] + r["objects"] for r in records)
    media_ok = sum(r["images_with_alt"] + r["objects_with_desc"] for r in records)
    src_rows = []
    for k, s in sources["sources"].items():
        age = (today - s["checked"]).days if isinstance(s.get("checked"), dt.date) else None
        src_rows.append({"key": k, "title": s.get("title"), "url": s.get("url"), "checked": str(s.get("checked")),
                         "page_updated": str(s.get("page_updated")) if s.get("page_updated") else None, "age_days": age})
    outputs_file = build / "outputs.json"
    outputs = json.loads(outputs_file.read_text()) if outputs_file.exists() else None
    planned = len(list((ROOT / "tpu" / "filters").glob("*.ditaval"))) + len(list((ROOT / "gemma" / "filters").glob("*.ditaval"))) + 2

    by_set = defaultdict(lambda: {"topics": 0, "words": 0, "types": Counter()})
    for r in records:
        b = by_set[r["set"]]
        b["topics"] += 1
        b["words"] += r["words"]
        b["types"][r["type"]] += 1
    metrics = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "commit": os.environ.get("GITHUB_SHA", "")[:7] or None,
        "totals": {"topics": len(records), "words": sum(r["words"] for r in records),
                   "files": validation.get("files"), "generated_topics": sum(r["generated"] for r in records)},
        "by_set": {s: {"topics": b["topics"], "words": b["words"], "types": dict(b["types"])} for s, b in sorted(by_set.items())},
        "single_source": {
            "spec_cells": total_cells, "spec_cells_keyed": keyed_cells,
            "spec_cells_keyed_pct": round(100 * keyed_cells / total_cells, 1) if total_cells else 100,
            "keys_defined": sum(len(v) for v in keys_defined.values()),
            "keyref_uses": sum(r["keyrefs"] for r in records), "conref_uses": sum(r["conrefs"] for r in records),
            "typed_numbers": len(typed), "typed_numbers_unexplained": sum(1 for i in typed if i["file"] not in ki_files),
            "unused_keys": unused,
        },
        "tpu_builds": generation_builds(),
        "quality": {"errors": validation.get("errors"), "warnings": validation.get("warnings"),
                    "grammar_checked": validation.get("grammar_checked"), "by_rule": validation.get("by_rule", {}),
                    "items": [i for i in items if i["severity"] in ("error", "warning")][:50]},
        "known_issues": sources.get("known_issues", []),
        "freshness": {"sources": src_rows,
                      "sources_current_pct": round(100 * sum(1 for s in src_rows if s["age_days"] is not None and s["age_days"] <= 90) / len(src_rows), 1)},
        "evidence": {"current": evidence("gemma-4"), "previous": evidence("gemma-3")},
        "api": api_metrics(),
        "media": {"items": media_total, "with_text_alternative": media_ok,
                  "text_alternative_pct": round(100 * media_ok / media_total, 1) if media_total else 100},
        "builds": {"outputs": outputs["count"] if outputs else planned, "measured": bool(outputs),
                   "seconds": outputs.get("seconds") if outputs else None, "list": outputs.get("list") if outputs else None},
        "topics": [{k: r[k] for k in ("set", "file", "type", "title", "words", "keyrefs", "conrefs", "platforms", "revised", "known_issue")} for r in records],
    }
    okrs = yaml.safe_load((ROOT / "dashboard" / "okrs.yaml").read_text(encoding="utf-8"))
    for o in okrs["objectives"]:
        for kr in o["key_results"]:
            v = dig(metrics, kr["metric"])
            kr["value"] = v
            kr["met"] = None if v is None else (v >= kr["target"] if kr["direction"] == "min" else v <= kr["target"])
    metrics["okrs"] = okrs["objectives"]
    out = ROOT / "dashboard" / "data" / "metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")
    met = sum(1 for o in metrics["okrs"] for kr in o["key_results"] if kr["met"])
    total = sum(len(o["key_results"]) for o in metrics["okrs"])
    print(f"{len(records)} topics, {metrics['totals']['words']} words. Key results met: {met}/{total}. Wrote {rel(out)}, build/topics.csv, build/topics.ndjson")
    return 0


if __name__ == "__main__":
    sys.exit(main())
