"""
models.py - Domain Entity / Data Transfer Object (DTO)
Principle: Single Responsibility - represents one dictionary entry.
"""

import json
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class LexicalEntry:
    """
    Encapsulates all linguistic data for a single English word.

    Attributes:
        word        : The English keyword (lowercase, stripped).
        meanings    : List of Vietnamese definitions.
        phonetic    : IPA pronunciation string, e.g. '/aepel/'.
        word_class  : Part of speech, e.g. 'noun', 'verb', 'adjective'.
        examples    : List of (english_sentence, vietnamese_sentence) pairs.
    """
    word: str
    meanings: List[str] = field(default_factory=list)
    phonetic: str = ""
    word_class: str = ""
    examples: List[Tuple[str, str]] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def to_json(self) -> str:
        """Serialize to a compact JSON string (UTF-8 safe)."""
        data = {
            "word":       self.word,
            "meanings":   self.meanings,
            "phonetic":   self.phonetic,
            "word_class": self.word_class,
            "examples":   self.examples,
        }
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    def to_bytes(self) -> bytes:
        """Encode to UTF-8 bytes ready for writing into meaning.data."""
        return self.to_json().encode("utf-8")

    @classmethod
    def from_json(cls, json_str: str) -> "LexicalEntry":
        """Deserialize from a JSON string."""
        data = json.loads(json_str)
        examples_raw = data.get("examples", [])
        # Normalize: each item should be a (str, str) tuple
        examples: List[Tuple[str, str]] = []
        for ex in examples_raw:
            if isinstance(ex, (list, tuple)) and len(ex) >= 2:
                examples.append((str(ex[0]), str(ex[1])))
        return cls(
            word=str(data.get("word", "")),
            meanings=[str(m) for m in data.get("meanings", [])],
            phonetic=str(data.get("phonetic", "")),
            word_class=str(data.get("word_class", "")),
            examples=examples,
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> "LexicalEntry":
        """Decode UTF-8 bytes and deserialize."""
        return cls.from_json(raw.decode("utf-8"))

    def __repr__(self) -> str:
        return (
            f"LexicalEntry(word={self.word!r}, "
            f"meanings={self.meanings}, phonetic={self.phonetic!r})"
        )
