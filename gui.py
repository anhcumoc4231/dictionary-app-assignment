"""
gui.py - Giao diện Người dùng kiểu Chatbot AI (DictionaryUI)
=============================================================
Entry point chính của ứng dụng.
Chạy ứng dụng: python gui.py
"""

import os
import sys
import threading
import webbrowser
import urllib.request
import tkinter as tk
from tkinter import messagebox  # type: ignore
from typing import Optional, List

# Bổ sung thư mục cha vào sys.path (an toàn khi chạy từ bất kỳ đâu)
sys.path.insert(0, os.path.dirname(__file__))  # type: ignore

from app import DictionaryApp  # type: ignore  # noqa: E402
from models import LexicalEntry  # type: ignore  # noqa: E402

if getattr(sys, 'frozen', False):
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))

DATA_PATH  = os.path.join(_BASE, "data", "meaning.data")
INDEX_PATH = os.path.join(_BASE, "data", "index.data")
WORDS_LIST_PATH = os.path.join(_BASE, "data", "words_list.txt")

# ── Bảng màu ─────────────────────────────────────────────────────────────────
C = {
    "bg":           "#0D0D1A",
    "chat_bg":      "#12121F",
    "bubble_ai":    "#1A1F35",
    "bubble_user":  "#3B1F5E",
    "bubble_border":"#2A2A4A",
    "accent":       "#8B5CF6",   # violet
    "accent2":      "#EC4899",   # pink/rose
    "gold":         "#F59E0B",
    "green":        "#10B981",
    "red":          "#EF4444",
    "text_main":    "#F1F5F9",
    "text_dim":     "#94A3B8",
    "text_example": "#CBD5E1",
    "input_bg":     "#1E1E35",
    "input_border": "#4C1D95",
    "header_bg":    "#0D0D1A",
}

FONT_FAMILY = "Segoe UI"

# ── Helper tải danh sách từ cho Autocomplete ─────────────────────────────────
def _ensure_words_list() -> None:
    if os.path.exists(WORDS_LIST_PATH):
        return
    os.makedirs(os.path.dirname(WORDS_LIST_PATH), exist_ok=True)
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

# ── Main GUI Class ─────────────────────────────────────────────────────────────
class DictionaryUI:
    def __init__(self) -> None:
        self.root = tk.Tk()  # type: ignore
        self.root.title("🤖 AI Dictionary — Từ Điển Anh-Việt")
        self.root.configure(bg=C["bg"])  # type: ignore
        self.root.geometry("900x720")
        self.root.minsize(700, 520)

        self._dict_app: Optional[DictionaryApp] = None
        self._autocomplete_words: List[str] = []
        self._search_var = tk.StringVar()  # type: ignore

        self._build_header()
        self._build_chat_area()
        self._build_input_bar()
        self._welcome_message()

        # Init backend in background
        threading.Thread(target=self._init_backend, daemon=True).start()

    # ------------------------------------------------------------------
    # Backend Init
    # ------------------------------------------------------------------

    def _init_backend(self) -> None:
        self._autocomplete_words = _load_words_list()
        self._dict_app = DictionaryApp(DATA_PATH, INDEX_PATH)
        n = self._dict_app.total_words_cached() # type: ignore
        self.root.after(0, lambda: self._add_ai_bubble(  # type: ignore
            f"✅ Hệ thống sẵn sàng!\n📦 Local Cache: **{n:,} từ** | 🌐 Free Dictionary API: Hoạt động"
        ))

    # ------------------------------------------------------------------
    # Widget builders
    # ------------------------------------------------------------------

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=C["header_bg"], pady=10) # type: ignore
        header.pack(fill="x", side="top")  # type: ignore

        tk.Label( # type: ignore
            header,
            text="🤖  AI TỪ ĐIỂN ANH-VIỆT",
            font=(FONT_FAMILY, 18, "bold"),
            bg=C["header_bg"], fg=C["text_main"]
        ).pack(side="left", padx=20)  # type: ignore

        tk.Label( # type: ignore
            header,
            text="Free Dictionary API · O(log n) Cache · Autocomplete",
            font=(FONT_FAMILY, 9),
            bg=C["header_bg"], fg=C["text_dim"]
        ).pack(side="left", padx=4)  # type: ignore

        # Clear button
        tk.Button( # type: ignore
            header, text="🗑 Xóa lịch sử",
            font=(FONT_FAMILY, 9), bg="#2A2A4A", fg=C["text_dim"],
            bd=0, relief="flat", padx=10, pady=4, cursor="hand2",
            activebackground="#3A3A5A", activeforeground=C["text_main"],
            command=self._clear_chat
        ).pack(side="right", padx=14)  # type: ignore

        # Audio buttons
        tk.Button( # type: ignore
            header, text="🇬🇧 UK", font=(FONT_FAMILY, 9),
            bg="#1a1a3a", fg=C["text_dim"],
            bd=0, relief="flat", padx=8, pady=4, cursor="hand2",
            command=lambda: self._on_speak("uk")
        ).pack(side="right", padx=2)  # type: ignore
        tk.Button( # type: ignore
            header, text="🇺🇸 US", font=(FONT_FAMILY, 9),
            bg="#1a1a3a", fg=C["text_dim"],
            bd=0, relief="flat", padx=8, pady=4, cursor="hand2",
            command=lambda: self._on_speak("us")
        ).pack(side="right", padx=2)  # type: ignore

        # Separator
        tk.Frame(self.root, bg=C["bubble_border"], height=1).pack(fill="x") # type: ignore

    def _build_chat_area(self) -> None:
        """Chat area: Canvas + Scrollbar để render bubble messages."""
        container = tk.Frame(self.root, bg=C["chat_bg"]) # type: ignore
        container.pack(fill="both", expand=True, padx=0, pady=0)  # type: ignore

        # Scrollbar
        scrollbar = tk.Scrollbar(container, orient="vertical", bg=C["bg"], troughcolor=C["chat_bg"]) # type: ignore
        scrollbar.pack(side="right", fill="y")  # type: ignore

        # Canvas
        self._canvas = tk.Canvas( # type: ignore
            container, bg=C["chat_bg"], bd=0, highlightthickness=0,
            yscrollcommand=scrollbar.set  # type: ignore
        )
        self._canvas.pack(side="left", fill="both", expand=True)  # type: ignore
        scrollbar.config(command=self._canvas.yview) # type: ignore

        # Inner frame where bubbles go
        self._chat_frame = tk.Frame(self._canvas, bg=C["chat_bg"]) # type: ignore
        self._chat_window = self._canvas.create_window((0, 0), window=self._chat_frame, anchor="nw") # type: ignore

        self._chat_frame.bind("<Configure>", self._on_frame_configure) # type: ignore
        self._canvas.bind("<Configure>", self._on_canvas_configure) # type: ignore

        # Mouse wheel scroll
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel) # type: ignore

    def _build_input_bar(self) -> None:
        """Bottom input bar with autocomplete."""
        bar = tk.Frame(self.root, bg=C["input_bg"], pady=10) # type: ignore
        bar.pack(fill="x", side="bottom")  # type: ignore

        # Separator
        tk.Frame(self.root, bg=C["input_border"], height=1).pack(fill="x", side="bottom") # type: ignore

        # Autocomplete Listbox (floats above input)
        self._listbox_frame = tk.Frame(self.root, bg=C["bubble_border"], bd=1, relief="solid") # type: ignore
        self._listbox = tk.Listbox( # type: ignore
            self._listbox_frame,
            font=(FONT_FAMILY, 11), bg="#1A1A35", fg=C["text_main"],
            selectbackground=C["accent"], selectforeground="white",
            bd=0, relief="flat", activestyle="none", height=5
        )
        self._listbox.pack(fill="both", expand=True)  # type: ignore
        self._listbox.bind("<<ListboxSelect>>", self._on_listbox_select) # type: ignore

        # Input row
        inner = tk.Frame(bar, bg=C["input_bg"]) # type: ignore
        inner.pack(fill="x", padx=14, pady=0)  # type: ignore

        # Entry
        entry_frame = tk.Frame(inner, bg=C["input_border"], bd=1, relief="solid") # type: ignore
        entry_frame.pack(side="left", fill="x", expand=True, ipady=2)  # type: ignore

        self._entry = tk.Entry( # type: ignore
            entry_frame,
            textvariable=self._search_var,
            font=(FONT_FAMILY, 14),
            bg=C["input_bg"], fg=C["text_main"],
            insertbackground=C["accent"],
            bd=0, relief="flat"
        )
        self._entry.pack(fill="x", padx=14, pady=10)  # type: ignore
        self._entry.bind("<Return>", self._on_search) # type: ignore
        self._entry.bind("<KeyRelease>", self._on_key_release) # type: ignore
        self._entry.bind("<Down>", self._on_arrow_down) # type: ignore
        self._entry.focus_set() # type: ignore

        # Send button
        tk.Button( # type: ignore
            inner, text="Tra  ➤",
            font=(FONT_FAMILY, 12, "bold"),
            bg=C["accent"], fg="white",
            activebackground=C["accent2"], activeforeground="white",
            bd=0, relief="flat", padx=20, pady=10, cursor="hand2",
            command=self._on_search
        ).pack(side="left", padx=(10, 0))  # type: ignore

    # ------------------------------------------------------------------
    # Canvas / Scroll helpers
    # ------------------------------------------------------------------

    def _on_frame_configure(self, event=None) -> None: # type: ignore
        self._canvas.configure(scrollregion=self._canvas.bbox("all")) # type: ignore

    def _on_canvas_configure(self, event) -> None: # type: ignore
        self._canvas.itemconfig(self._chat_window, width=event.width) # type: ignore

    def _on_mousewheel(self, event) -> None: # type: ignore
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units") # type: ignore

    def _scroll_to_bottom(self) -> None:
        self.root.update_idletasks()  # type: ignore
        self._canvas.yview_moveto(1.0) # type: ignore

    # ------------------------------------------------------------------
    # Bubble rendering
    # ------------------------------------------------------------------

    def _add_user_bubble(self, text: str) -> None:
        """Render a user query bubble (right-aligned, violet)."""
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=6) # type: ignore
        row.pack(fill="x", padx=16)  # type: ignore

        spacer = tk.Frame(row, bg=C["chat_bg"]) # type: ignore
        spacer.pack(side="left", expand=True)  # type: ignore

        bubble = tk.Frame(row, bg=C["bubble_user"], padx=16, pady=10) # type: ignore
        bubble.pack(side="right")  # type: ignore

        tk.Label( # type: ignore
            bubble, text=f"🔍  {text}",
            font=(FONT_FAMILY, 13, "bold"),
            bg=C["bubble_user"], fg="white",
            wraplength=400, justify="right"
        ).pack()  # type: ignore

        tk.Label( # type: ignore
            bubble, text="👤",
            font=(FONT_FAMILY, 9), bg=C["bubble_user"], fg=C["text_dim"]
        ).pack(anchor="e")  # type: ignore

        self._scroll_to_bottom()

    def _add_ai_bubble(self, markdown_text: str) -> None:
        """Render a simple AI info bubble (left-aligned, dark)."""
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=4) # type: ignore
        row.pack(fill="x", padx=16)  # type: ignore

        # Avatar
        tk.Label( # type: ignore
            row, text="🤖", font=(FONT_FAMILY, 18),
            bg=C["chat_bg"], fg=C["accent"]
        ).pack(side="left", anchor="n", padx=(0, 8), pady=4)  # type: ignore

        bubble = tk.Frame(row, bg=C["bubble_ai"], padx=16, pady=10) # type: ignore
        bubble.pack(side="left", fill="x", expand=True)  # type: ignore

        tk.Label( # type: ignore
            bubble, text=markdown_text.replace("**", ""),
            font=(FONT_FAMILY, 11),
            bg=C["bubble_ai"], fg=C["text_dim"],
            wraplength=680, justify="left"
        ).pack(anchor="w")  # type: ignore

        self._scroll_to_bottom()

    def _add_result_bubble(self, entry: LexicalEntry) -> None:
        """Render a rich dictionary result bubble (left-aligned)."""
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=6) # type: ignore
        row.pack(fill="x", padx=16)  # type: ignore

        # Avatar
        tk.Label( # type: ignore
            row, text="🤖", font=(FONT_FAMILY, 18),
            bg=C["chat_bg"], fg=C["accent"]
        ).pack(side="left", anchor="n", padx=(0, 8), pady=4)  # type: ignore

        bubble = tk.Frame(row, bg=C["bubble_ai"], padx=20, pady=14) # type: ignore
        bubble.pack(side="left", fill="x", expand=True)  # type: ignore

        # Word title & IPA
        ipa = entry.uk_ipa or entry.us_ipa
        title_text = entry.word.lower()
        if ipa:
            title_text += f" /{ipa}/"

        tk.Label(  # type: ignore
            bubble, text=title_text,
            font=(FONT_FAMILY, 20, "bold"),
            bg=C["bubble_ai"], fg=C["text_main"]
        ).pack(anchor="w", pady=(0, 2))

        # Source tag
        source = getattr(entry, "source", "")
        if source:
            algo = "⚡ O(1) RAM" if "Cache" in source else ("📀 O(log n) Disk" if source == "Local Cache" else "🌐 Free API")
            tk.Label(  # type: ignore
                bubble, text=algo,
                font=(FONT_FAMILY, 8),
                bg=C["bubble_ai"], fg=C["text_dim"]
            ).pack(anchor="w", pady=(0, 6))

        # Divider
        tk.Frame(bubble, bg=C["bubble_border"], height=1).pack(fill="x", pady=4)  # type: ignore

        # TFlat Pos Map
        pos_vi = {
            "noun": "danh từ", "verb": "động từ", "adjective": "tính từ",
            "adverb": "trạng từ", "pronoun": "đại từ", "preposition": "giới từ",
            "conjunction": "liên từ", "interjection": "thán từ", "idiom": "thành ngữ"
        }

        # Render senses
        current_pos = ""
        for i, sense in enumerate(entry.senses):
            pos_key = (sense.pos or "").lower()
            if pos_key and pos_key != current_pos:
                current_pos = pos_key
                vi_pos = pos_vi.get(current_pos, current_pos)
                tk.Label(  # type: ignore
                    bubble, text=f"* {vi_pos}",
                    font=(FONT_FAMILY, 12, "bold"),
                    bg=C["bubble_ai"], fg="#5C9BD1"
                ).pack(anchor="w", pady=(8, 2))

            # English definition (+ nghĩa tiếng Anh)
            if sense.definition:
                tk.Label(  # type: ignore
                    bubble, text=f"+ {sense.definition}",
                    font=(FONT_FAMILY, 11),
                    bg=C["bubble_ai"], fg=C["text_main"],
                    wraplength=640, justify="left"
                ).pack(anchor="w", padx=(10, 0))

            # Vietnamese meaning in parentheses (nghĩa tiếng Việt)
            if sense.translation:
                tk.Label(  # type: ignore
                    bubble, text=f"({sense.translation})",
                    font=(FONT_FAMILY, 10, "italic"),
                    bg=C["bubble_ai"], fg="#A8B5C8",
                    wraplength=640, justify="left"
                ).pack(anchor="w", padx=(25, 0))

            # Example (TFlat uses '=')
            for ex in sense.examples:
                en_ex = ex.get("en", "")
                if en_ex:
                    tk.Label(  # type: ignore
                        bubble, text=f"= {en_ex}",
                        font=(FONT_FAMILY, 10, "italic"),
                        bg=C["bubble_ai"], fg=C["text_example"],
                        wraplength=620, justify="left"
                    ).pack(anchor="w", padx=(10, 0))

        self._scroll_to_bottom()
        self._last_entry = entry

    def _add_not_found_bubble(self, keyword: str) -> None:
        """Render a not-found error bubble."""
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=6) # type: ignore
        row.pack(fill="x", padx=16)  # type: ignore
        tk.Label(row, text="🤖", font=(FONT_FAMILY, 18), bg=C["chat_bg"], fg=C["accent"]).pack(side="left", anchor="n", padx=(0, 8), pady=4) # type: ignore

        bubble = tk.Frame(row, bg="#2A1515", padx=16, pady=12) # type: ignore
        bubble.pack(side="left", fill="x", expand=True)  # type: ignore

        tk.Label(bubble, text=f"❌  Không tìm thấy «{keyword}»", # type: ignore
                 font=(FONT_FAMILY, 12, "bold"), bg="#2A1515", fg=C["red"]).pack(anchor="w")  # type: ignore
        tk.Label(bubble, text="Free Dictionary API không có dữ liệu cho từ này. Thử tra một từ vựng thông dụng khác nhé!", # type: ignore
                 font=(FONT_FAMILY, 10), bg="#2A1515", fg=C["text_dim"],
                 wraplength=620, justify="left").pack(anchor="w", pady=(4, 0))  # type: ignore

        self._scroll_to_bottom()

    def _welcome_message(self) -> None:
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=16) # type: ignore
        row.pack(fill="x", padx=16)  # type: ignore
        tk.Label(row, text="🤖", font=(FONT_FAMILY, 24), bg=C["chat_bg"], fg=C["accent"]).pack(side="left", anchor="n", padx=(0, 8)) # type: ignore
        bubble = tk.Frame(row, bg=C["bubble_ai"], padx=20, pady=14) # type: ignore
        bubble.pack(side="left", fill="x", expand=True)  # type: ignore
        tk.Label(bubble, text="Xin chào! Tôi là AI Từ Điển Anh-Việt 🌟", # type: ignore
                 font=(FONT_FAMILY, 14, "bold"), bg=C["bubble_ai"], fg=C["text_main"]).pack(anchor="w")  # type: ignore
        tk.Label(bubble, # type: ignore
                 text="Gõ một từ tiếng Anh vào ô bên dưới và nhấn \"Tra ➤\" để tra cứu nghĩa.\n"
                      "Tôi sẽ tra cứu từ Local Cache O(log n) trước — nếu chưa có sẽ gọi Free Dictionary API và dịch nghĩa Tiếng Việt ngay lập tức!",
                 font=(FONT_FAMILY, 10), bg=C["bubble_ai"], fg=C["text_dim"],
                 wraplength=640, justify="left").pack(anchor="w", pady=(6, 0))  # type: ignore

    def _clear_chat(self) -> None:
        for widget in self._chat_frame.winfo_children(): # type: ignore
            widget.destroy()  # type: ignore
        self._last_entry = None
        self._welcome_message()

    # ------------------------------------------------------------------
    # Search logic
    # ------------------------------------------------------------------

    def _on_search(self, event=None) -> None: # type: ignore
        self._hide_listbox()
        keyword = self._search_var.get().strip()  # type: ignore
        if not keyword:
            return
        self._search_var.set("")  # type: ignore

        # Render user bubble
        self._add_user_bubble(keyword)
        self._add_ai_bubble("⏳ Đang tra cứu...")

        def _do_search() -> None:
            if not self._dict_app:
                return
            entry = self._dict_app.find_word(keyword) # type: ignore
            # Remove the "loading" bubble
            self.root.after(0, lambda: self._remove_last_ai_bubble())  # type: ignore
            if entry:
                self.root.after(0, lambda: self._add_result_bubble(entry))  # type: ignore
            else:
                self.root.after(0, lambda: self._add_not_found_bubble(keyword))  # type: ignore

        threading.Thread(target=_do_search, daemon=True).start()

    def _remove_last_ai_bubble(self) -> None:
        """Remove the last child (loading indicator) from chat frame."""
        children = self._chat_frame.winfo_children() # type: ignore
        if children:
            children[-1].destroy()  # type: ignore

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------

    _last_entry: Optional[LexicalEntry] = None

    def _on_speak(self, accent: str) -> None:
        if not self._last_entry:
            return
        entry = self._last_entry
        url = entry.us_audio if accent == "us" else entry.uk_audio  # type: ignore[union-attr]
        if url:
            webbrowser.open_new_tab(url)
        else:
            def _fallback() -> None:
                try:
                    import pyttsx3  # type: ignore
                    e = pyttsx3.init()
                    e.say(entry.word)  # type: ignore[union-attr]
                    e.runAndWait()
                except Exception:
                    pass
            threading.Thread(target=_fallback, daemon=True).start()

    # ------------------------------------------------------------------
    # Autocomplete
    # ------------------------------------------------------------------

    def _show_listbox(self) -> None:
        x = self._entry.winfo_rootx() - self.root.winfo_rootx() # type: ignore
        y = self._entry.winfo_rooty() - self.root.winfo_rooty() - 130 # type: ignore
        w = self._entry.winfo_width() # type: ignore
        self._listbox_frame.place(x=x, y=y, width=w)  # type: ignore
        self._listbox_frame.lift() # type: ignore

    def _hide_listbox(self) -> None:
        self._listbox_frame.place_forget()  # type: ignore

    def _on_key_release(self, event) -> None: # type: ignore
        if event.keysym in ("Return", "Down", "Up", "Left", "Right"):  # type: ignore
            return
        keyword = self._search_var.get().strip().lower() # type: ignore
        if not keyword:
            self._hide_listbox()
            return
        matches = [w for w in self._autocomplete_words if w.startswith(keyword)][:7] # type: ignore
        if matches:
            self._listbox.delete(0, tk.END) # type: ignore
            for m in matches:
                self._listbox.insert(tk.END, m) # type: ignore
            self._show_listbox()
        else:
            self._hide_listbox()

    def _on_arrow_down(self, event) -> None: # type: ignore
        if self._listbox_frame.winfo_ismapped():  # type: ignore
            self._listbox.focus() # type: ignore
            self._listbox.selection_set(0) # type: ignore

    def _on_listbox_select(self, event) -> None: # type: ignore
        sel = self._listbox.curselection() # type: ignore
        if sel:  # type: ignore
            for idx in sel: # type: ignore
                word = str(self._listbox.get(int(idx))) # type: ignore
                self._search_var.set(word) # type: ignore
                break
            self._hide_listbox()
            self._entry.focus() # type: ignore
            self._on_search()

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.root.mainloop()  # type: ignore


# ── Entry Point ───────────────────────────────────────────────────────────────
def main() -> None:
    app = DictionaryUI()
    app.run()


if __name__ == "__main__":
    main()
