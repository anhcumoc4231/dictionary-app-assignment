"""
app.py - Lớp Vỏ Bọc (DictionaryApp)
=====================================
Điều phối việc Tra Cứu (Lookup).
- Ưu tiên #1: O(1) qua LRU RAM Cache.
- Ưu tiên #2: O(log n) qua ổ đĩa cứng (index.data + meaning.data).
- Ưu tiên #3: Mất mạng? Ra ngoài gọi Free Dictionary API, ghi lại kết quả vào ổ đĩa.
"""

import requests
import os
import sys
from functools import lru_cache
from typing import Optional, List

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

    def find_word(self, keyword: str, mode: str = "en_vi") -> Optional[LexicalEntry]:
        """ Public method tìm kiếm. Hỗ trợ mode 'en_vi' (mặc định) và 'vi_en'. """
        keyword = keyword.strip()
        if not keyword:
            return None

        # CHẾ ĐỘ 1: DỊCH VIỆT - ANH (Sử dụng Google Translate)
        if mode == "vi_en":  # type: ignore
            try:  # type: ignore
                from deep_translator import GoogleTranslator  # type: ignore
                translated = GoogleTranslator(source='vi', target='en').translate(keyword)
                return LexicalEntry(
                    word=keyword,
                    short_translation=translated,
                    senses=[],
                    source="Google Translate (Vi-En)"
                )
            except Exception as e:
                print(f"Vi-En translation failed: {e}")
                return None

        # CHẾ ĐỘ 2: ANH - VIỆT (Dùng Cache/API)
        # TÍNH NĂNG MỚI: Dịch Nguyên Câu & Kiểm tra Ngữ pháp
        if " " in keyword or len(keyword) > 25:
            try:
                from deep_translator import GoogleTranslator  # type: ignore
                translated = GoogleTranslator(source='en', target='vi').translate(keyword)
                
                # Tự động kiểm tra ngữ pháp (LanguageTool)
                grammar_fixes = self._check_grammar(keyword)
                
                # AI Refinement (Back-translation trick for high accuracy)
                # Dịch từ VI ngược lại EN để tìm câu chuẩn nhất
                ai_refined = ""
                try:
                    ai_refined = GoogleTranslator(source='vi', target='en').translate(translated)
                    if ai_refined.lower().strip("?.!") == keyword.lower().strip("?.!"):
                        ai_refined = "" # Giống hệt thì thôi
                except:
                    pass

                return LexicalEntry(
                    word=keyword,
                    short_translation=translated,
                    senses=[],
                    grammar_fixes=grammar_fixes,
                    ai_refined=ai_refined,
                    source="Google Translate + AI Grammar"
                )
            except Exception as e:
                print(f"Sentence translation/grammar failed: {e}")
                return None

        return self._lru_cache(keyword.lower())

    def _check_grammar(self, text: str):  # type: ignore
        """Call LanguageTool API to check English grammar."""
        try:
            from models import GrammarCorrection # type: ignore
            url = "https://api.languagetool.org/v2/check"
            params = {
                "text": text,
                "language": "en-US"
            }
            resp = requests.post(url, data=params, timeout=5)
            if resp.status_code == 200:
                matches = resp.json().get("matches", [])
                fixes = []
                for m in matches:
                    off = int(m.get("offset", 0))
                    le  = int(m.get("length", 0))
                    fixes.append(GrammarCorrection(
                        message=m.get("message", "Error found"),
                        offset=off,
                        length=le,
                        error_text=text[off : off + le],
                        replacements=[r.get("value") for r in m.get("replacements", [])][:3]
                    ))
                return fixes
        except Exception as e:
            print(f"Grammar check failed: {e}")
        return []

    def total_words_cached(self) -> int:
        return self._index.total_records()

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
