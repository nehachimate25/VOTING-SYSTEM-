"""
main.py — Bharat Vote (Tkinter Edition)
========================================
Run:  python main.py

Libraries:
  - tkinter   : GUI
  - sqlite3   : database (via database.py)
  - pickle    : vote backup (via database.py)
  - hashlib   : password hashing (via database.py)
  - datetime  : timestamps (via database.py)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import random
from datetime import datetime

import database as db
import theme as T
import widgets as W

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# ═══════════════════════════════════════════════════════════════════════════════
# SPLASH SCREEN
# ═══════════════════════════════════════════════════════════════════════════════
class SplashScreen(tk.Toplevel):
    STEPS = [
        "Loading encryption modules…",
        "Connecting to election database…",
        "Verifying party manifests…",
        "Securing session…",
        "Ready.",
    ]

    def __init__(self, root, on_done):
        super().__init__(root)
        self.on_done = on_done
        self.overrideredirect(True)
        self.configure(bg=T.BG_DARK)
        self.resizable(False, False)

        # Center on screen
        w, h = 540, 320
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        # Flag + title
        tk.Label(self, text="🇮🇳", bg=T.BG_DARK,
                 font=(T.FONT_FAMILY, 54)).pack(pady=(44, 4))
        tk.Label(self, text="BHARAT VOTE", bg=T.BG_DARK, fg=T.SAFFRON,
                 font=(T.FONT_FAMILY, 28, "bold")).pack()
        tk.Label(self, text="Secure Indian Digital Voting System",
                 bg=T.BG_DARK, fg=T.TEXT_SUB, font=T.FONT_BODY).pack(pady=(2, 24))

        # Progress bar (using ttk.Progressbar styled)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Saffron.Horizontal.TProgressbar",
                         troughcolor=T.BG_CARD,
                         background=T.SAFFRON,
                         thickness=6)
        self.pbar = ttk.Progressbar(self, style="Saffron.Horizontal.TProgressbar",
                                    length=400, maximum=100)
        self.pbar.pack(pady=4)

        self.status_lbl = tk.Label(self, text="Initialising…",
                                   bg=T.BG_DARK, fg=T.TEXT_MUTED, font=T.FONT_SMALL)
        self.status_lbl.pack(pady=6)

        self._val = 0
        self._tick()

    def _tick(self):
        if self._val < 100:
            self._val += 2
            self.pbar["value"] = self._val
            idx = min(self._val // 20, len(self.STEPS) - 1)
            self.status_lbl.configure(text=self.STEPS[idx])
            self.after(30, self._tick)
        else:
            self.after(300, self._finish)

    def _finish(self):
        self.destroy()
        self.on_done()


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
class Sidebar(tk.Frame):
    NAV = [
        ("home",     "🏠", "Home"),
        ("register", "📝", "Register"),
        ("login",    "🔐", "Login"),
        ("voting",   "🗳️",  "Vote"),
        ("results",  "📊", "Results"),
        ("admin",    "🛡️",  "Admin"),
    ]

    def __init__(self, master, navigate_cb, **kw):
        super().__init__(master, bg=T.BG_CARD, width=200,
                         highlightthickness=1, highlightbackground=T.BORDER, **kw)
        self.pack_propagate(False)
        self.navigate_cb = navigate_cb
        self._btns = {}

        # Brand
        branding = tk.Frame(self, bg=T.BG_CARD)
        branding.pack(fill="x", padx=18, pady=(28, 4))
        tk.Label(branding, text="🇮🇳", bg=T.BG_CARD, font=(T.FONT_FAMILY, 20)).pack()
        tk.Label(branding, text="BHARAT VOTE", bg=T.BG_CARD, fg=T.SAFFRON,
                 font=(T.FONT_FAMILY, 11, "bold")).pack()

        W.Separator(self).pack(fill="x", padx=16, pady=14)

        # Nav items
        for key, icon, label in self.NAV:
            btn = tk.Button(self, text=f"  {icon}  {label}",
                            bg=T.BG_CARD, fg=T.TEXT_SUB, anchor="w",
                            font=T.FONT_BODY, relief="flat", bd=0,
                            activebackground=T.BG_HOVER, activeforeground=T.TEXT_PRI,
                            cursor="hand2",
                            command=lambda k=key: navigate_cb(k))
            btn.pack(fill="x", padx=10, pady=2, ipady=10)
            self._btns[key] = btn

        # Spacer + user info
        tk.Frame(self, bg=T.BG_CARD).pack(fill="both", expand=True)
        W.Separator(self).pack(fill="x", padx=16)
        self.user_lbl = tk.Label(self, text="Not logged in", bg=T.BG_CARD,
                                  fg=T.TEXT_MUTED, font=T.FONT_TINY, wraplength=160)
        self.user_lbl.pack(padx=14, pady=12)

    def set_active(self, key: str):
        for k, btn in self._btns.items():
            if k == key:
                btn.configure(bg=T.BG_HOVER, fg=T.SAFFRON,
                               font=(T.FONT_FAMILY, 11, "bold"))
            else:
                btn.configure(bg=T.BG_CARD, fg=T.TEXT_SUB, font=T.FONT_BODY)

    def set_user(self, user):
        if user:
            name = user.get("full_name", "")
            vid  = user.get("voter_id", "")
            self.user_lbl.configure(text=f"👤 {name}\n{vid}", fg=T.TEXT_SUB)
        else:
            self.user_lbl.configure(text="Not logged in", fg=T.TEXT_MUTED)


# ═══════════════════════════════════════════════════════════════════════════════
# HOME PAGE
# ═══════════════════════════════════════════════════════════════════════════════
class HomePage(tk.Frame):
    def __init__(self, master, navigate_cb, **kw):
        super().__init__(master, bg=T.BG_DARK, **kw)
        self.navigate_cb = navigate_cb
        self._build()

    def _build(self):
        # ── Hero banner ───────────────────────────────────────────
        banner = tk.Frame(self, bg=T.SAFFRON)
        banner.pack(fill="x")
        banner_inner = tk.Frame(banner, bg=T.SAFFRON)
        banner_inner.pack(padx=60, pady=28)

        flag_title = tk.Frame(banner_inner, bg=T.SAFFRON)
        flag_title.pack()
        tk.Label(flag_title, text="🇮🇳", bg=T.SAFFRON,
                 font=(T.FONT_FAMILY, 52)).pack(side="left", padx=(0, 16))
        title_block = tk.Frame(flag_title, bg=T.SAFFRON)
        title_block.pack(side="left")
        tk.Label(title_block, text="BHARAT VOTE", bg=T.SAFFRON,
                 fg="#FFFFFF", font=(T.FONT_FAMILY, 34, "bold")).pack(anchor="w")
        tk.Label(title_block,
                 text="Secure Digital Voting for Every Indian Citizen",
                 bg=T.SAFFRON, fg="#FFF3E8",
                 font=(T.FONT_FAMILY, 13)).pack(anchor="w", pady=(2, 0))

        # Tricolor accent strip (saffron already above, white, green)
        tk.Frame(self, bg="#FFFFFF", height=5).pack(fill="x")
        tk.Frame(self, bg=T.GREEN_IND, height=5).pack(fill="x")

        # ── Body ──────────────────────────────────────────────────
        body = tk.Frame(self, bg=T.BG_DARK)
        body.pack(fill="both", expand=True, padx=50, pady=24)

        # ── Feature cards ─────────────────────────────────────────
        section_lbl = tk.Label(body, text="Why Bharat Vote?",
                               bg=T.BG_DARK, fg=T.SAFFRON,
                               font=(T.FONT_FAMILY, 13, "bold"))
        section_lbl.pack(anchor="w", pady=(0, 10))

        cards_row = tk.Frame(body, bg=T.BG_DARK)
        cards_row.pack(fill="x", pady=4)
        features = [
            ("🔒", "Secure", "SHA-256 hashed passwords\n& encrypted vote storage", "#FFF3E8", T.SAFFRON),
            ("🗄️", "Persistent", "SQLite DB + Pickle backup\nfor zero data loss", "#EAF5FF", T.INFO),
            ("📊", "Transparent", "Live results with charts\nafter each vote", "#EDFFF4", T.SUCCESS),
            ("⚡", "Fast", "Instant vote recording\nwith datetime timestamps", "#FFFBEA", T.WARNING),
        ]
        for icon, title, desc, accent_bg, accent_fg in features:
            card = W.Card(cards_row)
            card.pack(side="left", fill="both", expand=True, padx=5)
            # Coloured top strip
            tk.Frame(card, bg=accent_fg, height=4).pack(fill="x")
            tk.Label(card, text=icon, bg=T.BG_CARD,
                     font=(T.FONT_FAMILY, 28)).pack(pady=(16, 4))
            tk.Label(card, text=title, bg=T.BG_CARD, fg=accent_fg,
                     font=T.FONT_BOLD).pack()
            tk.Label(card, text=desc, bg=T.BG_CARD, fg=T.TEXT_SUB,
                     font=T.FONT_SMALL, justify="center").pack(pady=(4, 18))

        # ── CTA buttons ───────────────────────────────────────────
        btn_row = tk.Frame(body, bg=T.BG_DARK)
        btn_row.pack(pady=20)
        W.primary_btn(btn_row, "📝  Register to Vote",
                      lambda: self.navigate_cb("register")).pack(side="left", padx=8)
        W.ghost_btn(btn_row, "🔐  Login & Vote",
                    lambda: self.navigate_cb("login")).pack(side="left", padx=8)
        W.ghost_btn(btn_row, "📊  View Results",
                    lambda: self.navigate_cb("results")).pack(side="left", padx=8)

        # ── Live stats strip ──────────────────────────────────────
        stats_lbl = tk.Label(body, text="Live Statistics",
                             bg=T.BG_DARK, fg=T.TEXT_SUB,
                             font=(T.FONT_FAMILY, 10, "bold"))
        stats_lbl.pack(anchor="w", pady=(8, 6))

        self.stats_frame = tk.Frame(body, bg=T.BG_DARK)
        self.stats_frame.pack(fill="x", pady=0)
        self._stat_tiles = {}
        for label in ("Total Registered", "Votes Cast", "Turnout", "Leading Party"):
            t = W.StatTile(self.stats_frame, label)
            t.pack(side="left", fill="both", expand=True, padx=4)
            self._stat_tiles[label] = t

    def refresh(self):
        s = db.get_stats()
        self._stat_tiles["Total Registered"].set(str(s["total_users"]))
        self._stat_tiles["Votes Cast"].set(str(s["total_votes"]))
        self._stat_tiles["Turnout"].set(s["turnout"])
        self._stat_tiles["Leading Party"].set(s["top_party"])


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTER PAGE
# ═══════════════════════════════════════════════════════════════════════════════
class RegisterPage(tk.Frame):
    def __init__(self, master, navigate_cb, **kw):
        super().__init__(master, bg=T.BG_DARK, **kw)
        self.navigate_cb = navigate_cb
        self._build()

    def _build(self):
        # NO ScrollFrame — plain pack layout to avoid Canvas input issues on Windows
        outer = tk.Frame(self, bg=T.BG_DARK)
        outer.place(relx=0.5, rely=0.5, anchor="center")

        card = W.Card(outer)
        card.pack(ipadx=8, ipady=4)

        # ── Header ────────────────────────────────────────────
        tk.Label(card, text="📝  Create Voter Account",
                 bg=T.BG_CARD, fg=T.TEXT_PRI, font=T.FONT_H2).pack(pady=(22, 2))
        tk.Label(card, text="All fields required  ·  Aadhaar 12 digits  ·  Age 18+",
                 bg=T.BG_CARD, fg=T.TEXT_SUB, font=T.FONT_SMALL).pack()
        W.Separator(card).pack(fill="x", padx=24, pady=10)

        # ── Form grid ─────────────────────────────────────────
        form = tk.Frame(card, bg=T.BG_CARD)
        form.pack(padx=32, pady=4, fill="x")
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        def lbl(text, r, c):
            tk.Label(form, text=text, bg=T.BG_CARD, fg=T.TEXT_SUB,
                     font=T.FONT_SMALL).grid(row=r, column=c, sticky="w",
                                             padx=6, pady=(8, 1))

        def ent(r, c, show=""):
            e = W.styled_entry(form, show=show)
            e.grid(row=r, column=c, sticky="ew", padx=6, ipady=7)
            return e

        lbl("Full Name", 0, 0);               self.e_name   = ent(1, 0)
        lbl("Mobile (10 digits)", 0, 1);      self.e_mobile = ent(1, 1)
        lbl("Date of Birth (DD/MM/YYYY)", 2, 0); self.e_dob  = ent(3, 0)
        lbl("Aadhaar Number (12 digits)", 2, 1); self.e_aadhar = ent(3, 1)
        lbl("Password", 4, 0);                self.e_pw     = ent(5, 0, show="*")
        lbl("Confirm Password", 4, 1);        self.e_pw2    = ent(5, 1, show="*")

        self.e_pw.bind("<KeyRelease>", self._pw_strength)

        # Strength bar — rows 6-7 (below password)
        self.strength_bar = W.ColorBar(form, height=5)
        self.strength_bar.grid(row=6, column=0, sticky="ew", padx=6, pady=(4, 0))
        self.strength_lbl = tk.Label(form, text="", bg=T.BG_CARD,
                                     fg=T.TEXT_SUB, font=T.FONT_TINY)
        self.strength_lbl.grid(row=7, column=0, sticky="w", padx=6)

        # Location dropdown — rows 8-9
        lbl("📍 Voting Location / City", 8, 0)
        LOCATIONS = [
            "Ahmednagar", "Akola", "Amravati", "Aurangabad", "Beed",
            "Bhandara", "Buldhana", "Chandrapur", "Dhule", "Gadchiroli",
            "Gondia", "Hingoli", "Jalgaon", "Jalna", "Kolhapur",
            "Latur", "Mumbai City", "Mumbai Suburban", "Nagpur", "Nanded",
            "Nandurbar", "Nashik", "Osmanabad", "Palghar", "Parbhani",
            "Pune", "Raigad", "Ratnagiri", "Sangli", "Satara",
            "Sindhudurg", "Solapur", "Thane", "Wardha", "Washim",
            "Yavatmal"
        ]
        self._loc_var = tk.StringVar(value="Pune")
        loc_menu = ttk.Combobox(form, textvariable=self._loc_var,
                                values=LOCATIONS, state="readonly",
                                font=T.FONT_BODY,
                                style="Dark.TCombobox")
        loc_menu.grid(row=9, column=0, columnspan=2, sticky="ew", padx=6, ipady=8)
        self._loc_var.set("Pune")

        # Show password checkbox
        self._show_var = tk.BooleanVar()
        tk.Checkbutton(form, text="Show passwords", variable=self._show_var,
                       command=self._toggle_show,
                       bg=T.BG_CARD, fg=T.TEXT_SUB, selectcolor=T.BG_INPUT,
                       activebackground=T.BG_CARD, font=T.FONT_SMALL,
                       relief="flat", bd=0
                       ).grid(row=10, column=0, sticky="w", padx=6, pady=6)

        # ── Error label ───────────────────────────────────────
        self.err_lbl = tk.Label(card, text="", bg=T.BG_CARD,
                                fg=T.ERROR, font=T.FONT_SMALL)
        self.err_lbl.pack(pady=(2, 0))

        # ── Buttons ───────────────────────────────────────────
        btn_row = tk.Frame(card, bg=T.BG_CARD)
        btn_row.pack(pady=14, padx=32, fill="x")
        W.ghost_btn(btn_row, "← Login",
                    lambda: self.navigate_cb("login")).pack(side="left")
        W.primary_btn(btn_row, "✔  Register Now",
                      self._register).pack(side="right")

    # ── Helpers ───────────────────────────────────────────────
    def _pw_strength(self, _=None):
        pct = db.password_strength(self.e_pw.get())
        self.strength_bar.set(pct)
        label = ("Weak" if pct < 30 else "Fair" if pct < 60 else
                 "Good" if pct < 80 else "Strong")
        self.strength_lbl.configure(text=f"Strength: {label}")

    def _toggle_show(self):
        show = "" if self._show_var.get() else "*"
        self.e_pw.configure(show=show)
        self.e_pw2.configure(show=show)

    def _set_err(self, msg):
        self.err_lbl.configure(text=f"⚠  {msg}" if msg else "")

    def _register(self):
        name   = self.e_name.get().strip()
        mobile = self.e_mobile.get().strip()
        dob    = self.e_dob.get().strip()
        aadhar = self.e_aadhar.get().strip()
        pw     = self.e_pw.get()
        pw2    = self.e_pw2.get()
        loc    = self._loc_var.get().strip()

        # ── Client-side validation with inline error ──────────
        if not all([name, mobile, dob, aadhar, pw, pw2]):
            self._set_err("Please fill in all fields")
            return
        if pw != pw2:
            self._set_err("Passwords do not match")
            return
        if not loc or loc == "Select your city":
            self._set_err("Please select your voting city/location")
            return
        self._set_err("")

        ok, msg, voter_id = db.register_user(name, mobile, dob, aadhar, pw, loc)
        if ok:
            # Clear form
            for e in (self.e_name, self.e_mobile, self.e_dob,
                      self.e_aadhar, self.e_pw, self.e_pw2):
                e.delete(0, "end")
            self.strength_bar.set(0)
            self.strength_lbl.configure(text="")
            self._loc_var.set("Pune")
            # Show voter ID in a popup
            messagebox.showinfo(
                "Registration Successful ✔",
                f"Welcome, {name}!\n\n"
                f"Your Voter ID is:\n\n  {voter_id}\n\n"
                "Save this — you'll need it to login."
            )
            self.navigate_cb("login")
        else:
            self._set_err(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ═══════════════════════════════════════════════════════════════════════════════
class LoginPage(tk.Frame):
    def __init__(self, master, navigate_cb, on_login, **kw):
        super().__init__(master, bg=T.BG_DARK, **kw)
        self.navigate_cb = navigate_cb
        self.on_login    = on_login
        self._build()

    def _build(self):
        # Center card
        wrapper = tk.Frame(self, bg=T.BG_DARK)
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        card = W.Card(wrapper)
        card.pack(ipadx=10, ipady=6)

        tk.Label(card, text="🔐", bg=T.BG_CARD, font=(T.FONT_FAMILY, 40)).pack(pady=(28, 4))
        tk.Label(card, text="Welcome Back", bg=T.BG_CARD, fg=T.TEXT_PRI,
                 font=T.FONT_H2).pack()
        tk.Label(card, text="Login with your Aadhaar or Voter ID",
                 bg=T.BG_CARD, fg=T.TEXT_SUB, font=T.FONT_SMALL).pack(pady=(2, 14))
        W.Separator(card).pack(fill="x", padx=30, pady=4)

        form = tk.Frame(card, bg=T.BG_CARD)
        form.pack(padx=40, pady=10, fill="x")

        tk.Label(form, text="Aadhaar / Voter ID", bg=T.BG_CARD,
                 fg=T.TEXT_SUB, font=T.FONT_SMALL).pack(anchor="w", pady=(8, 2))
        self.e_id = W.styled_entry(form, width=36)
        self.e_id.pack(fill="x", ipady=8)

        tk.Label(form, text="Password", bg=T.BG_CARD,
                 fg=T.TEXT_SUB, font=T.FONT_SMALL).pack(anchor="w", pady=(12, 2))
        self.e_pw = W.styled_entry(form, show="*", width=36)
        self.e_pw.pack(fill="x", ipady=8)
        self.e_pw.bind("<Return>", lambda _: self._login())

        self._show_var = tk.BooleanVar()
        cb = tk.Checkbutton(form, text="Show password", variable=self._show_var,
                            command=lambda: self.e_pw.configure(
                                show="" if self._show_var.get() else "*"),
                            bg=T.BG_CARD, fg=T.TEXT_SUB, selectcolor=T.BG_CARD,
                            activebackground=T.BG_CARD, font=T.FONT_SMALL,
                            relief="flat", bd=0)
        cb.pack(anchor="w", pady=(6, 0))

        W.primary_btn(form, "Login Securely", self._login).pack(
            fill="x", pady=16, ipady=6)

        reg_row = tk.Frame(card, bg=T.BG_CARD)
        reg_row.pack(pady=(0, 20))
        tk.Label(reg_row, text="Don't have an account?", bg=T.BG_CARD,
                 fg=T.TEXT_SUB, font=T.FONT_SMALL).pack(side="left")
        tk.Button(reg_row, text=" Register here", bg=T.BG_CARD, fg=T.SAFFRON,
                  font=T.FONT_SMALL, relief="flat", bd=0, cursor="hand2",
                  activebackground=T.BG_CARD, activeforeground=T.SAFFRON_LT,
                  command=lambda: self.navigate_cb("register")).pack(side="left")

    def _login(self):
        ident = self.e_id.get().strip()
        pw    = self.e_pw.get()
        if not ident or not pw:
            W.show_toast(self.winfo_toplevel(), "Please enter your credentials", "error")
            return
        user = db.login_user(ident, pw)
        if user:
            W.show_toast(self.winfo_toplevel(),
                         f"Welcome back, {user['full_name']}!", "success")
            self.e_pw.delete(0, "end")
            self.on_login(user)
        else:
            W.show_toast(self.winfo_toplevel(), "Invalid credentials — try again", "error")

    def clear(self):
        self.e_id.delete(0, "end")
        self.e_pw.delete(0, "end")


# ═══════════════════════════════════════════════════════════════════════════════
# VOTING PAGE
# ═══════════════════════════════════════════════════════════════════════════════
class VotingPage(tk.Frame):
    def __init__(self, master, navigate_cb, on_voted, **kw):
        super().__init__(master, bg=T.BG_DARK, **kw)
        self.navigate_cb = navigate_cb
        self.on_voted    = on_voted
        self.user        = None
        self._selected   = None
        self._party_btns = {}
        self._build()

    def _build(self):
        # NO ScrollFrame — direct pack to avoid Windows Canvas input issues
        # Header
        head = tk.Frame(self, bg=T.BG_DARK)
        head.pack(fill="x", padx=40, pady=(20, 4))
        tk.Label(head, text="🗳️  Cast Your Vote", bg=T.BG_DARK, fg=T.TEXT_PRI,
                 font=T.FONT_H1).pack(side="left")
        self.user_lbl = tk.Label(head, text="", bg=T.BG_DARK, fg=T.TEXT_SUB,
                                  font=T.FONT_SMALL)
        self.user_lbl.pack(side="right")

        tk.Label(self, text="Select a party below. Your vote is secret and final.",
                 bg=T.BG_DARK, fg=T.TEXT_SUB, font=T.FONT_BODY).pack(anchor="w", padx=40)

        # Stat strip
        strip = tk.Frame(self, bg=T.BG_DARK)
        strip.pack(fill="x", padx=40, pady=10)
        self.t_voters  = W.StatTile(strip, "Total Voters")
        self.t_votes   = W.StatTile(strip, "Votes Cast")
        self.t_top     = W.StatTile(strip, "Leading Party", "—")
        self.t_turnout = W.StatTile(strip, "Turnout", "0%")
        for t in (self.t_voters, self.t_votes, self.t_top, self.t_turnout):
            t.pack(side="left", fill="both", expand=True, padx=4)

        W.Separator(self).pack(fill="x", padx=40, pady=8)

        # Party cards — 2 columns using grid inside a Frame
        grid_frame = tk.Frame(self, bg=T.BG_DARK)
        grid_frame.pack(padx=40, pady=4, fill="both", expand=True)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)

        for idx, party in enumerate(db.PARTIES):
            card = W.Card(grid_frame)
            card.grid(row=idx // 2, column=idx % 2, padx=8, pady=8, sticky="nsew")

            top = tk.Frame(card, bg=T.BG_CARD)
            top.pack(fill="x", padx=16, pady=(14, 4))
            tk.Label(top, text=party["emoji"], bg=T.BG_CARD,
                     font=(T.FONT_FAMILY, 30)).pack(side="left")
            info = tk.Frame(top, bg=T.BG_CARD)
            info.pack(side="left", padx=10)
            tk.Label(info, text=party["name"], bg=T.BG_CARD, fg=T.TEXT_PRI,
                     font=T.FONT_H3).pack(anchor="w")
            tk.Label(info, text=party["full"], bg=T.BG_CARD, fg=T.TEXT_SUB,
                     font=T.FONT_SMALL).pack(anchor="w")

            tk.Frame(card, bg=party["color"], height=3).pack(fill="x")

            btn = tk.Button(card, text=f"✔  Vote for {party['name']}",
                            bg=party["color"], fg="#FFFFFF",
                            activebackground=party["color"], activeforeground="#FFFFFF",
                            font=T.FONT_BOLD, relief="flat", bd=0, cursor="hand2",
                            padx=12, pady=8,
                            command=lambda p=party["name"]: self._select(p))
            btn.pack(fill="x", padx=16, pady=(6, 14), ipady=3)
            self._party_btns[party["name"]] = btn

    def _select(self, party_name: str):
        self._selected = party_name
        msg = (f"Confirm Your Vote\n\n"
               f"You are about to vote for:\n{party_name}\n\n"
               "This action cannot be undone.")
        if messagebox.askyesno("Confirm Vote", msg, icon="question"):
            self._cast(party_name)

    def _cast(self, party_name: str):
        if not self.user:
            W.show_toast(self.winfo_toplevel(), "Please login first", "error")
            self.navigate_cb("login")
            return
        ok, msg = db.cast_vote(self.user["voter_id"], party_name)
        if ok:
            W.show_toast(self.winfo_toplevel(), "✔ Vote cast successfully!", "success")
            self.on_voted(party_name)
        else:
            W.show_toast(self.winfo_toplevel(), msg, "error")

    def set_user(self, user):
        self.user = user
        self.user_lbl.configure(text=f"Logged in as: {user.get('full_name','')}  |  {user.get('voter_id','')}")
        self._refresh_stats()

    def _refresh_stats(self):
        s = db.get_stats()
        self.t_voters.set(str(s["total_users"]))
        self.t_votes.set(str(s["total_votes"]))
        self.t_top.set(s["top_party"])
        self.t_turnout.set(s["turnout"])


# ═══════════════════════════════════════════════════════════════════════════════
# SUCCESS PAGE
# ═══════════════════════════════════════════════════════════════════════════════
class SuccessPage(tk.Frame):
    def __init__(self, master, navigate_cb, **kw):
        super().__init__(master, bg=T.BG_DARK, **kw)
        self.navigate_cb = navigate_cb
        self._build()

    def _build(self):
        wrapper = tk.Frame(self, bg=T.BG_DARK)
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        card = W.Card(wrapper)
        card.pack(ipadx=10, ipady=6)

        tk.Label(card, text="✅", bg=T.BG_CARD, font=(T.FONT_FAMILY, 72)).pack(pady=(32, 8))
        tk.Label(card, text="Vote Cast Successfully!", bg=T.BG_CARD, fg=T.SUCCESS,
                 font=T.FONT_H1).pack()
        tk.Label(card, text="Your vote has been securely recorded.",
                 bg=T.BG_CARD, fg=T.TEXT_SUB, font=T.FONT_BODY).pack(pady=(4, 16))
        W.Separator(card).pack(fill="x", padx=40, pady=4)

        self.party_lbl = tk.Label(card, text="", bg=T.BG_CARD, fg=T.SAFFRON,
                                   font=T.FONT_H2)
        self.party_lbl.pack(pady=4)
        self.time_lbl = tk.Label(card, text="", bg=T.BG_CARD, fg=T.TEXT_SUB,
                                  font=T.FONT_SMALL)
        self.time_lbl.pack(pady=(0, 16))

        btn_row = tk.Frame(card, bg=T.BG_CARD)
        btn_row.pack(pady=16, padx=40)
        W.ghost_btn(btn_row, "← Home",
                    lambda: self.navigate_cb("home")).pack(side="left", padx=8)
        W.primary_btn(btn_row, "View Live Results 📊",
                      lambda: self.navigate_cb("results")).pack(side="left", padx=8)

    def show_for(self, party: str):
        self.party_lbl.configure(text=f"🗳️  You voted for:  {party}")
        ts = datetime.now().strftime("%d %B %Y  ·  %I:%M %p")
        self.time_lbl.configure(text=f"⏱  Recorded at: {ts}")


# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS PAGE
class ResultsPage(tk.Frame):
    def __init__(self, master, navigate_cb, **kw):
        super().__init__(master, bg=T.BG_DARK, **kw)
        self.navigate_cb = navigate_cb
        self._figures    = []
        self._build()

    def _build(self):
        # Scrollable wrapper
        self._canvas = tk.Canvas(self, bg=T.BG_DARK, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(self._canvas, bg=T.BG_DARK)
        self._win_id = self._canvas.create_window((0, 0), window=inner, anchor="nw")

        inner.bind("<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(self._win_id, width=e.width))
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Header bar
        head = tk.Frame(inner, bg=T.SAFFRON)
        head.pack(fill="x")
        tk.Frame(head, bg=T.SAFFRON, width=20).pack(side="left")
        tk.Label(head, text="LIVE ELECTION RESULTS",
                 bg=T.SAFFRON, fg="#FFFFFF",
                 font=(T.FONT_FAMILY, 18, "bold")).pack(side="left", pady=14)
        W.primary_btn(head, "Refresh", self.refresh).pack(side="right", padx=20, pady=10)
        tk.Frame(inner, bg="#FFFFFF", height=4).pack(fill="x")
        tk.Frame(inner, bg=T.GREEN_IND, height=4).pack(fill="x")

        # Stat tiles
        tile_row = tk.Frame(inner, bg=T.BG_DARK)
        tile_row.pack(fill="x", padx=30, pady=16)
        self.t_voters  = W.StatTile(tile_row, "Total Registered")
        self.t_votes   = W.StatTile(tile_row, "Votes Cast")
        self.t_top     = W.StatTile(tile_row, "Leading Party", "---")
        self.t_turnout = W.StatTile(tile_row, "Voter Turnout", "0%")
        for t in (self.t_voters, self.t_votes, self.t_top, self.t_turnout):
            t.pack(side="left", fill="both", expand=True, padx=5)

        # Charts row (fixed height so matplotlib renders)
        charts_row = tk.Frame(inner, bg=T.BG_DARK)
        charts_row.pack(fill="x", padx=30, pady=(0, 12))

        pie_card = tk.Frame(charts_row, bg=T.BG_CARD,
                            highlightthickness=1, highlightbackground=T.SAFFRON)
        pie_card.pack(side="left", fill="both", expand=True, padx=(0, 6))
        tk.Label(pie_card, text="Vote Share - 3D Pie",
                 bg=T.BG_CARD, fg=T.SAFFRON,
                 font=(T.FONT_FAMILY, 11, "bold")).pack(anchor="w", padx=14, pady=(10, 2))
        tk.Frame(pie_card, bg=T.SAFFRON, height=2).pack(fill="x", padx=14)
        self.pie_frame = tk.Frame(pie_card, bg=T.BG_CARD)
        self.pie_frame.pack(fill="x", padx=4, pady=(4, 8))

        bar_card = tk.Frame(charts_row, bg=T.BG_CARD,
                            highlightthickness=1, highlightbackground=T.GREEN_IND)
        bar_card.pack(side="left", fill="both", expand=True, padx=(6, 0))
        tk.Label(bar_card, text="District vs Party - Stacked Bar",
                 bg=T.BG_CARD, fg=T.GREEN_IND,
                 font=(T.FONT_FAMILY, 11, "bold")).pack(anchor="w", padx=14, pady=(10, 2))
        tk.Frame(bar_card, bg=T.GREEN_IND, height=2).pack(fill="x", padx=14)
        self.bar_frame = tk.Frame(bar_card, bg=T.BG_CARD)
        self.bar_frame.pack(fill="x", padx=4, pady=(4, 8))

        # Overall ranking
        rank_card = tk.Frame(inner, bg=T.BG_CARD,
                             highlightthickness=1, highlightbackground=T.BORDER)
        rank_card.pack(fill="x", padx=30, pady=(0, 12))
        rh = tk.Frame(rank_card, bg=T.BG_CARD)
        rh.pack(fill="x", padx=18, pady=(14, 6))
        tk.Label(rh, text="Overall Vote Distribution",
                 bg=T.BG_CARD, fg=T.TEXT_PRI, font=T.FONT_H3).pack(side="left")
        tk.Label(rh, text="All Districts Combined",
                 bg=T.BG_CARD, fg=T.TEXT_MUTED, font=T.FONT_SMALL).pack(side="right")
        self.bars_frame = tk.Frame(rank_card, bg=T.BG_CARD)
        self.bars_frame.pack(fill="x", padx=18, pady=(0, 16))

        # District breakdown
        tk.Frame(inner, bg=T.SAFFRON, height=2).pack(fill="x", padx=30, pady=(4, 0))
        lh = tk.Frame(inner, bg=T.BG_DARK)
        lh.pack(fill="x", padx=30, pady=(8, 4))
        tk.Label(lh, text="District-wise Breakdown",
                 bg=T.BG_DARK, fg=T.TEXT_PRI, font=T.FONT_H2).pack(side="left")
        self.loc_frame = tk.Frame(inner, bg=T.BG_DARK)
        self.loc_frame.pack(fill="x", padx=30, pady=(0, 8))

        # Audit log
        tk.Frame(inner, bg=T.DIVIDER, height=1).pack(fill="x", padx=30, pady=6)
        log_card = tk.Frame(inner, bg=T.BG_CARD,
                            highlightthickness=1, highlightbackground=T.BORDER)
        log_card.pack(fill="x", padx=30, pady=(0, 24))
        tk.Label(log_card, text="Pickle Audit Log (last 8 votes)",
                 bg=T.BG_CARD, fg=T.TEXT_PRI, font=T.FONT_H3).pack(
            anchor="w", padx=18, pady=(14, 4))
        self.log_frame = tk.Frame(log_card, bg=T.BG_CARD)
        self.log_frame.pack(fill="x", padx=18, pady=(0, 14))

    def _close_figs(self):
        for fig in self._figures:
            try:
                plt.close(fig)
            except Exception:
                pass
        self._figures.clear()

    def _embed(self, fig, frame):
        for w in frame.winfo_children():
            w.destroy()
        fc = FigureCanvasTkAgg(fig, master=frame)
        fc.draw()
        fc.get_tk_widget().pack(fill="both", expand=True)
        return fc

    def _draw_pie(self, results):
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        import matplotlib.patches as mpatches

        parties = db.PARTIES
        sizes   = [max(results.get(p["name"], 0), 0) for p in parties]
        colors  = [p["color"] for p in parties]
        labels  = [p["name"] for p in parties]
        emojis  = [p["emoji"] for p in parties]
        total   = sum(sizes)

        fig = plt.Figure(figsize=(5.2, 3.6), dpi=88)
        fig.patch.set_facecolor(T.BG_CARD)
        self._figures.append(fig)
        ax = fig.add_subplot(111, projection="3d")
        ax.set_facecolor(T.BG_CARD)

        if total == 0:
            ax.text2D(0.5, 0.5, "No votes cast yet",
                      transform=ax.transAxes,
                      ha="center", va="center",
                      color=T.TEXT_MUTED, fontsize=13)
        else:
            z_bot, z_top = 0.0, 0.22
            N = 60
            theta1 = 0.0
            for i, (size, color) in enumerate(zip(sizes, colors)):
                if size == 0:
                    continue
                frac   = size / total
                theta2 = theta1 + frac * 2 * np.pi
                n      = max(int(frac * N), 4)
                theta  = np.linspace(theta1, theta2, n)
                cx     = np.cos(theta)
                cy     = np.sin(theta)

                # Top face
                xst = np.concatenate([[0], cx, [0]])
                yst = np.concatenate([[0], cy, [0]])
                zst = np.full_like(xst, z_top)
                ax.add_collection3d(Poly3DCollection(
                    [list(zip(xst, yst, zst))],
                    facecolors=color, edgecolors="none", alpha=1.0, zorder=3))

                # Bottom face
                zsb = np.full_like(xst, z_bot)
                ax.add_collection3d(Poly3DCollection(
                    [list(zip(xst, yst, zsb))],
                    facecolors=color, edgecolors="none", alpha=0.45, zorder=1))

                # Side walls
                for j in range(len(theta) - 1):
                    side = [(cx[j], cy[j], z_bot), (cx[j+1], cy[j+1], z_bot),
                            (cx[j+1], cy[j+1], z_top), (cx[j], cy[j], z_top)]
                    ax.add_collection3d(Poly3DCollection(
                        [side], facecolors=color, edgecolors="none", alpha=0.78, zorder=2))

                # Label
                mid = (theta1 + theta2) / 2
                pct = frac * 100
                if pct >= 4:
                    ax.text(0.62 * np.cos(mid), 0.62 * np.sin(mid), z_top + 0.07,
                            "%s\n%.1f%%" % (labels[i], pct),
                            ha="center", va="bottom",
                            color="#FFFFFF", fontsize=7.5, fontweight="bold", zorder=10)
                theta1 = theta2

        patches = [mpatches.Patch(color=p["color"], label="%s %s" % (p["emoji"], p["name"]))
                   for p in parties]
        ax.legend(handles=patches, loc="upper left", fontsize=7,
                  framealpha=0.35, facecolor=T.BG_CARD,
                  edgecolor=T.BORDER, labelcolor=T.TEXT_PRI)

        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-1.3, 1.3)
        ax.set_zlim(0, 0.55)
        ax.set_axis_off()
        ax.view_init(elev=28, azim=-55)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

        self._embed(fig, self.pie_frame)

    def _draw_stacked_bar(self, loc_results, results):
        import matplotlib.patches as mpatches

        parties = db.PARTIES
        p_names = [p["name"] for p in parties]
        colors  = [p["color"] for p in parties]

        if loc_results:
            locations = sorted(
                [loc for loc, pv in loc_results.items() if sum(pv.values()) > 0])
        else:
            locations = []

        if not locations:
            locations   = ["All Districts"]
            loc_results = {"All Districts": results}

        n      = len(locations)
        fig_h  = max(3.6, 0.38 * n + 1.4)
        fig    = plt.Figure(figsize=(5.2, fig_h), dpi=88)
        fig.patch.set_facecolor(T.BG_CARD)
        self._figures.append(fig)
        ax = fig.add_subplot(111)
        ax.set_facecolor(T.BG_CARD)

        y_pos = np.arange(n)
        lefts = np.zeros(n)
        bar_h = 0.62

        for party, color in zip(p_names, colors):
            vals = np.array([loc_results[loc].get(party, 0)
                             for loc in locations], dtype=float)
            ax.barh(y_pos, vals, left=lefts, height=bar_h,
                    color=color, label=party, alpha=0.93,
                    edgecolor=T.BG_DARK, linewidth=0.4)
            for j, (v, l) in enumerate(zip(vals, lefts)):
                if v >= 1:
                    ax.text(l + v / 2, y_pos[j], str(int(v)),
                            ha="center", va="center",
                            color="#FFFFFF", fontsize=7, fontweight="bold")
            lefts += vals

        ax.set_yticks(y_pos)
        ax.set_yticklabels(locations, color=T.TEXT_PRI, fontsize=8)
        ax.set_xlabel("Votes", color=T.TEXT_SUB, fontsize=9)
        ax.tick_params(axis="x", colors=T.TEXT_SUB, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(T.BORDER)
        ax.grid(axis="x", linestyle="--", alpha=0.2, color=T.TEXT_MUTED)
        ax.set_axisbelow(True)

        patches = [mpatches.Patch(color=p["color"], label=p["name"]) for p in parties]
        leg = ax.legend(handles=patches, loc="lower right", fontsize=7,
                        ncol=2, framealpha=0.4, facecolor=T.BG_CARD,
                        edgecolor=T.BORDER, labelcolor=T.TEXT_PRI)

        fig.subplots_adjust(left=0.22, right=0.97, top=0.95, bottom=0.12)
        self._embed(fig, self.bar_frame)

    def _make_party_bar(self, parent, party, count, pct, rank=0):
        medals = ["1st", "2nd", "3rd", "4th", "5th"]
        bg = "#1E3A20" if rank == 0 and count > 0 else T.BG_CARD
        row = tk.Frame(parent, bg=bg)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=medals[min(rank, 4)], bg=bg,
                 fg=T.TEXT_MUTED, font=T.FONT_TINY, width=4).pack(side="left", padx=(4, 2))
        tk.Label(row, text="%s %s" % (party["emoji"], party["name"]),
                 bg=bg, fg=T.TEXT_PRI, font=T.FONT_BOLD,
                 width=12, anchor="w").pack(side="left")
        bar_bg = tk.Frame(row, bg=T.BG_INPUT, height=24)
        bar_bg.pack(side="left", fill="x", expand=True, padx=(4, 8))
        bar_bg.pack_propagate(False)
        if pct > 0:
            bar_fill = tk.Frame(bar_bg, bg=party["color"], height=24)
            bar_fill.place(relx=0, rely=0, relwidth=min(pct / 100, 1.0), relheight=1)
            tk.Label(bar_fill, text="%.1f%%" % pct, bg=party["color"],
                     fg="white", font=T.FONT_TINY).place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(row, text="%d votes" % count, bg=bg,
                 fg=T.TEXT_SUB, font=T.FONT_SMALL, width=10, anchor="w").pack(side="left")

    def refresh(self):
        self._close_figs()

        s           = db.get_stats()
        results     = s["results"]
        loc_results = s.get("location_results", {})
        total       = max(sum(results.values()), 1)

        self.t_voters.set(str(s["total_users"]))
        self.t_votes.set(str(s["total_votes"]))
        self.t_top.set(s["top_party"])
        self.t_turnout.set(s["turnout"])

        self._draw_pie(results)
        self._draw_stacked_bar(loc_results, results)

        # Overall ranking bars
        for w in self.bars_frame.winfo_children():
            w.destroy()
        sorted_p = sorted(db.PARTIES, key=lambda p: results.get(p["name"], 0), reverse=True)
        for rank, party in enumerate(sorted_p):
            count = results.get(party["name"], 0)
            pct   = count / total * 100
            self._make_party_bar(self.bars_frame, party, count, pct, rank=rank)

        # District breakdown
        for w in self.loc_frame.winfo_children():
            w.destroy()
        active = {loc: pv for loc, pv in loc_results.items() if sum(pv.values()) > 0}
        if not active:
            tk.Label(self.loc_frame,
                     text="No district data yet. Cast votes to see breakdown.",
                     bg=T.BG_DARK, fg=T.TEXT_MUTED, font=T.FONT_SMALL).pack(pady=8)
        else:
            for loc_name in sorted(active.keys()):
                pv        = active[loc_name]
                loc_total = max(sum(pv.values()), 1)
                loc_cast  = sum(pv.values())

                card = tk.Frame(self.loc_frame, bg=T.BG_CARD,
                                highlightthickness=1, highlightbackground=T.BORDER)
                card.pack(fill="x", pady=5)
                lh = tk.Frame(card, bg=T.BG_CARD)
                lh.pack(fill="x", padx=16, pady=(10, 6))
                tk.Label(lh, text="📍 %s" % loc_name, bg=T.BG_CARD,
                         fg=T.TEXT_PRI, font=T.FONT_H3).pack(side="left")
                bf = tk.Frame(lh, bg=T.BG_CARD)
                bf.pack(side="right")
                tk.Label(bf, text="%d votes" % loc_cast,
                         bg=T.BG_INPUT, fg=T.TEXT_SUB,
                         font=T.FONT_SMALL, padx=8, pady=2).pack(side="left", padx=3)
                if loc_cast > 0:
                    top_p   = max(pv, key=pv.get)
                    top_pct = pv[top_p] / loc_total * 100
                    tk.Label(bf, text="Top: %s %.0f%%" % (top_p, top_pct),
                             bg="#2A1A00", fg=T.SAFFRON,
                             font=T.FONT_SMALL, padx=8, pady=2).pack(side="left", padx=3)

                tk.Frame(card, bg=T.DIVIDER, height=1).pack(fill="x", padx=16)
                bars_area = tk.Frame(card, bg=T.BG_CARD)
                bars_area.pack(fill="x", padx=16, pady=(6, 12))
                for rank, party in enumerate(sorted(
                        db.PARTIES, key=lambda p: pv.get(p["name"], 0), reverse=True)):
                    count = pv.get(party["name"], 0)
                    pct   = count / loc_total * 100
                    self._make_party_bar(bars_area, party, count, pct, rank=rank)

        # Audit log
        for w in self.log_frame.winfo_children():
            w.destroy()
        logs = db.get_pickle_log()[-8:]
        if not logs:
            tk.Label(self.log_frame, text="No votes recorded yet.",
                     bg=T.BG_CARD, fg=T.TEXT_MUTED, font=T.FONT_SMALL).pack()
        else:
            hdr = tk.Frame(self.log_frame, bg=T.BG_CARD)
            hdr.pack(fill="x", pady=(0, 4))
            for txt, w in [("Voter ID", 25), ("Party", 14), ("Timestamp", 28)]:
                tk.Label(hdr, text=txt, bg=T.BG_CARD, fg=T.TEXT_MUTED,
                         font=T.FONT_TINY, width=w, anchor="w").pack(side="left", padx=4)
            for log in logs:
                r = tk.Frame(self.log_frame, bg=T.BG_INPUT)
                r.pack(fill="x", pady=2)
                for txt, w in [(log["voter_id"], 25), (log["party"], 14), (log["voted_at"], 28)]:
                    tk.Label(r, text=txt, bg=T.BG_INPUT, fg=T.TEXT_PRI,
                             font=T.FONT_SMALL, width=w, anchor="w").pack(
                        side="left", padx=6, pady=4)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN PAGE
# ═══════════════════════════════════════════════════════════════════════════════
class AdminPage(tk.Frame):
    def __init__(self, master, navigate_cb, **kw):
        super().__init__(master, bg=T.BG_DARK, **kw)
        self.navigate_cb = navigate_cb
        self._build()

    def _build(self):
        # Header
        head = tk.Frame(self, bg=T.BG_DARK)
        head.pack(fill="x", padx=40, pady=(24, 4))
        tk.Label(head, text="🛡️  Admin Dashboard", bg=T.BG_DARK, fg=T.TEXT_PRI,
                 font=T.FONT_H1).pack(side="left")

        btn_bar = tk.Frame(head, bg=T.BG_DARK)
        btn_bar.pack(side="right")
        W.primary_btn(btn_bar, "🔄 Refresh", self.refresh).pack(side="left", padx=4)
        W.ghost_btn(btn_bar, "📤 Export CSV", self._export).pack(side="left", padx=4)
        W.danger_btn(btn_bar, "🗑️  Reset Votes", self._reset).pack(side="left", padx=4)

        # Search
        search_row = tk.Frame(self, bg=T.BG_DARK)
        search_row.pack(fill="x", padx=40, pady=6)
        tk.Label(search_row, text="Search:", bg=T.BG_DARK, fg=T.TEXT_SUB,
                 font=T.FONT_BODY).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter())
        W.styled_entry(search_row, textvariable=self.search_var,
                       width=30).pack(side="left", padx=8, ipady=6)

        W.Separator(self).pack(fill="x", padx=40, pady=8)

        # Table
        tbl_frame = tk.Frame(self, bg=T.BG_DARK)
        tbl_frame.pack(fill="both", expand=True, padx=40, pady=(0, 20))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.Treeview",
                        background=T.BG_CARD,
                        fieldbackground=T.BG_CARD,
                        foreground=T.TEXT_PRI,
                        rowheight=30,
                        font=T.FONT_BODY)
        style.configure("Dark.Treeview.Heading",
                        background=T.BG_DARK,
                        foreground=T.TEXT_SUB,
                        font=T.FONT_SMALL)
        style.map("Dark.Treeview",
                  background=[("selected", T.BG_HOVER)],
                  foreground=[("selected", T.SAFFRON)])

        cols = ("Name", "Mobile", "Voter ID", "Voted?", "Party", "Voted At")
        self.tree = ttk.Treeview(tbl_frame, columns=cols, show="headings",
                                  style="Dark.Treeview")
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130, anchor="w")
        self.tree.column("Name", width=160)

        vsb = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # Delete selected
        W.danger_btn(self, "Delete Selected User", self._delete).pack(
            anchor="e", padx=40, pady=8)

        self._all_users = []

    def refresh(self):
        self._all_users = db.get_all_users()
        self._populate(self._all_users)

    def _filter(self):
        q = self.search_var.get().lower()
        filtered = [u for u in self._all_users
                    if q in u.get("full_name", "").lower()
                    or q in u.get("voter_id", "").lower()
                    or q in u.get("aadhar", "")]
        self._populate(filtered)

    def _populate(self, users):
        self.tree.delete(*self.tree.get_children())
        for u in users:
            voted = "✔ Yes" if u.get("has_voted") else "No"
            self.tree.insert("", "end", iid=u["voter_id"], values=(
                u.get("full_name", ""),
                u.get("mobile", ""),
                u.get("voter_id", ""),
                voted,
                u.get("voted_party") or "—",
                db.fmt_dt(u.get("voted_at") or ""),
            ))

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            W.show_toast(self.winfo_toplevel(), "Select a user first", "warning")
            return
        if messagebox.askyesno("Confirm Delete",
                               f"Delete {len(sel)} user(s)? This cannot be undone."):
            for voter_id in sel:
                db.delete_user(voter_id)
            self.refresh()
            W.show_toast(self.winfo_toplevel(), "User(s) deleted", "success")

    def _reset(self):
        if messagebox.askyesno("Reset All Votes",
                               "This will clear ALL votes and reset has_voted for every user.\n\nAre you sure?",
                               icon="warning"):
            db.reset_all_votes()
            self.refresh()
            W.show_toast(self.winfo_toplevel(), "All votes have been reset", "info")

    def _export(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")],
            title="Export Voter Data")
        if path:
            db.export_csv(path)
            W.show_toast(self.winfo_toplevel(), f"Exported to {path}", "success")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════
class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()   # hidden until splash done
        self.title("Bharat Vote  ·  Secure Indian Digital Voting System")
        self.geometry("1200x760")
        self.minsize(1000, 680)
        self.configure(bg=T.BG_DARK)

        # ── Global ttk styles for dark theme ───────────────────
        s = ttk.Style(self)
        s.theme_use("default")
        s.configure("Dark.TCombobox",
                     fieldbackground=T.BG_INPUT,
                     background=T.SAFFRON,
                     foreground=T.TEXT_PRI,
                     selectbackground=T.SAFFRON,
                     selectforeground="#FFFFFF",
                     bordercolor=T.BORDER,
                     lightcolor=T.BORDER,
                     darkcolor=T.BORDER,
                     arrowcolor=T.TEXT_PRI,
                     insertcolor=T.TEXT_PRI,
                     relief="flat",
                     padding=(10, 8))
        s.map("Dark.TCombobox",
              fieldbackground=[("readonly", T.BG_INPUT),
                               ("focus",    T.BG_HOVER)],
              foreground=[("readonly", T.TEXT_PRI),
                          ("disabled", T.TEXT_MUTED)],
              bordercolor=[("focus",  T.SAFFRON),
                           ("!focus", T.BORDER)],
              arrowcolor=[("hover",  T.SAFFRON),
                          ("!hover", T.TEXT_SUB)])
        # Dropdown listbox colours
        self.option_add("*TCombobox*Listbox.background",      T.BG_INPUT)
        self.option_add("*TCombobox*Listbox.foreground",      T.TEXT_PRI)
        self.option_add("*TCombobox*Listbox.selectBackground",T.SAFFRON)
        self.option_add("*TCombobox*Listbox.selectForeground","#FFFFFF")
        self.option_add("*TCombobox*Listbox.font",            T.FONT_BODY)
        self.option_add("*TCombobox*Listbox.relief",          "flat")

        self.user = None
        self._idle_after_id = None

        # ── Layout ─────────────────────────────────────────────
        root_h = tk.Frame(self, bg=T.BG_DARK)
        root_h.pack(fill="both", expand=True)

        self.sidebar = Sidebar(root_h, self.navigate)
        self.sidebar.pack(side="left", fill="y")

        # Vertical divider
        tk.Frame(root_h, bg=T.BORDER, width=1).pack(side="left", fill="y")

        # Page container
        self.page_container = tk.Frame(root_h, bg=T.BG_DARK)
        self.page_container.pack(side="left", fill="both", expand=True)

        # Topbar
        self.topbar = self._make_topbar()
        self.topbar.pack(side="top", fill="x")
        tk.Frame(self.page_container, bg=T.BORDER, height=1).pack(fill="x")

        # Pages (stacked, only one visible at a time)
        self.page_area = tk.Frame(self.page_container, bg=T.BG_DARK)
        self.page_area.pack(fill="both", expand=True)

        self.pages = {
            "home":     HomePage(self.page_area, self.navigate),
            "register": RegisterPage(self.page_area, self.navigate),
            "login":    LoginPage(self.page_area, self.navigate, self._on_login),
            "voting":   VotingPage(self.page_area, self.navigate, self._on_voted),
            "success":  SuccessPage(self.page_area, self.navigate),
            "results":  ResultsPage(self.page_area, self.navigate),
            "admin":    AdminPage(self.page_area, self.navigate),
        }
        for p in self.pages.values():
            p.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._current_page = None
        self.navigate("home")
        self._reset_idle()
        self.bind_all("<Motion>",    lambda _: self._reset_idle())
        self.bind_all("<KeyPress>",  lambda _: self._reset_idle())

    # ── Topbar ────────────────────────────────────────────────────────────────
    def _make_topbar(self):
        bar = tk.Frame(self.page_container, bg=T.BG_CARD,
                       highlightthickness=0)
        inner = tk.Frame(bar, bg=T.BG_CARD)
        inner.pack(fill="x", padx=16, pady=8)

        self.page_title_lbl = tk.Label(inner, text="Home", bg=T.BG_CARD,
                                        fg=T.TEXT_SUB, font=T.FONT_BOLD)
        self.page_title_lbl.pack(side="left")

        self.logout_btn = W.ghost_btn(inner, "Logout", self._logout)
        self.logout_btn.pack(side="right", padx=4)
        self.logout_btn.pack_forget()   # hidden until logged in

        self.user_badge = tk.Label(inner, text="", bg=T.BG_CARD,
                                    fg=T.SAFFRON, font=T.FONT_SMALL)
        self.user_badge.pack(side="right", padx=12)
        return bar

    # ── Navigation ────────────────────────────────────────────────────────────
    _PAGE_NAMES = {
        "home":     "Home",
        "register": "Register",
        "login":    "Login",
        "voting":   "Vote",
        "success":  "Vote Confirmed",
        "results":  "Live Results",
        "admin":    "Admin Dashboard",
    }

    def navigate(self, key: str):
        if key == "admin":
            if not W.admin_login_dialog(self):
                return
            self.pages["admin"].refresh()

        if key == "results":
            self.pages["results"].refresh()

        if key == "home":
            self.pages["home"].refresh()

        if key == "voting":
            if not self.user:
                W.show_toast(self, "Please login first", "error")
                key = "login"
            else:
                self.pages["voting"].set_user(self.user)

        # Show selected page
        page = self.pages.get(key, self.pages["home"])
        if self._current_page:
            self._current_page.lower()
        page.lift()
        self._current_page = page

        self.sidebar.set_active(key)
        self.page_title_lbl.configure(text=self._PAGE_NAMES.get(key, key.title()))

    # ── Auth events ───────────────────────────────────────────────────────────
    def _on_login(self, user):
        self.user = user
        self.sidebar.set_user(user)
        self.user_badge.configure(text=f"👤 {user['full_name']}")
        self.logout_btn.pack(side="right", padx=4)
        if user.get("has_voted"):
            W.show_toast(self, "You have already voted — showing results.", "info")
            self.navigate("results")
        else:
            self.navigate("voting")

    def _on_voted(self, party: str):
        self.pages["success"].show_for(party)
        self.navigate("success")
        # Update user record
        if self.user:
            self.user = db.get_user_by_voter_id(self.user["voter_id"]) or self.user

    def _logout(self):
        self.user = None
        self.sidebar.set_user(None)
        self.user_badge.configure(text="")
        self.logout_btn.pack_forget()
        self.pages["login"].clear()
        W.show_toast(self, "Logged out successfully", "info")
        self.navigate("home")

    # ── Idle auto-logout (5 min) ──────────────────────────────────────────────
    def _reset_idle(self):
        if self._idle_after_id:
            self.after_cancel(self._idle_after_id)
        self._idle_after_id = self.after(5 * 60 * 1000, self._auto_logout)

    def _auto_logout(self):
        if self.user:
            self._logout()
            W.show_toast(self, "Session expired — auto logged out", "info")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    db.init_db()

    root = MainWindow()

    def show_main():
        root.deiconify()

    splash = SplashScreen(root, show_main)

    root.mainloop()


if __name__ == "__main__":
    main()
