"""
storage.py - Persistence Layer (StorageEngine)
Principle: Single Responsibility - abstracts all low-level disk I/O.

meaning.data layout:
    Raw UTF-8 JSON bytes, packed sequentially.
    Each entry is located by (offset, length) pairs stored in index.data.
    The file is opened once and kept open for the lifetime of the engine.
"""

import os
import sys

# Ensure the project root is on the path so imports work from any working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import LexicalEntry # type: ignore  # type: ignore  # noqa: E402


class StorageEngine:
    """
    Manages binary read/write access to meaning.data.

    Private state:
        _data_path  : Absolute path to meaning.data.
        _fh         : Binary file handle (kept open for efficiency).

    Public interface:
        read_entry(offset, length) -> LexicalEntry
        append_entry(entry)        -> tuple[int, int]
        truncate()
        size()                     -> int
        close()
    """

    def __init__(self, data_path: str) -> None:
        self._data_path: str = data_path
        dir_path = os.path.dirname(data_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        # Create the file if it does not exist yet
        if not os.path.exists(data_path):
            open(data_path, "wb").close()

        # Open in read-write binary mode (no truncation)
        self._fh = open(data_path, "r+b")  # type: ignore

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def read_entry(self, offset: int, length: int) -> LexicalEntry:
        """
        Seek to `offset` in meaning.data, read exactly `length` bytes,
        and deserialize into a LexicalEntry.

        NOTE: `length` is byte-length (UTF-8 encoded), NOT char-length.
        Vietnamese diacritics consume 2-3 bytes each in UTF-8.
        """
        self._fh.seek(offset)  # type: ignore
        raw: bytes = self._fh.read(length)  # type: ignore
        return LexicalEntry.from_bytes(raw)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def append_entry(self, entry: LexicalEntry) -> tuple:
        """
        Serialize `entry` to UTF-8 bytes and append to meaning.data.

        Returns:
            (offset, length) - the physical coordinates of the written data.
        """
        data: bytes = entry.to_bytes()
        byte_length: int = len(data)

        self._fh.seek(0, 2)              # type: ignore
        offset: int = self._fh.tell()   # type: ignore
        self._fh.write(data)  # type: ignore
        self._fh.flush()  # type: ignore

        return offset, byte_length

    def truncate(self) -> None:
        """Erase all content in meaning.data (used during full rebuilds)."""
        self._fh.seek(0)  # type: ignore
        self._fh.truncate(0)  # type: ignore
        self._fh.flush()  # type: ignore

    def size(self) -> int:
        """Return current byte-size of the data file."""
        self._fh.seek(0, 2)  # type: ignore
        return self._fh.tell()  # type: ignore

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Flush and close the underlying file handle."""
        if self._fh and not self._fh.closed:  # type: ignore
            self._fh.flush()  # type: ignore
            self._fh.close()  # type: ignore

    def __enter__(self) -> "StorageEngine":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"StorageEngine(path={self._data_path!r}, open={not self._fh.closed})"  # type: ignore
