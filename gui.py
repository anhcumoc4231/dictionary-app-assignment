# pyre-ignore-all-errors
"""  # type: ignore
gui.py — AI Dictionary v3.2 (Gemini-Style UI + VS Code Left Sidebar)  # type: ignore
=====================================================================  # type: ignore
Entry point chính. Chạy: python gui.py  # type: ignore
"""  # type: ignore

import os
import sys
import threading
import webbrowser
import urllib.request
import tkinter as tk
from tkinter import messagebox  # type: ignore
from typing import Optional, List, Callable

sys.path.insert(0, os.path.dirname(__file__))  # type: ignore
from app import DictionaryApp      # type: ignore  # noqa: E402
from models import LexicalEntry    # type: ignore  # noqa: E402

if getattr(sys, "frozen", False):  # type: ignore
    _BASE = os.path.dirname(sys.executable)  # type: ignore
else:  # type: ignore
    _BASE = os.path.dirname(os.path.abspath(__file__))  # type: ignore

DATA_PATH       = os.path.join(_BASE, "data", "meaning.data")  # type: ignore
INDEX_PATH      = os.path.join(_BASE, "data", "index.data")  # type: ignore
WORDS_LIST_PATH = os.path.join(_BASE, "data", "words_list.txt")  # type: ignore
BOOKMARKS_PATH  = os.path.join(_BASE, "data", "bookmarks.txt")  # type: ignore
HISTORY_PATH    = os.path.join(_BASE, "data", "history.txt")  # type: ignore

def _ensure_file(path: str) -> None:
    if not os.path.exists(path):  # type: ignore
        os.makedirs(os.path.dirname(path), exist_ok=True)  # type: ignore
        open(path, "w", encoding="utf-8").close()  # type: ignore

# ── Colour Palette ─────────────────────────────────────────────────────────────
C: dict = {  # type: ignore
    "bg":          "#111827",  # type: ignore   # dark slate (readable)
    "sidebar":     "#0F172A",  # type: ignore   # navy sidebar
    "sidebar_h":   "#1E293B",  # type: ignore   # hover
    "sidebar_act": "#1E3A5F",  # type: ignore   # active (medium blue)
    "chat_bg":     "#111827",  # type: ignore
    "bubble_ai":   "#1E293B",  # type: ignore   # slightly lighter card
    "bubble_user": "#4C1D95",  # type: ignore   # vivid purple user
    "accent":      "#818CF8",  # type: ignore   # indigo-400 for readability
    "accent2":     "#EC4899",  # type: ignore
    "gold":        "#FBBF24",  # type: ignore
    "green":       "#34D399",  # type: ignore   # brighter mint
    "red":         "#F87171",  # type: ignore
    "text_main":   "#F1F5F9",  # type: ignore   # white-ish
    "text_dim":    "#94A3B8",  # type: ignore   # slate-400 — much easier to read
    "text_sub":    "#CBD5E1",  # type: ignore   # slate-300
    "input_bg":    "#1E293B",  # type: ignore
    "input_bdr":   "#4338CA",  # type: ignore   # bright indigo border
    "border":      "#334155",  # type: ignore   # slate-700
}  # type: ignore

FONT         = "Segoe UI"  # type: ignore
SIDEBAR_COL  = 64    # collapsed width px  # type: ignore
SIDEBAR_EXP  = 210   # expanded  width px  # type: ignore

# ── Word-list loader ───────────────────────────────────────────────────────────
def _load_words_list() -> List[str]:
    _ensure_file(WORDS_LIST_PATH)  # type: ignore
    url = ("https://raw.githubusercontent.com/first20hours/google-10000-english"  # type: ignore
           "/master/google-10000-english-no-swears.txt")  # type: ignore
    if os.path.getsize(WORDS_LIST_PATH) == 0:  # type: ignore
        try:  # type: ignore
            urllib.request.urlretrieve(url, WORDS_LIST_PATH)  # type: ignore
        except Exception as e:  # type: ignore
            print(f"words_list download error: {e}")  # type: ignore
    try:  # type: ignore
        with open(WORDS_LIST_PATH, "r", encoding="utf-8") as f:  # type: ignore
            return sorted(line.strip() for line in f if line.strip())
    except Exception:  # type: ignore
        return []  # type: ignore

# ── Main UI ────────────────────────────────────────────────────────────────────
class DictionaryUI:

    # Nav items: (page_id, icon, label)
    _NAV = [  # type: ignore
        ("chat",      "🔍", "Tra từ"),  # type: ignore
        ("bookmarks", "📖", "Sổ tay"),  # type: ignore
        ("wotd",      "💡", "Luyện từ"),  # type: ignore
        ("history",   "📜", "Lịch sử"),  # type: ignore
        ("settings",  "⚙️", "Cài đặt"),  # type: ignore
    ]  # type: ignore

    def __init__(self) -> None:
        self.root = tk.Tk()  # type: ignore
        self.root.title("AI Dictionary — Từ Điển Anh-Việt")  # type: ignore
        self.root.configure(bg=C["bg"])  # type: ignore
        self.root.geometry("1020x720")  # type: ignore
        self.root.minsize(760, 520)  # type: ignore

        # ── state ──
        self._current_page:  str = "chat"
        self._scrollers:    dict = {} # Canvas per page  # type: ignore
        self._search_mode:   str = "en_vi"
        self._dict_app:    Optional[DictionaryApp] = None  # type: ignore
        self._words:       List[str] = []  # type: ignore
        self._search_var = tk.StringVar()  # type: ignore
        self._last_entry:  Optional[LexicalEntry] = None  # type: ignore
        self._entry:       Optional[tk.Entry] = None  # type: ignore
        self._history:     List[str] = []  # type: ignore
        self._sidebar_expanded = False  # type: ignore
        self._glow_job:    Optional[str] = None  # type: ignore
        self._glow_on      = False  # type: ignore
        self._pages:       dict = {}  # type: ignore
        self._nav_btns:    dict = {}  # type: ignore
        self._sidebar_w:   int  = SIDEBAR_COL  # type: ignore  # tracks actual current width

        # ── chat canvas references (created by _build_chat_page) ──
        self._canvas:      Optional[tk.Canvas] = None  # type: ignore
        self._chat_frame:  Optional[tk.Frame]  = None  # type: ignore
        self._chat_window: Optional[int]       = None  # type: ignore
        self._listbox_frame: Optional[tk.Frame] = None  # type: ignore
        self._listbox:     Optional[tk.Listbox] = None  # type: ignore

        # ── strict layout type refs ──
        self._sidebar_frame: tk.Frame = None  # type: ignore
        self._main_frame: tk.Frame = None  # type: ignore
        self._toggle_lbl: tk.Label = None  # type: ignore
        self._app_lbl: tk.Label = None  # type: ignore

        self._build_layout()  # type: ignore
        self.root.after(50,  lambda: self._show_page("chat"))  # type: ignore
        threading.Thread(target=self._init_backend, daemon=True).start()  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Layout
    # ══════════════════════════════════════════════════════════════════════════

    def _build_layout(self) -> None:
        # Left sidebar
        self._sidebar_frame = tk.Frame(self.root, bg=C["sidebar"], width=SIDEBAR_COL)  # type: ignore
        self._sidebar_frame.pack(side="left", fill="y")  # type: ignore
        self._sidebar_frame.pack_propagate(False)  # type: ignore

        # Thin accent separator
        tk.Frame(self.root, bg=C["accent"], width=2).pack(side="left", fill="y")  # type: ignore

        # Right main area
        self._main_frame = tk.Frame(self.root, bg=C["bg"])  # type: ignore
        self._main_frame.pack(side="left", fill="both", expand=True)  # type: ignore

        self._build_sidebar()  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Sidebar
    # ══════════════════════════════════════════════════════════════════════════

    def _build_sidebar(self) -> None:
        sb = self._sidebar_frame  # type: ignore

        # Toggle (hamburger / ✕)
        self._toggle_lbl = tk.Label(  # type: ignore
            sb, text="☰", font=(FONT, 17),  # type: ignore
            bg=C["sidebar"], fg=C["text_dim"],  # type: ignore
            cursor="hand2", pady=14, padx=0,  # type: ignore
        )  # type: ignore
        self._toggle_lbl.pack(fill="x")  # type: ignore
        self._toggle_lbl.bind("<Button-1>", lambda e: self._toggle_sidebar())  # type: ignore
        self._bind_hover(self._toggle_lbl, C["sidebar"], C["sidebar_h"])  # type: ignore
        self._bind_click_flash(self._toggle_lbl, C["sidebar"])  # type: ignore

        tk.Frame(sb, bg=C["border"], height=1).pack(fill="x", pady=(0, 4))  # type: ignore

        for pid, icon, label in self._NAV:  # type: ignore
            self._nav_btns[pid] = self._make_nav_btn(sb, pid, icon, label)  # type: ignore

        # App label at bottom (shown when expanded)
        self._app_lbl = tk.Label(  # type: ignore
            sb, text="", font=(FONT, 8),  # type: ignore
            bg=C["sidebar"], fg=C["text_dim"], wraplength=SIDEBAR_EXP - 10,  # type: ignore
        )  # type: ignore
        self._app_lbl.pack(side="bottom", pady=10)  # type: ignore

    def _make_nav_btn(self, parent: tk.Frame, pid: str, icon: str, label: str) -> tk.Frame:  # type: ignore
        frame = tk.Frame(parent, bg=C["sidebar"], cursor="hand2")  # type: ignore
        frame.pack(fill="x", pady=1)  # type: ignore

        # Left active-indicator strip
        indicator = tk.Frame(frame, bg=C["sidebar"], width=3)  # type: ignore
        indicator.pack(side="left", fill="y")  # type: ignore

        icon_lbl = tk.Label(  # type: ignore
            frame, text=icon, font=(FONT, 17),  # type: ignore
            bg=C["sidebar"], fg=C["text_dim"],  # type: ignore
            width=3, pady=12,  # type: ignore
        )  # type: ignore
        icon_lbl.pack(side="left")  # type: ignore

        text_lbl = tk.Label(  # type: ignore
            frame, text=label, font=(FONT, 11),  # type: ignore
            bg=C["sidebar"], fg=C["text_dim"], anchor="w",  # type: ignore
        )  # type: ignore
        # Text hidden while collapsed; shown by _toggle_sidebar
        text_lbl.pack_forget()  # type: ignore

        # Store refs on the frame object for later access
        frame.__dict__.update(  # type: ignore
            _pid=pid, _indicator=indicator,  # type: ignore
            _icon_lbl=icon_lbl, _text_lbl=text_lbl,  # type: ignore
        )  # type: ignore

        def _enter(e: object) -> None:
            if self._current_page != pid:  # type: ignore
                for w in (frame, icon_lbl, text_lbl):  # type: ignore
                    w.config(bg=C["sidebar_h"])  # type: ignore

        def _leave(e: object) -> None:
            if self._current_page != pid:  # type: ignore
                for w in (frame, icon_lbl, text_lbl):  # type: ignore
                    w.config(bg=C["sidebar"])  # type: ignore

        def _click(e: object) -> None:
            self._nav_click_anim(pid, frame)  # type: ignore

        for widget in (frame, icon_lbl, text_lbl):  # type: ignore
            widget.bind("<Enter>",    _enter)  # type: ignore
            widget.bind("<Leave>",    _leave)  # type: ignore
            widget.bind("<Button-1>", _click)  # type: ignore

        return frame

    def _nav_click_anim(self, pid: str, frame: tk.Frame) -> None:  # type: ignore
        """Press-darken → navigate → highlight active."""  # type: ignore
        for wg in (frame, frame.__dict__["_icon_lbl"], frame.__dict__["_text_lbl"]):  # type: ignore
            try:  # type: ignore
                wg.config(bg="#0A0A14")  # type: ignore
            except Exception:  # type: ignore
                pass

        def _go() -> None:
            self._show_page(pid)  # type: ignore

        self.root.after(80, _go) # type: ignore

    def _set_nav_active(self, pid: str) -> None:
        for nav_id, btn in self._nav_btns.items():  # type: ignore
            if not btn.winfo_exists():  # type: ignore
                continue
            d = btn.__dict__  # type: ignore
            active = nav_id == pid  # type: ignore
            c_bg   = C["sidebar_act"] if active else C["sidebar"]  # type: ignore
            c_icon = C["accent"]      if active else C["text_dim"]  # type: ignore
            c_text = C["text_main"]   if active else C["text_dim"]  # type: ignore
            c_ind  = C["accent"]      if active else C["sidebar"]  # type: ignore
            btn.config(bg=c_bg)  # type: ignore
            d["_icon_lbl"].config(bg=c_bg, fg=c_icon)  # type: ignore
            d["_text_lbl"].config(bg=c_bg, fg=c_text)  # type: ignore
            d["_indicator"].config(bg=c_ind)  # type: ignore
        self._current_page = pid  # type: ignore

    def _toggle_sidebar(self) -> None:
        self._sidebar_expanded = not self._sidebar_expanded  # type: ignore
        target = SIDEBAR_EXP if self._sidebar_expanded else SIDEBAR_COL  # type: ignore
        self._toggle_lbl.config(text="✕" if self._sidebar_expanded else "☰")  # type: ignore
        self._app_lbl.config(text="AI Dictionary" if self._sidebar_expanded else "")  # type: ignore
        for btn in self._nav_btns.values():  # type: ignore
            tl = btn.__dict__["_text_lbl"]  # type: ignore
            if self._sidebar_expanded:  # type: ignore
                tl.pack(side="left", padx=6)  # type: ignore
            else:  # type: ignore
                tl.pack_forget()  # type: ignore
        self._anim_sidebar(target)  # type: ignore

    def _anim_sidebar(self, target: int) -> None:
        cur  = self._sidebar_w  # type: ignore
        diff = target - cur  # type: ignore
        if abs(diff) <= 4:  # type: ignore
            self._sidebar_w = target  # type: ignore
            self._sidebar_frame.config(width=target)  # type: ignore
            return
        step = 10 if abs(diff) > 20 else 4  # type: ignore
        self._sidebar_w = cur + (step if diff > 0 else -step)  # type: ignore
        self._sidebar_frame.config(width=self._sidebar_w)  # type: ignore
        self.root.after(8, self._anim_sidebar, target)  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Page routing
    # ══════════════════════════════════════════════════════════════════════════

    _LIVE_PAGES = {"bookmarks", "wotd", "history"}  # rebuilt every visit  # type: ignore

    _PAGE_BUILDERS: dict = {}  # filled after class definition  # type: ignore

    def _show_page(self, pid: str) -> None:
        # Hide all
        for p in self._pages.values():  # type: ignore
            if p.winfo_exists():  # type: ignore
                p.pack_forget()  # type: ignore

        builders: dict = { # type: ignore
            "chat":      self._build_chat_page,  # type: ignore
            "bookmarks": self._build_bookmarks_page,  # type: ignore
            "wotd":      self._build_wotd_page,  # type: ignore
            "history":   self._build_history_page,  # type: ignore
            "settings":  self._build_settings_page,  # type: ignore
        }  # type: ignore

        try:  # type: ignore
            if pid in self._LIVE_PAGES and pid in self._pages:  # type: ignore
                # Rebuild live page in place
                for w in self._pages[pid].winfo_children():  # type: ignore
                    w.destroy()  # type: ignore
                builders[pid](self._pages[pid])  # type: ignore
            elif pid not in self._pages:  # type: ignore
                frame = tk.Frame(self._main_frame, bg=C["bg"])  # type: ignore
                self._pages[pid] = frame  # type: ignore
                builders[pid](frame)  # type: ignore

            self._pages[pid].pack(fill="both", expand=True)  # type: ignore
            self._set_nav_active(pid)  # type: ignore
        except Exception as e:  # type: ignore
            print(f"Page builder error [{pid}]: {e}")  # type: ignore
            # Even if builder fails, ensure current page is packed (might be empty but not black)
            if pid in self._pages:  # type: ignore
                 self._pages[pid].pack(fill="both", expand=True)  # type: ignore
                 tk.Label(self._pages[pid], text=f"Lỗi khi nạp trang {pid}.\nVui lòng thử lại hoặc khởi động lại ứng dụng.", # type: ignore
                          bg=C["bg"], fg=C["red"], pady=40).pack() # type: ignore
            self._set_nav_active(pid)  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Page: Chat
    # ══════════════════════════════════════════════════════════════════════════

    def _build_chat_page(self, parent: tk.Frame) -> None:  # type: ignore
        # 1. Header with Mode Switcher
        header = tk.Frame(parent, bg=C["bg"], pady=15)  # type: ignore
        header.pack(fill="x", padx=40)  # type: ignore
        
        mode_box = tk.Frame(header, bg=C["sidebar"], padx=2, pady=2)  # type: ignore
        mode_box.pack(anchor="w")  # type: ignore

        self._btn_en_vi = tk.Label(mode_box, text="🇬🇧 Anh - Việt", font=(FONT, 9, "bold"),  # type: ignore
                                   bg=C["sidebar_act"], fg=C["accent"], padx=15, pady=6, cursor="hand2")  # type: ignore
        self._btn_en_vi.pack(side="left")  # type: ignore

        self._btn_vi_en = tk.Label(mode_box, text="🇻🇳 Việt - Anh", font=(FONT, 9),  # type: ignore
                                   bg=C["sidebar"], fg=C["text_dim"], padx=15, pady=6, cursor="hand2")  # type: ignore
        self._btn_vi_en.pack(side="left")  # type: ignore

        def switch_mode(m: str) -> None:
            self._search_mode = m  # type: ignore
            active_bg, active_fg = C["sidebar_act"], C["accent"]  # type: ignore
            idle_bg, idle_fg = C["sidebar"], C["text_dim"]  # type: ignore
            
            if m == "en_vi":  # type: ignore
                self._btn_en_vi.config(bg=active_bg, fg=active_fg, font=(FONT, 9, "bold"))  # type: ignore
                self._btn_vi_en.config(bg=idle_bg,   fg=idle_fg,   font=(FONT, 9))  # type: ignore
                self._search_var.set("")  # type: ignore
            else:  # type: ignore
                self._btn_en_vi.config(bg=idle_bg,   fg=idle_fg,   font=(FONT, 9))  # type: ignore
                self._btn_vi_en.config(bg=active_bg, fg=active_fg, font=(FONT, 9, "bold"))  # type: ignore
                self._search_var.set("")  # type: ignore

        self._btn_en_vi.bind("<Button-1>", lambda e: switch_mode("en_vi"))  # type: ignore
        self._btn_vi_en.bind("<Button-1>", lambda e: switch_mode("vi_en"))  # type: ignore

        # 2. Canvas & Scrollbar (minimal, no heavy header)
        topbar = tk.Frame(parent, bg=C["bg"], pady=8)  # type: ignore
        topbar.pack(fill="x", padx=18)  # type: ignore

        tk.Label(  # type: ignore
            topbar, text="🤖  AI Từ Điển Anh-Việt",  # type: ignore
            font=(FONT, 14, "bold"), bg=C["bg"], fg=C["text_main"],  # type: ignore
        ).pack(side="left")  # type: ignore

        # Mini audio + clear buttons
        for txt, cb in [("🗑", self._clear_chat), ("🇺🇸", lambda: self._on_speak("us")), ("🇬🇧", lambda: self._on_speak("uk"))]:  # type: ignore
            b = tk.Label(topbar, text=txt, font=(FONT, 13), bg=C["bg"],  # type: ignore
                         fg=C["text_dim"], cursor="hand2", padx=8)  # type: ignore
            b.pack(side="right")  # type: ignore
            b.bind("<Button-1>", lambda e, fn=cb: fn())  # type: ignore
            self._bind_hover(b, C["bg"], C["sidebar_h"])  # type: ignore
            self._bind_click_flash(b, C["bg"])  # type: ignore

        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")  # type: ignore

        # ── Chat canvas ──────────────────────────────────────────────────────
        container = tk.Frame(parent, bg=C["chat_bg"])  # type: ignore
        container.pack(fill="both", expand=True)  # type: ignore

        scrollbar = tk.Scrollbar(  # type: ignore
            container, orient="vertical",  # type: ignore
            bg=C["bg"], troughcolor=C["chat_bg"],  # type: ignore
            activebackground=C["accent"], width=8,  # type: ignore
        )  # type: ignore
        scrollbar.pack(side="right", fill="y")  # type: ignore

        self._canvas = tk.Canvas(  # type: ignore
            container, bg=C["chat_bg"], bd=0,  # type: ignore
            highlightthickness=0, yscrollcommand=scrollbar.set,  # type: ignore
        )  # type: ignore
        self._canvas.pack(side="left", fill="both", expand=True)  # type: ignore
        scrollbar.config(command=self._canvas.yview)  # type: ignore

        self._chat_frame = tk.Frame(self._canvas, bg=C["chat_bg"])  # type: ignore
        self._chat_window = self._canvas.create_window(  # type: ignore
            (0, 0), window=self._chat_frame, anchor="nw",  # type: ignore
        )  # type: ignore
        self._chat_frame.bind("<Configure>", self._on_frame_configure)  # type: ignore
        self._canvas.bind("<Configure>", self._on_canvas_configure)  # type: ignore
        self._scrollers["chat"] = self._canvas  # type: ignore

        # ── Input bar ──────────────────────────────────────────────────────
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")  # type: ignore
        bar = tk.Frame(parent, bg=C["input_bg"], pady=10)  # type: ignore
        bar.pack(fill="x", side="bottom")  # type: ignore

        # Autocomplete listbox — floats above input
        self._listbox_frame = tk.Frame(parent, bg=C["border"], bd=1, relief="solid")  # type: ignore
        self._listbox = tk.Listbox(  # type: ignore
            self._listbox_frame, font=(FONT, 11),  # type: ignore
            bg="#1A1A35", fg=C["text_main"],  # type: ignore
            selectbackground=C["accent"], selectforeground="white",  # type: ignore
            bd=0, relief="flat", activestyle="none", height=5,  # type: ignore
        )  # type: ignore
        self._listbox.pack(fill="both", expand=True)  # type: ignore
        self._listbox.bind("<<ListboxSelect>>", self._on_listbox_select)  # type: ignore

        inner = tk.Frame(bar, bg=C["input_bg"])  # type: ignore
        inner.pack(fill="x", padx=16)  # type: ignore

        entry_frame = tk.Frame(inner, bg=C["input_bdr"], bd=1, relief="solid")  # type: ignore
        entry_frame.pack(side="left", fill="x", expand=True, ipady=2)  # type: ignore

        self._entry = tk.Entry(  # type: ignore
            entry_frame, textvariable=self._search_var,  # type: ignore
            font=(FONT, 13), bg=C["input_bg"], fg=C["text_main"],  # type: ignore
            insertbackground=C["accent"], bd=0, relief="flat",  # type: ignore
        )  # type: ignore
        self._entry.pack(fill="x", padx=14, pady=9)  # type: ignore
        self._entry.bind("<Return>",     self._on_search)  # type: ignore
        self._entry.bind("<KeyRelease>", self._on_key_release)  # type: ignore
        self._entry.bind("<Down>",       self._on_arrow_down)  # type: ignore
        self._entry.bind("<FocusIn>",    lambda e: self._start_glow(entry_frame))  # type: ignore
        self._entry.bind("<FocusOut>",   lambda e: self._stop_glow(entry_frame))  # type: ignore
        self._entry.focus_set()  # type: ignore

        send_btn = tk.Label(  # type: ignore
            inner, text="➤", font=(FONT, 16, "bold"),  # type: ignore
            bg=C["accent"], fg="white",  # type: ignore
            padx=16, pady=9, cursor="hand2",  # type: ignore
        )  # type: ignore
        send_btn.pack(side="left", padx=(10, 0))  # type: ignore
        send_btn.bind("<Button-1>", self._on_search)  # type: ignore
        self._bind_hover(send_btn, C["accent"], C["accent2"])  # type: ignore
        self._bind_click_flash(send_btn, C["accent"])  # type: ignore

        self._welcome_message()  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Page: Bookmarks
    # ══════════════════════════════════════════════════════════════════════════

    def _build_bookmarks_page(self, parent: tk.Frame) -> None:  # type: ignore
        self._page_header(parent, "📖  Sổ Tay Từ Vựng", C["gold"])  # type: ignore

        _ensure_file(BOOKMARKS_PATH)  # type: ignore
        try:  # type: ignore
            with open(BOOKMARKS_PATH, "r", encoding="utf-8") as f:  # type: ignore
                lines = [l.strip() for l in f if l.strip()]  # type: ignore
        except Exception:  # type: ignore
            lines = []  # type: ignore

        body = tk.Frame(parent, bg=C["chat_bg"])  # type: ignore
        body.pack(fill="both", expand=True, padx=30, pady=10)  # type: ignore

        if not lines:  # type: ignore
            tk.Label(  # type: ignore
                body, text="✦ Sổ tay đang trống.\nBấm ⭐ sau khi tra từ để lưu.",  # type: ignore
                font=(FONT, 12), bg=C["chat_bg"], fg=C["text_dim"],  # type: ignore
            ).pack(pady=60)  # type: ignore
            return

        canvas = tk.Canvas(body, bg=C["chat_bg"], highlightthickness=0)  # type: ignore
        scr = tk.Scrollbar(body, orient="vertical", command=canvas.yview)  # type: ignore
        lf  = tk.Frame(canvas, bg=C["chat_bg"])  # type: ignore
        canvas.create_window((0, 0), window=lf, anchor="nw")  # type: ignore
        canvas.configure(yscrollcommand=scr.set)  # type: ignore
        canvas.pack(side="left", fill="both", expand=True)  # type: ignore
        scr.pack(side="right", fill="y")  # type: ignore
        self._scrollers["bookmarks"] = canvas  # type: ignore
        lf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))  # type: ignore

        def _add_item(idx: int, line: str) -> None:
            if not parent.winfo_exists():  # type: ignore
                return
            parts = line.split(" - ", 1)  # type: ignore
            word = parts[0]  # type: ignore
            mean = parts[1] if len(parts) > 1 else ""  # type: ignore
            row = tk.Frame(  # type: ignore
                lf, bg=C["bubble_ai"], pady=12, padx=18,  # type: ignore
                highlightthickness=1, highlightbackground=C["border"],  # type: ignore
            )  # type: ignore
            row.pack(fill="x", pady=5)  # type: ignore
            tk.Label(row, text=word, font=(FONT, 14, "bold"),  # type: ignore
                     bg=C["bubble_ai"], fg=C["text_main"]).pack(side="left")  # type: ignore
            tk.Label(row, text=f"  {mean}", font=(FONT, 11),  # type: ignore
                     bg=C["bubble_ai"], fg=C["green"]).pack(side="left")  # type: ignore

            def _del(w: str = word) -> None:
                if messagebox.askyesno("Xóa", f"Xóa '{w}' khỏi sổ tay?"):  # type: ignore
                    with open(BOOKMARKS_PATH, "r", encoding="utf-8") as f:  # type: ignore
                        rem = [l for l in f if not l.startswith(f"{w} -")]  # type: ignore
                    with open(BOOKMARKS_PATH, "w", encoding="utf-8") as f:  # type: ignore
                        f.writelines(rem)  # type: ignore
                    self._show_page("bookmarks")  # type: ignore

            del_b = tk.Label(row, text="🗑", font=(FONT, 12),  # type: ignore
                             bg=C["bubble_ai"], fg=C["red"], cursor="hand2", padx=6)  # type: ignore
            del_b.pack(side="right")  # type: ignore
            del_b.bind("<Button-1>", lambda e: _del())  # type: ignore
            self._bind_hover(del_b, C["bubble_ai"], "#3A1515")  # type: ignore
            self._bind_hover(row,   C["bubble_ai"], C["sidebar_h"])  # type: ignore

        for i, line in enumerate(lines):  # type: ignore
            self.root.after(i * 75, lambda l=line, i_=i: _add_item(i_, l))  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Page: WOTD (Flip Cards)
    # ══════════════════════════════════════════════════════════════════════════

    def _build_wotd_page(self, parent: tk.Frame) -> None:  # type: ignore
        import random
        self._page_header(parent, "💡  Luyện Từ Vựng — Lật Thẻ", C["accent"])  # type: ignore
        tk.Label(parent, text="Bấm vào thẻ bất kỳ để khám phá từ vựng!",  # type: ignore
                 font=(FONT, 10), bg=C["bg"], fg=C["text_dim"]).pack(pady=(0, 6))  # type: ignore
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")  # type: ignore

        # 1. Scrollable area
        outer = tk.Frame(parent, bg=C["chat_bg"])  # type: ignore
        outer.pack(fill="both", expand=True)  # type: ignore

        wotd_scr = tk.Scrollbar(outer, orient="vertical", bg=C["bg"],  # type: ignore
                                troughcolor=C["chat_bg"], activebackground=C["accent"], width=8)  # type: ignore
        wotd_scr.pack(side="right", fill="y")  # type: ignore

        wotd_canvas = tk.Canvas(outer, bg=C["chat_bg"], bd=0,  # type: ignore
                                highlightthickness=0, yscrollcommand=wotd_scr.set)  # type: ignore
        wotd_canvas.pack(side="left", fill="both", expand=True)  # type: ignore
        wotd_scr.config(command=wotd_canvas.yview)  # type: ignore
        self._scrollers["wotd"] = wotd_canvas  # type: ignore

        body = tk.Frame(wotd_canvas, bg=C["chat_bg"])  # type: ignore
        wotd_win = wotd_canvas.create_window((0, 0), window=body, anchor="nw")  # type: ignore

        def _on_resize(e):  # type: ignore
            wotd_canvas.itemconfig(wotd_win, width=e.width)  # type: ignore
        wotd_canvas.bind("<Configure>", _on_resize)  # type: ignore
        body.bind("<Configure>", lambda e: wotd_canvas.configure(scrollregion=wotd_canvas.bbox("all")))  # type: ignore

        # 2. Card Generation
        if not self._words or not self._dict_app:  # type: ignore
            tk.Label(body, text="⏳ Đang tải dữ liệu...",  # type: ignore
                     bg=C["chat_bg"], fg=C["text_dim"], font=(FONT, 13)).pack(pady=60)  # type: ignore
        else:
            # Randomly sample 5 words from the list
            if self._words:
                words = random.sample(self._words, min(5, len(self._words)))  # type: ignore
            else:
                words = []  # type: ignore
            
            CARD_BG  = ["#3730A3", "#9D174D", "#065F46", "#92400E", "#1E40AF"]  # type: ignore
            CARD_HOV = ["#4338CA", "#BE185D", "#047857", "#B45309", "#1D4ED8"]  # type: ignore

            for i, w in enumerate(words):  # type: ignore
                self._make_wotd_card(body, i, w, CARD_BG, CARD_HOV)  # type: ignore

        # 3. Shuffle button (always pack this)
        btn_row = tk.Frame(parent, bg=C["bg"])  # type: ignore
        btn_row.pack(fill="x", pady=15)  # type: ignore
        
        def _shuffle():  # type: ignore
            self._show_page("wotd")  # type: ignore

        shuffle_btn = tk.Label(btn_row, text="🔄  Xáo bài mới", font=(FONT, 10, "bold"),  # type: ignore
                               bg=C["sidebar_act"], fg=C["accent"], padx=25, pady=10, cursor="hand2")  # type: ignore
        shuffle_btn.pack()  # type: ignore
        shuffle_btn.bind("<Button-1>", lambda e: _shuffle())  # type: ignore
        self._bind_hover(shuffle_btn, C["sidebar_act"], C["sidebar_h"])  # type: ignore

    def _make_wotd_card(self, body: tk.Frame, idx: int, word: str, CARD_BG: list, CARD_HOV: list) -> None:  # type: ignore
        base  = CARD_BG[idx % len(CARD_BG)]  # type: ignore
        hover = CARD_HOV[idx % len(CARD_HOV)]  # type: ignore

        row_frame = tk.Frame(body, bg=C["chat_bg"])  # type: ignore
        row_frame.pack(fill="x", pady=8, padx=20)  # type: ignore

        card = tk.Frame(row_frame, bg=base, padx=22, pady=16, highlightthickness=2, highlightbackground=hover, cursor="hand2")  # type: ignore
        card.pack(fill="x")  # type: ignore

        q_lbl  = tk.Label(card, text="?", font=(FONT, 26, "bold"), bg=base, fg="white")  # type: ignore
        q_lbl.pack(side="left", padx=(0, 12))  # type: ignore
        ht_lbl = tk.Label(card, text="▸ Bấm để lật", font=(FONT, 9), bg=base, fg="#FBBF24")  # type: ignore
        ht_lbl.pack(side="left", anchor="s", pady=(0, 4))  # type: ignore

        def _flip(e=None, c=card, w=word, clr=base):  # type: ignore
            for wg in c.winfo_children(): wg.destroy()  # type: ignore
            
            top = tk.Frame(c, bg=clr)  # type: ignore
            top.pack(fill="x", pady=(0, 8))  # type: ignore
            tk.Label(top, text=w.upper(), font=(FONT, 20, "bold"), bg=clr, fg="white").pack(side="left")  # type: ignore

            loading_lbl = tk.Label(c, text="⏳ Đang tải...", font=(FONT, 10), bg=clr, fg="#FBBF24")  # type: ignore
            loading_lbl.pack(anchor="w")  # type: ignore

            def _fetch():  # type: ignore
                entry = self._dict_app.find_word(w) if self._dict_app else None  # type: ignore
                self.root.after(0, lambda: self._show_wotd_content(c, clr, loading_lbl, entry))  # type: ignore

            threading.Thread(target=_fetch, daemon=True).start()  # type: ignore

        for w in (card, q_lbl, ht_lbl):  # type: ignore
            w.bind("<Button-1>", _flip)  # type: ignore
        self._bind_hover(card, base, hover)  # type: ignore

    def _show_wotd_content(self, card: tk.Frame, clr: str, ll: tk.Label, entry: Optional[LexicalEntry]) -> None:  # type: ignore
        if not card.winfo_exists(): return  # type: ignore
        if ll.winfo_exists(): ll.destroy()  # type: ignore
        if not entry:  # type: ignore
            tk.Label(card, text="Không tìm thấy nghĩa", font=(FONT, 10), bg=clr, fg="white").pack(anchor="w")  # type: ignore
            return

        if entry.short_translation:  # type: ignore
            tk.Label(card, text=entry.short_translation, font=(FONT, 13, "bold"), bg=clr, fg=C["green"], wraplength=600, justify="left").pack(anchor="w", pady=(0, 8))  # type: ignore
        
        for sense in (entry.senses or [])[:2]:  # type: ignore
            pos = sense.get("pos", "") # type: ignore
            if pos:  # type: ignore
                tk.Label(card, text=f"* {pos}", font=(FONT, 10, "bold"), bg=clr, fg=C["accent"]).pack(anchor="w")  # type: ignore
            
            for m in (sense.get("meanings", []))[:1]:  # type: ignore
                en, vi = m.get("en", ""), m.get("vi", "")  # type: ignore
                if en: tk.Label(card, text=f"+ {en}", font=(FONT, 9), bg=clr, fg="white", wraplength=500, justify="left").pack(anchor="w", padx=10)  # type: ignore
                if vi: tk.Label(card, text=f"({vi})", font=(FONT, 9, "italic"), bg=clr, fg="#CBD5E1", wraplength=500, justify="left").pack(anchor="w", padx=25)  # type: ignore


    # ══════════════════════════════════════════════════════════════════════════
    # Page: History
    # ══════════════════════════════════════════════════════════════════════════

    def _build_history_page(self, parent: tk.Frame) -> None:  # type: ignore
        self._page_header(parent, "📜  Lịch Sử Tra Từ", C["text_sub"])  # type: ignore
        _ensure_file(HISTORY_PATH)  # type: ignore
        try:  # type: ignore
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:  # type: ignore
                raw = [l.strip() for l in f if l.strip()]  # type: ignore
            lines = list(dict.fromkeys(reversed(raw)))[:30]  # type: ignore
        except Exception:  # type: ignore
            lines = []  # type: ignore

        body = tk.Frame(parent, bg=C["chat_bg"])  # type: ignore
        body.pack(fill="both", expand=True, padx=30, pady=10)  # type: ignore

        if not lines:  # type: ignore
            tk.Label(body, text="✦ Chưa có lịch sử.\nHãy tra một từ để bắt đầu!",  # type: ignore
                     font=(FONT, 12), bg=C["chat_bg"], fg=C["text_dim"]).pack(pady=60)  # type: ignore
        else:  # type: ignore
            for i, word in enumerate(lines):  # type: ignore
                row = tk.Frame(  # type: ignore
                    body, bg=C["bubble_ai"], pady=10, padx=16,  # type: ignore
                    highlightthickness=1, highlightbackground=C["border"],  # type: ignore
                    cursor="hand2",  # type: ignore
                )  # type: ignore
                row.pack(fill="x", pady=4)  # type: ignore
                tk.Label(row, text=f"{i+1:02d}.", font=(FONT, 10),  # type: ignore
                         bg=C["bubble_ai"], fg=C["text_dim"]).pack(side="left", padx=(0, 8))  # type: ignore
                tk.Label(row, text=word, font=(FONT, 13, "bold"),  # type: ignore
                         bg=C["bubble_ai"], fg=C["text_main"]).pack(side="left")  # type: ignore
                rdo = tk.Label(row, text="↗ Tra lại", font=(FONT, 9),  # type: ignore
                               bg=C["bubble_ai"], fg=C["accent"], cursor="hand2")  # type: ignore
                rdo.pack(side="right", padx=8)  # type: ignore

                def _redo(w: str = word) -> None:
                    self._show_page("chat")  # type: ignore
                    self.root.after(120, lambda: (self._search_var.set(w), self._on_search()))  # type: ignore

                rdo.bind("<Button-1>", lambda e, cb=_redo: cb())  # type: ignore
                self._bind_hover(row, C["bubble_ai"], C["sidebar_h"])  # type: ignore

        clr = tk.Label(body, text="🗑  Xóa lịch sử", font=(FONT, 10),  # type: ignore
                       bg=C["chat_bg"], fg=C["red"], cursor="hand2", pady=12)  # type: ignore
        clr.pack()  # type: ignore

        def _clear_hist() -> None:
            if messagebox.askyesno("Xác nhận", "Xóa toàn bộ lịch sử tra từ?"):  # type: ignore
                open(HISTORY_PATH, "w").close()  # type: ignore
                self._history.clear()  # type: ignore
                self._show_page("history")  # type: ignore

        clr.bind("<Button-1>", lambda e: _clear_hist())  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Page: Settings
    # ══════════════════════════════════════════════════════════════════════════

    def _build_settings_page(self, parent: tk.Frame) -> None:  # type: ignore
        self._page_header(parent, "⚙️  Cài Đặt", C["text_sub"])  # type: ignore
        body = tk.Frame(parent, bg=C["chat_bg"])  # type: ignore
        body.pack(fill="both", expand=True, padx=40, pady=20)  # type: ignore

        def _section(txt: str) -> None:
            tk.Label(body, text=txt, font=(FONT, 11, "bold"),  # type: ignore
                     bg=C["chat_bg"], fg=C["accent"]).pack(anchor="w", pady=(18, 4))  # type: ignore
            tk.Frame(body, bg=C["border"], height=1).pack(fill="x")  # type: ignore

        _section("📦 Dữ liệu")  # type: ignore

        def _clear_cache() -> None:
            if messagebox.askyesno("Xác nhận", "Xóa cache sẽ buộc tải lại từ API. Tiếp tục?"):  # type: ignore
                for p in [DATA_PATH, INDEX_PATH]:  # type: ignore
                    if os.path.exists(p):  # type: ignore
                        os.remove(p)  # type: ignore
                messagebox.showinfo("Hoàn tất", "Cache đã xóa. Khởi lại app để hoàn tất.")  # type: ignore

        self._settings_btn(body, "🗑  Xóa Cache (Làm mới dữ liệu)", _clear_cache)  # type: ignore

        _section("📖 Sổ tay")  # type: ignore

        def _clear_bm() -> None:
            if messagebox.askyesno("Xác nhận", "Xóa toàn bộ sổ tay vĩnh viễn?"):  # type: ignore
                open(BOOKMARKS_PATH, "w").close()  # type: ignore
                messagebox.showinfo("Hoàn tất", "Sổ tay đã xóa sạch.")  # type: ignore

        self._settings_btn(body, "🗑  Xóa sạch Sổ tay", _clear_bm)  # type: ignore

        _section("ℹ️ Thông tin")  # type: ignore
        tk.Label(  # type: ignore
            body,  # type: ignore
            text="AI Dictionary v3.2  ·  Free Dictionary API  ·  O(log n) Cache",  # type: ignore
            font=(FONT, 10), bg=C["chat_bg"], fg=C["text_dim"], justify="left",  # type: ignore
        ).pack(anchor="w", pady=8)  # type: ignore

    def _settings_btn(self, parent: tk.Frame, text: str, cmd: Callable) -> None:  # type: ignore
        btn = tk.Label(  # type: ignore
            parent, text=text, font=(FONT, 11),  # type: ignore
            bg=C["bubble_ai"], fg=C["text_main"],  # type: ignore
            padx=16, pady=10, anchor="w", cursor="hand2",  # type: ignore
        )  # type: ignore
        btn.pack(fill="x", pady=4)  # type: ignore
        btn.bind("<Button-1>", lambda e: cmd())  # type: ignore
        self._bind_hover(btn, C["bubble_ai"], C["sidebar_h"])  # type: ignore
        self._bind_click_flash(btn, C["bubble_ai"])  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Shared: page header
    # ══════════════════════════════════════════════════════════════════════════

    def _page_header(self, parent: tk.Frame, title: str, color: str) -> None:  # type: ignore
        h = tk.Frame(parent, bg=C["bg"], pady=12)  # type: ignore
        h.pack(fill="x", padx=18)  # type: ignore
        tk.Label(h, text=title, font=(FONT, 16, "bold"),  # type: ignore
                 bg=C["bg"], fg=color).pack(side="left")  # type: ignore
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Backend
    # ══════════════════════════════════════════════════════════════════════════

    def _init_backend(self) -> None:
        self._words = _load_words_list()  # type: ignore
        self._dict_app = DictionaryApp(DATA_PATH, INDEX_PATH)  # type: ignore
        n = self._dict_app.total_words_cached()  # type: ignore
        self.root.after(0, lambda: self._add_ai_bubble(  # type: ignore
            f"✅ Hệ thống sẵn sàng!\n📦 Cache: **{n:,} từ** | 🌐 Free Dictionary API: Online"  # type: ignore
        ))  # type: ignore
        _ensure_file(HISTORY_PATH)  # type: ignore
        try:  # type: ignore
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:  # type: ignore
                self._history = [l.strip() for l in f if l.strip()]  # type: ignore
        except Exception:  # type: ignore
            self._history = []  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Animation helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _bind_hover(self, w: tk.Widget, normal: str, hover: str) -> None:  # type: ignore
        w.bind("<Enter>", lambda e: w.configure(bg=hover))   # type: ignore
        w.bind("<Leave>", lambda e: w.configure(bg=normal))  # type: ignore

    def _bind_click_flash(self, w: tk.Widget, normal: str) -> None:  # type: ignore
        """Darkens widget on press, restores on release — does NOT override existing handlers."""  # type: ignore
        w.bind("<ButtonPress-1>",   lambda e: w.configure(bg="#0A0A16"), "+")   # type: ignore
        w.bind("<ButtonRelease-1>", lambda e: w.configure(bg=normal), "+")      # type: ignore

    # — Glow pulse for input border —
    def _start_glow(self, frame: tk.Frame) -> None:  # type: ignore
        self._glow_on = True  # type: ignore
        self._do_glow(frame, 0)  # type: ignore

    def _stop_glow(self, frame: tk.Frame) -> None:  # type: ignore
        self._glow_on = False  # type: ignore
        if self._glow_job:  # type: ignore
            try:  # type: ignore
                self.root.after_cancel(self._glow_job)  # type: ignore
            except Exception:  # type: ignore
                pass
        if frame.winfo_exists():  # type: ignore
            frame.config(bg=C["input_bdr"])  # type: ignore

    def _do_glow(self, frame: tk.Frame, step: int) -> None:  # type: ignore
        if not self._glow_on or not frame.winfo_exists():  # type: ignore
            return
        cols = ["#4C1D95", "#7C3AED", "#8B5CF6", "#7C3AED", "#4C1D95"]  # type: ignore
        frame.config(bg=cols[step % len(cols)])  # type: ignore
        self._glow_job = self.root.after(120, self._do_glow, frame, step + 1)  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Typing animation
    # ══════════════════════════════════════════════════════════════════════════

    def _animate_typing(self, label: tk.Label, text: str,  # type: ignore
                        index: int = 0, on_complete: Optional[Callable] = None) -> None:  # type: ignore
        if not label.winfo_exists():  # type: ignore
            return
        step = 3 if len(text) > 50 else 2  # type: ignore
        label.config(text=text[: min(index, len(text))])  # type: ignore
        self._scroll_to_bottom()  # type: ignore
        if index < len(text):  # type: ignore
            self.root.after(1, self._animate_typing, label, text, index + step, on_complete)  # type: ignore
        else:  # type: ignore
            label.config(text=text)  # type: ignore
            if on_complete:  # type: ignore
                self.root.after(5, on_complete)  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Canvas / scroll helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _on_frame_configure(self, event: object = None) -> None:  # type: ignore
        if self._canvas:  # type: ignore
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))  # type: ignore

    def _on_canvas_configure(self, event: object) -> None:  # type: ignore
        if self._canvas and self._chat_window is not None:  # type: ignore
            self._canvas.itemconfig(self._chat_window, width=event.width)  # type: ignore

    def _on_mousewheel(self, event: object) -> None:  # type: ignore
        p = self._current_page  # type: ignore
        canv = self._scrollers.get(p)  # type: ignore
        if canv and canv.winfo_exists():  # type: ignore
            try:  # type: ignore
                canv.yview_scroll(int(-1 * (event.delta / 120)), "units")  # type: ignore
            except Exception:  # type: ignore
                pass

    def _scroll_to_bottom(self) -> None:
        if self._canvas:  # type: ignore
            self.root.update_idletasks()  # type: ignore
            self._canvas.yview_moveto(1.0)  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Bubble rendering
    # ══════════════════════════════════════════════════════════════════════════

    def _add_user_bubble(self, text: str) -> None:
        if not self._chat_frame:  # type: ignore
            return
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=4)  # type: ignore
        row.pack(fill="x", padx=16)  # type: ignore
        tk.Frame(row, bg=C["chat_bg"]).pack(side="left", expand=True)  # type: ignore
        bubble = tk.Frame(row, bg=C["bubble_user"], padx=16, pady=10)  # type: ignore
        bubble.pack(side="right")  # type: ignore
        tk.Label(bubble, text=f"🔍  {text}", font=(FONT, 12, "bold"),  # type: ignore
                 bg=C["bubble_user"], fg="white",  # type: ignore
                 wraplength=420, justify="right").pack()  # type: ignore
        self._scroll_to_bottom()  # type: ignore

    def _add_ai_bubble(self, text: str) -> None:
        if not self._chat_frame:  # type: ignore
            return
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=4)  # type: ignore
        row.pack(fill="x", padx=16)  # type: ignore
        tk.Label(row, text="🤖", font=(FONT, 16),  # type: ignore
                 bg=C["chat_bg"], fg=C["accent"]).pack(side="left", anchor="n", padx=(0, 8), pady=4)  # type: ignore
        bubble = tk.Frame(row, bg=C["bubble_ai"], padx=16, pady=10)  # type: ignore
        bubble.pack(side="left", fill="x", expand=True)  # type: ignore
        lbl = tk.Label(bubble, text="", font=(FONT, 11),  # type: ignore
                       bg=C["bubble_ai"], fg=C["text_sub"],  # type: ignore
                       wraplength=700, justify="left")  # type: ignore
        lbl.pack(anchor="w")  # type: ignore
        self._animate_typing(lbl, text.replace("**", "").replace("\\n", "\n"))  # type: ignore
        self._scroll_to_bottom()  # type: ignore

    def _add_result_bubble(self, entry: LexicalEntry) -> None:
        if not self._chat_frame:  # type: ignore
            return
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=6)  # type: ignore
        row.pack(fill="x", padx=16)  # type: ignore
        tk.Label(row, text="🤖", font=(FONT, 16),  # type: ignore
                 bg=C["chat_bg"], fg=C["accent"]).pack(side="left", anchor="n", padx=(0, 8), pady=4)  # type: ignore

        bubble = tk.Frame(row, bg=C["bubble_ai"], padx=20, pady=14)  # type: ignore
        bubble.pack(side="left")  # type: ignore

        import re
        ipa = entry.uk_ipa or entry.us_ipa  # type: ignore
        title_word = entry.word.lower()  # type: ignore
        ipa_str = f" /{re.sub(r'[/\\[\\]\\s]', '', ipa)}/" if ipa else ""  # type: ignore

        source = getattr(entry, "source", "")  # type: ignore

        title_frame = tk.Frame(bubble, bg=C["bubble_ai"])  # type: ignore
        title_frame.pack(anchor="w", pady=(0, 2))  # type: ignore
        
        title_lbl = tk.Label(title_frame, text="", font=(FONT, 22, "bold"),  # type: ignore
                             bg=C["bubble_ai"], fg=C["text_main"])  # type: ignore
        title_lbl.pack(side="left", anchor="s")  # type: ignore
        
        ipa_lbl = tk.Label(title_frame, text="", font=(FONT, 14),  # type: ignore
                           bg=C["bubble_ai"], fg=C["text_dim"])  # type: ignore
        ipa_lbl.pack(side="left", anchor="s", padx=(8, 0), pady=(0, 4))  # type: ignore

        src_lbl = tk.Label(bubble, text="", font=(FONT, 9),  # type: ignore
                           bg=C["bubble_ai"], fg=C["text_dim"])  # type: ignore

        def stage_3() -> None:
            if not bubble.winfo_exists():  # type: ignore
                return
            tk.Frame(bubble, bg="#4A4A8A", height=1).pack(fill="x", pady=10)  # type: ignore
            
            # Khôi phục short_translation cho các từ offline (chỉ có nghĩa TV, không có senses Anh-Anh)
            short_v = getattr(entry, "short_translation", "")  # type: ignore
            if short_v:  # type: ignore
                tk.Label(bubble, text=short_v, font=(FONT, 14, "bold"),  # type: ignore
                         bg=C["bubble_ai"], fg=C["green"], wraplength=660, justify="left").pack(anchor="w", pady=(0, 10))  # type: ignore
                         
            self._animate_senses(bubble, entry, entry.senses or [])  # type: ignore

        def stage_2() -> None:
            if not bubble.winfo_exists():  # type: ignore
                return
            if source:  # type: ignore
                src_lbl.pack(anchor="w", pady=(0, 4))  # type: ignore
                algo = "⚡ RAM Cache" if "Cache" in source else "🌐 Free API"  # type: ignore
                self._animate_typing(src_lbl, algo, on_complete=stage_3)  # type: ignore
            else:  # type: ignore
                stage_3()  # type: ignore

        def stage_1() -> None:
            if ipa_str and bubble.winfo_exists():  # type: ignore
                self._animate_typing(ipa_lbl, ipa_str, on_complete=stage_2)  # type: ignore
            else:
                stage_2()
                
        self._animate_typing(title_lbl, title_word, on_complete=stage_1)  # type: ignore
        self._last_entry = entry  # type: ignore

    def _add_not_found_bubble(self, kw: str) -> None:
        if not self._chat_frame:  # type: ignore
            return
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=6)  # type: ignore
        row.pack(fill="x", padx=16)  # type: ignore
        tk.Label(row, text="🤖", font=(FONT, 16),  # type: ignore
                 bg=C["chat_bg"], fg=C["accent"]).pack(side="left", anchor="n", padx=(0, 8), pady=4)  # type: ignore
        bubble = tk.Frame(row, bg="#2A1515", padx=16, pady=12)  # type: ignore
        bubble.pack(side="left")  # type: ignore
        tk.Label(bubble, text=f"❌  Không tìm thấy «{kw}»",  # type: ignore
                 font=(FONT, 12, "bold"), bg="#2A1515", fg=C["red"]).pack(anchor="w")  # type: ignore
        tk.Label(bubble,  # type: ignore
                 text="Từ này chưa có trong từ điển. Thử từ thông dụng khác nhé!",  # type: ignore
                 font=(FONT, 10), bg="#2A1515", fg=C["text_dim"],  # type: ignore
                 wraplength=620, justify="left").pack(anchor="w", pady=(4, 0))  # type: ignore
        self._scroll_to_bottom()  # type: ignore

    def _welcome_message(self) -> None:
        if not self._chat_frame:  # type: ignore
            return
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=16)  # type: ignore
        row.pack(fill="x", padx=16)  # type: ignore
        tk.Label(row, text="🤖", font=(FONT, 22),  # type: ignore
                 bg=C["chat_bg"], fg=C["accent"]).pack(side="left", anchor="n", padx=(0, 10))  # type: ignore
        b = tk.Frame(row, bg=C["bubble_ai"], padx=20, pady=14)  # type: ignore
        b.pack(side="left")  # type: ignore
        tk.Label(b, text="Xin chào! Tôi là AI Từ Điển Anh-Việt 🌟",  # type: ignore
                 font=(FONT, 14, "bold"), bg=C["bubble_ai"], fg=C["text_main"]).pack(anchor="w")  # type: ignore
        tk.Label(b,  # type: ignore
                 text="Gõ một từ tiếng Anh rồi nhấn ➤ hoặc Enter để tra nghĩa.\n\n"  # type: ignore
                      "📖 Sổ tay · 💡 Luyện từ · 📜 Lịch sử — có trong thanh bên trái!",  # type: ignore
                 font=(FONT, 10), bg=C["bubble_ai"], fg=C["text_dim"],  # type: ignore
                 wraplength=660, justify="left").pack(anchor="w", pady=(6, 0))  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Senses / examples rendering (sequential typing chain)
    # ══════════════════════════════════════════════════════════════════════════

    _POS_VI = {  # type: ignore
        "noun": "danh từ", "verb": "động từ", "adjective": "tính từ",  # type: ignore
        "adverb": "trạng từ", "pronoun": "đại từ", "preposition": "giới từ",  # type: ignore
        "conjunction": "liên từ", "interjection": "thán từ",  # type: ignore
    }  # type: ignore

    def _animate_senses(self, bubble: tk.Frame, entry: LexicalEntry,  # type: ignore
                        senses: list, idx: int = 0) -> None:  # type: ignore
        if idx >= len(senses) or not bubble.winfo_exists():  # type: ignore
            self._add_save_btn(bubble, entry)  # type: ignore
            self._scroll_to_bottom()  # type: ignore
            return

        s = senses[idx]  # type: ignore
        vi_pos = self._POS_VI.get((s.pos or "").lower(), s.pos or "")  # type: ignore
        if vi_pos:  # type: ignore
            tk.Label(bubble, text=f"* {vi_pos}", font=(FONT, 11, "bold"),  # type: ignore
                     bg=C["bubble_ai"], fg="#3B82F6").pack(anchor="w", pady=(10, 2))  # type: ignore

        def_lbl = tk.Label(bubble, text="", font=(FONT, 11),  # type: ignore
                           bg=C["bubble_ai"], fg=C["text_main"],  # type: ignore
                           wraplength=660, justify="left")  # type: ignore
        def_lbl.pack(anchor="w", padx=(10, 0))  # type: ignore

        def on_def_done() -> None:
            def on_tr_done() -> None:
                if s.examples:  # type: ignore
                    self._animate_examples(bubble, entry, senses, idx, s.examples, 0)  # type: ignore
                else:  # type: ignore
                    self._animate_senses(bubble, entry, senses, idx + 1)  # type: ignore

            if s.translation:  # type: ignore
                tl = tk.Label(bubble, text="", font=(FONT, 10, "italic"),  # type: ignore
                              bg=C["bubble_ai"], fg="#A8B5C8",  # type: ignore
                              wraplength=660, justify="left")  # type: ignore
                tl.pack(anchor="w", padx=(24, 0))  # type: ignore
                self._animate_typing(tl, f"({s.translation.strip('() ')})", on_complete=on_tr_done)  # type: ignore
            else:  # type: ignore
                on_tr_done()  # type: ignore

        self._animate_typing(def_lbl, f"+ {s.definition}", on_complete=on_def_done)  # type: ignore

    def _animate_examples(self, bubble: tk.Frame, entry: LexicalEntry,  # type: ignore
                          senses: list, si: int, examples: list, ei: int) -> None:  # type: ignore
        if ei >= len(examples) or not bubble.winfo_exists():  # type: ignore
            self._animate_senses(bubble, entry, senses, si + 1)  # type: ignore
            return

        ex = examples[ei]  # type: ignore
        en_ex = ex.get("en", "")  # type: ignore
        vi_ex = ex.get("vi", "")  # type: ignore
        if not en_ex:  # type: ignore
            self._animate_examples(bubble, entry, senses, si, examples, ei + 1)  # type: ignore
            return

        en_lbl = tk.Label(bubble, text="", font=(FONT, 10, "italic"),  # type: ignore
                          bg=C["bubble_ai"], fg="#BAE6FD",  # type: ignore
                          wraplength=640, justify="left")  # type: ignore
        en_lbl.pack(anchor="w", padx=(10, 0))  # type: ignore

        def on_en_done() -> None:
            if vi_ex:  # type: ignore
                vl = tk.Label(bubble, text="", font=(FONT, 9, "italic"),  # type: ignore
                              bg=C["bubble_ai"], fg="#8A9EB1",  # type: ignore
                              wraplength=640, justify="left")  # type: ignore
                vl.pack(anchor="w", padx=(28, 0))  # type: ignore
                self._animate_typing(  # type: ignore
                    vl, f"({vi_ex.strip('() ')})",  # type: ignore
                    on_complete=lambda: self._animate_examples(bubble, entry, senses, si, examples, ei + 1),  # type: ignore
                )  # type: ignore
            else:  # type: ignore
                self._animate_examples(bubble, entry, senses, si, examples, ei + 1)  # type: ignore

        self._animate_typing(en_lbl, f"+ {en_ex}", on_complete=on_en_done)  # type: ignore

    def _add_save_btn(self, bubble: tk.Frame, entry: LexicalEntry) -> None:  # type: ignore
        if not bubble.winfo_exists():  # type: ignore
            return
        btn = tk.Label(bubble, text="⭐  Lưu vào Sổ tay", font=(FONT, 9, "bold"),  # type: ignore
                       bg="#2A2A4A", fg=C["gold"], padx=12, pady=6, cursor="hand2")  # type: ignore
        btn.pack(anchor="w", pady=(12, 4))  # type: ignore

        def _save() -> None:
            _ensure_file(BOOKMARKS_PATH)  # type: ignore
            line = f"{entry.word} - {getattr(entry, 'short_translation', '')}\n"  # type: ignore
            with open(BOOKMARKS_PATH, "a", encoding="utf-8") as f:  # type: ignore
                f.write(line)  # type: ignore
            btn.config(text="✅  Đã lưu", fg=C["green"])  # type: ignore

        btn.bind("<Button-1>", lambda e: _save())  # type: ignore
        self._bind_hover(btn, "#2A2A4A", "#3A3A5A")  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Search
    # ══════════════════════════════════════════════════════════════════════════

    def _on_search(self, event: object = None) -> None:
        self._hide_listbox()  # type: ignore
        kw = self._search_var.get().strip()  # type: ignore
        if not kw:  # type: ignore
            return
        self._search_var.set("")  # type: ignore
        self._add_user_bubble(kw)  # type: ignore
        loading_txt = "⏳ Đang dịch..." if self._search_mode == "vi_en" else "⏳ Đang tra cứu..."  # type: ignore
        self._add_ai_bubble(loading_txt)  # type: ignore

        # Save to history
        try:  # type: ignore
            _ensure_file(HISTORY_PATH)  # type: ignore
            with open(HISTORY_PATH, "a", encoding="utf-8") as f:  # type: ignore
                f.write(kw + "\n")  # type: ignore
            self._history.append(kw)  # type: ignore
        except Exception:  # type: ignore
            pass

        def _do() -> None:
            if not self._dict_app:  # type: ignore
                return
            current_m = self._search_mode  # type: ignore
            e = self._dict_app.find_word(kw, mode=current_m)  # type: ignore
            self.root.after(0, self._remove_last_bubble)  # type: ignore
            if e:  # type: ignore
                self.root.after(0, lambda: self._add_result_bubble(e))  # type: ignore
            else:  # type: ignore
                self.root.after(0, lambda: self._add_not_found_bubble(kw))  # type: ignore

        threading.Thread(target=_do, daemon=True).start()  # type: ignore

    def _remove_last_bubble(self) -> None:
        if self._chat_frame:  # type: ignore
            ch = self._chat_frame.winfo_children()  # type: ignore
            if ch:  # type: ignore
                ch[-1].destroy()  # type: ignore

    def _clear_chat(self) -> None:
        if self._chat_frame:  # type: ignore
            for w in self._chat_frame.winfo_children():  # type: ignore
                w.destroy()  # type: ignore
        self._last_entry = None  # type: ignore
        self._welcome_message()  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Audio
    # ══════════════════════════════════════════════════════════════════════════

    def _on_speak(self, accent: str) -> None:
        if not self._last_entry:  # type: ignore
            return
        url = self._last_entry.us_audio if accent == "us" else self._last_entry.uk_audio  # type: ignore
        if url:  # type: ignore
            webbrowser.open_new_tab(url)  # type: ignore
        else:  # type: ignore
            def _fb() -> None:
                try:  # type: ignore
                    import pyttsx3  # type: ignore
                    e = pyttsx3.init()  # type: ignore
                    e.say(self._last_entry.word)  # type: ignore
                    e.runAndWait()  # type: ignore
                except Exception:  # type: ignore
                    pass
            threading.Thread(target=_fb, daemon=True).start()  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Autocomplete
    # ══════════════════════════════════════════════════════════════════════════

    def _show_listbox(self) -> None:
        if not self._entry or not self._listbox_frame:  # type: ignore
            return
        x = self._entry.winfo_rootx() - self.root.winfo_rootx()  # type: ignore
        y = self._entry.winfo_rooty() - self.root.winfo_rooty() - 130  # type: ignore
        w = self._entry.winfo_width()  # type: ignore
        self._listbox_frame.place(x=x, y=y, width=w)  # type: ignore
        self._listbox_frame.lift()  # type: ignore

    def _hide_listbox(self) -> None:
        if self._listbox_frame and self._listbox_frame.winfo_exists():  # type: ignore
            self._listbox_frame.place_forget()  # type: ignore

    def _on_key_release(self, event: object) -> None:  # type: ignore
        if event.keysym in ("Return", "Down", "Up", "Left", "Right"):  # type: ignore
            return
        kw = self._search_var.get().strip().lower()  # type: ignore
        if not kw:  # type: ignore
            self._hide_listbox()  # type: ignore
            return
        matches = [w for w in self._words if w.startswith(kw)][:7]  # type: ignore
        if matches and self._listbox:  # type: ignore
            self._listbox.delete(0, tk.END)  # type: ignore
            for m in matches:  # type: ignore
                self._listbox.insert(tk.END, m)  # type: ignore
            self._show_listbox()  # type: ignore
        else:  # type: ignore
            self._hide_listbox()  # type: ignore

    def _on_arrow_down(self, event: object) -> None:  # type: ignore
        if self._listbox_frame and self._listbox_frame.winfo_ismapped() and self._listbox:  # type: ignore
            self._listbox.focus()  # type: ignore
            self._listbox.selection_set(0)  # type: ignore

    def _on_listbox_select(self, event: object) -> None:  # type: ignore
        if not self._listbox:  # type: ignore
            return
        sel = self._listbox.curselection()  # type: ignore
        if sel:  # type: ignore
            word = str(self._listbox.get(int(sel[0])))  # type: ignore
            self._search_var.set(word)  # type: ignore
            self._hide_listbox()  # type: ignore
            if self._entry:  # type: ignore
                self._entry.focus()  # type: ignore
            self._on_search()  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Run
    # ══════════════════════════════════════════════════════════════════════════

    def run(self) -> None:
        self.root.mainloop()  # type: ignore


def main() -> None:
    DictionaryUI().run()  # type: ignore


if __name__ == "__main__":  # type: ignore
    main()  # type: ignore