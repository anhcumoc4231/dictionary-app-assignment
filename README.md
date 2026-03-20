# 📖 Từ Điển Anh-Việt — Dictionary App

> **PFP191 Assignment** — English-Vietnamese Dictionary with O(log n) Binary Search Engine

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Algorithm](https://img.shields.io/badge/Search-O(log%20n)%20Binary-green.svg)](#)
[![Cache](https://img.shields.io/badge/Cache-O(1)%20LRU-yellow.svg)](#)

---

## 📋 Tổng quan Dự án

Ứng dụng từ điển Anh-Việt với kiến trúc hướng đối tượng (OOP), thuật toán tìm kiếm nhị phân trên ổ đĩa O(log n), giao diện đồ họa Tkinter dark-mode, và hệ thống đệm bộ nhớ LRU O(1).

### ✨ Tính năng

| Tính năng | Chi tiết |
|-----------|----------|
| 🔍 Tra cứu | Binary Search trên ổ đĩa — O(log n) |
| ⚡ Cache | LRU Cache (maxsize=256) — O(1) lần sau |
| 📐 Chỉ mục | Fixed-width 53-byte records |
| 🎧 Phát âm | Text-to-Speech (pyttsx3) |
| 🇻🇳 Nội dung | Nghĩa VI + Phiên âm IPA + Ví dụ ngữ cảnh |
| 🖥️ GUI | Tkinter dark-mode (violet/gold theme) |

---

## 🏗️ Kiến trúc Hệ thống (OOP)

```
┌─────────────────────────────────────────────────────┐
│                    gui.py (DictionaryUI)             │  ← Giao diện người dùng
│           Tkinter · Event-driven · Dark Mode         │
└─────────────────────┬───────────────────────────────┘
                      │ calls
┌─────────────────────▼───────────────────────────────┐
│                app.py (DictionaryApp)                │  ← Facade Layer
│           LRU Cache · Coordinates layers             │
└──────────┬──────────────────────────┬───────────────┘
           │                          │
┌──────────▼──────────┐  ┌────────────▼──────────────┐
│  index_navigator.py │  │      storage.py            │
│  (IndexNavigator)   │  │   (StorageEngine)          │  ← Algorithmic + Persistence
│  O(log n) Binary    │  │   seek/read binary I/O     │
│  Search on disk     │  │   meaning.data             │
└──────────┬──────────┘  └───────────────────────────┘
           │ coordinates
┌──────────▼──────────┐
│     models.py       │
│  (LexicalEntry)     │  ← DTO
│  word, meanings,    │
│  phonetic, examples │
└─────────────────────┘
```

### Cấu trúc tệp index.data (53-byte fixed-width)

```
┌──────────────────────────────────────┬──────────────┬──────────┬──────┐
│  keyword (32 bytes, space-padded)    │ offset (12B) │ len (8B) │  \n  │
└──────────────────────────────────────┴──────────────┴──────────┴──────┘
  Ví dụ:  "apple                           " + "000000001024" + "00000287" + "\n"
```

**Tìm kiếm nhị phân:** `seek(mid * 53)` → hạ cánh chính xác vào đầu record.

---

## 🚀 Hướng dẫn Cài đặt & Chạy

### Yêu cầu
- Python 3.10+
- `pip install pyttsx3` (cho tính năng phát âm)

### Bước 1 — Cài thư viện

```powershell
pip install -r requirements.txt
```

### Bước 2 — Tạo dữ liệu từ điển

```powershell
python build_database.py
```

> Lệnh này tạo ra `data/meaning.data` và `data/index.data` từ 100 từ mẫu tích hợp sẵn.

### Bước 3 — Chạy ứng dụng

```powershell
python gui.py
```

---

## 📊 Dữ liệu Mở rộng (Tùy chọn)

Để nạp thêm dữ liệu từ nguồn ngoài, tạo thư mục `data/raw/` và đặt các file:

| File | Định dạng | Nguồn |
|------|-----------|-------|
| `data/raw/en_vi.csv` | `word,meaning` per line | [Kaggle EN-VI Dict](https://kaggle.com) |
| `data/raw/ipa.json` | `{"word": "/ɪpɑː/"}` | [open-dict-data](https://github.com/open-dict-data) |
| `data/raw/tatoeba.tsv` | `english\tvietnamese` | [Tatoeba Project](https://tatoeba.org) |

Sau đó chạy lại:
```powershell
python build_database.py
```

---

## 📁 Cấu trúc Thư mục

```
PhucdeptraihonwBaAnh/
├── gui.py                  # 🖥️  Entry point — Tkinter GUI (chạy cái này)
├── app.py                  # 🔗  DictionaryApp facade + LRU cache
├── models.py               # 📦  LexicalEntry DTO
├── storage.py              # 💾  StorageEngine (binary I/O)
├── index_navigator.py      # 🔍  IndexNavigator (O(log n) binary search)
├── build_database.py       # 🏗️  ETL pipeline — tạo meaning.data + index.data
├── build_index.py          # 🔄  Rebuild index.data từ meaning.data
├── requirements.txt        # 📋  pip dependencies
├── .gitignore              # 🚫  Loại trừ data thô và cache
├── README.md               # 📖  Tài liệu này
├── data/
│   ├── meaning.data        # Binary: JSON entries packed sequentially
│   ├── index.data          # Binary: 53-byte fixed-width sorted records
│   └── raw/                # (gitignored) Raw CSV/JSON downloads
└── evidence/
    ├── development-log.txt # 📝  Nhật ký phát triển từng giai đoạn
    └── prompts-used.txt    # 🤖  Các câu prompt AI đã sử dụng
```

---

## 🧪 Xác minh Kỹ thuật

### Kiểm tra tính toàn vẹn của index

```powershell
python -c "
import os
size = os.path.getsize('data/index.data')
assert size % 53 == 0, f'BAD: {size} bytes'
print(f'OK: {size//53} records × 53 bytes = {size} bytes')
"
```

### Kiểm tra binary search

```powershell
python -c "
from app import DictionaryApp
d = DictionaryApp('data/meaning.data', 'data/index.data')
e = d.find_word('apple')
assert e, 'apple not found!'
print('FOUND:', e.word, '|', e.phonetic, '|', e.meanings)
print('Cache:', d._lookup_cached.cache_info())
d.close()
"
```

---

## ⚙️ Phân tích Hiệu năng

| Thao tác | Độ phức tạp | Mô tả |
|----------|-------------|-------|
| Tìm kiếm lần đầu | **O(log n)** | Binary search trên đĩa, n = số từ |
| Tìm kiếm lặp lại | **O(1)** | LRU cache từ RAM |
| Tìm kiếm tuyến tính (cũ) | O(n) | Đã thay thế |
| Ví dụ 100K từ | ~17 phép so sánh | log₂(100,000) ≈ 16.6 |

---

*Dự án tuân thủ yêu cầu assignment PFP191: OOP, Binary Search O(log n), Data Pipeline, GUI Tkinter, GitHub workflow.*
