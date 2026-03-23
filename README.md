# 📖 AI Dictionary Pro 4.1 — Integrated Grammar AI

> **PFP191 Assignment Final** — Từ điển Anh-Việt/Việt-Anh: O(log n) Binary Search + Gemini-Style AI Chat + **Grammar Correction AI**.

[![Python](https://img.shields.io/badge/Python-3.14-blue.svg)](https://python.org)
[![UI](https://img.shields.io/badge/UI-Gemini%20Style-purple.svg)](#)
[![Algorithm](https://img.shields.io/badge/Search-O(log%20n)%20Binary-green.svg)](#)
[![Translation](https://img.shields.io/badge/Mode-Dual%20(EN--VI%20%26%20VI--EN)-orange.svg)](#)

---

## 🌟 Siêu phẩm Từ điển 4.0

Chào mừng đến với bản nâng cấp lớn nhất! Không chỉ là tra từ, đây là một trợ lý ngôn ngữ thực thụ với kiến trúc lai (Hybrid) cực mạnh:
- **Giao diện Gemini:** Trải nghiệm chat mượt mà, bong bóng AI thông minh, hiệu ứng gõ chữ sinh động.
- **Dịch & Sửa lỗi Grammar**: Tự động nhận diện câu văn tiếng Anh để dịch nghĩa đồng thời chỉ ra lỗi ngữ pháp/chính tả ngay trong khung chat.
- **WOTD Flip Cards**: Trang luyện từ vựng mỗi ngày với phong cách thẻ lật (Flashcards), giúp ghi nhớ từ vựng hiệu quả hơn.
- **Tốc độ Thần sầu:** Lần đầu tra từ sẽ tải từ **Free Dictionary API** và dịch qua **Google Translate**. Lần sau, app đọc từ cache ổ đĩa bằng **Binary Search O(log n)** — siêu nhanh, không cần mạng.

### ✨ Tính năng nổi bật

| ✨ AI Grammar | Tự động phát hiện lỗi ngữ pháp, chính tả và gợi ý sửa lỗi trực quan ngay trong bubble chat. |
| 🤖 Gemini UI | Giao diện Chatbot bong bóng hiện đại, sidebar thu gọn, hiệu ứng Glow ảo diệu. |
| 🇬🇧/🇻🇳 Dual Mode | Thanh gạt thông minh trên đỉnh khung chat để đổi chiều dịch thuật tức thì. |
| 🃏 WOTD Cards | Hệ thống thẻ lật 5 từ vựng ngẫu nhiên mỗi lần mở hoặc "Xáo bài" mới. |
| 🔍 Tra cứu Hybrid | Kết hợp dữ liệu Local (O(log n)) và API (TFlat Style) để luôn có kết quả tốt nhất. |
| 💾 Siêu Cache | LRU Cache O(1) trên RAM + Binary Search O(log n) trên đĩa (Data 53-byte fixed). |
| ⭐ Bookmarks | Lưu từ yêu thích vào sổ tay, xem lại bằng icon 📖 trên Sidebar. |

---

## 🏗️ Kiến trúc Hệ thống

```
┌─────────────────────────────────────────────────────┐
│                gui.py (DictionaryUI)                │  ← Gemini UI Layer
│  Sidebar · Mode Switcher · Bubble Animation · WOTD  │
└─────────────────────┬───────────────────────────────┘
                      │ calls (mode: en_vi / vi_en)
┌─────────────────────▼───────────────────────────────┐
│              app.py (DictionaryApp)                 │  ← Logic Controller
│   Translation Strategy · LRU Cache · Multi-source   │
└──────┬───────────────────────────────────┬──────────┘
       │                                   │
┌──────▼──────────┐             ┌──────────▼──────────┐
│ index_navigator │             │     storage.py      │
│ O(log n) Binary │             │  (StorageEngine)    │
│ Search on disk  │             │  seek/read binary   │
└──────┬──────────┘             └─────────────────────┘
       │ (on MISS)
┌──────▼──────────────────┐
│   free_dict_api.py      │  ← Deep Translator Layer
│  + Free Dictionary API  │  + Google Translate (EN/VI)
│  + Async Cache Sync     │
└─────────────────────────┘
```

---

## 🚀 Hướng dẫn Cài đặt & Chạy

### 1. Cách nhanh nhất (Dành cho người dùng)
Tải file **`dist/gui.exe`** trong repository này về và chạy ngay trên Windows. Không cần cài Python, không cần cài thư viện!

### 2. Dành cho nhà phát triển
- Cài đặt Python 3.10 trở lên.
- Cài đặt thư viện: `pip install -r requirements.txt`
- Chạy ứng dụng: `python gui.py`

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
