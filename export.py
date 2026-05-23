#!/usr/bin/env python3
"""
Bible Data Exporter - Converts bible_data.json into individual per-translation
files formatted as flat verse lists.

Output format per verse:
    { "book": "Genesis", "chapter": 1, "verse": 1, "text": "In the beginning..." }

Output structure:
    versions/
        NIV/
            NIV_bible.json
        ESV/
            ESV_bible.json
        ...

Usage:
    python export.py
    python export.py --input bible_data.json --output versions
    python export.py --version NIV           # Export a single translation only
"""

import json
import argparse
import sys
import re
from pathlib import Path

import verify


VERSION_CODE_MAP: dict[str, str] = {
    "AMERICAN STANDARD VERSION": "ASV",
    "AMPLIFIED BIBLE": "AMP",
    "ANDERSON NEW TESTAMENT": "ANDERSON",
    "ARAMAIC BIBLE IN PLAIN ENGLISH": "ABPE",
    "BEREAN ANNOTATED BIBLE": "BAB",
    "BEREAN LITERAL BIBLE": "BLB",
    "BEREAN STANDARD BIBLE": "BSB",
    "BRENTON SEPTUAGINT TRANSLATION": "BST",
    "CATHOLIC PUBLIC DOMAIN VERSION": "CPDV",
    "CHRISTIAN STANDARD BIBLE": "CSB",
    "CONTEMPORARY ENGLISH VERSION": "CEV",
    "DOUAY-RHEIMS BIBLE": "DRB",
    "ENGLISH REVISED VERSION": "ERV",
    "ENGLISH STANDARD VERSION": "ESV",
    "GOD'S WORDŽ TRANSLATION": "GWT",
    "GOD'S WORD® TRANSLATION": "GWT",
    "GODBEY NEW TESTAMENT": "GODB",
    "GOOD NEWS TRANSLATION": "GNT",
    "HAWEIS NEW TESTAMENT": "HAWEIS",
    "HOLMAN CHRISTIAN STANDARD BIBLE": "HCSB",
    "INTERNATIONAL STANDARD VERSION": "ISV",
    "JPS TANAKH 1917": "JPS",
    "KING JAMES BIBLE": "KJV",
    "LAMSA BIBLE": "LAMSA",
    "LEGACY STANDARD BIBLE": "LSB",
    "LITERAL STANDARD VERSION": "LSV",
    "MACE NEW TESTAMENT": "MACE",
    "MAJORITY STANDARD BIBLE": "MSB",
    "NASB 1977": "NASB1977",
    "NASB 1995": "NASB1995",
    "NET BIBLE": "NET",
    "NEW AMERICAN BIBLE": "NAB",
    "NEW AMERICAN STANDARD BIBLE": "NASB",
    "NEW HEART ENGLISH BIBLE": "NHEB",
    "NEW INTERNATIONAL VERSION": "NIV",
    "NEW KING JAMES VERSION": "NKJV",
    "NEW LIVING TRANSLATION": "NLT",
    "NEW REVISED STANDARD VERSION": "NRSV",
    "PESHITTA HOLY BIBLE TRANSLATED": "HPBT",
    "SMITH'S LITERAL TRANSLATION": "SLT",
    "WEBSTER'S BIBLE TRANSLATION": "WBT",
    "WEYMOUTH NEW TESTAMENT": "WEY",
    "WORLD ENGLISH BIBLE": "WEB",
    "WORRELL NEW TESTAMENT": "WORRELL",
    "WORSLEY NEW TESTAMENT": "WORSLEY",
    "YOUNG'S LITERAL TRANSLATION": "YLT",
}


def export_code(version_name: str) -> str:
    """Return the short output code used for folders and JSON filenames."""
    mapped = VERSION_CODE_MAP.get(version_name)
    if mapped:
        return mapped

    safe_code = re.sub(r"[^A-Z0-9]+", "_", version_name.upper()).strip("_")
    return safe_code or "UNKNOWN"


def resolve_requested_version(requested: str, bible_data: dict) -> str | None:
    """Allow --version to accept either the scraped long name or output code."""
    if requested in bible_data:
        return requested

    requested_code = requested.upper()
    for version_name in bible_data:
        if export_code(version_name) == requested_code:
            return version_name

    return None


def export_version(version_name: str, version_data: dict, output_path: Path) -> tuple[int, Path]:
    """Flatten and export a single translation. Returns verse count written."""
    version_code = export_code(version_name)
    version_dir = output_path / version_code
    version_dir.mkdir(parents=True, exist_ok=True)

    output_file = version_dir / f"{version_code}_bible.json"

    flat_data: list[dict] = []

    if isinstance(version_data, dict):
        for book, chapters in version_data.items():
            if not isinstance(chapters, dict):
                continue
            for chapter in sorted(chapters.keys(), key=lambda x: int(x)):
                verses = chapters[chapter]
                if not isinstance(verses, dict):
                    continue
                for verse in sorted(verses.keys(), key=lambda x: int(x)):
                    flat_data.append(
                        {
                            "book": book,
                            "chapter": int(chapter),
                            "verse": int(verse),
                            "text": verses[verse],
                        }
                    )

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(flat_data, f, indent=2, ensure_ascii=False)

    return len(flat_data), output_file


def find_book_data(version_data: dict, canonical_book: str) -> dict | None:
    """Find book data using canonical or underscore-style book keys."""
    book_data = version_data.get(canonical_book)
    if book_data is not None:
        return book_data

    for alias, canon in verify.BOOK_NAME_ALIASES.items():
        if canon == canonical_book and alias in version_data:
            return version_data[alias]

    underscore_name = canonical_book.replace(" ", "_")
    return version_data.get(underscore_name)


def detect_scope(version_data: dict) -> tuple[str, list[str]]:
    """Detect whether a translation is full Bible, OT only, NT only, or empty."""
    has_ot = any(find_book_data(version_data, book) is not None for book in verify.OT_BOOKS)
    has_nt = any(find_book_data(version_data, book) is not None for book in verify.NT_BOOKS)

    if has_ot and not has_nt:
        return "OT Only", verify.OT_BOOKS
    if has_nt and not has_ot:
        return "NT Only", verify.NT_BOOKS
    if not has_ot and not has_nt:
        return "Empty", []
    return "Full Bible", list(verify.BIBLE_STRUCTURE.keys())


def analyze_book(
    version_name: str,
    version_data: dict,
    canonical_book: str,
) -> dict:
    """Return completeness stats for a single book in one translation."""
    book_data = find_book_data(version_data, canonical_book)
    present = 0
    expected = 0
    missing = 0
    source_blank = 0
    source_unavailable = 0
    standard_omissions = 0

    for chapter_idx, verse_count in enumerate(verify.BIBLE_STRUCTURE[canonical_book], start=1):
        chapter_data = book_data.get(str(chapter_idx)) if isinstance(book_data, dict) else None

        for verse_idx in range(1, verse_count + 1):
            expected += 1
            verse_text = chapter_data.get(str(verse_idx)) if isinstance(chapter_data, dict) else None
            if verse_text is not None and str(verse_text).strip():
                present += 1
                continue

            ref = (canonical_book, chapter_idx, verse_idx)
            if ref in verify.STANDARD_OMISSIONS:
                standard_omissions += 1
            elif verify.is_source_blank(version_name, canonical_book, chapter_idx, verse_idx):
                source_blank += 1
            elif verify.is_source_unavailable(version_name, canonical_book, chapter_idx, verse_idx):
                source_unavailable += 1
            else:
                missing += 1

    source_limits = source_blank + source_unavailable
    adjusted_expected = expected - standard_omissions - source_limits
    status = "OK"
    if missing:
        status = "MISSING"
    elif source_limits:
        status = "SOURCE_LIMITS"

    return {
        "book": canonical_book,
        "present": present,
        "expected": adjusted_expected,
        "missing": missing,
        "source_blank": source_blank,
        "source_unavailable": source_unavailable,
        "source_limits": source_limits,
        "status": status,
    }


def analyze_version(version_name: str, version_data: dict) -> dict:
    """Return export completeness stats for a translation."""
    scope, books_to_check = detect_scope(version_data)
    book_rows = [
        analyze_book(version_name, version_data, canonical_book)
        for canonical_book in books_to_check
    ]

    complete_books = sum(1 for row in book_rows if row["status"] == "OK")
    limited_books = sum(1 for row in book_rows if row["status"] == "SOURCE_LIMITS")
    incomplete_books = sum(1 for row in book_rows if row["status"] == "MISSING")
    missing = sum(row["missing"] for row in book_rows)
    source_blank = sum(row["source_blank"] for row in book_rows)
    source_unavailable = sum(row["source_unavailable"] for row in book_rows)
    present = sum(row["present"] for row in book_rows)
    expected = sum(row["expected"] for row in book_rows)

    status = "OK"
    if missing:
        status = "INCOMPLETE"
    elif source_blank or source_unavailable:
        status = "SOURCE_LIMITS"

    return {
        "scope": scope,
        "book_count": len(books_to_check),
        "complete_books": complete_books,
        "limited_books": limited_books,
        "incomplete_books": incomplete_books,
        "present": present,
        "expected": expected,
        "missing": missing,
        "source_blank": source_blank,
        "source_unavailable": source_unavailable,
        "status": status,
        "book_rows": book_rows,
    }


def print_export_report(report_rows: list[dict]) -> None:
    """Print a compact table describing exported completeness."""
    print("\nExport completeness:")
    print(
        f"  {'Code':<10} {'Scope':<12} {'Books':>5} {'OK':>5} {'Limited':>7}"
        f" {'Bad':>5} {'Verses':>8} {'Expected':>8} {'Missing':>8} {'SrcLimit':>8} {'Status':>13}"
    )
    print(
        f"  {'-'*10} {'-'*12} {'-'*5} {'-'*5} {'-'*7}"
        f" {'-'*5} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*13}"
    )

    issue_rows: list[dict] = []
    for row in report_rows:
        stats = row["stats"]
        source_limits = stats["source_blank"] + stats["source_unavailable"]
        print(
            f"  {row['code']:<10} {stats['scope']:<12} {stats['book_count']:>5}"
            f" {stats['complete_books']:>5} {stats['limited_books']:>7}"
            f" {stats['incomplete_books']:>5} {stats['present']:>8,}"
            f" {stats['expected']:>8,} {stats['missing']:>8,}"
            f" {source_limits:>8,} {stats['status']:>13}"
        )

        for book_row in stats["book_rows"]:
            if book_row["status"] != "OK":
                issue_rows.append({"code": row["code"], **book_row})

    if not issue_rows:
        return

    print("\nBooks with missing/source-limited content:")
    print(
        f"  {'Code':<10} {'Book':<24} {'Verses':>8} {'Expected':>8}"
        f" {'Missing':>8} {'SrcBlank':>8} {'SrcNA':>8} {'Status':>13}"
    )
    print(
        f"  {'-'*10} {'-'*24} {'-'*8} {'-'*8}"
        f" {'-'*8} {'-'*8} {'-'*8} {'-'*13}"
    )
    for row in issue_rows:
        print(
            f"  {row['code']:<10} {row['book']:<24} {row['present']:>8,}"
            f" {row['expected']:>8,} {row['missing']:>8,}"
            f" {row['source_blank']:>8,} {row['source_unavailable']:>8,}"
            f" {row['status']:>13}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export bible_data.json into individual flat translation files"
    )
    parser.add_argument(
        "--input", "-i",
        default="bible_data.json",
        help="Input JSON file (default: bible_data.json)",
    )
    parser.add_argument(
        "--output", "-o",
        default="versions",
        help="Output directory (default: versions/)",
    )
    parser.add_argument(
        "--version", "-v",
        default=None,
        help="Export only a specific translation by short code or full name (e.g. NIV, ESV)",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip the export completeness report",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: '{args.input}' not found.")
        sys.exit(1)

    print(f"Loading {args.input}...")
    with open(input_path, "r", encoding="utf-8") as f:
        bible_data: dict = json.load(f)

    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    requested_version = resolve_requested_version(args.version, bible_data) if args.version else None
    versions_to_export = (
        {requested_version: bible_data[requested_version]}
        if requested_version
        else bible_data
    )

    if args.version and requested_version is None:
        print(f"Error: Translation '{args.version}' not found.")
        available = ", ".join(
            f"{export_code(version_name)} ({version_name})"
            for version_name in sorted(bible_data.keys())
        )
        print(f"Available: {available}")
        sys.exit(1)

    print(f"Found {len(bible_data)} translations. Exporting {len(versions_to_export)}...\n")

    report_rows: list[dict] = []
    for version_name, version_data in sorted(versions_to_export.items()):
        count, out_file = export_version(version_name, version_data, output_path)
        size_kb = out_file.stat().st_size / 1024
        code = export_code(version_name)
        print(
            f"  {code:<10} {count:>7,} verses  "
            f"({size_kb:.1f} KB)  {version_name}"
        )
        if not args.no_report:
            report_rows.append(
                {
                    "code": code,
                    "version_name": version_name,
                    "stats": analyze_version(version_name, version_data),
                }
            )

    if report_rows:
        print_export_report(report_rows)

    print(f"\nDone! Files written to: {output_path.resolve()}")
    print("Copy the translation folders you need into your app's resource directory (e.g., your-app/resources/bibles/)")


if __name__ == "__main__":
    main()
