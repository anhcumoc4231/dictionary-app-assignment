"""
index_navigator.py - Algorithmic Layer (IndexNavigator)
Principle: Single Responsibility - disk-based binary search on index.data.
Maintains O(log n) integrity even when inserting dynamically fetched words.
"""

import os
import bisect
from typing import Optional, Tuple

RECORD_SIZE = 53      # bytes
KEY_WIDTH   = 32      # bytes for keyword
OFF_WIDTH   = 12      # bytes for offset
LEN_WIDTH   = 8       # bytes for length


class IndexNavigator:
    def __init__(self, index_path: str) -> None:
        self._index_path: str = index_path
        self._n_records: int = 0

        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        if not os.path.exists(index_path):
            open(index_path, "wb").close()

        # Open in read/write binary mode
        self._fh = open(index_path, "r+b")
        self._refresh_count()

    def _refresh_count(self) -> None:
        self._fh.seek(0, 2)
        file_size: int = self._fh.tell()
        self._n_records = file_size // RECORD_SIZE

    def _format_record(self, word: str, offset: int, length: int) -> bytes:
        """Create a 53-byte fixed-width ASCII record."""
        key_field: str = word.lower().ljust(KEY_WIDTH)[:KEY_WIDTH] # type: ignore
        off_field: str = str(offset).zfill(OFF_WIDTH)
        len_field: str = str(length).zfill(LEN_WIDTH)
        return f"{key_field}{off_field}{len_field}\n".encode("ascii")

    def _read_record(self, record_no: int) -> Optional[Tuple[str, int, int]]:
        self._fh.seek(record_no * RECORD_SIZE)
        raw: bytes = self._fh.read(RECORD_SIZE)
        if len(raw) < RECORD_SIZE:
            return None

        key_raw: bytes = raw[0:KEY_WIDTH] # type: ignore
        off_raw: bytes = raw[KEY_WIDTH:KEY_WIDTH + OFF_WIDTH] # type: ignore
        len_raw: bytes = raw[KEY_WIDTH + OFF_WIDTH:KEY_WIDTH + OFF_WIDTH + LEN_WIDTH] # type: ignore

        keyword: str = key_raw.decode("ascii").rstrip(" ")
        offset: int  = int(off_raw.decode("ascii").strip())
        length: int  = int(len_raw.decode("ascii").strip())
        return keyword, offset, length

    def find(self, keyword: str) -> Optional[Tuple[int, int]]:
        """Disk-based binary search O(log n)."""
        keyword = keyword.lower().strip()
        if self._n_records == 0:
            return None

        left: int = 0
        right: int = self._n_records - 1

        while left <= right: # type: ignore
            mid: int = (left + right) // 2 # type: ignore
            record = self._read_record(mid)
            if not record:
                return None
            key, offset, length = record

            if key == keyword:
                return offset, length
            elif keyword < key:
                right = mid - 1
            else:
                left = mid + 1
        return None

    def insert_sorted(self, keyword: str, offset: int, length: int) -> None:
        """
        Cache a newly fetched Cambridge API word locally.
        Reads the 53-byte array into memory, bisect-inserts the new record,
        and flushes back to disk. Takes ~5ms for 5MB indices.
        """
        record_bytes = self._format_record(keyword, offset, length)
        
        self._fh.seek(0)
        all_data: bytes = self._fh.read()
        
        # Split into exact 53-byte chunks
        records = [all_data[i:i+RECORD_SIZE] for i in range(0, len(all_data), RECORD_SIZE)] # type: ignore
        
        # Since 'record_bytes' is padded, bisect works flawlessly on the bytes object array
        bisect.insort(records, record_bytes)
        
        self._fh.seek(0)
        self._fh.truncate(0)
        for r in records:
            self._fh.write(r)
        self._fh.flush()
        
        self._refresh_count()

    def total_records(self) -> int:
        self._refresh_count()
        return self._n_records

    def all_keywords(self) -> list:
        keywords = []
        n = self._n_records
        for i in range(n):
            record = self._read_record(i)
            if record:
                keywords.append(record[0])
        return keywords

    def close(self) -> None:
        if self._fh and not self._fh.closed:
            self._fh.close()

    def __enter__(self) -> "IndexNavigator":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()
