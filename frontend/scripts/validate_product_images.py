"""Validate product-type coverage without modifying the catalog database."""

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAPPING = ROOT / "frontend" / "src" / "productImages.js"
DATABASE = ROOT / "data" / "db" / "ecommerce.db"


def normalize(value):
    return " ".join(str(value or "").strip().lower().split())


def mapping_entries(source):
    block = source.split("const TYPE_IMAGES = {", 1)[1].split("};", 1)[0]
    entries = {}
    for match in re.finditer(r'^\s*(?:"([^"]+)"|([\w-]+)):\s*PHOTO\("([^"]+)"\)', block, re.MULTILINE):
        entries[normalize(match.group(1) or match.group(2))] = match.group(3)
    return entries


def unavailable_entries(source):
    marker = "export const UNAVAILABLE_TYPES = new Set(["
    if marker not in source:
        return set()
    block = source.split(marker, 1)[1].split("]);", 1)[0]
    return {normalize(value) for value in re.findall(r'"([^"]+)"', block)}


def related_entries(source):
    block = source.split("const RELATED_TYPE_IMAGES = {", 1)[1].split("};", 1)[0]
    entries = {}
    for match in re.finditer(r'^\s*(?:"([^"]+)"|([\w-]+)):\s*\[([^\]]*)\]', block, re.MULTILINE):
        entries[normalize(match.group(1) or match.group(2))] = [normalize(value) for value in re.findall(r'"([^"]+)"', match.group(3))]
    return entries


def main():
    source = MAPPING.read_text(encoding="utf-8")
    entries = mapping_entries(source)
    unavailable = unavailable_entries(source)
    related = related_entries(source)
    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute("SELECT product_type, department, COUNT(*) FROM products GROUP BY product_type, department ORDER BY product_type").fetchall()

    missing = [(product_type, department, count) for product_type, department, count in rows if normalize(product_type) not in entries and normalize(product_type) not in related and normalize(product_type) not in unavailable]
    explicitly_unavailable = [(product_type, department, count) for product_type, department, count in rows if normalize(product_type) in unavailable]
    bad_related_targets = [(product_type, target) for product_type, targets in related.items() for target in targets if target not in entries]
    duplicate_urls = {}
    for product_type, url_id in entries.items():
        duplicate_urls.setdefault(url_id, []).append(product_type)
    duplicate_urls = {url_id: types for url_id, types in duplicate_urls.items() if len(types) > 1}

    print(f"observed_product_types={len(rows)}")
    print(f"mapped_product_types={sum(normalize(product_type) in entries for product_type, _, _ in rows)}")
    print(f"related_fallback_types={sum(normalize(product_type) in related for product_type, _, _ in rows)}")
    for product_type, _, _ in rows:
        normalized = normalize(product_type)
        if normalized in related:
            print(f"RELATED|{product_type}|{', '.join(related[normalized])}")
    print(f"explicit_placeholder_types={len(explicitly_unavailable)}")
    print(f"unmapped_product_types={len(missing)}")
    if missing:
        for product_type, department, count in missing:
            print(f"UNMAPPED|{product_type}|{department}|{count}")
    for product_type, department, count in explicitly_unavailable:
        print(f"PLACEHOLDER|{product_type}|{department}|{count}")
    for product_type, target in bad_related_targets:
        print(f"BAD_RELATED_TARGET|{product_type}|{target}")
    if duplicate_urls:
        print("related_shared_sources=")
        for url_id, types in sorted(duplicate_urls.items()):
            print(f"  {', '.join(types)} -> {url_id}")
    if missing or bad_related_targets:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
