"""
theme.py — Color palette, fonts, and style helpers
===================================================
Bold Indian tricolor theme — deep navy bg, vivid saffron accents, rich greens.
"""

# ── Palette ───────────────────────────────────────────────────────────────────
BG_DARK    = "#0F1C2E"   # main background — deep midnight navy
BG_CARD    = "#1A2C44"   # card / panel background — rich dark blue
BG_INPUT   = "#162035"   # entry fields — darker navy
BG_HOVER   = "#1E3450"   # hover state

SAFFRON    = "#FF6B00"   # primary accent — vibrant saffron
SAFFRON_LT = "#FF9140"   # lighter saffron
SAFFRON_DK = "#CC5500"   # darker saffron for pressed
GREEN_IND  = "#00A550"   # Indian flag green — bright
GREEN_LT   = "#00CC66"   # lighter green
WHITE_IND  = "#FFFFFF"

TEXT_PRI   = "#F0F4FF"   # primary text — near white, slightly cool
TEXT_SUB   = "#A8BBCC"   # subtle / muted — blue-grey
TEXT_MUTED = "#5C7A96"   # very muted

BORDER     = "#1E3A5F"   # card border
DIVIDER    = "#1A3050"   # horizontal rule

SUCCESS    = "#00C853"
ERROR      = "#FF3B3B"
WARNING    = "#FFB300"
INFO       = "#40AAFF"

PARTY_COLORS = {
    "BJP":       "#FF6B00",
    "INC":       "#19AAED",
    "AAP":       "#4FC3F7",
    "Shiv Sena": "#FFD600",
    "NCP":       "#00E5CC",
}

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONT_FAMILY   = "Segoe UI"
FONT_H1       = (FONT_FAMILY, 22, "bold")
FONT_H2       = (FONT_FAMILY, 17, "bold")
FONT_H3       = (FONT_FAMILY, 14, "bold")
FONT_BODY     = (FONT_FAMILY, 11)
FONT_BOLD     = (FONT_FAMILY, 11, "bold")
FONT_SMALL    = (FONT_FAMILY, 9)
FONT_TINY     = (FONT_FAMILY, 8)
FONT_EMOJI    = (FONT_FAMILY, 28)

# ── Widget defaults ────────────────────────────────────────────────────────────
ENTRY_OPTS = dict(
    bg=BG_INPUT, fg=TEXT_PRI, insertbackground=SAFFRON,
    relief="flat", bd=0, font=FONT_BODY,
    highlightthickness=1, highlightbackground=BORDER,
    highlightcolor=SAFFRON,
)

BTN_PRIMARY = dict(
    bg=SAFFRON, fg="#FFFFFF", activebackground=SAFFRON_LT,
    activeforeground="#FFFFFF", relief="flat", bd=0,
    font=FONT_BOLD, cursor="hand2", padx=18, pady=10,
)

BTN_GHOST = dict(
    bg=BG_CARD, fg=TEXT_SUB, activebackground=BG_HOVER,
    activeforeground=TEXT_PRI, relief="flat", bd=0,
    font=FONT_BODY, cursor="hand2", padx=14, pady=8,
    highlightthickness=1, highlightbackground=BORDER,
    highlightcolor=SAFFRON,
)

BTN_DANGER = dict(
    bg=ERROR, fg="#FFFFFF", activebackground="#CC0000",
    activeforeground="#FFFFFF", relief="flat", bd=0,
    font=FONT_BOLD, cursor="hand2", padx=14, pady=8,
)

LBL_OPTS = dict(bg=BG_DARK, fg=TEXT_PRI, font=FONT_BODY)
