#!/usr/bin/env python3
"""Validate the generated offline wiki without third-party Python packages.

Usage:
  python validate_wiki.py --html path/to/index.html --repo path/to/repository \
      --report audit/html-integrity.json

Optional --expected-markdown and --expected-game-json assert edition counts.
Coverage is always compared with the supplied checkout, even without these
count assertions. Git must be available to enumerate tracked Markdown files.
Exit status: 0 = pass, 1 = integrity findings, 2 = input/invocation failure.
This is a static integrity check, not a browser or gameplay test.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, unquote_to_bytes, urlsplit
import xml.etree.ElementTree as ET


VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


class Node:
    def __init__(self, tag, attrs=(), parent=None, line=0):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.line = line
        self.children = []

    def text(self):
        return "".join(child.text() if isinstance(child, Node) else child
                       for child in self.children)

    def descendants(self, tag=None):
        for child in self.children:
            if isinstance(child, Node):
                if tag is None or child.tag == tag:
                    yield child
                yield from child.descendants(tag)

    def closest(self, tag=None, css_class=None):
        node = self
        while node is not None:
            if ((tag is None or node.tag == tag) and
                    (css_class is None or css_class in node.attrs.get("class", "").split())):
                return node
            node = node.parent
        return None


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]
        self.nodes = []

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1], self.getpos()[0])
        self.stack[-1].children.append(node)
        self.nodes.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo, *args):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True, encoding="utf-8",
        stderr=subprocess.PIPE,
    ).strip()


def short_id(value):
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")


def strict_json(raw):
    def invalid_constant(value):
        raise ValueError("Non-standard JSON numeric constant: " + value)
    return json.loads(raw, parse_constant=invalid_constant)


def same_json(left, right):
    """Compare JSON values, keeping booleans distinct from numeric 0 and 1."""
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(same_json(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same_json(a, b) for a, b in zip(left, right))
    return left == right and (
        type(left) is type(right) or
        isinstance(left, (int, float)) and isinstance(right, (int, float))
    )


def source_link(href):
    parts = urlsplit(href)
    match = re.search(r"/blob/([^/]+)/(.+)$", parts.path)
    return (match.group(1), unquote(match.group(2))) if match else None


def location(node):
    article = node.closest("article")
    return {"line": node.line, "page": article.attrs.get("id") if article else None}


def validate(args):
    repo = args.repo.resolve()
    html_path = args.html.resolve()
    from wiki_inputs import check_products
    root=Path(__file__).resolve().parent
    config=json.loads((root/'wiki-config.json').read_text(encoding='utf-8'))
    binding=check_products(root,repo,config,html_path)
    head=config['commit']
    tracked=sorted(binding['source']['files'])
    expected_docs = {p for p in tracked if p.lower().endswith(".md") and (repo / p).is_file()}
    expected_data = {p for p in tracked if p.startswith("roguelike/data/") and p.endswith(".json") and (repo / p).is_file()}
    expected_examples = {p for p in tracked if p.startswith("roguelike/docs/examples/") and p.endswith(".json") and (repo / p).is_file()}
    document = Document()
    document.feed(html_path.read_text(encoding="utf-8"))
    document.close()
    report = {
        "schema_version": 1,
        "validator_version": "1.0",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "html": str(html_path), "html_sha256": digest(html_path),
        "html_bytes": html_path.stat().st_size,
        "repository": str(repo), "repository_head": head,
        "expected_count_assertions": {"markdown": args.expected_markdown, "game_json": args.expected_game_json},
        "checks": {}, "errors": [], "skips": [],
        "limitations": [
            "Static checks do not execute JavaScript, simulate browser layout, verify clipboard/download behavior, or test gameplay.",
            "External ordinary hyperlinks are permitted and are not fetched or checked for availability.",
            "Source coverage checks one rendered source article, pinned path, revision and displayed source hash per tracked Markdown file; they do not independently re-render Markdown or compare every rendered word.",
            "Runtime asset checking covers declared HTML resources, CSS url()/@import, and embedded SVG references. It is not a JavaScript interpreter or a proof against dynamically constructed network requests.",
            "Unbraced JSON documentation entries are syntax-checked after temporary braces are added. Abbreviated historical examples containing an unquoted ellipsis are reported separately, not treated as machine payloads.",
        ],
    }

    def fail(check, message, **context):
        report["errors"].append({"check": check, "message": message, **context})

    def coverage(name, expected, actual):
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        report["checks"][name] = {
            "expected": len(expected), "observed": len(actual),
            "missing": missing, "unexpected": extra,
        }
        if missing or extra:
            fail(name, "Coverage differs from the supplied repository.", missing=missing, unexpected=extra)

    if args.expected_markdown is not None and len(expected_docs) != args.expected_markdown:
        fail("edition_counts", "Tracked Markdown count differs from the requested edition count.", expected=args.expected_markdown, actual=len(expected_docs))
    if args.expected_game_json is not None and len(expected_data) != args.expected_game_json:
        fail("edition_counts", "Game JSON count differs from the requested edition count.", expected=args.expected_game_json, actual=len(expected_data))

    id_nodes = {}
    id_counts = Counter()
    for node in document.nodes:
        identifier = node.attrs.get("id")
        if identifier is not None:
            id_counts[identifier] += 1
            id_nodes.setdefault(identifier, node)
    duplicates = {k: v for k, v in id_counts.items() if v > 1}
    report["checks"]["html_ids"] = {"unique": len(id_counts), "duplicate_ids": duplicates}
    if duplicates:
        fail("html_ids", "Duplicate HTML IDs.", duplicates=duplicates)

    internal_count = 0
    external_links = 0
    for node in document.nodes:
        href = node.attrs.get("href", "")
        if href.startswith("#"):
            internal_count += 1
            target = unquote(href[1:])
            if target and target not in id_nodes:
                fail("internal_hrefs", "Internal href has no target.", target=target, **location(node))
        elif node.tag == "a" and urlsplit(href).scheme in {"http", "https", "mailto"}:
            external_links += 1
        for attribute in ("data-download", "data-filter", "data-expand", "data-filter-count", "for"):
            target = node.attrs.get(attribute)
            if target and target not in id_nodes:
                fail("ui_targets", "UI attribute has no target.", attribute=attribute, target=target, **location(node))
    report["checks"]["internal_hrefs"] = {"checked": internal_count, "external_hyperlinks_permitted": external_links}

    articles = {n.attrs.get("id"): n for n in document.nodes if n.tag == "article" and "data-page" in n.attrs}
    for identifier, article in articles.items():
        if article.attrs["data-page"] != identifier:
            fail("article_metadata", "Article ID and data-page differ.", page=identifier)
    report["checks"]["articles"] = dict(Counter(n.attrs.get("data-kind") for n in articles.values()))

    payloads = {}
    json_script_count = 0
    for node in document.nodes:
        if node.tag == "script" and node.attrs.get("type", "").split(";")[0].strip().lower() in {"application/json", "application/ld+json", "importmap"}:
            json_script_count += 1
            try:
                payloads[node.attrs.get("id", f"script-at-{node.line}")] = strict_json(node.text())
            except ValueError as error:
                fail("embedded_json", str(error), payload=node.attrs.get("id"), **location(node))
    report["checks"]["json_scripts"] = {"checked": json_script_count, "parsed": len(payloads)}

    code_values = {}
    complete_json = 0
    wrapped_fragments = 0
    ellipses = 0
    json_code_nodes = [n for n in document.nodes if n.tag == "code" and "language-json" in n.attrs.get("class", "").split()]
    for node in json_code_nodes:
        raw = node.text().strip()
        try:
            code_values[id(node)] = strict_json(raw)
            complete_json += 1
            continue
        except ValueError as original_error:
            message = str(original_error)
        if node.closest(css_class="data-record") is not None:
            fail("catalog_json", message, **location(node))
            continue
        if raw.startswith('"'):
            try:
                strict_json("{" + raw.rstrip(",") + "}")
                wrapped_fragments += 1
                report["skips"].append({"check": "standalone_json_document", "reason": "Documentation insertion fragment; valid after temporary object braces.", **location(node)})
                continue
            except ValueError:
                pass
        without_strings = re.sub(r'"(?:\\.|[^"\\])*"', '""', raw)
        article = node.closest("article")
        if "..." in without_strings and article is not None and article.attrs.get("data-kind") == "source":
            ellipses += 1
            report["skips"].append({"check": "standalone_json_document", "reason": "Preserved historical illustration contains an unquoted ellipsis; it is not complete JSON.", **location(node)})
        else:
            fail("document_json", message, **location(node))
    report["checks"]["json_code_blocks"] = {"total": len(json_code_nodes), "complete_parsed": complete_json, "insertion_fragments_syntax_checked": wrapped_fragments, "historical_abbreviations_skipped": ellipses}

    for node in document.nodes:
        if node.tag=='a' and node.closest('article') is not None and node.closest('article').attrs.get('data-kind')=='guide':
            pinned=source_link(node.attrs.get('href',''))
            if pinned and pinned[0]!=head:
                fail('source_revision','Ordinary guide/source link is not pinned to reviewed source',href=node.attrs['href'])
    observed_docs = []
    source_hashes_checked = 0
    for article in articles.values():
        if article.attrs.get("data-kind") != "source":
            continue
        links = [n for n in article.descendants("a") if "Original at this commit" in n.text()]
        if len(links) != 1 or source_link(links[0].attrs.get("href", "")) is None:
            fail("source_coverage", "Source article needs exactly one pinned original link.", page=article.attrs.get("id"))
            continue
        revision, path = source_link(links[0].attrs["href"])
        observed_docs.append(path)
        if revision != head:
            fail("source_revision", "Source link does not identify reviewed source revision.", path=path, revision=revision)
        if article.attrs.get("id") != "source-" + short_id(path):
            fail("source_coverage", "Source article ID does not match its source path.", path=path, page=article.attrs.get("id"))
        if path in expected_docs:
            headers = list(article.descendants("header"))
            match = re.search(r"SHA-256 ([0-9a-f]{12})", headers[0].text() if headers else "")
            if match is None or match.group(1) != binding['source']['files'][path]['raw_sha256'][:12]:
                fail("source_hashes", "Displayed source hash differs from current repository file.", path=path)
            else:
                source_hashes_checked += 1
    for path, count in Counter(observed_docs).items():
        if count != 1:
            fail("source_coverage", "Source path is represented more than once.", path=path, count=count)
    coverage("source_coverage", expected_docs, set(observed_docs))
    report["checks"]["source_hashes"] = {"matched": source_hashes_checked}

    records = {}
    observed_paths = []
    compared_data = 0
    wiki_only = 0
    for record in [n for n in document.nodes if "data-record" in n.attrs.get("class", "").split()]:
        path_nodes = [n for n in record.children if isinstance(n, Node) and n.tag == "p" and "path-label" in n.attrs.get("class", "").split()]
        codes = [n for n in record.descendants("code") if "language-json" in n.attrs.get("class", "").split()]
        if len(path_nodes) != 1 or len(codes) != 1:
            fail("catalog_records", "Record needs one full path and one JSON block.", target=record.attrs.get("id"))
            continue
        path = path_nodes[0].text().strip()
        payload=codes[0].text().encode('utf-8')
        if (record.attrs.get('data-payload-bytes')!=str(len(payload)) or
            record.attrs.get('data-payload-sha256')!=hashlib.sha256(payload).hexdigest()):
            fail('download_identity','Advertised download bytes/hash differ from exact embedded UTF-8 payload.',path=path)
        captured=(binding['wiki'].get(path.removeprefix('wiki/')) if path.startswith('wiki/') else binding['source']['files'].get(path))
        if not captured or record.attrs.get('data-source-bytes')!=str(captured['bytes']) or record.attrs.get('data-source-sha256')!=captured['raw_sha256']:
            fail('source_capture_identity','Advertised raw source differs from recorded capture.',path=path)
        source_file=root/path.removeprefix('wiki/') if path.startswith('wiki/') else repo/path
        if source_file.is_file() and payload!=source_file.read_text(encoding='utf-8-sig').encode('utf-8'):
            fail('download_identity','Payload is not the declared LF/no-BOM source representation.',path=path)
        observed_paths.append(path)
        value = code_values.get(id(codes[0]))
        records[record.attrs.get("id")] = {"path": path, "value": value, "node": record}
        if record.attrs.get("id") != "data-" + short_id(path):
            fail("catalog_records", "Data record ID does not match its path.", path=path, target=record.attrs.get("id"))
        if path.startswith("wiki/"):
            wiki_only += 1
            report["skips"].append({"check": "repository_data_comparison", "path": path, "reason": "New wiki example is outside the game repository; its catalog JSON and search copy are still checked."})
            continue
        file = (repo / path).resolve()
        if not file.is_relative_to(repo) or not file.is_file():
            fail("repository_data_comparison", "Catalog path is not an existing file inside the repository.", path=path)
            continue
        try:
            expected_value = strict_json(file.read_text(encoding="utf-8-sig"))
        except ValueError as error:
            fail("repository_data_comparison", "Repository JSON is invalid: " + str(error), path=path)
            continue
        if id(codes[0]) not in code_values or not same_json(value, expected_value):
            fail("repository_data_comparison", "Embedded JSON value differs from the repository.", path=path)
        else:
            compared_data += 1
        links = [n for n in record.descendants("a") if "Pinned source" in n.text()]
        pinned = source_link(links[0].attrs.get("href", "")) if len(links) == 1 else None
        if pinned != (head, path):
            fail("data_revision", "Data record needs a matching path and reviewed source revision in its pinned link.", path=path, observed=pinned)
    for path, count in Counter(observed_paths).items():
        if count != 1:
            fail("catalog_records", "Data path is represented more than once.", path=path, count=count)
    coverage("game_json_coverage", expected_data, {p for p in observed_paths if p.startswith("roguelike/data/")})
    coverage("repository_example_coverage", expected_examples, {p for p in observed_paths if p.startswith("roguelike/docs/examples/")})
    report["checks"]["repository_data_comparison"] = {"matched": compared_data, "wiki_examples_not_in_repo": wiki_only, "catalog_records": len(records)}

    search = payloads.get("search-index")
    search_seen = Counter()
    search_data_matches = 0
    if not isinstance(search, list):
        fail("search_index", "search-index must be a JSON array.")
        search = []
    for index, row in enumerate(search):
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) for k in ("id", "page", "title", "group", "kind", "text")):
            fail("search_index", "Search row lacks required string fields.", row=index)
            continue
        identifier, page = row["id"], row["page"]
        search_seen[identifier] += 1
        target = id_nodes.get(identifier)
        owner = target.closest("article") if target else None
        if target is None or page not in articles or owner is None or owner.attrs.get("id") != page:
            fail("search_targets", "Search target is missing or belongs to another page.", target=identifier, page=page)
        elif row["kind"] != articles[page].attrs.get("data-kind"):
            fail("search_targets", "Search kind disagrees with its article.", target=identifier, page=page)
        if row["kind"] == "data":
            record = records.get(identifier)
            if record is None:
                fail("search_data", "Search data row has no catalog record.", target=identifier)
                continue
            prefix = record["path"] + " "
            try:
                if not row["text"].startswith(prefix):
                    raise ValueError("Search text does not begin with the catalog path.")
                value = strict_json(row["text"][len(prefix):])
                if not same_json(value, record["value"]):
                    raise ValueError("Search JSON value differs from the catalog JSON.")
                search_data_matches += 1
            except ValueError as error:
                fail("search_data", str(error), target=identifier)
    for identifier, count in search_seen.items():
        if count != 1:
            fail("search_index", "Duplicate search record ID.", target=identifier, count=count)
    expected_search = set(records) | {k for k, a in articles.items() if a.attrs.get("data-kind") != "data"}
    coverage("search_coverage", expected_search, set(search_seen))
    report["checks"]["search_index"] = {"records": len(search), "catalog_json_copies_matched": search_data_matches}

    runtime_refs = []
    css_blocks = []
    embedded_svgs = 0

    def inspect_css(text, where):
        clean = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        for match in re.finditer(r"url\(\s*(?:\"([^\"]*)\"|'([^']*)'|([^)]*))\s*\)", clean, re.I):
            inspect_resource(next(x for x in match.groups() if x is not None).strip(), where + " CSS url()")
        for match in re.finditer(r"@import\s+['\"]([^'\"]+)['\"]", clean, re.I):
            inspect_resource(match.group(1), where + " CSS @import")

    def inspect_resource(url, where):
        nonlocal embedded_svgs
        url = url.strip()
        runtime_refs.append({"where": where, "embedded": url.startswith("data:"), "fragment": url.startswith("#")})
        if not url or url.startswith("#"):
            return
        if not url.startswith("data:"):
            fail("runtime_assets", "Runtime asset is outside the HTML document.", where=where, url=url)
            return
        if url.lower().startswith("data:image/svg+xml"):
            embedded_svgs += 1
            try:
                header, payload = url.split(",", 1)
                raw = base64.b64decode(payload, validate=True) if ";base64" in header.lower() else unquote_to_bytes(payload)
                svg = ET.fromstring(raw)
                for element in svg.iter():
                    tag = element.tag.rsplit("}", 1)[-1] if isinstance(element.tag, str) else ""
                    if tag == "style":
                        inspect_css("".join(element.itertext()), where + " embedded SVG")
                    if "style" in element.attrib:
                        inspect_css(element.attrib["style"], where + " embedded SVG style")
                    if tag in {"image", "use", "script", "feImage"}:
                        for key, value in element.attrib.items():
                            if key.rsplit("}", 1)[-1] in {"href", "src"}:
                                inspect_resource(value, where + " embedded SVG " + tag)
            except (ValueError, ET.ParseError) as error:
                fail("runtime_assets", "Cannot inspect embedded SVG: " + str(error), where=where)

    for node in document.nodes:
        where = f"{node.tag} at HTML line {node.line}"
        if node.tag == "style":
            css_blocks.append((node.text(), where))
        if "style" in node.attrs:
            css_blocks.append((node.attrs["style"], where + " style attribute"))
        if node.tag in {"script", "img", "iframe", "embed", "audio", "video", "source", "track", "input"} and "src" in node.attrs:
            inspect_resource(node.attrs["src"], where + " src")
        if node.tag == "video" and "poster" in node.attrs:
            inspect_resource(node.attrs["poster"], where + " poster")
        if node.tag in {"image", "use", "feimage"}:
            for attr in ("href", "xlink:href"):
                if attr in node.attrs:
                    inspect_resource(node.attrs[attr], where + " " + attr)
        if node.tag == "object" and "data" in node.attrs:
            inspect_resource(node.attrs["data"], where + " data")
        if node.tag == "link" and "href" in node.attrs:
            inspect_resource(node.attrs["href"], where + " link")
        if "srcset" in node.attrs:
            # The current builder emits no srcset. Reject an uninspected
            # extension rather than pretend comma splitting handles data URIs.
            fail("runtime_assets", "srcset requires explicit review; this validator does not parse its candidate grammar.", where=where)
    for css, where in css_blocks:
        inspect_css(css, where)
    report["checks"]["runtime_assets"] = {
        "references_checked": len(runtime_refs),
        "embedded_references": sum(r["embedded"] for r in runtime_refs),
        "fragment_references": sum(r["fragment"] for r in runtime_refs),
        "css_blocks_and_style_attributes_checked": len(css_blocks),
        "embedded_svgs_inspected": embedded_svgs,
        "inline_executable_scripts": sum(n.tag == "script" and n.attrs.get("type", "") not in {"application/json", "application/ld+json", "importmap"} and "src" not in n.attrs for n in document.nodes),
    }
    report["status"] = "pass" if not report["errors"] else "fail"
    report["error_count"] = len(report["errors"])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--html", required=True, type=Path, help="Generated standalone HTML file.")
    parser.add_argument("--repo", required=True, type=Path, help="Local audited Git checkout.")
    parser.add_argument("--report", required=True, type=Path, help="Destination for the complete JSON audit report.")
    parser.add_argument("--expected-markdown", type=int, help="Optional assertion for this edition's tracked Markdown count.")
    parser.add_argument("--expected-game-json", type=int, help="Optional assertion for this edition's game JSON count.")
    args = parser.parse_args()
    try:
        report = validate(args)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Input or invocation failure: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"status": report["status"], "errors": report["error_count"], "report": str(args.report.resolve()), "checks": report["checks"]}, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
