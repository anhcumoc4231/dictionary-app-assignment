"""
build_index.py - Rebuild index.data from existing meaning.data.
=============================================================
Use when:
  - You add entries manually to meaning.data
  - Need to re-sort the index after merging external data
  - Want to verify index integrity

Usage:
  python build_index.py

Note: This script does NOT re-read CSV/JSON source files. To rebuild from
scratch, run python build_database.py instead.
"""

import os
import sys
import json

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DATA_DIR      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MEANING_FILE  = os.path.join(DATA_DIR, "meaning.data")
INDEX_FILE    = os.path.join(DATA_DIR, "index.data")

RECORD_SIZE   = 53
KEY_WIDTH     = 32
OFF_WIDTH     = 12
LEN_WIDTH     = 8


def scan_meaning_file() -> list:
    """
    Scan meaning.data and return a list of (keyword, offset, length) tuples.
    Reads sequentially, using JSON brace-depth tracking to find boundaries.
    """
    entries: list = []

    with open(MEANING_FILE, "rb") as f:
        data: bytes = f.read()

    offset: int = 0
    total: int = len(data)

    while offset < total:
        start: int  = offset
        depth: int  = 0
        i: int      = offset
        in_string   = False
        escape      = False

        while i < total:
            c: int = data[i] # type: ignore
            ch: str = chr(c)

            if escape:
                escape = False
            elif ch == "\\" and in_string:
                escape = True
            elif ch == '"' and not escape:
                in_string = not in_string
            elif not in_string:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
            i += 1

        chunk: bytes = data[start:i] # type: ignore
        byte_length: int = len(chunk)

        try:
            obj = json.loads(chunk.decode("utf-8")) # type: ignore
            word: str = str(obj.get("word", "")).lower().strip() # type: ignore
            if word:
                entries.append((word, start, byte_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass  # Skip malformed chunks

        offset = i

    return entries


def _format_record(word: str, offset: int, length: int) -> bytes:
    """Build one 53-byte fixed-width index record."""
    key_field: str = word.lower().ljust(KEY_WIDTH)[:KEY_WIDTH] # type: ignore
    off_field: str = str(offset).zfill(OFF_WIDTH) # type: ignore
    len_field: str = str(length).zfill(LEN_WIDTH) # type: ignore
    record: str = f"{key_field}{off_field}{len_field}\n"
    return record.encode("ascii")


def rebuild_index() -> None:
    print("=" * 50)
    print("Index Rebuilder")
    print("=" * 50)

    if not os.path.exists(MEANING_FILE):
        print("ERROR: meaning.data not found. Run build_database.py first.")
        return

    print(f"\n[1] Scanning {MEANING_FILE} ...")
    entries: list = scan_meaning_file()
    print(f"  Found {len(entries)} entries.")

    print("\n[2] Sorting alphabetically ...")
    entries.sort(key=lambda x: x[0]) # type: ignore

    print(f"\n[3] Writing index.data ({RECORD_SIZE}-byte fixed-width records) ...")
    with open(INDEX_FILE, "wb") as f:
        for word, entry_offset, entry_length in entries:
            record: bytes = _format_record(word, entry_offset, entry_length)
            assert len(record) == RECORD_SIZE, (
                f"Record for '{word}' is {len(record)} bytes, expected {RECORD_SIZE}"
            )
            f.write(record)

    idx_size: int = os.path.getsize(INDEX_FILE)
    print(f"\n[OK] Written {len(entries)} records  ({idx_size:,} bytes)")
    assert idx_size % RECORD_SIZE == 0, "ERROR: index size not divisible by RECORD_SIZE"
    print(f"[OK] Integrity check PASSED -- {RECORD_SIZE} bytes/record")


if __name__ == "__main__":
    rebuild_index()
