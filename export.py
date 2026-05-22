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
from pathlib import Path


def export_version(version_code: str, version_data: dict, output_path: Path) -> int:
    """Flatten and export a single translation. Returns verse count written."""
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

    return len(flat_data)


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
        help="Export only a specific translation (e.g. NIV, ESV)",
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

    versions_to_export = (
        {args.version: bible_data[args.version]}
        if args.version and args.version in bible_data
        else bible_data
    )

    if args.version and args.version not in bible_data:
        print(f"Error: Translation '{args.version}' not found.")
        print(f"Available: {', '.join(bible_data.keys())}")
        sys.exit(1)

    print(f"Found {len(bible_data)} translations. Exporting {len(versions_to_export)}...\n")

    for version_code, version_data in sorted(versions_to_export.items()):
        count = export_version(version_code, version_data, output_path)
        out_file = output_path / version_code / f"{version_code}_bible.json"
        size_kb = out_file.stat().st_size / 1024
        print(f"  {version_code:<20} {count:>7,} verses  ({size_kb:.1f} KB)")

    print("\nDone! Files written to: {output_path.resolve()}")
    print("Copy the translation folders you need into your app's resource directory (e.g., your-app/resources/bibles/)")


if __name__ == "__main__":
    main()
