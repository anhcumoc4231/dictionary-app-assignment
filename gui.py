"""
gui.py - Giao diện Người dùng (DictionaryUI)
=============================================
Entry point chính của ứng dụng.
Chạy ứng dụng: python gui.py
"""

import os
import sys
import threading
import webbrowser
import urllib.request
import tkinter as tk
from tkinter import messagebox, simpledialog  # type: ignore
from typing import Optional, List

# Bổ sung thư mục cha vào sys.path (an toàn khi chạy từ bất kỳ đâu)
sys.path.insert(0, os.path.dirname(__file__))

from app import DictionaryApp  # type: ignore  # noqa: E402
from models import LexicalEntry, Sense  # type: ignore  # noqa: E402

if getattr(sys, 'frozen', False):
    _BASE = sys._MEIPASS  # type: ignore
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))

DATA_PATH  = os.path.join(_BASE, "data", "meaning.data")
INDEX_PATH = os.path.join(_BASE, "data", "index.data")
WORDS_LIST_PATH = os.path.join(_BASE, "data", "words_list.txt")

# ── Bảng màu (Dark Mode Violet-Gold) ─────────────────────────────────────
C = {
    "bg":           "#0F0F1A",
    "panel":        "#1A1A2E",
    "card":         "#16213E",
    "border":       "#0F3460",
    "accent":       "#E94560",
    "gold":         "#F5A623",
    "text_main":    "#EAEAEA",
    "text_dim":     "#8892A4",
    "text_example": "#A8B5C8",
    "search_bg":    "#1E1E2E",
    "btn_bg":       "#E94560",
    "btn_fg":       "#FFFFFF",
    "btn_speak":    "#0F3460",
    "green":        "#4CAF50",
    "tag_noun":     "#5C9BD1",
    "tag_verb":     "#C97BDB",
    "tag_adj":      "#F0A500",
    "tag_other":    "#7EC8A4",
}

FONT_FAMILY = "Segoe UI"


# ── Helper tải danh sách từ cho Autocomplete ────────────────────────────
def _ensure_words_list() -> None:
    if os.path.exists(WORDS_LIST_PATH):
        return
    os.makedirs(os.path.dirname(WORDS_LIST_PATH), exist_ok=True)
    # Tải 10,000 từ tiếng Anh thông dụng nhất (100KB)
    url = "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt"
    try:
        urllib.request.urlretrieve(url, WORDS_LIST_PATH)
    except Exception as e:
        print(f"Error downloading words list: {e}")


def _load_words_list() -> List[str]:
    _ensure_words_list()
    words = []
    if os.path.exists(WORDS_LIST_PATH):
        with open(WORDS_LIST_PATH, "r", encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]
    return sorted(words)


# ── Main GUI Class ────────────────────────────────────────────────────────

class DictionaryUI:
    def __init__(self, root: tk.Tk) -> None:  # type: ignore
        self.root = root
        self._dict_app: Optional[DictionaryApp] = None
        self._last_entry: Optional[LexicalEntry] = None
        self._autocomplete_words: List[str] = []
        
        self._listbox_frame: tk.Frame = None # type: ignore
        self._search_frame: tk.Frame = None # type: ignore
        self._status_var: tk.StringVar = None # type: ignore
        self._status_lbl: tk.Label = None # type: ignore

        self._setup_window()
        self._build_header()
        self._build_search_bar()
        self._build_result_panel()
        self._build_status_bar()
        
        # Initialization threading to keep UI responsive
        threading.Thread(target=self._init_backend, daemon=True).start()

    def _init_backend(self) -> None:
        self._set_status("Đang khởi tạo hệ thống Cache và dữ liệu Autocomplete...", C["gold"]) # type: ignore
        self.root.update()  # type: ignore
        
        self._autocomplete_words = _load_words_list()
        self._dict_app = DictionaryApp(DATA_PATH, INDEX_PATH)
        self._update_status_idle()

    def _update_status_idle(self) -> None:
        if not self._dict_app: return
        n = self._dict_app.total_words_cached() # type: ignore
        self._set_status( # type: ignore
            f"✓ Sẵn sàng | O(log n) Local Cache: {n:,} từ | Free Dictionary API: Hoạt động",
            C["green"]
        )

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.root.title("📖 Từ Điển Anh-Việt — Hybrid FreeDict Architecture")  # type: ignore
        self.root.configure(bg=C["bg"])  # type: ignore
        self.root.geometry("860x720")  # type: ignore
        self.root.minsize(700, 520)  # type: ignore

    # ------------------------------------------------------------------
    # Widget builders
    # ------------------------------------------------------------------

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=C["card"], pady=16)  # type: ignore
        header.pack(fill="x")  # type: ignore

        tk.Label(  # type: ignore
            header, text="📖 TỪ ĐIỂN ANH - VIỆT",
            font=(FONT_FAMILY, 22, "bold"), bg=C["card"], fg=C["accent"]
        ).pack()

        tk.Label(  # type: ignore
            header, text="Free Dictionary API  ·  Local O(log n) Cache  ·  Autocomplete",
            font=(FONT_FAMILY, 10), bg=C["card"], fg=C["text_dim"]
        ).pack(pady=(2, 0))

        # API settings button (disabled because it's free now)
        tk.Button(  # type: ignore
            header, text="🟢 API Miễn phí", font=(FONT_FAMILY, 9),
            bg=C["card"], fg=C["green"], bd=0, relief="flat", cursor="arrow",
        ).place(relx=0.95, rely=0.5, anchor="e")

    def _build_search_bar(self) -> None:
        self._search_frame = tk.Frame(self.root, bg=C["bg"], pady=14, padx=24)  # type: ignore
        self._search_frame.pack(fill="x", anchor="n")  # type: ignore

        self._search_var = tk.StringVar()  # type: ignore
        self._entry = tk.Entry(  # type: ignore
            self._search_frame, textvariable=self._search_var,
            font=(FONT_FAMILY, 15), bg=C["search_bg"], fg=C["text_main"],
            insertbackground=C["accent"], relief="flat", bd=0
        )
        self._entry.pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 10))  # type: ignore
        self._entry.bind("<Return>", lambda e: self._on_search())  # type: ignore
        self._entry.bind("<KeyRelease>", self._on_key_release)  # type: ignore
        self._entry.bind("<Down>", self._on_arrow_down)  # type: ignore
        self._entry.focus()  # type: ignore

        tk.Button(  # type: ignore
            self._search_frame, text="🔍 Tìm", font=(FONT_FAMILY, 12, "bold"),
            bg=C["btn_bg"], fg=C["btn_fg"], activebackground=C["border"],
            relief="flat", cursor="hand2", padx=16, pady=8,
            command=self._on_search
        ).pack(side="left")

        # Nút phát âm US/UK
        self._speak_us_btn = tk.Button(  # type: ignore
            self._search_frame, text="🇺🇸 Phát âm (US)", font=(FONT_FAMILY, 10),
            bg=C["btn_speak"], fg=C["text_main"],
            relief="flat", cursor="hand2", padx=10, pady=10,
            command=lambda: self._on_speak("us")
        )
        self._speak_us_btn.pack(side="left", padx=(8, 0))  # type: ignore
        
        self._speak_uk_btn = tk.Button(  # type: ignore
            self._search_frame, text="🇬🇧 Phát âm (UK)", font=(FONT_FAMILY, 10),
            bg=C["btn_speak"], fg=C["text_main"],
            relief="flat", cursor="hand2", padx=10, pady=10,
            command=lambda: self._on_speak("uk")
        )
        self._speak_uk_btn.pack(side="left", padx=(8, 0))  # type: ignore

        # --- Autocomplete Listbox Overlay ---
        self._listbox_frame = tk.Frame(self.root, bg=C["search_bg"])  # type: ignore
        # listbox is placed dynamically below search_frame, managed internally
        self._listbox = tk.Listbox(  # type: ignore
            self._listbox_frame, font=(FONT_FAMILY, 13), bg=C["search_bg"], 
            fg=C["text_main"], selectbackground=C["border"], relief="flat", bd=0, height=6
        )
        self._listbox.pack(fill="both", expand=True)  # type: ignore
        self._listbox.bind("<Double-Button-1>", self._on_listbox_select)  # type: ignore
        self._listbox.bind("<Return>", self._on_listbox_select)  # type: ignore

    def _build_result_panel(self) -> None:
        outer = tk.Frame(self.root, bg=C["bg"], padx=20, pady=0)  # type: ignore
        outer.pack(fill="both", expand=True)  # type: ignore

        scroll = tk.Scrollbar(outer, cursor="arrow", bg=C["panel"])  # type: ignore
        scroll.pack(side="right", fill="y")  # type: ignore

        self._result = tk.Text(  # type: ignore
            outer, font=(FONT_FAMILY, 12), bg=C["panel"], fg=C["text_main"],
            relief="flat", bd=0, wrap="word", padx=20, pady=16,
            state="disabled", yscrollcommand=scroll.set, cursor="arrow",
            spacing1=2, spacing3=2,
        )
        self._result.pack(fill="both", expand=True)  # type: ignore
        scroll.config(command=self._result.yview)  # type: ignore

        # Tags definition
        self._result.tag_configure("word", font=(FONT_FAMILY, 26, "bold"), foreground=C["text_main"])  # type: ignore
        self._result.tag_configure("phonetic", font=("Georgia", 14, "italic"), foreground=C["gold"])  # type: ignore
        self._result.tag_configure("ipa", font=("Georgia", 14, "italic"), foreground=C["gold"]) # Added for ipa
        self._result.tag_configure("wclass", font=(FONT_FAMILY, 12, "bold", "italic"), foreground=C["accent"])  # type: ignore
        self._result.tag_configure("section", font=(FONT_FAMILY, 11, "bold"), foreground=C["accent"])  # type: ignore
        self._result.tag_configure("short_meaning", font=(FONT_FAMILY, 14, "bold"), foreground=C["green"], spacing1=4, spacing3=4)
        self._result.tag_configure("meaning", font=(FONT_FAMILY, 11, "bold"), foreground=C["gold"], spacing1=4)  # type: ignore
        self._result.tag_configure("index", font=(FONT_FAMILY, 13, "bold"), foreground=C["gold"])  # type: ignore
        self._result.tag_configure("ex_en", font=(FONT_FAMILY, 11, "italic"), foreground=C["text_example"])  # type: ignore
        self._result.tag_configure("ex_vi", font=(FONT_FAMILY, 11), foreground=C["text_dim"])  # type: ignore
        self._result.tag_configure("divider", font=(FONT_FAMILY, 8), foreground=C["border"])  # type: ignore
        self._result.tag_configure("not_found", font=(FONT_FAMILY, 14), foreground=C["accent"])  # type: ignore
        self._result.tag_configure("hint", font=(FONT_FAMILY, 11, "italic"), foreground=C["text_dim"])  # type: ignore

        self._show_welcome()

    def _build_status_bar(self) -> None:
        self._status_var = tk.StringVar(value="Đang khởi động …")  # type: ignore
        self._status_lbl = tk.Label(  # type: ignore
            self.root, textvariable=self._status_var, font=(FONT_FAMILY, 9),
            bg=C["card"], fg=C["text_dim"], anchor="w", padx=16, pady=5
        )
        self._status_lbl.pack(fill="x", side="bottom")  # type: ignore

    def _set_status(self, message: str, color: str = "") -> None:
        if hasattr(self, "_status_var") and self._status_var:
            self._status_var.set(message) # type: ignore
        if hasattr(self, "_status_lbl") and self._status_lbl and color:
            self._status_lbl.configure(fg=color) # type: ignore

    # ------------------------------------------------------------------
    # Autocomplete Logic
    # ------------------------------------------------------------------

    def _show_listbox(self) -> None:
        # Overlay below search bar
        self._listbox_frame.place(
            in_=self._search_frame, x=24, rely=1.0, 
            relwidth=1.0, width=-300, y=-10
        )
        self._listbox_frame.lift()

    def _hide_listbox(self) -> None:
        self._listbox_frame.place_forget()

    def _on_key_release(self, event) -> None:  # type: ignore
        if event.keysym in ("Return", "Down", "Up", "Left", "Right"):
            return
            
        keyword = self._search_var.get().strip().lower()  # type: ignore
        if not keyword:
            self._hide_listbox()
            self._show_welcome()
            return
            
        # Filter autocomplete matches
        matches = [w for w in self._autocomplete_words if w.startswith(keyword)][:7] # type: ignore
        if matches:
            self._listbox.delete(0, tk.END)  # type: ignore
            for m in matches:
                self._listbox.insert(tk.END, m)  # type: ignore
            self._show_listbox()
        else:
            self._hide_listbox()

    def _on_arrow_down(self, event) -> None:  # type: ignore
        if self._listbox_frame.winfo_ismapped():
            self._listbox.focus()  # type: ignore
            self._listbox.selection_set(0)  # type: ignore

    def _on_listbox_select(self, event) -> None:  # type: ignore
        sel = self._listbox.curselection()  # type: ignore
        if sel:
            for idx in sel: # type: ignore
                word = str(self._listbox.get(int(idx))) # type: ignore
                self._search_var.set(word)  # type: ignore
                break
            self._hide_listbox()
            self._entry.focus()  # type: ignore
            self._on_search()

    # ------------------------------------------------------------------
    # Search & Audio
    # ------------------------------------------------------------------

    def _on_search(self) -> None:
        self._hide_listbox()
        keyword = self._search_var.get().strip()  # type: ignore
        if not keyword: return
        
        if not self._dict_app:
            self._set_status("✗ Hệ thống chưa khởi tạo xong.", C["accent"]) # type: ignore
            return

        self._set_status(f"🌐 Đang tra cứu '{keyword}'...", C["gold"]) # type: ignore
        self._entry.config(state="disabled")  # type: ignore
        self.root.update()  # type: ignore

        # Run search in thread
        threading.Thread(target=self._search_worker, args=(keyword,), daemon=True).start()

    def _search_worker(self, keyword: str) -> None:
        entry = self._dict_app.find_word(keyword)  # type: ignore
        
        # Make sure UI updates in main thread
        self.root.after(0, lambda: self._handle_search_result(keyword, entry))  # type: ignore

    def _handle_search_result(self, keyword: str, entry: Optional[LexicalEntry]) -> None:
        self._entry.config(state="normal")  # type: ignore
        self._entry.focus()  # type: ignore
        
        self._last_entry = entry

        if entry:
            source = entry.source
            self._display_entry(entry)
            
            algo_info = "O(1) RAM Cache" if "Cache" in source else ("O(log n) Disk Cache" if source == "Local Cache" else "🌐 Free Dictionary API + Saved to Disk")
            self._set_status(f"✓ Tìm thấy «{entry.word}» — {algo_info}", C["green"]) # type: ignore
        else:
            self._display_not_found(keyword)
            self._set_status(f"✗ Không tìm thấy «{keyword}» trên mạng cũng như trong cache.", C["accent"]) # type: ignore

    def _on_speak(self, locale: str) -> None:
        if not self._last_entry:
            self._set_status("⚠ Vui lòng tra cứu một từ trước.", C["gold"]) # type: ignore
            return
            
        url = self._last_entry.us_audio if locale == "us" else self._last_entry.uk_audio # type: ignore
        
        if url:
            self._set_status(f"🔊 Mở MP3 [{locale.upper()}]: {url}", C["gold"]) # type: ignore
            # Fallback to system web browser to play MP3 since Tkinter doesn't have a built-in player
            webbrowser.open_new_tab(url)
        else:
            # Fallback to offline pyttsx3
            self._set_status(f"⚠ Free Dictionary API không có audio cho từ này. Đang dùng giọng máy offline...", C["gold"]) # type: ignore
            def _speak():
                try:
                    import pyttsx3  # type: ignore
                    engine = pyttsx3.init()
                    engine.say(self._last_entry.word)  # type: ignore
                    engine.runAndWait()
                except Exception:
                    pass
            threading.Thread(target=_speak, daemon=True).start()

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def _write(self, text: str, *tags) -> None:  # type: ignore
        self._result.configure(state="normal")  # type: ignore
        self._result.insert("end", text, tags)  # type: ignore
        self._result.configure(state="disabled")  # type: ignore

    def _clear(self) -> None:
        self._result.configure(state="normal")  # type: ignore
        self._result.delete("1.0", "end")  # type: ignore
        self._result.configure(state="disabled")  # type: ignore

    def _display_entry(self, entry: LexicalEntry) -> None:
        self._clear()

        # Word Header
        self._write(f"  {entry.word.upper()}\n", "word")
        
        if entry.uk_ipa or entry.us_ipa:
            ipa = entry.uk_ipa or entry.us_ipa
            self._write(f"  {ipa}\n", "ipa")
            
        # KẾT QUẢ "MỲ ĂN LIỀN" - Dịch trực tiếp từ vựng
        short_trans = getattr(entry, "short_translation", "")
        if short_trans:
            self._write(f"  {short_trans}\n", "short_meaning")
            
        self._write("\n", "text_main")
        
        if getattr(entry, "source", ""):
            self._write(f"   ⚡ Chế độ: {entry.source}\n", "hint")
            
        self._write("  " + "━" * 50 + "\n\n", "divider")

        # Senses
        senses = getattr(entry, "senses", [])
        if not senses:
            self._write("  Chưa có định nghĩa cho từ này.\n", "hint")
            return
            
        current_pos = ""
        for i, sense in enumerate(senses, 1):
            if sense.pos and sense.pos != current_pos:
                current_pos = sense.pos
                self._write(f"\n  ■ {current_pos.upper()}\n", "wclass")
            
            self._write(f"  {i}. ", "index")
            if sense.translation:
                self._write(f"{sense.translation}\n", "meaning")
            
            if sense.definition:
                self._write(f"     ({sense.definition})\n", "text_main")

            for idx, ex in enumerate(sense.examples):
                self._write(f"     ▸ {ex.get('en', '')}\n", "ex_en")
                if ex.get('vi'):
                    self._write(f"       {ex.get('vi', '')}\n", "ex_vi")
            self._write("\n")

    def _display_not_found(self, keyword: str) -> None:
        self._clear()
        self._write(f"\n\n  ✗ Không tìm thấy từ «{keyword}»\n\n", "not_found")
        self._write(
            "  Gợi ý:\n"
            "  • Kiểm tra lại kết nối mạng (API Cambridge).\n"
            "  • Truy cập Cấu hình API để điền đúng Access Key.\n",
            "hint"
        )

    def _show_welcome(self) -> None:
        self._clear()
        self._write("\n\n  Xin chào! Nhập từ tiếng Anh vào ô tìm kiếm.\n\n", "section")
        self._write(
            "  ⚡ Cập nhật MỚI: HYBRID ARCHITECTURE\n\n"
            "  🌐 Online Free Dict API: Tra cứu nhanh chóng, miễn phí 100%.\n"
            "  💾 O(log n) Disk Cache: Tự động lưu những từ đã tải xuống đĩa cứng.\n"
            "  🎵 Native Audio: Mở trực tiếp file MP3 bản xứ (US/UK) (tuỳ thuộc API).\n"
            "  ⌨️ Autocomplete: Gợi ý nhanh 10,000 từ phổ thông khi bạn gõ.\n",
            "hint"
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
    root.protocol("WM_DELETE_WINDOW", app.on_close)  # type: ignore
    root.mainloop()  # type: ignore

if __name__ == "__main__":
    main()
