"""
download_dictionary.py — Tải từ điển Anh-Việt (Hồ Ngọc Đức)
============================================================
Tải từ điển Anh-Việt nổi tiếng (raw text) từ GitHub và chuyển
đổi thành JSON đầy đủ (nghĩa tiếng Việt, phiên âm, từ loại, ví dụ).
"""

import os
import sys
import json
import urllib.request

# Fix Windows terminal Unicode
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
DICT_TXT = os.path.join(RAW_DIR, "anhviet.txt")
FULL_JSON = os.path.join(RAW_DIR, "full_dict.json")

# Free Vietnamese Dictionary Project (Hồ Ngọc Đức)
DICT_URL = "https://raw.githubusercontent.com/vuduc153/IT3240/master/anhviet.txt"

def download():
    os.makedirs(RAW_DIR, exist_ok=True)
    if not os.path.exists(DICT_TXT):
        print("  Downloading anhviet.txt from GitHub (~15MB) ...")
        urllib.request.urlretrieve(DICT_URL, DICT_TXT)  # type: ignore
        print("  Download OK.")

def parse():
    print("  Parsing anhviet.txt ...")
    with open(DICT_TXT, "r", encoding="utf-8") as f:
        lines = f.readlines()

    master = {}
    current_word = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("@"):
            parts = line[1:].split("/", 1)  # type: ignore
            word = parts[0].strip().lower()
            phonetic = f"/{parts[1].strip()}" if len(parts) > 1 else ""
            if phonetic == "/": phonetic = ""
            
            # Khởi tạo entry mới
            current_word = {"word": word, "meanings": [], "phonetic": phonetic, "word_class": "", "examples": []}
            # Chỉ lấy những từ ngắn gọn
            if len(word) > 1 and len(word) <= 30:
                master[word] = current_word

        elif current_word and word in master:  # type: ignore
            if line.startswith("*"):
                # Word class
                current_word["word_class"] = line[1:].strip()  # type: ignore
            elif line.startswith("-"):
                # Meaning
                meaning = line[1:].strip()  # type: ignore
                if meaning:
                    current_word["meanings"].append(meaning)  # type: ignore
            elif line.startswith("="):
                # Example: =english+vietnamese
                example_parts = line[1:].split("+", 1)  # type: ignore
                en_ex = example_parts[0].strip()  # type: ignore
                vi_ex = example_parts[1].strip() if len(example_parts) > 1 else ""
                if en_ex:
                    current_word["examples"].append([en_ex, vi_ex])  # type: ignore

    count = len(master)
    print(f"  Parsed {count:,} words.")
    
    # Save to JSON
    with open(FULL_JSON, "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False)
    print("  JSON built successfully.")

def main():
    print("=" * 60)
    print("Dictionary Downloader — Từ Điển Anh-Việt (Hồ Ngọc Đức)")
    print("=" * 60)
    download()
    parse()
    print("Xong! Bây giờ chạy  python build_database.py")

if __name__ == "__main__":
    main()
