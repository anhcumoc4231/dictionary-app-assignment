"""
gui.py — Giao diện Người dùng (DictionaryUI)
=============================================
Entry point chính của ứng dụng.

Kiến trúc:
  - DictionaryUI   : Lớp Tkinter, điều hướng bằng sự kiện (event-driven).
  - DictionaryApp  : Facade OOP bên dưới (từ app.py).
  - LRU Cache      : Được tích hợp trong DictionaryApp — O(1) cho các từ đã tra.
  - TTS            : pyttsx3 chạy trong luồng riêng để không đóng băng UI.

Chạy ứng dụng:
  python gui.py
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog  # type: ignore
from typing import Optional

# Bổ sung thư mục cha vào sys.path (an toàn khi chạy từ bất kỳ đâu)
sys.path.insert(0, os.path.dirname(__file__))

import pyttsx3  # type: ignore
from app import DictionaryApp  # type: ignore  # noqa: E402
from models import LexicalEntry  # type: ignore  # noqa: E402
import rag_engine  # type: ignore  # noqa: E402

# ── Đường dẫn dữ liệu ────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    # Đang chạy từ file .exe được đóng gói
    _BASE = sys._MEIPASS  # type: ignore
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))

DATA_PATH  = os.path.join(_BASE, "data", "meaning.data")
INDEX_PATH = os.path.join(_BASE, "data", "index.data")

# ── Bảng màu (Dark Mode Violet-Gold) ─────────────────────────────────────
C = {
    "bg":           "#0F0F1A",   # Nền cửa sổ chính (navy đậm)
    "panel":        "#1A1A2E",   # Nền panel kết quả
    "card":         "#16213E",   # Nền card từ khóa
    "border":       "#0F3460",   # Viền
    "accent":       "#E94560",   # Màu nhấn (đỏ hồng)
    "gold":         "#F5A623",   # Vàng cho phiên âm
    "text_main":    "#EAEAEA",   # Chữ chính
    "text_dim":     "#8892A4",   # Chữ mờ
    "text_example": "#A8B5C8",   # Chữ ví dụ
    "search_bg":    "#1E1E2E",   # Nền ô tìm kiếm
    "btn_bg":       "#E94560",   # Nền nút tìm kiếm
    "btn_fg":       "#FFFFFF",   # Chữ nút
    "btn_speak":    "#0F3460",   # Nền nút loa
    "green":        "#4CAF50",   # Màu trạng thái OK
    "tag_noun":     "#5C9BD1",   # Nhãn từ loại — danh từ
    "tag_verb":     "#C97BDB",   # Nhãn từ loại — động từ
    "tag_adj":      "#F0A500",   # Nhãn từ loại — tính từ
    "tag_other":    "#7EC8A4",   # Nhãn từ loại — khác
}

FONT_FAMILY = "Segoe UI"


# ── TTS helper ────────────────────────────────────────────────────────────

def _speak_async(word: str) -> None:
    """Phát âm từ trong luồng riêng (không chặn UI)."""
    def _run():
        try:
            import pyttsx3  # type: ignore
            engine = pyttsx3.init()
            engine.setProperty("rate", 160)
            engine.say(word)
            engine.runAndWait()
        except ImportError:
            pass  # pyttsx3 chưa cài — bỏ qua lặng lẽ
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


# ── Main GUI Class ────────────────────────────────────────────────────────

class DictionaryUI:
    """
    Giao diện đồ họa từ điển Anh-Việt.
    Sử dụng event-driven architecture của Tkinter.
    """

    def __init__(self, root: tk.Tk) -> None:  # type: ignore
        self.root = root
        self._dict_app: Optional[DictionaryApp] = None
        self._last_word: str = ""

        self._setup_window()
        self._build_header()
        self._build_search_bar()
        self._build_result_panel()
        self._build_status_bar()
        self._load_dictionary()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.root.title(  # type: ignore
            "📖  Từ Điển Anh-Việt  —  O(log n) Binary Search Engine"
        )
        self.root.configure(bg=C["bg"])  # type: ignore
        self.root.geometry("860x680")  # type: ignore
        self.root.minsize(700, 520)  # type: ignore
        self.root.resizable(True, True)  # type: ignore

        # Icon (ký tự unicode — không cần file .ico)
        try:
            self.root.iconbitmap("")  # type: ignore
        except Exception:
            pass

    def _load_dictionary(self) -> None:
        """Khởi động DictionaryApp; nếu chưa có data thì build trước."""
        if not os.path.exists(DATA_PATH) or not os.path.exists(INDEX_PATH):
            self._set_status(
                "⚠  Chưa có dữ liệu — đang tạo từ điển mẫu …",
                C["gold"]
            )
            self.root.update()  # type: ignore
            try:
                import build_database  # type: ignore
                build_database.build()
            except Exception as e:
                messagebox.showerror(
                    "Lỗi", f"Không thể tạo dữ liệu:\n{e}"
                )
                return

        try:
            self._dict_app = DictionaryApp(DATA_PATH, INDEX_PATH)
            n = self._dict_app.total_words()  # type: ignore
            self._set_status(
                f"✓  Đã tải {n:,} từ vựng  —  "
                f"Thuật toán: O(log n) Binary Search  "
                f"|  Cache: O(1) LRU",
                C["green"]
            )
        except Exception as e:
            self._set_status(
                f"✗  Lỗi tải dữ liệu: {e}", C["accent"]
            )

    # ------------------------------------------------------------------
    # Widget builders
    # ------------------------------------------------------------------

    def _build_header(self) -> None:
        header = tk.Frame(  # type: ignore
            self.root, bg=C["card"], pady=16
        )
        header.pack(fill="x")  # type: ignore

        tk.Label(  # type: ignore
            header,
            text="📖  TỪ ĐIỂN ANH - VIỆT",
            font=(FONT_FAMILY, 22, "bold"),
            bg=C["card"], fg=C["accent"]
        ).pack()

        tk.Label(  # type: ignore
            header,
            text="Binary Search Engine  ·  O(log n) lookup"
                 "  ·  LRU Cache  ·  IPA Phonetics",
            font=(FONT_FAMILY, 10),
            bg=C["card"], fg=C["text_dim"]
        ).pack(pady=(2, 0))

    def _build_search_bar(self) -> None:
        bar = tk.Frame(  # type: ignore
            self.root, bg=C["bg"], pady=14, padx=24
        )
        bar.pack(fill="x")  # type: ignore

        # Ô nhập liệu
        self._search_var = tk.StringVar()  # type: ignore
        self._entry = tk.Entry(  # type: ignore
            bar,
            textvariable=self._search_var,
            font=(FONT_FAMILY, 15),
            bg=C["search_bg"], fg=C["text_main"],
            insertbackground=C["accent"],
            relief="flat",
            bd=0,
        )
        self._entry.pack(  # type: ignore
            side="left", fill="x", expand=True,
            ipady=9, padx=(0, 10)
        )
        self._entry.bind(  # type: ignore
            "<Return>", lambda e: self._on_search()
        )
        self._entry.bind(  # type: ignore
            "<KeyRelease>", self._on_key_release
        )
        self._entry.focus()  # type: ignore

        # Nút tìm kiếm
        tk.Button(  # type: ignore
            bar,
            text="🔍  Tìm",
            font=(FONT_FAMILY, 12, "bold"),
            bg=C["btn_bg"], fg=C["btn_fg"],
            activebackground=C["border"],
            relief="flat", cursor="hand2",
            padx=16, pady=8,
            command=self._on_search,
        ).pack(side="left")

        # Nút phát âm
        self._speak_btn = tk.Button(  # type: ignore
            bar,
            text="🔊",
            font=(FONT_FAMILY, 14),
            bg=C["btn_speak"], fg=C["text_main"],
            activebackground=C["border"],
            relief="flat", cursor="hand2",
            padx=10, pady=8,
            command=self._on_speak,
        )
        self._speak_btn.pack(  # type: ignore
            side="left", padx=(8, 0)
        )

        # Nút RAG AI
        self._rag_btn = tk.Button(  # type: ignore
            bar,
            text="✨ Giải thích AI",
            font=(FONT_FAMILY, 11, "bold"),
            bg="#BB86FC", fg="#121212",
            activebackground="#9965f4",
            relief="flat", cursor="hand2",
            padx=12, pady=9,
            command=self._on_rag,
        )
        self._rag_btn.pack(  # type: ignore
            side="left", padx=(8, 0)
        )

    def _build_result_panel(self) -> None:
        """Vùng hiển thị kết quả — Text widget có khả năng cuộn."""
        outer = tk.Frame(  # type: ignore
            self.root, bg=C["bg"], padx=20, pady=0
        )
        outer.pack(fill="both", expand=True)  # type: ignore

        # Scrollbar
        scroll = tk.Scrollbar(  # type: ignore
            outer, cursor="arrow", bg=C["panel"]
        )
        scroll.pack(side="right", fill="y")  # type: ignore

        self._result = tk.Text(  # type: ignore
            outer,
            font=(FONT_FAMILY, 12),
            bg=C["panel"], fg=C["text_main"],
            relief="flat", bd=0,
            wrap="word",
            padx=20, pady=16,
            state="disabled",
            yscrollcommand=scroll.set,
            cursor="arrow",
            spacing1=2, spacing3=2,
        )
        self._result.pack(  # type: ignore
            fill="both", expand=True
        )
        scroll.config(command=self._result.yview)  # type: ignore

        # Cấu hình các tag định dạng
        self._result.tag_configure(  # type: ignore
            "word",
            font=(FONT_FAMILY, 26, "bold"),
            foreground=C["text_main"]
        )
        self._result.tag_configure(  # type: ignore
            "phonetic",
            font=("Georgia", 14, "italic"),
            foreground=C["gold"]
        )
        self._result.tag_configure(  # type: ignore
            "wclass",
            font=(FONT_FAMILY, 11, "italic"),
            foreground=C["text_dim"]
        )
        self._result.tag_configure(  # type: ignore
            "section",
            font=(FONT_FAMILY, 11, "bold"),
            foreground=C["accent"]
        )
        self._result.tag_configure(  # type: ignore
            "meaning",
            font=(FONT_FAMILY, 12),
            foreground=C["text_main"]
        )
        self._result.tag_configure(  # type: ignore
            "index",
            font=(FONT_FAMILY, 12, "bold"),
            foreground=C["gold"]
        )
        self._result.tag_configure(  # type: ignore
            "ex_en",
            font=(FONT_FAMILY, 11, "italic"),
            foreground=C["text_example"]
        )
        self._result.tag_configure(  # type: ignore
            "ex_vi",
            font=(FONT_FAMILY, 11),
            foreground=C["text_dim"]
        )
        self._result.tag_configure(  # type: ignore
            "divider",
            font=(FONT_FAMILY, 8),
            foreground=C["border"]
        )
        self._result.tag_configure(  # type: ignore
            "not_found",
            font=(FONT_FAMILY, 14),
            foreground=C["accent"]
        )
        self._result.tag_configure(  # type: ignore
            "hint",
            font=(FONT_FAMILY, 11, "italic"),
            foreground=C["text_dim"]
        )
        self._result.tag_configure(  # type: ignore
            "tag_noun",
            font=(FONT_FAMILY, 10, "bold"),
            foreground="#FFFFFF",
            background=C["tag_noun"]
        )
        self._result.tag_configure(  # type: ignore
            "tag_verb",
            font=(FONT_FAMILY, 10, "bold"),
            foreground="#FFFFFF",
            background=C["tag_verb"]
        )
        self._result.tag_configure(  # type: ignore
            "tag_adj",
            font=(FONT_FAMILY, 10, "bold"),
            foreground="#FFFFFF",
            background=C["tag_adj"]
        )
        self._result.tag_configure(  # type: ignore
            "tag_other",
            font=(FONT_FAMILY, 10, "bold"),
            foreground="#FFFFFF",
            background=C["tag_other"]
        )

        # Màn hình chào
        self._show_welcome()

    def _build_status_bar(self) -> None:
        self._status_var = tk.StringVar(  # type: ignore
            value="Đang khởi động …"
        )
        self._status_lbl = tk.Label(  # type: ignore
            self.root,
            textvariable=self._status_var,
            font=(FONT_FAMILY, 9),
            bg=C["card"], fg=C["text_dim"],
            anchor="w", padx=16, pady=5
        )
        self._status_lbl.pack(  # type: ignore
            fill="x", side="bottom"
        )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_key_release(self, event) -> None:  # type: ignore
        """Cho phép tìm kiếm bằng Enter; xóa text nếu ô trống."""
        if not self._search_var.get().strip():  # type: ignore
            self._show_welcome()

    def _on_search(self) -> None:
        keyword = self._search_var.get().strip()  # type: ignore
        if not keyword:
            return
        if not self._dict_app:
            self._set_status(
                "✗  Dữ liệu chưa sẵn sàng.", C["accent"]
            )
            return

        self._last_word = keyword
        entry = self._dict_app.find_word(keyword)  # type: ignore
        cache_info = (
            self._dict_app._lookup_cached.cache_info()  # type: ignore
        )

        if entry:
            cache_hit = cache_info.hits > 0  # type: ignore
            self._display_entry(entry, from_cache=cache_hit)
            algo_info = (
                "O(1) LRU Cache" if cache_hit
                else "O(log n) Binary Search"
            )
            self._set_status(
                f"✓  Tìm thấy  «{entry.word}»  —  "
                f"Thuật toán: {algo_info}  "
                f"|  Cache: {cache_info.hits} hits "  # type: ignore
                f"/ {cache_info.misses} misses",  # type: ignore
                C["green"]
            )
        else:
            self._display_not_found(keyword)
            self._set_status(
                f"✗  Không tìm thấy  «{keyword}»  —  "
                f"O(log n) Binary Search hoàn tất",
                C["accent"]
            )

    def _on_speak(self) -> None:
        word = (
            self._last_word
            or self._search_var.get().strip()  # type: ignore
        )
        if word:
            _speak_async(word)
            self._set_status(
                f"🔊  Đang phát âm: {word}", C["gold"]
            )
        else:
            self._set_status(
                "⚠  Nhập từ cần tra cứu trước.", C["gold"]
            )

    def _on_rag(self) -> None:
        """Kích hoạt giải thích bằng AI / RAG."""
        word = self._last_word
        if not word:
            messagebox.showinfo("Lỗi", "Vui lòng tìm kiếm một từ trước khi dùng AI.")  # type: ignore
            return
            
        # Kiểm tra API Key
        if not rag_engine.check_has_key() and not rag_engine.setup_from_env():
            key = simpledialog.askstring(  # type: ignore
                "Gemini API Key", 
                "Nhập Google Gemini API Key của bạn để sử dụng tính năng RAG:\n"
                "(Bạn có thể lấy miễn phí tại aistudio.google.com)",
                show="*"
            )
            if not key:
                return
            rag_engine.setup_api_key(key)

        entry = self._dict_app.find_word(word)  # type: ignore
        if not entry:
            return

        self._set_status(f"✨ Đang suy nghĩ: {word} ...", "#BB86FC")
        self._rag_btn.config(state="disabled", text="⏳ Đang tải...")  # type: ignore
        
        # Chạy nền để khỏi treo GUI
        def worker():  # type: ignore
            # Build raw text to feed the LLM
            raw_text = f"Nghĩa gốc: {entry.meanings}\nVí dụ: {entry.examples}"
            result = rag_engine.summarize_definition(word, raw_text)
            
            # Cập nhật GUI
            self.root.after(0, lambda: self._display_rag_result(result))  # type: ignore
            
        threading.Thread(target=worker, daemon=True).start()

    def _display_rag_result(self, result: str) -> None:
        """Hiển thị kết quả AI trả về lên GUI."""
        self._rag_btn.config(state="normal", text="✨ Giải thích AI")  # type: ignore
        self._set_status(f"✨ Đã giải thích xong: {self._last_word}", "#BB86FC")
        
        self._write(
            "\n  ✨  AI GIẢI THÍCH (RAG)\n", "section"
        )
        self._write(
            "  " + "─" * 48 + "\n", "divider"
        )
        # In kết quả
        for line in result.split("\n"):
            self._write(f"  {line}\n", "meaning")
        self._write("\n")
        
        # Tự động cuộn xuống dưới cùng
        self._result.see("end")  # type: ignore


    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def _write(self, text: str, *tags) -> None:  # type: ignore
        """Ghi text vào widget kết quả với các tag định dạng."""
        self._result.configure(state="normal")  # type: ignore
        self._result.insert(  # type: ignore
            "end", text, tags
        )
        self._result.configure(state="disabled")  # type: ignore

    def _clear(self) -> None:
        self._result.configure(state="normal")  # type: ignore
        self._result.delete("1.0", "end")  # type: ignore
        self._result.configure(state="disabled")  # type: ignore

    def _word_class_tag(self, wclass: str) -> str:
        wc = wclass.lower()
        if "noun" in wc:
            return "tag_noun"
        if "verb" in wc:
            return "tag_verb"
        if "adj" in wc:
            return "tag_adj"
        return "tag_other"

    def _display_entry(
        self, entry: LexicalEntry, from_cache: bool = False
    ) -> None:
        self._clear()

        # ── Từ khóa + phiên âm ─────────────────────────────────────────
        self._write(f"  {entry.word.upper()}", "word")
        if entry.phonetic:
            self._write(f"   {entry.phonetic}", "phonetic")
        self._write("\n")

        # ── Từ loại (tag pill) ─────────────────────────────────────────
        if entry.word_class:
            tag = self._word_class_tag(entry.word_class)
            self._write(
                f"  {entry.word_class.upper()}  ", tag
            )
        if from_cache:
            self._write("   ⚡ Từ cache RAM", "hint")
        self._write("\n\n")

        # ── Nghĩa tiếng Việt ───────────────────────────────────────────
        self._write("  📚  NGHĨA TIẾNG VIỆT\n", "section")
        self._write("  " + "─" * 48 + "\n", "divider")
        for i, meaning in enumerate(entry.meanings[:3], 1):
            self._write(f"  {i}. ", "index")
            self._write(f"{meaning}\n", "meaning")
        if len(entry.meanings) > 3:
            self._write(f"  ... (và {len(entry.meanings) - 3} nghĩa khác. Bấm 'Giải thích AI' để xem chi tiết)\n", "hint")

        # ── Ví dụ ngữ cảnh ─────────────────────────────────────────────
        if entry.examples:
            self._write(
                "\n  💬  VÍ DỤ SỬ DỤNG\n", "section"
            )
            self._write(
                "  " + "─" * 48 + "\n", "divider"
            )
            for en_sent, vi_sent in entry.examples[:2]:
                self._write(
                    f"  ▸ {en_sent}\n", "ex_en"
                )
                self._write(
                    f"    {vi_sent}\n\n", "ex_vi"
                )
            if len(entry.examples) > 2:
                self._write(f"  ... (và {len(entry.examples) - 2} ví dụ khác)\n", "hint")

    def _display_not_found(self, keyword: str) -> None:
        self._clear()
        self._write(
            f"\n\n  ✗  Không tìm thấy từ «{keyword}»\n\n",
            "not_found"
        )
        self._write(
            "  Gợi ý:\n"
            "  • Kiểm tra chính tả "
            "(ứng dụng phân biệt từng ký tự)\n"
            "  • Thử dạng nguyên mẫu "
            "(ví dụ: 'run' thay vì 'running')\n"
            "  • Chạy  python build_database.py  "
            "để cập nhật dữ liệu\n",
            "hint"
        )

    def _show_welcome(self) -> None:
        self._clear()
        self._write(
            "\n\n  Xin chào! Nhập từ tiếng Anh vào "
            "ô tìm kiếm và nhấn Enter.\n\n",
            "section"
        )
        self._write(
            "  ⚡  Tính năng nổi bật:\n\n"
            "  🔍  Tìm kiếm nhị phân trên ổ đĩa"
            " — O(log n)\n"
            "  💾  Bộ nhớ đệm LRU"
            " — O(1) cho từ đã tra\n"
            "  📐  Chỉ mục cố định 53-byte"
            " (fixed-width records)\n"
            "  🎧  Phát âm bằng Text-to-Speech\n"
            "  🇻🇳  Nghĩa tiếng Việt"
            " + Phiên âm IPA + Ví dụ ngữ cảnh\n",
            "hint"
        )

    def _set_status(
        self, message: str, color: str = ""
    ) -> None:
        self._status_var.set(message)  # type: ignore
        if color:
            self._status_lbl.configure(  # type: ignore
                fg=color
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_close(self) -> None:
        if self._dict_app:
            self._dict_app.close()  # type: ignore
        self.root.destroy()  # type: ignore


# ── Entry point ────────────────────────────────────────────────────────────

def main() -> None:
    root = tk.Tk()  # type: ignore
    app = DictionaryUI(root)
    root.protocol(  # type: ignore
        "WM_DELETE_WINDOW", app.on_close
    )
    root.mainloop()  # type: ignore


if __name__ == "__main__":
    main()
