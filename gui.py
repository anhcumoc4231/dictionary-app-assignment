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
BOOKMARKS_PATH = os.path.join(_BASE, "data", "bookmarks.txt")

def _ensure_bookmarks() -> None:
    if not os.path.exists(BOOKMARKS_PATH):
        os.makedirs(os.path.dirname(BOOKMARKS_PATH), exist_ok=True)
        with open(BOOKMARKS_PATH, "w", encoding="utf-8"):
            pass

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
        self._last_entry: Optional[LexicalEntry] = None
        self._entry: Optional[tk.Entry] = None  # type: ignore

        # Navigation State
        self._current_page: Optional[str] = None
        self._pages: dict[str, tk.Frame] = {} # type: ignore

        # Main Layout Container
        self._main_container = tk.Frame(self.root, bg=C["bg"]) # type: ignore
        self._main_container.pack(fill="both", expand=True) # type: ignore

        self._build_menu()
        self.show_page("chat") # type: ignore

        # Init backend in background
        threading.Thread(target=self._init_backend, daemon=True).start()  # type: ignore

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

    def _show_word_of_the_day(self) -> None:
        if not self._autocomplete_words or not self._dict_app: return
        import random
        w = random.choice(self._autocomplete_words)
        self._add_ai_bubble("💡 **Word of the Day** (Từ vựng mỗi ngày):")
        threading.Thread(target=self._process_wotd, args=(w,), daemon=True).start()  # type: ignore

    def _process_wotd(self, word: str) -> None:
        entry = self._dict_app.find_word(word)  # type: ignore
        if entry:
            self.root.after(0, lambda: self._add_result_bubble(entry))  # type: ignore

    # ------------------------------------------------------------------
    # UI Navigation (SPA Style)
    # ------------------------------------------------------------------

    def show_page(self, page_id: str) -> None:
        if self._current_page == page_id:
            return

        # Hide current page
        if self._current_page and self._current_page in self._pages:
            self._pages[self._current_page].pack_forget()  # type: ignore

        # Create page if not exists
        if page_id not in self._pages:
            self._create_page(page_id)

        # Show new page
        # Show new page with a tiny 'fluid' delay
        def _do_show():
            self._pages[page_id].pack(fill="both", expand=True)
            self._current_page = page_id
            self._scroll_to_bottom()
        
        self.root.after(10, _do_show) # type: ignore

    def _create_page(self, page_id: str) -> None:
        frame = tk.Frame(self._main_container, bg=C["bg"]) # type: ignore
        self._pages[page_id] = frame

        if page_id == "chat":
            self._build_chat_page(frame)
        elif page_id == "bookmarks":
            self._build_bookmarks_page(frame)
        elif page_id == "wotd":
            self._build_wotd_page(frame)

    # ------------------------------------------------------------------
    # Menu Bar
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)  # type: ignore
        
        # Menu: Hệ thống
        file_menu = tk.Menu(menubar, tearoff=0)  # type: ignore
        file_menu.add_command(label="🏠 Trang chủ (Chat)", command=lambda: self.show_page("chat"))  # type: ignore
        file_menu.add_separator()  # type: ignore
        file_menu.add_command(label="🗑 Xóa lịch sử chat", command=self._clear_chat)  # type: ignore
        file_menu.add_command(label="❌ Thoát", command=self.root.quit)  # type: ignore
        menubar.add_cascade(label="Hệ thống", menu=file_menu)  # type: ignore

        # Menu: Công cụ
        tools_menu = tk.Menu(menubar, tearoff=0)  # type: ignore
        tools_menu.add_command(label="🌟 Từ vựng mỗi ngày", command=lambda: self.show_page("wotd"))  # type: ignore
        tools_menu.add_separator()  # type: ignore
        tools_menu.add_command(label="📖 Xem Sổ tay (Bookmarks)", command=lambda: self.show_page("bookmarks"))  # type: ignore
        tools_menu.add_command(label="🗑 Xóa sạch Sổ tay", command=self._menu_clear_saved)  # type: ignore
        menubar.add_cascade(label="Công cụ", menu=tools_menu)  # type: ignore

        # Menu: Trợ giúp
        help_menu = tk.Menu(menubar, tearoff=0)  # type: ignore
        help_menu.add_command(label="ℹ️ Thông tin App", command=self._menu_about)  # type: ignore
        menubar.add_cascade(label="Trợ giúp", menu=help_menu)  # type: ignore

        self.root.config(menu=menubar)  # type: ignore

    def _menu_show_saved(self) -> None:
        # This is now handled by show_page("bookmarks")
        self.show_page("bookmarks")

    def _menu_clear_saved(self) -> None:
        if messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa toàn bộ sổ tay vĩnh viễn?"): # type: ignore
            _ensure_bookmarks()
            with open(BOOKMARKS_PATH, "w", encoding="utf-8") as f:
                pass
            self._add_ai_bubble("🗑 Đã xóa sạch sổ tay!")
            if self._current_page == "bookmarks":
                self._build_bookmarks_page(self._pages["bookmarks"]) # Refresh page

    def _menu_about(self) -> None:
        messagebox.showinfo("Thông tin", "🤖 AI Dictionary — Từ Điển Anh-Việt\nVersion 3.0 (Multi-Page SPA)") # type: ignore

    # ------------------------------------------------------------------
    # Page Builders
    # ------------------------------------------------------------------

    def _build_chat_page(self, parent: tk.Frame) -> None: # type: ignore
        self._build_header(parent)
        self._build_chat_area(parent)
        self._build_input_bar(parent)
        self._welcome_message()

    def _build_bookmarks_page(self, parent: tk.Frame) -> None: # type: ignore
        # Clear existing
        for widget in parent.winfo_children(): # type: ignore
            widget.destroy() # type: ignore
            
        header = tk.Frame(parent, bg=C["header_bg"], pady=20) # type: ignore
        header.pack(fill="x") # type: ignore
        tk.Label(header, text="📖 SỔ TAY TỪ VỰNG", font=(FONT_FAMILY, 20, "bold"), bg=C["header_bg"], fg=C["gold"]).pack() # type: ignore
        
        container = tk.Frame(parent, bg=C["chat_bg"], padx=40, pady=20) # type: ignore
        container.pack(fill="both", expand=True) # type: ignore
        
        _ensure_bookmarks()
        with open(BOOKMARKS_PATH, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            
        if not lines:
            tk.Label(container, text="Sổ tay của bạn hiện đang trống.\nBấm nút ⭐ khi tra từ để lưu lại nhé!", # type: ignore
                     font=(FONT_FAMILY, 12), bg=C["chat_bg"], fg=C["text_dim"]).pack(pady=50) # type: ignore
        else:
            # Scrollable list
            canvas = tk.Canvas(container, bg=C["chat_bg"], highlightthickness=0) # type: ignore
            scr = tk.Scrollbar(container, orient="vertical", command=canvas.yview) # type: ignore
            list_frame = tk.Frame(canvas, bg=C["chat_bg"]) # type: ignore
            
            canvas.create_window((0, 0), window=list_frame, anchor="nw") # type: ignore
            canvas.configure(yscrollcommand=scr.set) # type: ignore
            
            canvas.pack(side="left", fill="both", expand=True) # type: ignore
            scr.pack(side="right", fill="y") # type: ignore
            
            def _on_scroll(e): canvas.configure(scrollregion=canvas.bbox("all")) # type: ignore
            list_frame.bind("<Configure>", _on_scroll) # type: ignore
            
            def _add_item(idx, line_text):
                if not parent.winfo_exists(): return
                item = tk.Frame(list_frame, bg=C["bubble_ai"], pady=12, padx=18, 
                                highlightthickness=1, highlightbackground=C["bubble_border"]) # type: ignore
                
                parts = line_text.split(" - ", 1)
                word = parts[0]
                mean = parts[1] if len(parts) > 1 else ""
                
                tk.Label(item, text=word, font=(FONT_FAMILY, 14, "bold"), bg=C["bubble_ai"], fg=C["text_main"]).pack(side="left") # type: ignore
                tk.Label(item, text=f": {mean}", font=(FONT_FAMILY, 11), bg=C["bubble_ai"], fg=C["green"]).pack(side="left", padx=10) # type: ignore
                
                def _del(w=word):
                    if messagebox.askyesno("Xác nhận", f"Xóa '{w}' khỏi sổ tay?"): # type: ignore
                        with open(BOOKMARKS_PATH, "r", encoding="utf-8") as f:
                            rem = [l for l in f if not l.startswith(f"{w} -")]
                        with open(BOOKMARKS_PATH, "w", encoding="utf-8") as f:
                            f.writelines(rem)
                        self._build_bookmarks_page(parent)
                
                btn_del = tk.Button(item, text="🗑", bg=C["bubble_ai"], fg=C["red"], bd=0, command=_del, cursor="hand2") # type: ignore
                btn_del.pack(side="right") # type: ignore
                self._bind_hover(btn_del, C["bubble_ai"], "#FEE2E2")
                
                # Staggered entry from bottom
                item.pack(fill="x", pady=6, padx=5) # type: ignore
                self._current_page = "bookmarks" # Ensure we are here

            # Load sequentially
            for i, line in enumerate(lines):
                self.root.after(i * 100, lambda l=line, idx=i: _add_item(idx, l)) # type: ignore

    def _build_wotd_page(self, parent: tk.Frame) -> None: # type: ignore
        """Word of the Day as a 5-card flip game."""
        import random
        for widget in parent.winfo_children():
            widget.destroy()

        # --- Header ---
        header = tk.Frame(parent, bg=C["header_bg"], pady=16)
        header.pack(fill="x")
        tk.Label(header, text="💡 LUYỆN TẪ VỰNG — LẬT THẾ",
                 font=(FONT_FAMILY, 18, "bold"), bg=C["header_bg"], fg=C["accent"]).pack()
        tk.Label(header, text="Bấm vào thẻ bất kỳ để khám phá từ vựng!",
                 font=(FONT_FAMILY, 10), bg=C["header_bg"], fg=C["text_dim"]).pack()
        tk.Frame(parent, bg=C["bubble_border"], height=1).pack(fill="x")

        # --- Cards Container ---
        body = tk.Frame(parent, bg=C["chat_bg"])
        body.pack(fill="both", expand=True, padx=40, pady=20)

        if not self._autocomplete_words or not self._dict_app:
            tk.Label(body, text="⏳ Đang tải dữ liệu...",
                     bg=C["chat_bg"], fg=C["text_dim"], font=(FONT_FAMILY, 13)).pack(pady=60)
            return

        words = random.sample(self._autocomplete_words, min(5, len(self._autocomplete_words)))

        CARD_COLORS = ["#6D28D9", "#DB2777", "#059669", "#D97706", "#2563EB"]
        CARD_HOVER  = ["#7C3AED", "#EC4899", "#10B981", "#F59E0B", "#3B82F6"]

        def _make_card(idx: int, word: str) -> None:
            color    = CARD_COLORS[idx % len(CARD_COLORS)]
            hover_c  = CARD_HOVER[idx  % len(CARD_HOVER)]

            card = tk.Frame(body, bg=color, padx=30, pady=28,
                            highlightthickness=2, highlightbackground=hover_c,
                            cursor="hand2")
            card.pack(fill="x", pady=8, padx=10)
            # Placeholder: ? 
            q_lbl = tk.Label(card, text="?", font=(FONT_FAMILY, 36, "bold"),
                             bg=color, fg="white")
            q_lbl.pack()
            hint = tk.Label(card, text="▸ Bấm để lật", font=(FONT_FAMILY, 9),
                            bg=color, fg="rgba(255,255,255,0.6)")
            hint.config(fg="#FBBF24")
            hint.pack()

            flipped = [False]

            def _flip(e=None, c=card, w=word, clr=color, h=hover_c,
                      ql=q_lbl, hl=hint, f=flipped):
                if f[0]: return
                f[0] = True
                # Clear
                for wg in c.winfo_children():
                    wg.destroy()
                # Reveal word
                wl = tk.Label(c, text=w.upper(), font=(FONT_FAMILY, 28, "bold"),
                              bg=clr, fg="white")
                wl.pack()
                # Get meaning in background
                def _fetch():
                    entry = self._dict_app.find_word(w) # type: ignore
                    def _show():
                        if not c.winfo_exists(): return
                        meaning = ""
                        if entry:
                            meaning = getattr(entry, "short_translation", "")
                            if not meaning and entry.senses:
                                for s in entry.senses:
                                    if s.translation:
                                        meaning = s.translation; break
                        ml = tk.Label(c, text=meaning or "(đang tải...)",
                                      font=(FONT_FAMILY, 16), bg=clr, fg=C["green"],
                                      wraplength=700, justify="left")
                        ml.pack(pady=(6, 0))
                        # Pop-in: scale simulation via font change
                        def _pop(step: int = 0) -> None:
                            if not ml.winfo_exists() or step >= 3: return
                            sizes = [10, 13, 16]
                            ml.config(font=(FONT_FAMILY, sizes[step]))
                            self.root.after(60, _pop, step + 1) # type: ignore
                        ml.config(font=(FONT_FAMILY, 10))
                        self.root.after(20, _pop)
                    self.root.after(0, _show)
                import threading
                threading.Thread(target=_fetch, daemon=True).start()
                # Glow border flash
                def _flash(step=0, on=True):
                    if not c.winfo_exists(): return
                    c.config(highlightbackground="white" if on else h)
                    if step < 5:
                        self.root.after(80, _flash, step+1, not on)
                _flash()

            card.bind("<Button-1>", _flip)
            for ch in card.winfo_children():
                ch.bind("<Button-1>", _flip)
            self._bind_hover(card, color, hover_c)

        # Slide each card in with stagger
        for i, w in enumerate(words):
            self.root.after(i * 120, lambda idx=i, wd=w: _make_card(idx, wd))

        # --- Bottom buttons ---
        btn_row = tk.Frame(parent, bg=C["chat_bg"])
        btn_row.pack(side="bottom", fill="x", padx=40, pady=12)

        btn_shuffle = tk.Button(btn_row, text="🃏 Xáo bài mới",
                                font=(FONT_FAMILY, 11, "bold"),
                                bg=C["accent"], fg="white", bd=0,
                                padx=20, pady=8, cursor="hand2",
                                command=lambda: self._build_wotd_page(parent))
        btn_shuffle.pack(side="left")
        self._bind_hover(btn_shuffle, C["accent"], C["accent2"])

        btn_back = tk.Button(btn_row, text="← Quay lại tra từ",
                             font=(FONT_FAMILY, 10), bg=C["chat_bg"], fg=C["text_dim"],
                             bd=0, cursor="hand2",
                             command=lambda: self.show_page("chat"))
        btn_back.pack(side="right")
        self._bind_hover(btn_back, C["chat_bg"], C["bubble_border"])


    # ------------------------------------------------------------------
    # Widget builders
    # ------------------------------------------------------------------

    def _build_header(self, parent: tk.Frame) -> None: # type: ignore
        header = tk.Frame(parent, bg=C["header_bg"], pady=10) # type: ignore
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

    def _build_chat_area(self, parent: tk.Frame) -> None: # type: ignore
        """Chat area: Canvas + Scrollbar để render bubble messages."""
        container = tk.Frame(parent, bg=C["chat_bg"]) # type: ignore
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

    def _build_input_bar(self, parent: tk.Frame) -> None: # type: ignore
        """Bottom input bar with autocomplete."""
        bar = tk.Frame(parent, bg=C["input_bg"], pady=10) # type: ignore
        bar.pack(fill="x", side="bottom")  # type: ignore

        # Separator
        tk.Frame(parent, bg=C["input_border"], height=1).pack(fill="x", side="bottom") # type: ignore

        # Autocomplete Listbox (floats above input)
        self._listbox_frame = tk.Frame(parent, bg=C["bubble_border"], bd=1, relief="solid") # type: ignore
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
        btn = tk.Button( # type: ignore
            inner, text="Tra  ➤",
            font=(FONT_FAMILY, 12, "bold"),
            bg=C["accent"], fg="white",
            activebackground=C["accent2"], activeforeground="white",
            bd=0, relief="flat", padx=20, pady=10, cursor="hand2",
            command=self._on_search
        )
        btn.pack(side="left", padx=(10, 0))  # type: ignore
        self._bind_hover(btn, C["accent"], C["accent2"])

        # Input glow pulse on focus
        entry_widget = self._entry  # local ref to satisfy typechecker
        if entry_widget is not None:
            def _on_focus_in(e): self._start_glow(entry_frame)
            def _on_focus_out(e): self._stop_glow(entry_frame)
            entry_widget.bind("<FocusIn>", _on_focus_in)  # type: ignore
            entry_widget.bind("<FocusOut>", _on_focus_out)  # type: ignore

    # ------------------------------------------------------------------
    # Visual Polish Helpers (Animations/Transitions)
    # ------------------------------------------------------------------

    def _animate_typing(self, label: tk.Label, text: str, index: int = 0, on_complete: Optional[Callable[[], None]] = None) -> None: # type: ignore
        if not label.winfo_exists(): return 
        
        step_size = 3 if len(text) > 50 else 2
        
        # Display index ensures we don't skip the last part
        d_idx = min(index, len(text))
        label.config(text=text[:d_idx]) # type: ignore
        self._scroll_to_bottom()
        
        if index < len(text):
            self.root.after(1, self._animate_typing, label, text, index + step_size, on_complete) # type: ignore
        else:
            # Final safety check to make sure full text is shown
            label.config(text=text) # type: ignore
            if on_complete:
                self.root.after(5, on_complete) # type: ignore

    def _bind_hover(self, widget: tk.Widget, normal_bg: str, hover_bg: str) -> None: # type: ignore
        widget.bind("<Enter>", lambda e: widget.config(bg=hover_bg)) # type: ignore
        widget.bind("<Leave>", lambda e: widget.config(bg=normal_bg)) # type: ignore

    # Input Glow Pulse
    _glow_job: Optional[str] = None
    _glow_on: bool = False

    def _start_glow(self, frame: tk.Frame) -> None: # type: ignore
        self._glow_on = True
        self._do_glow(frame)

    def _stop_glow(self, frame: tk.Frame) -> None: # type: ignore
        self._glow_on = False
        if self._glow_job:
            try:
                self.root.after_cancel(self._glow_job) # type: ignore
            except Exception:
                pass
        if frame.winfo_exists(): # type: ignore
            frame.config(bg=C["input_border"]) # type: ignore

    def _do_glow(self, frame: tk.Frame, step: int = 0) -> None: # type: ignore
        if not self._glow_on or not frame.winfo_exists(): return # type: ignore
        # Pulse between violet shades
        colors = ["#4C1D95", "#7C3AED", "#8B5CF6", "#7C3AED", "#4C1D95"]
        frame.config(bg=colors[step % len(colors)]) # type: ignore
        self._glow_job = self.root.after(120, self._do_glow, frame, step + 1) # type: ignore

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

        bubble = tk.Frame(row, bg=C["bubble_user"], padx=16, pady=10,
                         highlightthickness=1, highlightbackground="#6D28D9") # type: ignore
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

        bubble = tk.Frame(row, bg=C["bubble_ai"], padx=16, pady=10, 
                         highlightthickness=1, highlightbackground=C["bubble_border"]) # type: ignore
        bubble.pack(side="left", fill="x", expand=True)  # type: ignore

        lbl = tk.Label( # type: ignore
            bubble, text="",
            font=(FONT_FAMILY, 11),
            bg=C["bubble_ai"], fg=C["text_dim"],
            wraplength=680, justify="left"
        )
        lbl.pack(anchor="w")  # type: ignore
        
        # Start animation
        clean_text = markdown_text.replace("**", "").replace("\\n", "\n")
        self._animate_typing(lbl, clean_text)

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
        import re
        ipa = entry.uk_ipa or entry.us_ipa
        title_text = entry.word.lower()
        if ipa:
            clean_ipa = re.sub(r'[/\[\]\s]', '', ipa)
            title_text += f" /{clean_ipa}/"

        source = getattr(entry, "source", "") # Define early 
        
        # 1. Title
        title_lbl = tk.Label(  # type: ignore
            bubble, text="",
            font=(FONT_FAMILY, 24, "bold"), # Slightly larger
            bg=C["bubble_ai"], fg=C["text_main"]
        )
        title_lbl.pack(anchor="w", pady=(0, 2))  # type: ignore

        # 2. Source Tag (Sequential)
        source_lbl = tk.Label(bubble, text="", font=(FONT_FAMILY, 9), bg=C["bubble_ai"], fg=C["text_dim"]) # type: ignore

        # 3. Short Translation (Green, Big)
        short = getattr(entry, "short_translation", "")
        if not short and entry.senses:
            # Fallback for old cache entries that were saved without short_translation
            for s in entry.senses:
                if s.translation:
                    short = s.translation
                    break
        
        short_lbl = tk.Label(bubble, text="", font=(FONT_FAMILY, 18, "bold"), bg=C["bubble_ai"], fg=C["green"], wraplength=640, justify="left") # type: ignore

        # --- ANIMATION CHAIN ---
        def stage_4(): # Final: Senses
            if not bubble.winfo_exists(): return
            tk.Frame(bubble, bg="#4A4A8A", height=1).pack(fill="x", pady=12) # Lighter divider
            self._animate_senses_sequentially(bubble, entry, entry.senses)

        def stage_3(): # Green Translation
            if not bubble.winfo_exists(): return
            if short:
                short_lbl.pack(anchor="w", pady=(10, 5)) # type: ignore
                self._animate_typing(short_lbl, short, on_complete=stage_4)
            else:
                stage_4()

        def stage_2(): # Source Tag
            if not bubble.winfo_exists(): return
            if source:
                source_lbl.pack(anchor="w", pady=(0, 6)) # type: ignore
                algo = "🌍 Google Translate" if source == "Google Translate" else ("⚡ RAM O(1)" if "Cache" in source else ("📀 Disk O(log n)" if source == "Local Cache" else "🌐 Free API"))
                self._animate_typing(source_lbl, algo, on_complete=stage_3)
            else:
                stage_3()

        # Start Chain
        self._animate_typing(title_lbl, title_text, on_complete=stage_2)

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
                      "Tôi sẽ tra cứu từ Local Cache O(log n) trước — nếu chưa có sẽ gọi Free Dictionary API và dịch nghĩa Tiếng Việt ngay lập tức!\n\n"
                      "**Tính năng mới**: Sổ tay từ vựng và Word of the Day hiện đã có trong menu **Công cụ** bên trên!",
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

        threading.Thread(target=_do_search, daemon=True).start()  # type: ignore

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
            threading.Thread(target=_fallback, daemon=True).start()  # type: ignore

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

    def _hide_listbox(self) -> None:
        if self._listbox_frame.winfo_exists(): # type: ignore
            self._listbox_frame.place_forget()  # type: ignore

    def _animate_senses_sequentially(self, parent_bubble: tk.Frame, entry: LexicalEntry, senses: list, index: int = 0) -> None: # type: ignore
        if index >= len(senses) or not parent_bubble.winfo_exists():
             self._add_save_button_after_animation(parent_bubble, entry)
             self._scroll_to_bottom()
             return

        sense = senses[index]
        pos_vi = {
            "noun": "danh từ", "verb": "động từ", "adjective": "tính từ",
            "adverb": "trạng từ", "pronoun": "đại từ", "preposition": "giới từ",
            "conjunction": "liên từ", "interjection": "thán từ", "idiom": "thành ngữ"
        }
        
        pos_key = (sense.pos or "").lower()
        vi_pos = pos_vi.get(pos_key, pos_key)
        if vi_pos:
            tk.Label(parent_bubble, text=f"* {vi_pos}", font=(FONT_FAMILY, 11, "bold"), 
                     bg=C["bubble_ai"], fg="#5C9BD1").pack(anchor="w", pady=(8, 2)) # type: ignore

        def_lbl = tk.Label(parent_bubble, text="", font=(FONT_FAMILY, 11), 
                           bg=C["bubble_ai"], fg=C["text_main"], wraplength=640, justify="left") # type: ignore
        def_lbl.pack(anchor="w", padx=(10, 0)) # type: ignore

        def on_def_done():
            # 3. Animate Translation
            def on_tr_done():
                # 4. Animate Examples
                if sense.examples:
                    self._animate_examples_sequentially(parent_bubble, entry, senses, index, sense.examples, 0)
                else:
                    self._animate_senses_sequentially(parent_bubble, entry, senses, index + 1)

            if sense.translation:
                tr_lbl = tk.Label(parent_bubble, text="", font=(FONT_FAMILY, 10, "italic"), 
                                  bg=C["bubble_ai"], fg="#A8B5C8", wraplength=640, justify="left") # type: ignore
                tr_lbl.pack(anchor="w", padx=(25, 0)) # type: ignore
                # Strip and ensure single parenthesis
                clean_tr = sense.translation.strip("() ")
                self._animate_typing(tr_lbl, f"({clean_tr})", on_complete=on_tr_done)
            else:
                on_tr_done()

        self._animate_typing(def_lbl, f"+ {sense.definition}", on_complete=on_def_done)


    def _animate_examples_sequentially(self, parent_bubble: tk.Frame, entry: LexicalEntry, senses: list, s_idx: int, examples: list, e_idx: int) -> None: # type: ignore
        if e_idx >= len(examples) or not parent_bubble.winfo_exists():
            # Done with this sense, move to next sense
            self._animate_senses_sequentially(parent_bubble, entry, senses, s_idx + 1)
            return
        
        ex = examples[e_idx]
        en_ex = ex.get("en", "")
        vi_ex = ex.get("vi", "")
        if not en_ex:
            self._animate_examples_sequentially(parent_bubble, entry, senses, s_idx, examples, e_idx + 1)
            return

        en_lbl = tk.Label(parent_bubble, text="", font=(FONT_FAMILY, 10, "italic"), 
                          bg=C["bubble_ai"], fg=C["text_example"], wraplength=620, justify="left") # type: ignore
        en_lbl.pack(anchor="w", padx=(10, 0)) # type: ignore
        
        def on_en_done():
            if vi_ex:
                vi_lbl = tk.Label(parent_bubble, text="", font=(FONT_FAMILY, 9, "italic"), 
                                  bg=C["bubble_ai"], fg="#8A9EB1", wraplength=620, justify="left") # type: ignore
                vi_lbl.pack(anchor="w", padx=(30, 0)) # type: ignore
                clean_vi = vi_ex.strip("() ")
                self._animate_typing(vi_lbl, f"({clean_vi})", on_complete=lambda: self._animate_examples_sequentially(parent_bubble, entry, senses, s_idx, examples, e_idx + 1))
            else:
                self._animate_examples_sequentially(parent_bubble, entry, senses, s_idx, examples, e_idx + 1)

        self._animate_typing(en_lbl, f"+ {en_ex}", on_complete=on_en_done)


        
    def _add_save_button_after_animation(self, bubble: tk.Frame, entry: LexicalEntry) -> None: # type: ignore
        if not bubble.winfo_exists(): return
        source = getattr(entry, "source", "")
        if source == "Google Translate": return 
        
        btn = tk.Button( # type: ignore
            bubble, text="⭐ Lưu vào Sổ tay", font=(FONT_FAMILY, 9, "bold"),
            bg="#2A2A4A", fg=C["gold"], bd=0, padx=12, pady=6, cursor="hand2"
        )
        btn.pack(anchor="w", pady=(15, 5)) # type: ignore
        self._bind_hover(btn, "#2A2A4A", "#3A3A5A")
        
        def _save():
            _ensure_bookmarks()
            line = f"{entry.word} - {getattr(entry, 'short_translation', '')}\n"
            with open(BOOKMARKS_PATH, "a", encoding="utf-8") as f:
                f.write(line)
            btn.config(text="✅ Đã lưu", fg=C["green"]) # type: ignore
            
        btn.config(command=_save) # type: ignore



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
