"""
app.py - Facade Layer (DictionaryApp)
Principle: Coordinates IndexNavigator + StorageEngine.
Provides a clean, high-level API consumed by the GUI layer.

LRU Cache is applied here for O(1) repeat lookups.
"""

import os
import sys
import functools
from typing import Optional

# Ensure the project root is on the path so imports work from any working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import LexicalEntry       # type: ignore # noqa: E402
from storage import StorageEngine     # type: ignore # noqa: E402
from index_navigator import IndexNavigator  # type: ignore # noqa: E402


class DictionaryApp:
    """
    Facade that wires together the storage and index layers.

    Usage:
        app = DictionaryApp('data/meaning.data', 'data/index.data')
        entry = app.find_word('apple')
        if entry:
            print(entry.meanings)
        app.close()
    """

    def __init__(self, data_path: str, index_path: str) -> None:
        self._storage = StorageEngine(data_path)
        self._index   = IndexNavigator(index_path)

        # Build a cached version of _lookup after __init__ so that
        # `self` is available as a bound method reference.
        # This avoids the "lru_cache on instance method" problem:
        # the cache is per-instance, not per-class.
        self._lookup_cached = functools.lru_cache(maxsize=256)(self._lookup)

    # ------------------------------------------------------------------
    # Core lookup (uncached) - called by the cached wrapper below
    # ------------------------------------------------------------------

    def _lookup(self, keyword: str) -> Optional[LexicalEntry]:
        """
        Internal lookup: binary-search the index, then read meaning.data.
        Do NOT call directly - use find_word() to get caching benefits.
        """
        coords = self._index.find(keyword)
        if coords is None:
            return None
        offset, length = coords
        return self._storage.read_entry(offset, length)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_word(self, keyword: str) -> Optional[LexicalEntry]:
        """
        Look up `keyword` in the dictionary.

        First call   -> O(log n)  disk binary search.
        Repeat calls -> O(1)      from LRU RAM cache.

        Returns:
            LexicalEntry if found, None otherwise.
        """
        keyword = keyword.lower().strip()
        if not keyword:
            return None
        return self._lookup_cached(keyword)

    def total_words(self) -> int:
        """Return the number of entries in the dictionary."""
        return self._index.total_records()

    def all_keywords(self) -> list:
        """Return a sorted list of all keywords (for autocomplete)."""
        return self._index.all_keywords()

    def clear_cache(self) -> None:
        """Invalidate the LRU cache (use after rebuilding data)."""
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
            f"words={self.total_words()}, "
            f"cache={self._lookup_cached.cache_info()})"
        )
