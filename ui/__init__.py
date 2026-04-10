"""
ui — Reusable UI components for ProductPhotoManager
Dark-themed Tkinter widgets with consistent styling.
"""
import tkinter as tk
from utils.constants import C

# ─── Spacing System ──────────────────────────────────────────
SP = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}

# ─── Fonts ───────────────────────────────────────────────────
FONT_TITLE = ("Segoe UI Semibold", 14)
FONT_HEADING = ("Segoe UI Semibold", 10)
FONT_BODY = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO = ("Consolas", 10)
FONT_MONO_LG = ("Consolas", 22, "bold")


def create_card(parent, title=None, padx=SP["lg"], pady=SP["md"]):
    """Surface panel with optional header label. Returns (card_frame, content_frame)."""
    card = tk.Frame(parent, bg=C["surface"], padx=padx, pady=pady,
                    highlightbackground=C["border"], highlightthickness=1)

    if title:
        hdr = tk.Label(card, text=title, font=FONT_HEADING,
                       fg=C["text_dim"], bg=C["surface"], anchor="w")
        hdr.pack(fill="x", pady=(0, SP["sm"]))

    content = tk.Frame(card, bg=C["surface"])
    content.pack(fill="both", expand=True)
    return card, content


def create_button(parent, text, command=None, variant="default", width=None, **kw):
    """Styled button. Variants: default, primary, danger, success, outline, icon."""
    styles = {
        "default":  {"bg": C["surface2"], "fg": C["text"], "abg": C["btn_hover"]},
        "primary":  {"bg": C["accent"],   "fg": "#ffffff", "abg": C["accent_hover"]},
        "danger":   {"bg": C["red"],      "fg": "#ffffff", "abg": "#ef4444"},
        "success":  {"bg": C["green"],    "fg": "#0f1117", "abg": "#22c55e"},
        "outline":  {"bg": C["bg"],       "fg": C["text_dim"], "abg": C["surface2"]},
        "icon":     {"bg": C["surface"],  "fg": C["text_dim"], "abg": C["btn_hover"]},
    }
    s = styles.get(variant, styles["default"])

    btn = tk.Button(
        parent, text=text, font=FONT_SMALL, relief="flat", cursor="hand2",
        bg=s["bg"], fg=s["fg"], activebackground=s["abg"], activeforeground=s["fg"],
        padx=SP["md"], pady=SP["xs"], borderwidth=0,
        command=command, **kw,
    )
    if width:
        btn.configure(width=width)
    return btn


def create_entry(parent, textvariable=None, font=None, width=None, **kw):
    """Dark-themed entry field."""
    return tk.Entry(
        parent, textvariable=textvariable,
        font=font or FONT_BODY,
        bg=C["surface2"], fg=C["text"], insertbackground=C["text"],
        relief="flat", highlightbackground=C["border"], highlightthickness=1,
        highlightcolor=C["accent"],
        width=width, **kw,
    )


def create_badge(parent, text="", bg_color=None, fg_color=None):
    """Small status badge / pill label."""
    return tk.Label(
        parent, text=f"  {text}  ", font=FONT_SMALL,
        fg=fg_color or C["text_dim"], bg=bg_color or C["tag_bg"],
        padx=SP["sm"], pady=2,
    )


def create_separator(parent, orient="horizontal"):
    """Thin line separator."""
    sep = tk.Frame(parent, bg=C["border"],
                   height=1 if orient == "horizontal" else None,
                   width=1 if orient == "vertical" else None)
    return sep
