"""
free_dict_api.py - Client cho Free Dictionary API (https://dictionaryapi.dev/)
=============================================================================
Miễn phí 100%, không cần API Key, trả về JSON rất sạch sẽ (Nghĩa, Từ loại, Phiên âm, Audio).
Tuy nhiên bản chất là từ điển Anh-Anh nên trường 'translation' (Dịch tiếng Việt) sẽ để trống.
"""

import os
import requests  # type: ignore
from typing import Optional, Dict, Any, List
from deep_translator import GoogleTranslator # type: ignore

from models import LexicalEntry, Sense  # type: ignore


class FreeDictClient:
    BASE_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"

    def fetch_word(self, word: str) -> Optional[LexicalEntry]:
        try:
            resp = requests.get(f"{self.BASE_URL}{word}", timeout=10)
            if resp.status_code != 200:
                print(f"FreeDict API returned {resp.status_code} for '{word}'")
                return None
                
            data = resp.json()
            if not isinstance(data, list) or len(data) == 0:
                return None
                
            return self._parse_freedict_json(word, data[0])
        except Exception as e:
            print(f"Error fetching from Free Dictionary API: {e}")
            return None

    def _parse_freedict_json(self, query_word: str, entry_data: Dict[str, Any]) -> LexicalEntry:
        # 1. Phonetics and Audio
        us_audio = ""
        uk_audio = ""
        us_ipa = ""
        uk_ipa = ""
        
        # Free Dictionary thường trả về nhiều object phonetics cho UK, US, AU
        for phonetic in entry_data.get("phonetics", []):
            audio = phonetic.get("audio", "")
            text = phonetic.get("text", "")
            
            if "-us." in audio or "us" in audio.lower():
                if not us_audio: us_audio = audio
                if not us_ipa and text: us_ipa = text
            elif "-uk." in audio or "uk" in audio.lower():
                if not uk_audio: uk_audio = audio
                if not uk_ipa and text: uk_ipa = text
            else:
                # Fallback nếu API không cung cấp locale rõ ràng
                if not us_audio and audio: us_audio = audio
                if not us_ipa and text: us_ipa = text
                
        # 2. Senses (Meanings)
        senses = []
        
        # Tiền xử lý để gom text đi dịch 1 lần (Batch Translation) giúp tăng tốc độ đáng kể
        lines_to_translate: List[str] = []
        
        for meaning in entry_data.get("meanings", []):
            for def_data in meaning.get("definitions", []):
                lines_to_translate.append(def_data.get("definition", ""))
                lines_to_translate.append(def_data.get("example", ""))
                
        # Thực hiện dịch Song song (Thread Pool) để tránh giới hạn 5000 ký tự và lỗi mất dòng
        translated_lines = []
        if lines_to_translate:
            from concurrent.futures import ThreadPoolExecutor
            
            def _safe_translate(text: str) -> str:
                if not text.strip(): return ""
                try:
                    res = GoogleTranslator(source='en', target='vi').translate(text)
                    return res if res else ""
                except Exception:
                    return ""
                    
            try:
                # 20 workers là đủ nhanh (khoảng 1-2s cho toàn bộ list)
                with ThreadPoolExecutor(max_workers=20) as executor:
                    translated_lines = list(executor.map(_safe_translate, lines_to_translate))
            except Exception as e:
                print(f"Translation failed: {e}")
                translated_lines = [""] * len(lines_to_translate)

        # Trích xuất lại từ mảng đã dịch
        idx = 0
        for meaning in entry_data.get("meanings", []):
            pos = meaning.get("partOfSpeech", "")
            for def_data in meaning.get("definitions", []):
                definition = def_data.get("definition", "")
                ex_text = def_data.get("example", "")
                
                translated_def = str(translated_lines[idx]) if idx < len(translated_lines) and translated_lines[idx] else "" # type: ignore
                idx += 1
                translated_ex = str(translated_lines[idx]) if idx < len(translated_lines) and translated_lines[idx] else "" # type: ignore
                idx += 1
                
                examples = []
                if ex_text:
                    examples.append({
                        "en": ex_text,
                        "vi": translated_ex
                    })
                    
                s_obj = Sense(
                    pos=pos.capitalize() if pos else "",
                    definition=definition,
                    translation=translated_def,  # Đã có tiếng Việt!
                    examples=examples
                )
                senses.append(s_obj)
                
        return LexicalEntry(
            word=entry_data.get("word", query_word),
            us_audio=us_audio,
            uk_audio=uk_audio,
            us_ipa=us_ipa,
            uk_ipa=uk_ipa,
            senses=senses,
            source="Free Dictionary API"
        )
