# 📖 Từ Điển Anh-Việt — Hybrid FreeDict Architecture

> **PFP191 Assignment** — English-Vietnamese Dictionary with Hybrid Architecture: O(log n) Binary Search + Free Dictionary API + Real-time Vietnamese Translation

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Algorithm](https://img.shields.io/badge/Search-O(log%20n)%20Binary-green.svg)](#)
[![Cache](https://img.shields.io/badge/Cache-O(1)%20LRU-yellow.svg)](#)
[![API](https://img.shields.io/badge/API-Free%20Dictionary-brightgreen.svg)](https://dictionaryapi.dev)

---

## 📋 Tổng quan Dự án

Ứng dụng từ điển **Anh-Việt** với kiến trúc lai (Hybrid):
- Lần đầu tra từ: Gọi **Free Dictionary API** (miễn phí, không cần key) → tự động dịch nghĩa sang tiếng Việt qua **Google Translate** → lưu vào ổ đĩa.
- Lần tra lại: Đọc thẳng từ cache ổ đĩa bằng **Binary Search O(log n)** — không tốn 1 byte băng thông.

### ✨ Tính năng

| Tính năng | Chi tiết |
|-----------|----------|
| 🔍 Tra cứu Hybrid | Binary Search O(log n) on-disk + Free Dictionary API |
| 🇻🇳 Nghĩa Tiếng Việt | Dịch tự động qua Google Translate (deep-translator) |
| ⚡ Mỳ ăn liền | Nghĩa ngắn gọn hiển thị ngay bên dưới từ vựng |
| 💾 Cache | LRU Cache O(1) trên RAM + Binary Search O(log n) trên đĩa |
| 🎵 Âm thanh | Phát MP3 giọng US/UK từ API (hoặc pyttsx3 offline) |
| ⌨️ Autocomplete | Gợi ý từ vựng từ kho 5,000 từ phổ biến nhất |
| 🖥️ GUI | Tkinter dark-mode (Violet-Gold theme) |

---

## 🏗️ Kiến trúc Hệ thống

```
┌─────────────────────────────────────────────────────┐
│                gui.py (DictionaryUI)                │  ← Giao diện Tkinter
│    Dark Mode · Autocomplete · Audio Playback        │
└─────────────────────┬───────────────────────────────┘
                      │ calls
┌─────────────────────▼───────────────────────────────┐
│              app.py (DictionaryApp)                 │  ← Facade + LRU Cache
│          RAM O(1) cache · Layer coordinator         │
└──────┬───────────────────────────────────┬──────────┘
       │                                   │
┌──────▼──────────┐             ┌──────────▼──────────┐
│ index_navigator │             │     storage.py       │
│ O(log n) Binary │             │  (StorageEngine)     │
│ Search on disk  │             │  seek/read binary    │
└──────┬──────────┘             └─────────────────────┘
       │ (on MISS)
┌──────▼──────────────────┐
│   free_dict_api.py       │  ← Free Dictionary API
│  + deep-translator       │     + Google Translate (VI)
│  + Insert into cache     │
└──────────────────────────┘
```

### Cấu trúc bản ghi index.data (53-byte fixed-width)

```
┌──────────────────────────────────────┬──────────────┬──────────┬──────┐
│  keyword (32 bytes, space-padded)    │ offset (12B) │ len (8B) │  \n  │
└──────────────────────────────────────┴──────────────┴──────────┴──────┘
  Ví dụ: "apple                           " + "000000001024" + "00000287" + "\n"
```

**Tìm kiếm nhị phân:** `seek(mid * 53)` → hạ cánh chính xác vào đầu record.

---

## 🚀 Hướng dẫn Cài đặt & Chạy

### Yêu cầu
- Python 3.10+
- Kết nối Internet (lần đầu tra từ mới)

### Bước 1 — Cài thư viện

```powershell
pip install -r requirements.txt
```

### Bước 2 — Chạy ứng dụng

```powershell
python gui.py
```

> Không cần cài đặt gì thêm! Lần đầu tra từ sẽ tự động tải dữ liệu từ API và lưu vào máy.

### Hoặc chạy file `.exe` trực tiếp (Windows)

Tải file `dist/gui.exe` từ repo này, chạy thẳng — không cần cài Python!

---

## 📁 Cấu trúc Thư mục

```
PhucdeptraihonwBaAnh/
├── gui.py                  # 🖥️  Entry point — Giao diện Tkinter
├── app.py                  # 🔗  DictionaryApp — Facade + LRU Cache
├── free_dict_api.py        # 🌐  Free Dictionary API + Google Translate
├── models.py               # 📦  LexicalEntry DTO
├── storage.py              # 💾  StorageEngine — Binary I/O
├── index_navigator.py      # 🔍  IndexNavigator — O(log n) Binary Search
├── download_dictionary.py  # 🔄  Tiện ích quản lý dữ liệu
├── requirements.txt        # 📋  Pip dependencies
├── .gitignore
├── README.md
├── data/
│   ├── meaning.data        # Binary: dữ liệu nghĩa từ (tự tạo khi chạy)
│   ├── index.data          # Binary: 53-byte sorted records (tự tạo khi chạy)
│   └── words_list.txt      # 5,000 từ phổ biến nhất (dùng cho Autocomplete)
├── dist/
│   └── gui.exe             # 🚀  File chạy Windows (không cần cài Python)
└── evidence/
    ├── development-log.txt # 📝  Nhật ký phát triển
    └── prompts-used.txt    # 🤖  Các prompt AI đã sử dụng
```

---

## ⚙️ Phân tích Hiệu năng

| Thao tác | Độ phức tạp | Mô tả |
|----------|-------------|-------|
| Tra từ lần đầu (có mạng) | ~1.5s | Gọi API + Dịch Tiếng Việt + Lưu vào đĩa |
| Tra từ lần 2+ (từ đĩa) | **O(log n)** | Binary search trên đĩa, n = số từ đã lưu |
| Tra từ đã dùng gần đây | **O(1)** | LRU cache từ RAM |
| Ví dụ với 100K từ | ~17 phép so sánh | log₂(100,000) ≈ 16.6 |

---

## 📦 Dependencies

```
requests       # Gọi Free Dictionary API
deep-translator # Dịch tiếng Anh → tiếng Việt (Google Translate)
pyttsx3        # Fallback offline text-to-speech
```

---

*Dự án tuân thủ yêu cầu assignment PFP191: OOP, Binary Search O(log n), Hybrid API Architecture, GUI Tkinter, GitHub workflow.*
