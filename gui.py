"""
gui.py — AI Dictionary v3.2 (Gemini-Style UI + VS Code Left Sidebar)
=====================================================================
Entry point chính. Chạy: python gui.py
"""

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

if getattr(sys, "frozen", False):
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))

DATA_PATH       = os.path.join(_BASE, "data", "meaning.data")
INDEX_PATH      = os.path.join(_BASE, "data", "index.data")
WORDS_LIST_PATH = os.path.join(_BASE, "data", "words_list.txt")
BOOKMARKS_PATH  = os.path.join(_BASE, "data", "bookmarks.txt")
HISTORY_PATH    = os.path.join(_BASE, "data", "history.txt")

def _ensure_file(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").close()

# ── Colour Palette ─────────────────────────────────────────────────────────────
C: dict = {
    "bg":          "#0F0F17",
    "sidebar":     "#13131F",
    "sidebar_h":   "#1D1D30",
    "sidebar_act": "#1E1E38",
    "chat_bg":     "#0F0F17",
    "bubble_ai":   "#1C1C2E",
    "bubble_user": "#3B1F5E",
    "accent":      "#8B5CF6",
    "accent2":     "#EC4899",
    "gold":        "#F59E0B",
    "green":       "#10B981",
    "red":         "#EF4444",
    "text_main":   "#F1F5F9",
    "text_dim":    "#6B7280",
    "text_sub":    "#9CA3AF",
    "input_bg":    "#1C1C2E",
    "input_bdr":   "#2D2D5E",
    "border":      "#2A2A4A",
}

FONT         = "Segoe UI"
SIDEBAR_COL  = 64    # collapsed width px
SIDEBAR_EXP  = 210   # expanded  width px

# ── Word-list loader ───────────────────────────────────────────────────────────
def _load_words_list() -> List[str]:
    _ensure_file(WORDS_LIST_PATH)
    url = ("https://raw.githubusercontent.com/first20hours/google-10000-english"
           "/master/google-10000-english-no-swears.txt")
    if os.path.getsize(WORDS_LIST_PATH) == 0:
        try:
            urllib.request.urlretrieve(url, WORDS_LIST_PATH)
        except Exception as e:
            print(f"words_list download error: {e}")
    try:
        with open(WORDS_LIST_PATH, "r", encoding="utf-8") as f:
            return sorted(line.strip() for line in f if line.strip())
    except Exception:
        return []

# ── Main UI ────────────────────────────────────────────────────────────────────
class DictionaryUI:

    # Nav items: (page_id, icon, label)
    _NAV = [
        ("chat",      "🔍", "Tra từ"),
        ("bookmarks", "📖", "Sổ tay"),
        ("wotd",      "💡", "Luyện từ"),
        ("history",   "📜", "Lịch sử"),
        ("settings",  "⚙️", "Cài đặt"),
    ]

    def __init__(self) -> None:
        self.root = tk.Tk()  # type: ignore
        self.root.title("AI Dictionary — Từ Điển Anh-Việt")
        self.root.configure(bg=C["bg"])
        self.root.geometry("1020x720")
        self.root.minsize(760, 520)

        # ── state ──
        self._dict_app:    Optional[DictionaryApp] = None
        self._words:       List[str] = []
        self._search_var = tk.StringVar()  # type: ignore
        self._last_entry:  Optional[LexicalEntry] = None
        self._entry:       Optional[tk.Entry] = None  # type: ignore
        self._history:     List[str] = []
        self._current_page = ""
        self._sidebar_expanded = False
        self._glow_job:    Optional[str] = None
        self._glow_on      = False
        self._pages:       dict = {}
        self._nav_btns:    dict = {}

        # ── chat canvas references (created by _build_chat_page) ──
        self._canvas:      Optional[tk.Canvas] = None  # type: ignore
        self._chat_frame:  Optional[tk.Frame]  = None  # type: ignore
        self._chat_window: Optional[int]       = None
        self._listbox_frame: Optional[tk.Frame] = None  # type: ignore
        self._listbox:     Optional[tk.Listbox] = None  # type: ignore

        self._build_layout()
        self.root.after(50,  lambda: self._show_page("chat"))
        threading.Thread(target=self._init_backend, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # Layout
    # ══════════════════════════════════════════════════════════════════════════

    def _build_layout(self) -> None:
        # Left sidebar
        self._sidebar_frame = tk.Frame(self.root, bg=C["sidebar"], width=SIDEBAR_COL)
        self._sidebar_frame.pack(side="left", fill="y")
        self._sidebar_frame.pack_propagate(False)

        # Thin accent separator
        tk.Frame(self.root, bg=C["accent"], width=2).pack(side="left", fill="y")

        # Right main area
        self._main_frame = tk.Frame(self.root, bg=C["bg"])
        self._main_frame.pack(side="left", fill="both", expand=True)

        self._build_sidebar()

    # ══════════════════════════════════════════════════════════════════════════
    # Sidebar
    # ══════════════════════════════════════════════════════════════════════════

    def _build_sidebar(self) -> None:
        sb = self._sidebar_frame

        # Toggle (hamburger / ✕)
        self._toggle_lbl = tk.Label(
            sb, text="☰", font=(FONT, 17),
            bg=C["sidebar"], fg=C["text_dim"],
            cursor="hand2", pady=14, padx=0,
        )
        self._toggle_lbl.pack(fill="x")
        self._toggle_lbl.bind("<Button-1>", lambda e: self._toggle_sidebar())
        self._bind_hover(self._toggle_lbl, C["sidebar"], C["sidebar_h"])
        self._bind_click_flash(self._toggle_lbl, C["sidebar"])

        tk.Frame(sb, bg=C["border"], height=1).pack(fill="x", pady=(0, 4))

        for pid, icon, label in self._NAV:
            self._nav_btns[pid] = self._make_nav_btn(sb, pid, icon, label)

        # App label at bottom (shown when expanded)
        self._app_lbl = tk.Label(
            sb, text="", font=(FONT, 8),
            bg=C["sidebar"], fg=C["text_dim"], wraplength=SIDEBAR_EXP - 10,
        )
        self._app_lbl.pack(side="bottom", pady=10)

    def _make_nav_btn(self, parent: tk.Frame, pid: str, icon: str, label: str) -> tk.Frame:  # type: ignore
        frame = tk.Frame(parent, bg=C["sidebar"], cursor="hand2")
        frame.pack(fill="x", pady=1)

        # Left active-indicator strip
        indicator = tk.Frame(frame, bg=C["sidebar"], width=3)
        indicator.pack(side="left", fill="y")

        icon_lbl = tk.Label(
            frame, text=icon, font=(FONT, 17),
            bg=C["sidebar"], fg=C["text_dim"],
            width=3, pady=12,
        )
        icon_lbl.pack(side="left")

        text_lbl = tk.Label(
            frame, text=label, font=(FONT, 11),
            bg=C["sidebar"], fg=C["text_dim"], anchor="w",
        )
        # Text hidden while collapsed; shown by _toggle_sidebar
        text_lbl.pack_forget()

        # Store refs on the frame object for later access
        frame.__dict__.update(
            _pid=pid, _indicator=indicator,
            _icon_lbl=icon_lbl, _text_lbl=text_lbl,
        )

        def _enter(e: object) -> None:
            if self._current_page != pid:
                for w in (frame, icon_lbl, text_lbl):
                    w.config(bg=C["sidebar_h"])

        def _leave(e: object) -> None:
            if self._current_page != pid:
                for w in (frame, icon_lbl, text_lbl):
                    w.config(bg=C["sidebar"])

        def _click(e: object) -> None:
            self._nav_click_anim(pid, frame)

        for widget in (frame, icon_lbl, text_lbl):
            widget.bind("<Enter>",    _enter)
            widget.bind("<Leave>",    _leave)
            widget.bind("<Button-1>", _click)

        return frame

    def _nav_click_anim(self, pid: str, frame: tk.Frame) -> None:  # type: ignore
        """Press-darken → navigate → highlight active."""
        for wg in (frame, frame.__dict__["_icon_lbl"], frame.__dict__["_text_lbl"]):
            try:
                wg.config(bg="#0A0A14")
            except Exception:
                pass

        def _go() -> None:
            self._show_page(pid)

        self.root.after(80, _go)

    def _set_nav_active(self, pid: str) -> None:
        for nav_id, btn in self._nav_btns.items():
            if not btn.winfo_exists():
                continue
            d = btn.__dict__
            active = nav_id == pid
            c_bg   = C["sidebar_act"] if active else C["sidebar"]
            c_icon = C["accent"]      if active else C["text_dim"]
            c_text = C["text_main"]   if active else C["text_dim"]
            c_ind  = C["accent"]      if active else C["sidebar"]
            btn.config(bg=c_bg)
            d["_icon_lbl"].config(bg=c_bg, fg=c_icon)
            d["_text_lbl"].config(bg=c_bg, fg=c_text)
            d["_indicator"].config(bg=c_ind)
        self._current_page = pid

    def _toggle_sidebar(self) -> None:
        self._sidebar_expanded = not self._sidebar_expanded
        target = SIDEBAR_EXP if self._sidebar_expanded else SIDEBAR_COL
        self._toggle_lbl.config(text="✕" if self._sidebar_expanded else "☰")
        self._app_lbl.config(text="AI Dictionary" if self._sidebar_expanded else "")
        for btn in self._nav_btns.values():
            tl = btn.__dict__["_text_lbl"]
            if self._sidebar_expanded:
                tl.pack(side="left", padx=6)
            else:
                tl.pack_forget()
        self._anim_sidebar(target)

    def _anim_sidebar(self, target: int) -> None:
        cur  = self._sidebar_frame.winfo_width()
        diff = target - cur
        if abs(diff) <= 4:
            self._sidebar_frame.config(width=target)
            return
        self._sidebar_frame.config(width=cur + (10 if diff > 0 else -10))
        self.root.after(8, self._anim_sidebar, target)  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Page routing
    # ══════════════════════════════════════════════════════════════════════════

    _LIVE_PAGES = {"bookmarks", "wotd", "history"}  # rebuilt every visit

    _PAGE_BUILDERS: dict = {}  # filled after class definition

    def _show_page(self, pid: str) -> None:
        # Hide all
        for p in self._pages.values():
            if p.winfo_exists():
                p.pack_forget()

        builders = {
            "chat":      self._build_chat_page,
            "bookmarks": self._build_bookmarks_page,
            "wotd":      self._build_wotd_page,
            "history":   self._build_history_page,
            "settings":  self._build_settings_page,
        }

        if pid in self._LIVE_PAGES and pid in self._pages:
            # Rebuild live page in place
            for w in self._pages[pid].winfo_children():
                w.destroy()
            builders[pid](self._pages[pid])
        elif pid not in self._pages:
            frame = tk.Frame(self._main_frame, bg=C["bg"])
            self._pages[pid] = frame
            builders[pid](frame)

        self._pages[pid].pack(fill="both", expand=True)
        self._set_nav_active(pid)

    # ══════════════════════════════════════════════════════════════════════════
    # Page: Chat
    # ══════════════════════════════════════════════════════════════════════════

    def _build_chat_page(self, parent: tk.Frame) -> None:  # type: ignore
        # Top bar (minimal, no heavy header)
        topbar = tk.Frame(parent, bg=C["bg"], pady=8)
        topbar.pack(fill="x", padx=18)

        tk.Label(
            topbar, text="🤖  AI Từ Điển Anh-Việt",
            font=(FONT, 14, "bold"), bg=C["bg"], fg=C["text_main"],
        ).pack(side="left")

        # Mini audio + clear buttons
        for txt, cb in [("🗑", self._clear_chat), ("🇺🇸", lambda: self._on_speak("us")), ("🇬🇧", lambda: self._on_speak("uk"))]:
            b = tk.Label(topbar, text=txt, font=(FONT, 13), bg=C["bg"],
                         fg=C["text_dim"], cursor="hand2", padx=8)
            b.pack(side="right")
            b.bind("<Button-1>", lambda e, fn=cb: fn())
            self._bind_hover(b, C["bg"], C["sidebar_h"])
            self._bind_click_flash(b, C["bg"])

        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")

        # ── Chat canvas ──────────────────────────────────────────────────────
        container = tk.Frame(parent, bg=C["chat_bg"])
        container.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(
            container, orient="vertical",
            bg=C["bg"], troughcolor=C["chat_bg"],
            activebackground=C["accent"], width=8,
        )
        scrollbar.pack(side="right", fill="y")

        self._canvas = tk.Canvas(
            container, bg=C["chat_bg"], bd=0,
            highlightthickness=0, yscrollcommand=scrollbar.set,
        )
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._canvas.yview)

        self._chat_frame = tk.Frame(self._canvas, bg=C["chat_bg"])
        self._chat_window = self._canvas.create_window(
            (0, 0), window=self._chat_frame, anchor="nw",
        )
        self._chat_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # ── Input bar ──────────────────────────────────────────────────────
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")
        bar = tk.Frame(parent, bg=C["input_bg"], pady=10)
        bar.pack(fill="x", side="bottom")

        # Autocomplete listbox — floats above input
        self._listbox_frame = tk.Frame(parent, bg=C["border"], bd=1, relief="solid")
        self._listbox = tk.Listbox(
            self._listbox_frame, font=(FONT, 11),
            bg="#1A1A35", fg=C["text_main"],
            selectbackground=C["accent"], selectforeground="white",
            bd=0, relief="flat", activestyle="none", height=5,
        )
        self._listbox.pack(fill="both", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_listbox_select)

        inner = tk.Frame(bar, bg=C["input_bg"])
        inner.pack(fill="x", padx=16)

        entry_frame = tk.Frame(inner, bg=C["input_bdr"], bd=1, relief="solid")
        entry_frame.pack(side="left", fill="x", expand=True, ipady=2)

        self._entry = tk.Entry(
            entry_frame, textvariable=self._search_var,
            font=(FONT, 13), bg=C["input_bg"], fg=C["text_main"],
            insertbackground=C["accent"], bd=0, relief="flat",
        )
        self._entry.pack(fill="x", padx=14, pady=9)
        self._entry.bind("<Return>",     self._on_search)
        self._entry.bind("<KeyRelease>", self._on_key_release)
        self._entry.bind("<Down>",       self._on_arrow_down)
        self._entry.bind("<FocusIn>",    lambda e: self._start_glow(entry_frame))
        self._entry.bind("<FocusOut>",   lambda e: self._stop_glow(entry_frame))
        self._entry.focus_set()

        send_btn = tk.Label(
            inner, text="➤", font=(FONT, 16, "bold"),
            bg=C["accent"], fg="white",
            padx=16, pady=9, cursor="hand2",
        )
        send_btn.pack(side="left", padx=(10, 0))
        send_btn.bind("<Button-1>", self._on_search)
        self._bind_hover(send_btn, C["accent"], C["accent2"])
        self._bind_click_flash(send_btn, C["accent"])

        self._welcome_message()

    # ══════════════════════════════════════════════════════════════════════════
    # Page: Bookmarks
    # ══════════════════════════════════════════════════════════════════════════

    def _build_bookmarks_page(self, parent: tk.Frame) -> None:  # type: ignore
        self._page_header(parent, "📖  Sổ Tay Từ Vựng", C["gold"])

        _ensure_file(BOOKMARKS_PATH)
        try:
            with open(BOOKMARKS_PATH, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
        except Exception:
            lines = []

        body = tk.Frame(parent, bg=C["chat_bg"])
        body.pack(fill="both", expand=True, padx=30, pady=10)

        if not lines:
            tk.Label(
                body, text="✦ Sổ tay đang trống.\nBấm ⭐ sau khi tra từ để lưu.",
                font=(FONT, 12), bg=C["chat_bg"], fg=C["text_dim"],
            ).pack(pady=60)
            return

        canvas = tk.Canvas(body, bg=C["chat_bg"], highlightthickness=0)
        scr = tk.Scrollbar(body, orient="vertical", command=canvas.yview)
        lf  = tk.Frame(canvas, bg=C["chat_bg"])
        canvas.create_window((0, 0), window=lf, anchor="nw")
        canvas.configure(yscrollcommand=scr.set)
        canvas.pack(side="left", fill="both", expand=True)
        scr.pack(side="right", fill="y")
        lf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _add_item(idx: int, line: str) -> None:
            if not parent.winfo_exists():
                return
            parts = line.split(" - ", 1)
            word = parts[0]
            mean = parts[1] if len(parts) > 1 else ""
            row = tk.Frame(
                lf, bg=C["bubble_ai"], pady=12, padx=18,
                highlightthickness=1, highlightbackground=C["border"],
            )
            row.pack(fill="x", pady=5)
            tk.Label(row, text=word, font=(FONT, 14, "bold"),
                     bg=C["bubble_ai"], fg=C["text_main"]).pack(side="left")
            tk.Label(row, text=f"  {mean}", font=(FONT, 11),
                     bg=C["bubble_ai"], fg=C["green"]).pack(side="left")

            def _del(w: str = word) -> None:
                if messagebox.askyesno("Xóa", f"Xóa '{w}' khỏi sổ tay?"):
                    with open(BOOKMARKS_PATH, "r", encoding="utf-8") as f:
                        rem = [l for l in f if not l.startswith(f"{w} -")]
                    with open(BOOKMARKS_PATH, "w", encoding="utf-8") as f:
                        f.writelines(rem)
                    self._show_page("bookmarks")

            del_b = tk.Label(row, text="🗑", font=(FONT, 12),
                             bg=C["bubble_ai"], fg=C["red"], cursor="hand2", padx=6)
            del_b.pack(side="right")
            del_b.bind("<Button-1>", lambda e: _del())
            self._bind_hover(del_b, C["bubble_ai"], "#3A1515")
            self._bind_hover(row,   C["bubble_ai"], C["sidebar_h"])

        for i, line in enumerate(lines):
            self.root.after(i * 75, lambda l=line, i_=i: _add_item(i_, l))  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Page: WOTD (Flip Cards)
    # ══════════════════════════════════════════════════════════════════════════

    def _build_wotd_page(self, parent: tk.Frame) -> None:  # type: ignore
        import random
        self._page_header(parent, "💡  Luyện Từ Vựng — Lật Thẻ", C["accent"])
        tk.Label(parent, text="Bấm vào thẻ bất kỳ để khám phá từ vựng!",
                 font=(FONT, 10), bg=C["bg"], fg=C["text_dim"]).pack(pady=(0, 6))
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")

        body = tk.Frame(parent, bg=C["chat_bg"])
        body.pack(fill="both", expand=True, padx=40, pady=14)

        if not self._words or not self._dict_app:
            tk.Label(body, text="⏳ Đang tải dữ liệu...",
                     bg=C["chat_bg"], fg=C["text_dim"], font=(FONT, 13)).pack(pady=60)
            return

        words = random.sample(self._words, min(5, len(self._words)))
        CARD_BG  = ["#6D28D9", "#DB2777", "#059669", "#D97706", "#2563EB"]
        CARD_HOV = ["#7C3AED", "#EC4899", "#10B981", "#F59E0B", "#3B82F6"]

        def _make_card(idx: int, word: str) -> None:
            base  = CARD_BG[idx  % len(CARD_BG)]
            hover = CARD_HOV[idx % len(CARD_HOV)]

            card = tk.Frame(
                body, bg=base, padx=28, pady=20,
                highlightthickness=2, highlightbackground=hover,
                cursor="hand2",
            )
            card.pack(fill="x", pady=6, padx=6)

            q_lbl  = tk.Label(card, text="?",    font=(FONT, 30, "bold"), bg=base, fg="white")
            q_lbl.pack()
            ht_lbl = tk.Label(card, text="▸ Bấm để lật", font=(FONT, 9), bg=base, fg="#FBBF24")
            ht_lbl.pack()

            flipped = [False]

            def _flip(e: object = None, c: tk.Frame = card, w: str = word,
                      clr: str = base, hv: str = hover, f: list = flipped) -> None:
                if f[0]:
                    return
                f[0] = True
                for wg in c.winfo_children():
                    wg.destroy()
                tk.Label(c, text=w.upper(), font=(FONT, 26, "bold"), bg=clr, fg="white").pack()

                # Instant from cache, background-fetch if miss
                entry = None
                if self._dict_app:
                    try:
                        entry = self._dict_app.find_word_cached(w)  # type: ignore
                    except AttributeError:
                        pass

                ml = tk.Label(c, text="…", font=(FONT, 15), bg=clr,
                              fg=C["green"], wraplength=720)
                ml.pack(pady=(6, 0))

                if entry:
                    meaning = getattr(entry, "short_translation", "") or ""
                    ml.config(text=meaning or "—")
                else:
                    def _fetch(label: tk.Label = ml, word_: str = w) -> None:
                        en = self._dict_app.find_word(word_) if self._dict_app else None  # type: ignore
                        def _upd() -> None:
                            if label.winfo_exists():
                                label.config(text=(getattr(en, "short_translation", "") or "—") if en else "—")
                        self.root.after(0, _upd)
                    threading.Thread(target=_fetch, daemon=True).start()

                # Border glow-flash on flip
                def _flash(step: int = 0, on: bool = True) -> None:
                    if not c.winfo_exists():
                        return
                    c.config(highlightbackground="white" if on else hv)
                    if step < 5:
                        self.root.after(80, _flash, step + 1, not on)  # type: ignore
                _flash()

            # Hover — slight padding grow (scale illusion)
            def _card_enter(e: object, c: tk.Frame = card, clr: str = base, hv: str = hover) -> None:
                c.config(bg=hv, pady=24)
                for wg in c.winfo_children():
                    try:
                        wg.config(bg=hv)
                    except Exception:
                        pass

            def _card_leave(e: object, c: tk.Frame = card, clr: str = base) -> None:
                c.config(bg=clr, pady=20)
                for wg in c.winfo_children():
                    try:
                        wg.config(bg=clr)
                    except Exception:
                        pass

            card.bind("<Enter>",    _card_enter)
            card.bind("<Leave>",    _card_leave)
            card.bind("<Button-1>", _flip)
            for ch in card.winfo_children():
                ch.bind("<Button-1>", _flip)

        for i, w in enumerate(words):
            self.root.after(i * 110, lambda i_=i, w_=w: _make_card(i_, w_))  # type: ignore

        # Bottom buttons
        btn_row = tk.Frame(parent, bg=C["chat_bg"])
        btn_row.pack(side="bottom", fill="x", padx=40, pady=10)
        sh = tk.Label(btn_row, text="🃏  Xáo bài mới", font=(FONT, 11, "bold"),
                      bg=C["accent"], fg="white", padx=20, pady=8, cursor="hand2")
        sh.pack(side="left")
        sh.bind("<Button-1>", lambda e: self._show_page("wotd"))
        self._bind_hover(sh, C["accent"], C["accent2"])
        self._bind_click_flash(sh, C["accent"])

    # ══════════════════════════════════════════════════════════════════════════
    # Page: History
    # ══════════════════════════════════════════════════════════════════════════

    def _build_history_page(self, parent: tk.Frame) -> None:  # type: ignore
        self._page_header(parent, "📜  Lịch Sử Tra Từ", C["text_sub"])
        _ensure_file(HISTORY_PATH)
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                raw = [l.strip() for l in f if l.strip()]
            lines = list(dict.fromkeys(reversed(raw)))[:30]
        except Exception:
            lines = []

        body = tk.Frame(parent, bg=C["chat_bg"])
        body.pack(fill="both", expand=True, padx=30, pady=10)

        if not lines:
            tk.Label(body, text="✦ Chưa có lịch sử.\nHãy tra một từ để bắt đầu!",
                     font=(FONT, 12), bg=C["chat_bg"], fg=C["text_dim"]).pack(pady=60)
        else:
            for i, word in enumerate(lines):
                row = tk.Frame(
                    body, bg=C["bubble_ai"], pady=10, padx=16,
                    highlightthickness=1, highlightbackground=C["border"],
                    cursor="hand2",
                )
                row.pack(fill="x", pady=4)
                tk.Label(row, text=f"{i+1:02d}.", font=(FONT, 10),
                         bg=C["bubble_ai"], fg=C["text_dim"]).pack(side="left", padx=(0, 8))
                tk.Label(row, text=word, font=(FONT, 13, "bold"),
                         bg=C["bubble_ai"], fg=C["text_main"]).pack(side="left")
                rdo = tk.Label(row, text="↗ Tra lại", font=(FONT, 9),
                               bg=C["bubble_ai"], fg=C["accent"], cursor="hand2")
                rdo.pack(side="right", padx=8)

                def _redo(w: str = word) -> None:
                    self._show_page("chat")
                    self.root.after(120, lambda: (self._search_var.set(w), self._on_search()))  # type: ignore

                rdo.bind("<Button-1>", lambda e, cb=_redo: cb())
                self._bind_hover(row, C["bubble_ai"], C["sidebar_h"])

        clr = tk.Label(body, text="🗑  Xóa lịch sử", font=(FONT, 10),
                       bg=C["chat_bg"], fg=C["red"], cursor="hand2", pady=12)
        clr.pack()

        def _clear_hist() -> None:
            if messagebox.askyesno("Xác nhận", "Xóa toàn bộ lịch sử tra từ?"):
                open(HISTORY_PATH, "w").close()
                self._history.clear()
                self._show_page("history")

        clr.bind("<Button-1>", lambda e: _clear_hist())

    # ══════════════════════════════════════════════════════════════════════════
    # Page: Settings
    # ══════════════════════════════════════════════════════════════════════════

    def _build_settings_page(self, parent: tk.Frame) -> None:  # type: ignore
        self._page_header(parent, "⚙️  Cài Đặt", C["text_sub"])
        body = tk.Frame(parent, bg=C["chat_bg"])
        body.pack(fill="both", expand=True, padx=40, pady=20)

        def _section(txt: str) -> None:
            tk.Label(body, text=txt, font=(FONT, 11, "bold"),
                     bg=C["chat_bg"], fg=C["accent"]).pack(anchor="w", pady=(18, 4))
            tk.Frame(body, bg=C["border"], height=1).pack(fill="x")

        _section("📦 Dữ liệu")

        def _clear_cache() -> None:
            if messagebox.askyesno("Xác nhận", "Xóa cache sẽ buộc tải lại từ API. Tiếp tục?"):
                for p in [DATA_PATH, INDEX_PATH]:
                    if os.path.exists(p):
                        os.remove(p)
                messagebox.showinfo("Hoàn tất", "Cache đã xóa. Khởi lại app để hoàn tất.")

        self._settings_btn(body, "🗑  Xóa Cache (Làm mới dữ liệu)", _clear_cache)

        _section("📖 Sổ tay")

        def _clear_bm() -> None:
            if messagebox.askyesno("Xác nhận", "Xóa toàn bộ sổ tay vĩnh viễn?"):
                open(BOOKMARKS_PATH, "w").close()
                messagebox.showinfo("Hoàn tất", "Sổ tay đã xóa sạch.")

        self._settings_btn(body, "🗑  Xóa sạch Sổ tay", _clear_bm)

        _section("ℹ️ Thông tin")
        tk.Label(
            body,
            text="AI Dictionary v3.2  ·  Free Dictionary API  ·  O(log n) Cache",
            font=(FONT, 10), bg=C["chat_bg"], fg=C["text_dim"], justify="left",
        ).pack(anchor="w", pady=8)

    def _settings_btn(self, parent: tk.Frame, text: str, cmd: Callable) -> None:  # type: ignore
        btn = tk.Label(
            parent, text=text, font=(FONT, 11),
            bg=C["bubble_ai"], fg=C["text_main"],
            padx=16, pady=10, anchor="w", cursor="hand2",
        )
        btn.pack(fill="x", pady=4)
        btn.bind("<Button-1>", lambda e: cmd())
        self._bind_hover(btn, C["bubble_ai"], C["sidebar_h"])
        self._bind_click_flash(btn, C["bubble_ai"])

    # ══════════════════════════════════════════════════════════════════════════
    # Shared: page header
    # ══════════════════════════════════════════════════════════════════════════

    def _page_header(self, parent: tk.Frame, title: str, color: str) -> None:  # type: ignore
        h = tk.Frame(parent, bg=C["bg"], pady=12)
        h.pack(fill="x", padx=18)
        tk.Label(h, text=title, font=(FONT, 16, "bold"),
                 bg=C["bg"], fg=color).pack(side="left")
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")

    # ══════════════════════════════════════════════════════════════════════════
    # Backend
    # ══════════════════════════════════════════════════════════════════════════

    def _init_backend(self) -> None:
        self._words = _load_words_list()
        self._dict_app = DictionaryApp(DATA_PATH, INDEX_PATH)
        n = self._dict_app.total_words_cached()
        self.root.after(0, lambda: self._add_ai_bubble(
            f"✅ Hệ thống sẵn sàng!\n📦 Cache: **{n:,} từ** | 🌐 Free Dictionary API: Online"
        ))
        _ensure_file(HISTORY_PATH)
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                self._history = [l.strip() for l in f if l.strip()]
        except Exception:
            self._history = []

    # ══════════════════════════════════════════════════════════════════════════
    # Animation helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _bind_hover(self, w: tk.Widget, normal: str, hover: str) -> None:  # type: ignore
        w.bind("<Enter>", lambda e: w.config(bg=hover))   # type: ignore
        w.bind("<Leave>", lambda e: w.config(bg=normal))  # type: ignore

    def _bind_click_flash(self, w: tk.Widget, normal: str) -> None:  # type: ignore
        """Darkens widget on press, restores on release."""
        w.bind("<ButtonPress-1>",   lambda e: w.config(bg="#090910"))   # type: ignore
        w.bind("<ButtonRelease-1>", lambda e: w.config(bg=normal))      # type: ignore

    # — Glow pulse for input border —
    def _start_glow(self, frame: tk.Frame) -> None:  # type: ignore
        self._glow_on = True
        self._do_glow(frame, 0)

    def _stop_glow(self, frame: tk.Frame) -> None:  # type: ignore
        self._glow_on = False
        if self._glow_job:
            try:
                self.root.after_cancel(self._glow_job)  # type: ignore
            except Exception:
                pass
        if frame.winfo_exists():
            frame.config(bg=C["input_bdr"])

    def _do_glow(self, frame: tk.Frame, step: int) -> None:  # type: ignore
        if not self._glow_on or not frame.winfo_exists():
            return
        cols = ["#4C1D95", "#7C3AED", "#8B5CF6", "#7C3AED", "#4C1D95"]
        frame.config(bg=cols[step % len(cols)])
        self._glow_job = self.root.after(120, self._do_glow, frame, step + 1)  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Typing animation
    # ══════════════════════════════════════════════════════════════════════════

    def _animate_typing(self, label: tk.Label, text: str,  # type: ignore
                        index: int = 0, on_complete: Optional[Callable] = None) -> None:
        if not label.winfo_exists():
            return
        step = 3 if len(text) > 50 else 2
        label.config(text=text[: min(index, len(text))])
        self._scroll_to_bottom()
        if index < len(text):
            self.root.after(1, self._animate_typing, label, text, index + step, on_complete)  # type: ignore
        else:
            label.config(text=text)
            if on_complete:
                self.root.after(5, on_complete)  # type: ignore

    # ══════════════════════════════════════════════════════════════════════════
    # Canvas / scroll helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _on_frame_configure(self, event: object = None) -> None:  # type: ignore
        if self._canvas:
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event: object) -> None:  # type: ignore
        if self._canvas and self._chat_window is not None:
            self._canvas.itemconfig(self._chat_window, width=event.width)  # type: ignore

    def _on_mousewheel(self, event: object) -> None:  # type: ignore
        if self._current_page == "chat" and self._canvas:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")  # type: ignore

    def _scroll_to_bottom(self) -> None:
        if self._canvas:
            self.root.update_idletasks()
            self._canvas.yview_moveto(1.0)

    # ══════════════════════════════════════════════════════════════════════════
    # Bubble rendering
    # ══════════════════════════════════════════════════════════════════════════

    def _add_user_bubble(self, text: str) -> None:
        if not self._chat_frame:
            return
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=4)
        row.pack(fill="x", padx=16)
        tk.Frame(row, bg=C["chat_bg"]).pack(side="left", expand=True)
        bubble = tk.Frame(row, bg=C["bubble_user"], padx=16, pady=10)
        bubble.pack(side="right")
        tk.Label(bubble, text=f"🔍  {text}", font=(FONT, 12, "bold"),
                 bg=C["bubble_user"], fg="white",
                 wraplength=420, justify="right").pack()
        self._scroll_to_bottom()

    def _add_ai_bubble(self, text: str) -> None:
        if not self._chat_frame:
            return
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=4)
        row.pack(fill="x", padx=16)
        tk.Label(row, text="🤖", font=(FONT, 16),
                 bg=C["chat_bg"], fg=C["accent"]).pack(side="left", anchor="n", padx=(0, 8), pady=4)
        bubble = tk.Frame(row, bg=C["bubble_ai"], padx=16, pady=10)
        bubble.pack(side="left", fill="x", expand=True)
        lbl = tk.Label(bubble, text="", font=(FONT, 11),
                       bg=C["bubble_ai"], fg=C["text_sub"],
                       wraplength=700, justify="left")
        lbl.pack(anchor="w")
        self._animate_typing(lbl, text.replace("**", "").replace("\\n", "\n"))
        self._scroll_to_bottom()

    def _add_result_bubble(self, entry: LexicalEntry) -> None:
        if not self._chat_frame:
            return
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=6)
        row.pack(fill="x", padx=16)
        tk.Label(row, text="🤖", font=(FONT, 16),
                 bg=C["chat_bg"], fg=C["accent"]).pack(side="left", anchor="n", padx=(0, 8), pady=4)

        bubble = tk.Frame(row, bg=C["bubble_ai"], padx=20, pady=14)
        bubble.pack(side="left", fill="x", expand=True)

        import re
        ipa = entry.uk_ipa or entry.us_ipa
        title = entry.word.lower()
        if ipa:
            title += f" /{re.sub(r'[/\\[\\]\\s]', '', ipa)}/"

        short = getattr(entry, "short_translation", "")
        if not short and entry.senses:
            for s in entry.senses:
                if s.translation:
                    short = s.translation
                    break

        source = getattr(entry, "source", "")

        title_lbl = tk.Label(bubble, text="", font=(FONT, 22, "bold"),
                             bg=C["bubble_ai"], fg=C["text_main"])
        title_lbl.pack(anchor="w", pady=(0, 2))

        src_lbl   = tk.Label(bubble, text="", font=(FONT, 9),
                             bg=C["bubble_ai"], fg=C["text_dim"])
        short_lbl = tk.Label(bubble, text="", font=(FONT, 17, "bold"),
                             bg=C["bubble_ai"], fg=C["green"],
                             wraplength=660, justify="left")

        def stage_4() -> None:
            if not bubble.winfo_exists():
                return
            tk.Frame(bubble, bg="#4A4A8A", height=1).pack(fill="x", pady=10)
            self._animate_senses(bubble, entry, entry.senses)

        def stage_3() -> None:
            if not bubble.winfo_exists():
                return
            if short:
                short_lbl.pack(anchor="w", pady=(8, 4))
                self._animate_typing(short_lbl, short, on_complete=stage_4)
            else:
                stage_4()

        def stage_2() -> None:
            if not bubble.winfo_exists():
                return
            if source:
                src_lbl.pack(anchor="w", pady=(0, 4))
                algo = "⚡ RAM Cache" if "Cache" in source else "🌐 Free API"
                self._animate_typing(src_lbl, algo, on_complete=stage_3)
            else:
                stage_3()

        self._animate_typing(title_lbl, title, on_complete=stage_2)
        self._last_entry = entry

    def _add_not_found_bubble(self, kw: str) -> None:
        if not self._chat_frame:
            return
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=6)
        row.pack(fill="x", padx=16)
        tk.Label(row, text="🤖", font=(FONT, 16),
                 bg=C["chat_bg"], fg=C["accent"]).pack(side="left", anchor="n", padx=(0, 8), pady=4)
        bubble = tk.Frame(row, bg="#2A1515", padx=16, pady=12)
        bubble.pack(side="left", fill="x", expand=True)
        tk.Label(bubble, text=f"❌  Không tìm thấy «{kw}»",
                 font=(FONT, 12, "bold"), bg="#2A1515", fg=C["red"]).pack(anchor="w")
        tk.Label(bubble,
                 text="Từ này chưa có trong từ điển. Thử từ thông dụng khác nhé!",
                 font=(FONT, 10), bg="#2A1515", fg=C["text_dim"],
                 wraplength=620, justify="left").pack(anchor="w", pady=(4, 0))
        self._scroll_to_bottom()

    def _welcome_message(self) -> None:
        if not self._chat_frame:
            return
        row = tk.Frame(self._chat_frame, bg=C["chat_bg"], pady=16)
        row.pack(fill="x", padx=16)
        tk.Label(row, text="🤖", font=(FONT, 22),
                 bg=C["chat_bg"], fg=C["accent"]).pack(side="left", anchor="n", padx=(0, 10))
        b = tk.Frame(row, bg=C["bubble_ai"], padx=20, pady=14)
        b.pack(side="left", fill="x", expand=True)
        tk.Label(b, text="Xin chào! Tôi là AI Từ Điển Anh-Việt 🌟",
                 font=(FONT, 14, "bold"), bg=C["bubble_ai"], fg=C["text_main"]).pack(anchor="w")
        tk.Label(b,
                 text="Gõ một từ tiếng Anh rồi nhấn ➤ hoặc Enter để tra nghĩa.\n\n"
                      "📖 Sổ tay · 💡 Luyện từ · 📜 Lịch sử — có trong thanh bên trái!",
                 font=(FONT, 10), bg=C["bubble_ai"], fg=C["text_dim"],
                 wraplength=660, justify="left").pack(anchor="w", pady=(6, 0))

    # ══════════════════════════════════════════════════════════════════════════
    # Senses / examples rendering (sequential typing chain)
    # ══════════════════════════════════════════════════════════════════════════

    _POS_VI = {
        "noun": "danh từ", "verb": "động từ", "adjective": "tính từ",
        "adverb": "trạng từ", "pronoun": "đại từ", "preposition": "giới từ",
        "conjunction": "liên từ", "interjection": "thán từ",
    }

    def _animate_senses(self, bubble: tk.Frame, entry: LexicalEntry,  # type: ignore
                        senses: list, idx: int = 0) -> None:
        if idx >= len(senses) or not bubble.winfo_exists():
            self._add_save_btn(bubble, entry)
            self._scroll_to_bottom()
            return

        s = senses[idx]
        vi_pos = self._POS_VI.get((s.pos or "").lower(), s.pos or "")
        if vi_pos:
            tk.Label(bubble, text=f"* {vi_pos}", font=(FONT, 10, "bold"),
                     bg=C["bubble_ai"], fg="#5C9BD1").pack(anchor="w", pady=(6, 2))

        def_lbl = tk.Label(bubble, text="", font=(FONT, 11),
                           bg=C["bubble_ai"], fg=C["text_main"],
                           wraplength=660, justify="left")
        def_lbl.pack(anchor="w", padx=(10, 0))

        def on_def_done() -> None:
            def on_tr_done() -> None:
                if s.examples:
                    self._animate_examples(bubble, entry, senses, idx, s.examples, 0)
                else:
                    self._animate_senses(bubble, entry, senses, idx + 1)

            if s.translation:
                tl = tk.Label(bubble, text="", font=(FONT, 10, "italic"),
                              bg=C["bubble_ai"], fg="#A8B5C8",
                              wraplength=660, justify="left")
                tl.pack(anchor="w", padx=(24, 0))
                self._animate_typing(tl, f"({s.translation.strip('() ')})", on_complete=on_tr_done)
            else:
                on_tr_done()

        self._animate_typing(def_lbl, f"+ {s.definition}", on_complete=on_def_done)

    def _animate_examples(self, bubble: tk.Frame, entry: LexicalEntry,  # type: ignore
                          senses: list, si: int, examples: list, ei: int) -> None:
        if ei >= len(examples) or not bubble.winfo_exists():
            self._animate_senses(bubble, entry, senses, si + 1)
            return

        ex = examples[ei]
        en_ex = ex.get("en", "")
        vi_ex = ex.get("vi", "")
        if not en_ex:
            self._animate_examples(bubble, entry, senses, si, examples, ei + 1)
            return

        en_lbl = tk.Label(bubble, text="", font=(FONT, 10, "italic"),
                          bg=C["bubble_ai"], fg=C["text_example"],
                          wraplength=640, justify="left")
        en_lbl.pack(anchor="w", padx=(10, 0))

        def on_en_done() -> None:
            if vi_ex:
                vl = tk.Label(bubble, text="", font=(FONT, 9, "italic"),
                              bg=C["bubble_ai"], fg="#8A9EB1",
                              wraplength=640, justify="left")
                vl.pack(anchor="w", padx=(28, 0))
                self._animate_typing(
                    vl, f"({vi_ex.strip('() ')})",
                    on_complete=lambda: self._animate_examples(bubble, entry, senses, si, examples, ei + 1),
                )
            else:
                self._animate_examples(bubble, entry, senses, si, examples, ei + 1)

        self._animate_typing(en_lbl, f"+ {en_ex}", on_complete=on_en_done)

    def _add_save_btn(self, bubble: tk.Frame, entry: LexicalEntry) -> None:  # type: ignore
        if not bubble.winfo_exists():
            return
        btn = tk.Label(bubble, text="⭐  Lưu vào Sổ tay", font=(FONT, 9, "bold"),
                       bg="#2A2A4A", fg=C["gold"], padx=12, pady=6, cursor="hand2")
        btn.pack(anchor="w", pady=(12, 4))

        def _save() -> None:
            _ensure_file(BOOKMARKS_PATH)
            line = f"{entry.word} - {getattr(entry, 'short_translation', '')}\n"
            with open(BOOKMARKS_PATH, "a", encoding="utf-8") as f:
                f.write(line)
            btn.config(text="✅  Đã lưu", fg=C["green"])

        btn.bind("<Button-1>", lambda e: _save())
        self._bind_hover(btn, "#2A2A4A", "#3A3A5A")

    # ══════════════════════════════════════════════════════════════════════════
    # Search
    # ══════════════════════════════════════════════════════════════════════════

    def _on_search(self, event: object = None) -> None:
        self._hide_listbox()
        kw = self._search_var.get().strip()
        if not kw:
            return
        self._search_var.set("")
        self._add_user_bubble(kw)
        self._add_ai_bubble("⏳ Đang tra cứu...")

        # Save to history
        try:
            _ensure_file(HISTORY_PATH)
            with open(HISTORY_PATH, "a", encoding="utf-8") as f:
                f.write(kw + "\n")
            self._history.append(kw)
        except Exception:
            pass

        def _do() -> None:
            if not self._dict_app:
                return
            e = self._dict_app.find_word(kw)  # type: ignore
            self.root.after(0, self._remove_last_bubble)
            if e:
                self.root.after(0, lambda: self._add_result_bubble(e))
            else:
                self.root.after(0, lambda: self._add_not_found_bubble(kw))

        threading.Thread(target=_do, daemon=True).start()

    def _remove_last_bubble(self) -> None:
        if self._chat_frame:
            ch = self._chat_frame.winfo_children()
            if ch:
                ch[-1].destroy()

    def _clear_chat(self) -> None:
        if self._chat_frame:
            for w in self._chat_frame.winfo_children():
                w.destroy()
        self._last_entry = None
        self._welcome_message()

    # ══════════════════════════════════════════════════════════════════════════
    # Audio
    # ══════════════════════════════════════════════════════════════════════════

    def _on_speak(self, accent: str) -> None:
        if not self._last_entry:
            return
        url = self._last_entry.us_audio if accent == "us" else self._last_entry.uk_audio  # type: ignore
        if url:
            webbrowser.open_new_tab(url)
        else:
            def _fb() -> None:
                try:
                    import pyttsx3  # type: ignore
                    e = pyttsx3.init()
                    e.say(self._last_entry.word)  # type: ignore
                    e.runAndWait()
                except Exception:
                    pass
            threading.Thread(target=_fb, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # Autocomplete
    # ══════════════════════════════════════════════════════════════════════════

    def _show_listbox(self) -> None:
        if not self._entry or not self._listbox_frame:
            return
        x = self._entry.winfo_rootx() - self.root.winfo_rootx()
        y = self._entry.winfo_rooty() - self.root.winfo_rooty() - 130
        w = self._entry.winfo_width()
        self._listbox_frame.place(x=x, y=y, width=w)
        self._listbox_frame.lift()

    def _hide_listbox(self) -> None:
        if self._listbox_frame and self._listbox_frame.winfo_exists():
            self._listbox_frame.place_forget()

    def _on_key_release(self, event: object) -> None:  # type: ignore
        if event.keysym in ("Return", "Down", "Up", "Left", "Right"):  # type: ignore
            return
        kw = self._search_var.get().strip().lower()
        if not kw:
            self._hide_listbox()
            return
        matches = [w for w in self._words if w.startswith(kw)][:7]
        if matches and self._listbox:
            self._listbox.delete(0, tk.END)
            for m in matches:
                self._listbox.insert(tk.END, m)
            self._show_listbox()
        else:
            self._hide_listbox()

    def _on_arrow_down(self, event: object) -> None:  # type: ignore
        if self._listbox_frame and self._listbox_frame.winfo_ismapped() and self._listbox:
            self._listbox.focus()
            self._listbox.selection_set(0)

    def _on_listbox_select(self, event: object) -> None:  # type: ignore
        if not self._listbox:
            return
        sel = self._listbox.curselection()
        if sel:
            word = str(self._listbox.get(int(sel[0])))
            self._search_var.set(word)
            self._hide_listbox()
            if self._entry:
                self._entry.focus()
            self._on_search()

    # ══════════════════════════════════════════════════════════════════════════
    # Run
    # ══════════════════════════════════════════════════════════════════════════

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    DictionaryUI().run()


if __name__ == "__main__":
    main()
