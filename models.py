"""
models.py - Domain Entity / Data Transfer Object (DTO)
Principle: Single Responsibility - represents one dictionary entry from Cambridge API.
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Sense:
    """Represents a specific meaning and part of speech of a word."""
    pos: str               # e.g., 'noun', 'verb'
    definition: str        # e.g., 'a financial institution'
    translation: str       # e.g., 'ngân hàng'
    examples: List[Dict[str, str]] = field(default_factory=list) # [{'en': '...', 'vi': '...'}]

    def to_dict(self) -> dict:
        return {
            "pos": self.pos,
            "definition": self.definition,
            "translation": self.translation,
            "examples": self.examples
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Sense":
        return cls(
            pos=str(data.get("pos", "")),
            definition=str(data.get("definition", "")),
            translation=str(data.get("translation", "")),
            examples=list(data.get("examples", []))
        )


@dataclass
class GrammarCorrection:
    """Represents a grammar or spelling correction suggestion."""
    message: str           # e.g., 'Possible spelling mistake found.'
    offset: int            # start index in original text
    length: int            # length of original text to replace
    error_text: str        # the original text that has error
    replacements: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "offset": self.offset,
            "length": self.length,
            "error_text": self.error_text,
            "replacements": self.replacements
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GrammarCorrection":
        return cls(
            message=str(data.get("message", "")),
            offset=int(data.get("offset", 0)),
            length=int(data.get("length", 0)),
            error_text=str(data.get("error_text", "")),
            replacements=list(data.get("replacements", []))
        )


@dataclass
class LexicalEntry:
    """
    Encapsulates linguistic data for a single English word based on Cambridge API format.
    """
    word: str
    us_ipa: str = ""
    uk_ipa: str = ""
    us_audio: str = "" # URL to mp3/ogg
    uk_audio: str = "" # URL to mp3/ogg
    short_translation: str = ""
    senses: List[Sense] = field(default_factory=list)
    grammar_fixes: List[GrammarCorrection] = field(default_factory=list)
    ai_refined: str = "" # Best version from back-translation
    source: str = "Cambridge" # Tag for debugging

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def to_json(self) -> str:
        """Serialize to a compact JSON string (UTF-8 safe)."""
        data = {
            "word": self.word,
            "us_ipa": self.us_ipa,
            "uk_ipa": self.uk_ipa,
            "us_audio": self.us_audio,
            "uk_audio": self.uk_audio,
            "short_translation": self.short_translation,
            "senses": [s.to_dict() for s in self.senses],
            "grammar_fixes": [g.to_dict() for g in self.grammar_fixes],
            "ai_refined": self.ai_refined,
            "source": self.source
        }
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    def to_bytes(self) -> bytes:
        """Encode to UTF-8 bytes ready for writing into meaning.data."""
        return self.to_json().encode("utf-8")

    @classmethod
    def from_json(cls, json_str: str) -> "LexicalEntry":
        """Deserialize from a JSON string."""
        data = json.loads(json_str)
        senses_raw = data.get("senses", [])
        senses = [Sense.from_dict(s) for s in senses_raw if isinstance(s, dict)]
        
        grammar_raw = data.get("grammar_fixes", [])
        grammar_fixes = [GrammarCorrection.from_dict(g) for g in grammar_raw if isinstance(g, dict)]

        return cls(
            word=str(data.get("word", "")),
            us_ipa=str(data.get("us_ipa", "")),
            uk_ipa=str(data.get("uk_ipa", "")),
            us_audio=str(data.get("us_audio", "")),
            uk_audio=str(data.get("uk_audio", "")),
            short_translation=str(data.get("short_translation", "")),
            senses=senses,
            grammar_fixes=grammar_fixes,
            ai_refined=str(data.get("ai_refined", "")),
            source=str(data.get("source", "Local Cache"))
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> "LexicalEntry":
        """Decode UTF-8 bytes and deserialize."""
        return cls.from_json(raw.decode("utf-8"))

    def __repr__(self) -> str:
        return (
            f"LexicalEntry('{self.word}', "
            f"us_ipa='{self.us_ipa}', senses_count={len(self.senses)})"
        )
