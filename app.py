"""
app.py - Facade Layer (DictionaryApp)
Principle: Coordinates IndexNavigator, StorageEngine, and Cambridge API.
Provides a clean, high-level API consumed by the GUI layer.
"""

import os
import sys
import functools
from typing import Optional

# Ensure the project root is on the path so imports work from any working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import LexicalEntry       # noqa: E402
from storage import StorageEngine     # noqa: E402
from index_navigator import IndexNavigator  # noqa: E402
from cambridge_api import CambridgeClient   # noqa: E402


class DictionaryApp:
    """
    Facade that wires together local storage and the Cambridge online API.
    
    Architecture:
      Local RAM Cache -> Local Disk Binary Search -> Online API -> Caches to Disk
    """

    def __init__(self, data_path: str, index_path: str, api_key: str = "") -> None:
        self._storage = StorageEngine(data_path)
        self._index   = IndexNavigator(index_path)
        self._cambridge = CambridgeClient(api_key=api_key)

        self._lookup_cached = functools.lru_cache(maxsize=256)(self._lookup)

    def set_api_key(self, api_key: str) -> None:
        self._cambridge.set_key(api_key)

    def has_api_key(self) -> bool:
        return self._cambridge.has_key()

    # ------------------------------------------------------------------
    # Core lookup (uncached) - called by the cached wrapper below
    # ------------------------------------------------------------------

    def _lookup(self, keyword: str) -> Optional[LexicalEntry]:
        """
        Internal lookup:
        1. Binary-search the local index (super fast O(log n)).
        2. If missing, query Cambridge API.
        3. If found locally, return.
        4. If found via API, append to meaning.data and index.data, then return.
        """
        # Step 1: Check Local Disk index
        coords = self._index.find(keyword)
        if coords is not None:
            offset, length = coords
            entry = self._storage.read_entry(offset, length)
            entry.source = "Local Cache"  # Tag it to show in UI
            return entry

        # Step 2: Fallback to Online API
        if not self.has_api_key():
            print("[App] Không có sẵn trên máy và chưa cấu hình Cambridge API Key.")
            return None

        # Fetch from the internet
        entry = self._cambridge.fetch_word(keyword)
        
        # Step 3: Write to local disk to preserve O(log n) next time
        if entry is not None:
            offset, length = self._storage.append_entry(entry)
            self._index.insert_sorted(entry.word, offset, length)

        return entry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_word(self, keyword: str) -> Optional[LexicalEntry]:
        """
        Look up `keyword` in the dictionary. First call checks disk or API,
        repeat calls pull instantly from RAM cache.
        """
        keyword = keyword.lower().strip()
        if not keyword:
            return None
        return self._lookup_cached(keyword)

    def total_words_cached(self) -> int:
        """Return the number of entries currently cached on disk."""
        return self._index.total_records()

    def all_keywords_cached(self) -> list:
        """Return a list of all locally cached keywords."""
        return self._index.all_keywords()

    def clear_cache(self) -> None:
        """Invalidate the LRU RAM cache."""
        self._lookup_cached.cache_clear()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close all file handles gracefully."""
        self._storage.close()
        self._index.close()

    def __enter__(self) -> "DictionaryApp":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"DictionaryApp("
            f"cached={self.total_words_cached()}, "
            f"ram_lru={self._lookup_cached.cache_info()})"
        )
