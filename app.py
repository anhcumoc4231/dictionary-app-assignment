"""
app.py - Lớp Vỏ Bọc (DictionaryApp)
=====================================
Điều phối việc Tra Cứu (Lookup).
- Ưu tiên #1: O(1) qua LRU RAM Cache.
- Ưu tiên #2: O(log n) qua ổ đĩa cứng (index.data + meaning.data).
- Ưu tiên #3: Mất mạng? Ra ngoài gọi Free Dictionary API, ghi lại kết quả vào ổ đĩa.
"""

import os
import sys
from functools import lru_cache
from typing import Optional

# Ensure the project root is on the path so imports work from any working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import LexicalEntry       # type: ignore
from storage import StorageEngine     # type: ignore
from index_navigator import IndexNavigator  # type: ignore
from free_dict_api import FreeDictClient   # type: ignore


class DictionaryApp:
    def __init__(self, data_path: str, index_path: str) -> None:
        # 1. Ổ đĩa: Storage Engine (đọc ý nghĩa - O(1) direct access)
        self._storage = StorageEngine(data_path)
        
        # 2. Ổ đĩa: Index Navigator (tìm kiếm nhị phân - O(log n))
        self._index = IndexNavigator(index_path)

        # 3. Free Dictionary API (Tự do, không giới hạn)
        self._freedict = FreeDictClient()
        
        # In-memory RAM cache function
        self._lru_cache = lru_cache(maxsize=1000)(self._lookup)

    def total_words_cached(self) -> int:
        return self._index.total_records()

    def find_word(self, keyword: str) -> Optional[LexicalEntry]:
        """ Public method có bọc lru_cache để đảm bảo lần tra lại lần 3+ là O(1) RAM. """
        keyword = keyword.strip()
        if not keyword:
            return None

        # TÍNH NĂNG MỚI: Dịch Nguyên Câu bằng Google Translate
        if " " in keyword or len(keyword) > 25:
            try:
                from deep_translator import GoogleTranslator  # type: ignore
                translated = GoogleTranslator(source='en', target='vi').translate(keyword)
                return LexicalEntry(
                    word=keyword,
                    short_translation=translated,
                    senses=[],
                    source="Google Translate"
                )
            except Exception as e:
                print(f"Sentence translation failed: {e}")
                return None

        return self._lru_cache(keyword.lower())

    def _lookup(self, keyword: str) -> Optional[LexicalEntry]:
        """ Logic tìm kiếm nội bộ: HDD -> API -> Save to HDD """
        # 1. Thử tìm trong đĩa cứng (O(log n))
        coords = self._index.find(keyword)
        if coords is not None:
            offset, length = coords
            entry = self._storage.read_entry(offset, length)
            entry.source = "Local Cache"  # Tag it to show in UI
            return entry
            
        # 2. Không có trong đĩa? Dùng Free Dictionary API
        entry = self._freedict.fetch_word(keyword) # type: ignore
        if entry is not None:
            # 3. Cache xuống đĩa để bảo tồn thuật toán
            offset, length = self._storage.append_entry(entry)
            self._index.insert_sorted(entry.word, offset, length)
            return entry
            
        return None

    def close(self) -> None:
        self._index.close()
        self._storage.close()
