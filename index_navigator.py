"""
index_navigator.py - Algorithmic Layer (IndexNavigator)
Principle: Single Responsibility - disk-based binary search on index.data.

index.data record format (FIXED-WIDTH, exactly 53 bytes per record):
    [keyword: 32 bytes, space-padded ASCII]
    [offset : 12 bytes, zero-padded integer]
    [length :  8 bytes, zero-padded integer]
    [newline:  1 byte  ]
    Total = 32 + 12 + 8 + 1 = 53 bytes

Algorithm: O(log n) -- seek(mid * 53) lands exactly on record boundary.
"""

import os
from typing import Optional, Tuple

RECORD_SIZE = 53      # bytes - must match build_database.py
KEY_WIDTH   = 32      # bytes for keyword field
OFF_WIDTH   = 12      # bytes for offset field
LEN_WIDTH   = 8       # bytes for length field


class IndexNavigator:
    """
    Reads index.data and performs a disk-based binary search.

    Private state:
        _index_path : Absolute path to index.data.
        _fh         : Binary file handle (kept open for efficiency).
        _n_records  : Total number of 53-byte records (computed on open).

    Public interface:
        find(keyword)     -> Optional[Tuple[int, int]]
        total_records()   -> int
        all_keywords()    -> list
        close()
    """

    def __init__(self, index_path: str) -> None:
        self._index_path: str = index_path
        self._n_records: int = 0          # declared explicitly for IDE

        os.makedirs(os.path.dirname(index_path), exist_ok=True)

        if not os.path.exists(index_path):
            open(index_path, "wb").close()

        # Open in binary mode for byte-exact seeks
        self._fh = open(index_path, "rb")  # type: ignore
        self._refresh_count()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_count(self) -> None:
        """Recompute how many records are in index.data."""
        self._fh.seek(0, 2)  # type: ignore
        file_size: int = self._fh.tell()  # type: ignore
        self._n_records = file_size // RECORD_SIZE

    def _read_record(self, record_no: int) -> Optional[Tuple[str, int, int]]:
        """
        Read the record at position `record_no` (0-indexed).
        Returns (keyword_stripped, offset, length) or None on read error.
        """
        self._fh.seek(record_no * RECORD_SIZE)  # type: ignore
        raw: bytes = self._fh.read(RECORD_SIZE)  # type: ignore
        if len(raw) < RECORD_SIZE:
            return None

        # Slice bytes into fields
        key_raw: bytes = raw[0:KEY_WIDTH]  # type: ignore
        off_raw: bytes = raw[KEY_WIDTH:KEY_WIDTH + OFF_WIDTH]  # type: ignore
        len_raw: bytes = raw[KEY_WIDTH + OFF_WIDTH:KEY_WIDTH + OFF_WIDTH + LEN_WIDTH]  # type: ignore

        keyword: str = key_raw.decode("utf-8", errors="replace").rstrip(" ")  # type: ignore
        offset: int  = int(off_raw.decode("ascii").strip())  # type: ignore
        length: int  = int(len_raw.decode("ascii").strip())  # type: ignore

        return keyword, offset, length

    # ------------------------------------------------------------------
    # Binary Search - O(log n)
    # ------------------------------------------------------------------

    def find(self, keyword: str) -> Optional[Tuple[int, int]]:
        """
        Perform disk-based binary search for `keyword`.

        Returns:
            (offset, length) tuple if found.
            None if the keyword does not exist in the index.
        """
        keyword = keyword.lower().strip()

        if self._n_records == 0:
            return None

        left: int  = 0
        right: int = self._n_records - 1

        while left <= right:  # type: ignore
            mid: int = (left + right) // 2  # type: ignore
            record = self._read_record(mid)
            if record is None:
                return None

            key, offset, length = record

            if key == keyword:
                return offset, length
            elif keyword < key:
                right = mid - 1  # type: ignore
            else:
                left = mid + 1  # type: ignore

        return None

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def total_records(self) -> int:
        """Return the number of entries in the index."""
        self._refresh_count()
        return self._n_records

    def all_keywords(self) -> list:
        """
        Return a sorted list of all keywords.
        Useful for autocomplete or verification.
        """
        keywords = []
        n = self._n_records
        for i in range(n):
            record = self._read_record(i)
            if record is not None:
                keywords.append(record[0])
        return keywords

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        if self._fh and not self._fh.closed:  # type: ignore
            self._fh.close()  # type: ignore

    def __enter__(self) -> "IndexNavigator":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"IndexNavigator(path={self._index_path!r}, "
            f"records={self._n_records})"
        )
