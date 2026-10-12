"""
widgets.py — Reusable Tkinter UI components
============================================
GlassCard, Toast, ProgressBar, ScrollableFrame
"""
import tkinter as tk
from tkinter import ttk
import theme as T


# ── Rounded card frame ────────────────────────────────────────────────────────
class Card(tk.Frame):
    """A dark card with a subtle border."""
    def __init__(self, master, **kw):
        super().__init__(
            master,
            bg=T.BG_CARD,
            highlightthickness=1,
            highlightbackground=T.BORDER,
            **kw,
        )


# ── Scrollable inner frame ────────────────────────────────────────────────────
class ScrollFrame(tk.Frame):
    """A Frame that gets a vertical scrollbar on the right."""
    def __init__(self, master, bg=T.BG_DARK, **kw):
        super().__init__(master, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_configure)
        self.canvas.bind("<Configure>", self._resize_inner)
        # Mouse-wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_configure(self, _):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner(self, e):
        self.canvas.itemconfig(self._win_id, width=e.width)

    def _on_mousewheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")


# ── Toast notification ────────────────────────────────────────────────────────
_toast_win = None

def show_toast(root, message: str, kind: str = "info", duration: int = 2800):
    """
    Display a brief floating notification at the bottom of `root`.
    kind: "success" | "error" | "info" | "warning"
    """
    global _toast_win
    if _toast_win:
        try:
            _toast_win.destroy()
        except Exception:
            pass

    colors = {
        "success": (T.SUCCESS, "#000000"),
        "error":   (T.ERROR,   "#FFFFFF"),
        "warning": (T.WARNING, "#000000"),
        "info":    (T.INFO,    "#FFFFFF"),
    }
    icons = {
        "success": "✔  ",
        "error":   "✖  ",
        "warning": "⚠  ",
        "info":    "ℹ  ",
    }
    bg, fg = colors.get(kind, (T.INFO, "#FFFFFF"))
    icon   = icons.get(kind, "")

    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.configure(bg=bg)

    lbl = tk.Label(
        win, text=icon + message,
        bg=bg, fg=fg,
        font=T.FONT_BOLD,
        padx=20, pady=12,
    )
    lbl.pack()

    # Position — center bottom of root
    root.update_idletasks()
    rx, ry = root.winfo_rootx(), root.winfo_rooty()
    rw, rh = root.winfo_width(), root.winfo_height()
    win.update_idletasks()
    tw, th = win.winfo_width(), win.winfo_height()
    x = rx + (rw - tw) // 2
    y = ry + rh - th - 48
    win.geometry(f"+{x}+{y}")

    _toast_win = win
    root.after(duration, lambda: _safe_destroy(win))


def _safe_destroy(w):
    global _toast_win
    try:
        w.destroy()
    except Exception:
        pass
    if _toast_win is w:
        _toast_win = None


# ── Separator ─────────────────────────────────────────────────────────────────
class Separator(tk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, bg=T.BORDER, height=1, **kw)


# ── Coloured progress bar (Frame-based, no Canvas — avoids Windows grid bug) ──
class ColorBar(tk.Frame):
    """
    Thin horizontal strength bar using nested Frames only.
    Using tk.Canvas inside grid() causes TclError on Windows Python 3.13,
    so we use a plain Frame trough + a fill Frame placed inside it.
    """
    def __init__(self, master, height=6, **kw):
        super().__init__(master, bg=T.BG_INPUT, height=height, **kw)
        self.pack_propagate(False)
        self._fill = tk.Frame(self, bg=T.BG_INPUT, height=height)
        self._fill.place(x=0, y=0, relheight=1, relwidth=0)
        self._pct = 0

    def set(self, pct: int):
        self._pct = max(0, min(pct, 100))
        color = (T.ERROR   if self._pct < 30 else
                 T.WARNING if self._pct < 60 else
                 T.INFO    if self._pct < 80 else
                 T.SUCCESS)
        self._fill.configure(bg=color if self._pct > 0 else T.BG_INPUT)
        self._fill.place(relwidth=self._pct / 100)


# ── Styled entry ──────────────────────────────────────────────────────────────
def styled_entry(master, show="", **kw) -> tk.Entry:
    e = tk.Entry(master, show=show, **{**T.ENTRY_OPTS, **kw})
    return e


# ── Primary button ─────────────────────────────────────────────────────────────
def primary_btn(master, text, command=None, **kw) -> tk.Button:
    return tk.Button(master, text=text, command=command, **{**T.BTN_PRIMARY, **kw})


# ── Ghost button ──────────────────────────────────────────────────────────────
def ghost_btn(master, text, command=None, **kw) -> tk.Button:
    return tk.Button(master, text=text, command=command, **{**T.BTN_GHOST, **kw})


# ── Danger button ─────────────────────────────────────────────────────────────
def danger_btn(master, text, command=None, **kw) -> tk.Button:
    return tk.Button(master, text=text, command=command, **{**T.BTN_DANGER, **kw})


# ── Stat tile ─────────────────────────────────────────────────────────────────
class StatTile(Card):
    def __init__(self, master, label: str, value: str = "0", **kw):
        super().__init__(master, **kw)
        tk.Label(self, text=label, bg=T.BG_CARD, fg=T.TEXT_SUB,
                 font=T.FONT_SMALL).pack(anchor="w", padx=16, pady=(14, 2))
        self.val_lbl = tk.Label(self, text=value, bg=T.BG_CARD, fg=T.SAFFRON,
                                font=(T.FONT_FAMILY, 20, "bold"))
        self.val_lbl.pack(anchor="w", padx=16, pady=(0, 14))

    def set(self, value: str):
        self.val_lbl.configure(text=value)


# ── Admin password dialog ─────────────────────────────────────────────────────
def admin_login_dialog(parent) -> bool:
    """Modal dialog — returns True if credentials match."""
    import database as db
    result = {"ok": False}

    dlg = tk.Toplevel(parent)
    dlg.title("Admin Portal")
    dlg.configure(bg=T.BG_DARK)
    dlg.resizable(False, False)
    dlg.grab_set()

    # Center on parent
    parent.update_idletasks()
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    pw_, ph = parent.winfo_width(), parent.winfo_height()
    dlg.geometry(f"400x420+{px + pw_//2 - 200}+{py + ph//2 - 200}")

    card = Card(dlg)
    card.pack(fill="both", expand=True, padx=20, pady=20)

    tk.Label(card, text="🛡️", bg=T.BG_CARD, font=(T.FONT_FAMILY, 36)).pack(pady=(28, 4))
    tk.Label(card, text="Admin Portal", bg=T.BG_CARD, fg=T.TEXT_PRI, font=T.FONT_H2).pack()
    tk.Label(card, text="Authorized Personnel Only", bg=T.BG_CARD,
             fg=T.TEXT_SUB, font=T.FONT_SMALL).pack(pady=(2, 16))
    Separator(card).pack(fill="x", padx=20, pady=4)

    def field(label, show=""):
        tk.Label(card, text=label, bg=T.BG_CARD, fg=T.TEXT_SUB,
                 font=T.FONT_SMALL).pack(anchor="w", padx=30, pady=(10, 2))
        e = styled_entry(card, show=show)
        e.pack(fill="x", padx=30, ipady=8)
        return e

    u_ent = field("Username")
    u_ent.insert(0, "admin")
    p_ent = field("Password", show="*")

    err_lbl = tk.Label(card, text="", bg=T.BG_CARD, fg=T.ERROR, font=T.FONT_SMALL)
    err_lbl.pack(pady=4)

    hint = tk.Label(card, text="Default:  admin  /  admin123",
                    bg=T.BG_CARD, fg=T.TEXT_MUTED, font=T.FONT_TINY)
    hint.pack(pady=4)

    def _check():
        if u_ent.get().strip() == db.ADMIN_USER and p_ent.get() == db.ADMIN_PASS:
            result["ok"] = True
            dlg.destroy()
        else:
            err_lbl.configure(text="⚠  Invalid credentials")

    p_ent.bind("<Return>", lambda _: _check())
    btn_row = tk.Frame(card, bg=T.BG_CARD)
    btn_row.pack(fill="x", padx=30, pady=16)
    ghost_btn(btn_row, "Cancel", dlg.destroy).pack(side="left")
    primary_btn(btn_row, "Login", _check).pack(side="right")

    dlg.wait_window()
    return result["ok"]
