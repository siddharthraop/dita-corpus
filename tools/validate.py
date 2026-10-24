#!/usr/bin/env python3
"""Validate the corpus in four stages and write build/validation.json.

    python tools/validate.py                  # all stages
    python tools/validate.py --skip-grammar   # stages 2-4 only (no DTDs needed)

1. Grammar   every .dita/.ditamap/.ditaval against the OASIS DITA 1.3 DTDs (xmllint + XML catalog).
2. Integrity lxml: unique IDs, local links and media exist, conrefs resolve to an element of the
             same type, keyrefs are defined, @platform/@audience/@product values are in the subject scheme.
3. Rules     ISO Schematron house rules (tools/schematron/corpus.sch) via lxml.isoschematron.
4. Sources   every source in sources/sources.yaml checked within the last 90 days.

Why stage 1 shells out to xmllint: lxml 6 bundles libxml2 2.14, whose entity-amplification guard
rejects the OASIS DITA DTDs (they expand many parameter entities). libxml2 2.9's xmllint, as shipped
by Ubuntu, loads them. Everything else is lxml.

Exit code 1 if any error. Warnings are reported, not fatal.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml
from lxml import etree, isoschematron

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import ROOT, SETS, dita_files, is_local, keydefs, parse, rel, scheme_values, set_of, split_href  # noqa: E402

SCH = ROOT / "tools" / "schematron" / "corpus.sch"
SVRL = "{http://purl.oclc.org/dsdl/svrl}"
LINK_ATTRS = {"topicref": "href", "mapref": "href", "xref": "href", "image": "href", "object": "data", "keydef": "href"}
PROFILE_ATTRS = ("platform", "audience", "product")
STALE_DAYS = 90


class Report:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, stage, severity, rule, path, msg, line=None):
        self.items.append({"stage": stage, "severity": severity, "rule": rule, "file": path, "line": line, "message": msg})

    def count(self, sev):
        return sum(1 for i in self.items if i["severity"] == sev)


def stage_grammar(files, rep: Report):
    catalog = os.environ.get("XML_CATALOG_FILES") or str(ROOT / ".grammar" / "catalog.xml")
    if not Path(catalog.split()[0]).exists() or not shutil.which("xmllint"):
        rep.add("grammar", "error", "GRAM-0", None, "DTDs or xmllint not found. Run tools/fetch_grammar.sh and install libxml2-utils, or pass --skip-grammar.")
        return
    env = dict(os.environ, XML_CATALOG_FILES=catalog)
    pattern = re.compile(r"^(.+?):(\d+): (?:element \S+: )?(validity|parser) (error|warning) : (.*)$")
    for i in range(0, len(files), 40):
        batch = [str(f) for f in files[i:i + 40]]
        out = subprocess.run(["xmllint", "--noout", "--valid", "--nonet", "--huge", *batch], env=env,
                             capture_output=True, text=True)
        for line in out.stderr.splitlines():
            m = pattern.match(line)
            if m:
                rep.add("grammar", "error", "DTD", rel(Path(m.group(1))), m.group(5), int(m.group(2)))


def stage_integrity(files, rep: Report):
    keys = {s: keydefs(s) for s in SETS}
    allowed = {s: scheme_values(s) for s in SETS}
    used_keys: dict[str, Counter] = {s: Counter() for s in SETS}
    trees = {}
    for f in files:
        try:
            trees[f] = parse(f)
        except etree.XMLSyntaxError as ex:
            rep.add("integrity", "error", "XML", rel(f), str(ex))
    for f, tree in trees.items():
        s, path = set_of(f), rel(f)
        root = tree.getroot()
        ids = Counter(el.get("id") for el in root.iter() if isinstance(el.tag, str) and el.get("id"))
        for i, n in ids.items():
            if n > 1 and root.tag not in ("map",):
                rep.add("integrity", "error", "ID-1", path, f'id "{i}" is used {n} times in one topic')
        for el in root.iter():
            if not isinstance(el.tag, str):
                continue
            att = LINK_ATTRS.get(el.tag)
            href = el.get(att) if att else None
            if href and is_local(href) and el.get("scope") != "external":
                target, topic_id, elem_id = split_href(href)
                tpath = (f.parent / target).resolve()
                if not tpath.exists():
                    sev = "error"
                    rep.add("integrity", sev, "LINK-1", path, f"<{el.tag}> points to a missing file: {href}", el.sourceline)
                elif topic_id and tpath.suffix == ".dita":
                    t = trees.get(tpath) or parse(tpath)
                    if t.getroot().get("id") != topic_id or (elem_id and not t.xpath("//*[@id=$i]", i=elem_id)):
                        rep.add("integrity", "error", "LINK-2", path, f"<{el.tag}> fragment not found: {href}", el.sourceline)
            conref = el.get("conref")
            if conref:
                target, topic_id, elem_id = split_href(conref)
                tpath = (f.parent / target).resolve()
                if not tpath.exists():
                    rep.add("integrity", "error", "CONREF-1", path, f"conref to a missing file: {conref}", el.sourceline)
                else:
                    t = trees.get(tpath) or parse(tpath)
                    hits = t.xpath("//*[@id=$i]", i=elem_id) if elem_id else [t.getroot()]
                    if t.getroot().get("id") != topic_id or not hits:
                        rep.add("integrity", "error", "CONREF-2", path, f"conref target not found: {conref}", el.sourceline)
                    elif hits[0].tag != el.tag:
                        rep.add("integrity", "error", "CONREF-3", path,
                                f"conref from <{el.tag}> to <{hits[0].tag}>: elements must be the same type", el.sourceline)
            kref = el.get("keyref")
            if kref and s in keys and el.tag != "subjectdef" and el.tag != "subjectref":
                k = kref.split("/")[0]
                used_keys[s][k] += 1
                if k not in keys[s]:
                    rep.add("integrity", "error", "KEY-1", path, f'keyref "{k}" is not defined in the {s} key maps', el.sourceline)
            for pa in PROFILE_ATTRS:
                v = el.get(pa)
                if v and allowed.get(s, {}).get(pa) and root.tag != "val":
                    for token in v.split():
                        if token not in allowed[s][pa]:
                            rep.add("integrity", "error", "PROF-1", path,
                                    f'@{pa}="{token}" is not an allowed value in the {s} subject scheme', el.sourceline)
        if root.tag == "val":
            for p in root.iter("prop"):
                pa, v = p.get("att"), p.get("val")
                if v and allowed.get(s, {}).get(pa) and v not in allowed[s][pa]:
                    rep.add("integrity", "error", "PROF-2", path, f'DITAVAL value {pa}="{v}" is not in the subject scheme')
    for s, defined in keys.items():
        for k in sorted(set(defined) - set(used_keys[s])):
            if not k.startswith("schema-"):
                rep.add("integrity", "warning", "KEY-2", SETS[s]["keys"][0], f'key "{k}" is defined but never used')
    return used_keys


def stage_rules(files, rep: Report):
    sch = isoschematron.Schematron(etree.parse(str(SCH)), store_report=True)
    for f in files:
        if f.suffix != ".dita":
            continue
        tree = parse(f)
        sch.validate(tree)
        for node in sch.validation_report.getroot():
            if node.tag in (SVRL + "failed-assert", SVRL + "successful-report"):
                msg = " ".join("".join(node.find(SVRL + "text").itertext()).split())
                rep.add("rules", node.get("role", "error"), node.get("id"), rel(f), msg)


def stage_sources(rep: Report, today: dt.date):
    data = yaml.safe_load((ROOT / "sources" / "sources.yaml").read_text(encoding="utf-8"))
    for key, src in data["sources"].items():
        checked = src.get("checked")
        age = (today - checked).days if isinstance(checked, dt.date) else None
        if age is None or age > STALE_DAYS:
            rep.add("sources", "warning", "SRC-1", "sources/sources.yaml",
                    f'source "{key}" was last checked {age} days ago; re-check {src.get("url")}')
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate the DITA corpus.")
    ap.add_argument("--skip-grammar", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "build" / "validation.json")
    args = ap.parse_args()
    today = dt.date.today()
    files = [f for f in dita_files() if set_of(f) in SETS]
    rep = Report()
    if not args.skip_grammar:
        stage_grammar(files, rep)
    used = stage_integrity(files, rep)
    stage_rules(files, rep)
    sources = stage_sources(rep, today)
    summary = {
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "files": len(files),
        "errors": rep.count("error"),
        "warnings": rep.count("warning"),
        "grammar_checked": not args.skip_grammar,
        "by_rule": dict(Counter(i["rule"] for i in rep.items)),
        "known_issues": sources.get("known_issues", []),
        "key_usage": {s: dict(c) for s, c in used.items()},
        "items": rep.items,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    for i in rep.items:
        loc = f'{i["file"]}:{i["line"]}' if i["line"] else (i["file"] or "")
        print(f'{i["severity"].upper():7} {i["rule"]:9} {loc}  {i["message"]}')
    print(f"\n{len(files)} files. {summary['errors']} errors, {summary['warnings']} warnings. Report: {rel(args.out)}")
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
