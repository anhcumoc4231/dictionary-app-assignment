"""
cambridge_api.py - REST API Client for Cambridge Dictionaries Online
===================================================================
Handles authentication, networking, and JSON parsing for the Cambridge API.
Requires a valid Access Key from Cambridge Dictionary API (Trial or Pro).
"""

import os
import requests
from typing import Optional

from models import LexicalEntry, Sense


class CambridgeClient:
    """
    Client for interacting with the official Cambridge Dictionary API.
    """
    
    BASE_URL = "https://dictionary.cambridge.org/api/v1/dictionaries/english-vietnamese"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the client. 
        If api_key is None, it attempts to load from os.environ["CAMBRIDGE_API_KEY"].
        """
        self.api_key = api_key or os.environ.get("CAMBRIDGE_API_KEY", "")
        
        self.headers = {
            "accessKey": self.api_key,
            "Accept": "application/json"
        }

    def set_key(self, api_key: str) -> None:
        """Update the API key at runtime (e.g., from GUI settings)."""
        self.api_key = api_key
        self.headers["accessKey"] = api_key

    def has_key(self) -> bool:
        """Check if an API key is currently configured."""
        return bool(self.api_key and self.api_key.strip())

    def fetch_word(self, keyword: str) -> Optional[LexicalEntry]:
        """
        Fetch a word from Cambridge API and convert it into our local LexicalEntry DTO.
        Returns None if word not found or error occurs.
        """
        if not self.has_key():
            print("[CambridgeClient] Lỗi: Chưa cấu hình API Key.")
            return None

        keyword = keyword.lower().strip()
        if not keyword:
            return None

        try:
            # Step 1: Search to get the entryId
            search_url = f"{self.BASE_URL}/search"
            params = {"q": keyword}
            
            search_resp = requests.get(search_url, headers=self.headers, params=params, timeout=10)
            
            if search_resp.status_code == 401:
                print("[CambridgeClient] Lỗi 401: API Key không hợp lệ hoặc đã hết hạn (Trial).")
                return None
            elif search_resp.status_code == 404:
                return None
                
            search_resp.raise_for_status()
            search_data = search_resp.json()
            
            # Cambridge API returns a list of results. Get the exact match entryId.
            results = search_data.get("results", [])
            if not results:
                return None
            
            # Find exact match or use the first result's entryId
            entry_id = results[0].get("entryId")
            for res in results:
                if res.get("word", "").lower() == keyword:
                    entry_id = res.get("entryId")
                    break
                    
            if not entry_id:
                return None
                
            # Step 2: Fetch the full entry using the entryId
            entry_url = f"{self.BASE_URL}/entries/{entry_id}"
            entry_resp = requests.get(entry_url, headers=self.headers, timeout=10)
            entry_resp.raise_for_status()
            
            raw_entry = entry_resp.json()
            return self._parse_cambridge_json(keyword, raw_entry)

        except requests.exceptions.RequestException as e:
            print(f"[CambridgeClient] Lỗi mạng khi gọi API: {e}")
            return None
        except ValueError as e:
            print(f"[CambridgeClient] Lỗi parse JSON từ API: {e}")
            return None

    def _parse_cambridge_json(self, keyword: str, raw: dict) -> LexicalEntry:
        """
        Convert Cambridge's complex JSON structure into our clean LexicalEntry DTO.
        Note: The actual Cambridge JSON schema is very nested. This parser extracts
        surface-level pronunciation and senses.
        """
        # Base setup
        entry = LexicalEntry(word=keyword, source="Cambridge API")
        
        # Pronunciations are usually in an array of 'pronunciations'
        prons = raw.get("pronunciations", [])
        for p in prons:
            lang = str(p.get("lang", "")).lower()
            pron = p.get("pronunciation", "")
            audio = p.get("audio", "")
            
            if lang == "us":
                entry.us_ipa = pron
                if audio:
                    entry.us_audio = f"https://dictionary.cambridge.org{audio}"
            elif lang == "uk":
                entry.uk_ipa = pron
                if audio:
                    entry.uk_audio = f"https://dictionary.cambridge.org{audio}"
                    
        # Senses usually contain parts of speech and definitions
        senses = raw.get("senses", [])
        for s in senses:
            pos = s.get("partOfSpeech", "")
            # Some senses have nested definition blocks
            defs = s.get("definitions", [])
            for d in defs:
                definition = d.get("text", "")
                translation = d.get("translation", "")
                
                # Examples
                ex_list = []
                for ex in d.get("examples", []):
                    en = ex.get("en", "")
                    vi = ex.get("vi", "")
                    if en or vi:
                        ex_list.append({"en": en, "vi": vi})
                        
                sense_obj = Sense(
                    pos=pos,
                    definition=definition,
                    translation=translation,
                    examples=ex_list
                )
                entry.senses.append(sense_obj)

        return entry
