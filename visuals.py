"""
OutfitAI — visuals.py
SVG clothing silhouettes + parallel background image fetcher.
No API keys needed. Zero cost.
"""
import re
import threading
import requests


# ── Color helpers ─────────────────────────────────────────────────────────────

COLOR_MAP = {
    "white":   "#F5F5F5", "black":  "#1a1a1a", "navy":    "#1e3a5f",
    "blue":    "#2563eb", "gray":   "#9ca3af", "grey":    "#9ca3af",
    "charcoal":"#374151", "beige":  "#c8a97e", "cream":   "#f5f0e8",
    "brown":   "#6b4226", "tan":    "#c19a6b", "khaki":   "#c3b091",
    "green":   "#2d6a4f", "olive":  "#6b7c45", "red":     "#dc2626",
    "burgundy":"#7f1d1d", "maroon": "#7f1d1d", "pink":    "#f9a8d4",
    "purple":  "#7c3aed", "yellow": "#fbbf24", "orange":  "#f97316",
    "camel":   "#c19a6b", "rust":   "#b45309", "teal":    "#0d9488",
    "lavender":"#c4b5fd", "coral":  "#f87171", "gold":    "#d97706",
    "silver":  "#9ca3af", "denim":  "#1e3a5f",
}

def resolve_color(color_name: str) -> str:
    """Map a color name string to a hex value."""
    return COLOR_MAP.get(color_name.lower().strip(), "#888888")

def darken(hex_color: str, amount: int = 55) -> str:
    """Return a darker version of a hex color for strokes/shadows."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return "#555555"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r2 = max(0, r - amount)
    g2 = max(0, g - amount)
    b2 = max(0, b - amount)
    return f"#{r2:02x}{g2:02x}{b2:02x}"

def bg_for(hex_color: str) -> str:
    """Light background tint for card backgrounds."""
    if hex_color.upper() in ("#F5F5F5", "#FFFFFF"):
        return "#e8e8e8"
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return "#f0f0f0"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r2 = min(255, r + 120)
    g2 = min(255, g + 120)
    b2 = min(255, b + 120)
    return f"#{r2:02x}{g2:02x}{b2:02x}"


# ── SVG clothing shapes ───────────────────────────────────────────────────────

def clothing_svg(shape: str, color_name: str, size: int = 80) -> str:
    """
    Return an inline SVG string for a clothing item.
    shape: one of the keys in SHAPES below.
    color_name: e.g. 'White', 'Navy', 'Black'
    size: pixel size of the SVG
    """
    c = resolve_color(color_name)
    d = darken(c)

    SHAPES = {
        "tshirt": f"""
          <polygon points="15,8 5,28 20,28 20,72 50,72 50,28 65,28 55,8 42,18 28,18"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>""",

        "shirt": f"""
          <polygon points="15,6 5,26 20,26 20,72 50,72 50,26 65,26 55,6 44,16 35,10 26,16"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>
          <line x1="35" y1="10" x2="35" y2="30" stroke="{d}" stroke-width="1.5"/>""",

        "polo": f"""
          <polygon points="15,8 5,28 20,28 20,72 50,72 50,28 65,28 55,8 42,17 28,17"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>
          <rect x="29" y="8" width="12" height="13" rx="2"
            fill="{c}" stroke="{d}" stroke-width="1.5"/>""",

        "sweater": f"""
          <polygon points="15,10 4,32 20,32 20,72 50,72 50,32 66,32 55,10 40,20 30,20"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>
          <rect x="20" y="68" width="30" height="5" rx="1" fill="{d}" opacity="0.5"/>""",

        "hoodie": f"""
          <polygon points="15,8 4,30 20,30 20,72 50,72 50,30 66,30 55,8 40,18 30,18"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>
          <path d="M28,8 Q35,22 42,8" fill="{c}" stroke="{d}" stroke-width="2"/>""",

        "tank": f"""
          <path d="M22,6 L22,72 L48,72 L48,6 Q42,14 35,14 Q28,14 22,6 Z"
            fill="{c}" stroke="{d}" stroke-width="2"/>""",

        "pants": f"""
          <path d="M14,4 L56,4 L52,78 L38,78 L35,48 L32,78 L18,78 Z"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>""",

        "shorts": f"""
          <path d="M14,4 L56,4 L52,50 L38,50 L35,34 L32,50 L18,50 Z"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>""",

        "skirt": f"""
          <path d="M22,4 L48,4 L58,72 L12,72 Z"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>""",

        "leggings": f"""
          <path d="M18,4 L52,4 L48,78 L36,78 L35,48 L34,78 L22,78 Z"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>""",

        "blazer": f"""
          <path d="M10,4 L60,4 L58,72 L40,72 L38,50 L32,50 L30,72 L12,72 Z"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>
          <path d="M10,4 L30,22 L35,10 L40,22 L60,4"
            fill="{c}" stroke="{d}" stroke-width="1.5"/>""",

        "jacket": f"""
          <path d="M12,4 L58,4 L56,72 L40,72 L37,46 L33,46 L30,72 L14,72 Z"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>
          <path d="M12,4 L28,20 L35,8 L42,20 L58,4"
            fill="{c}" stroke="{d}" stroke-width="1.5"/>
          <line x1="35" y1="8" x2="35" y2="72" stroke="{d}" stroke-width="1"/>""",

        "coat": f"""
          <path d="M10,4 L60,4 L60,80 L40,80 L38,54 L32,54 L30,80 L10,80 Z"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>
          <path d="M10,4 L28,18 L35,6 L42,18 L60,4"
            fill="{c}" stroke="{d}" stroke-width="1.5"/>""",

        "dress": f"""
          <path d="M26,4 Q35,2 44,4 L52,26 L62,88 L8,88 L18,26 Z"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>
          <line x1="26" y1="4" x2="18" y2="26" stroke="{d}" stroke-width="1.5"/>
          <line x1="44" y1="4" x2="52" y2="26" stroke="{d}" stroke-width="1.5"/>""",

        "minidress": f"""
          <path d="M26,4 Q35,2 44,4 L54,24 L60,60 L10,60 L16,24 Z"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>""",

        "sneaker": f"""
          <path d="M8,34 Q10,18 30,16 L56,14 Q74,12 76,26 L76,36
                   Q52,44 8,40 Z"
            fill="{c}" stroke="{d}" stroke-width="2"/>
          <path d="M8,36 L76,36 L76,42 Q52,48 8,42 Z" fill="{d}" opacity="0.6"/>
          <path d="M28,16 L30,28" stroke="{d}" stroke-width="1.5"/>
          <path d="M40,14 L42,28" stroke="{d}" stroke-width="1.5"/>""",

        "boot": f"""
          <path d="M22,4 L22,48 Q10,50 10,64 L10,74 L60,74 L60,58
                   Q58,50 44,48 L44,4 Z"
            fill="{c}" stroke="{d}" stroke-width="2" stroke-linejoin="round"/>""",

        "loafer": f"""
          <path d="M10,32 Q12,14 32,12 L52,12 Q68,10 70,24 L70,34
                   Q48,44 10,38 Z"
            fill="{c}" stroke="{d}" stroke-width="2"/>
          <path d="M10,34 L70,34 L70,40 Q48,46 10,42 Z" fill="{d}" opacity="0.6"/>
          <path d="M26,12 Q35,6 44,12" fill="none" stroke="{d}" stroke-width="2"/>""",

        "sandal": f"""
          <path d="M14,36 L66,36 L66,44 Q44,52 14,44 Z"
            fill="{c}" stroke="{d}" stroke-width="2"/>
          <line x1="28" y1="10" x2="28" y2="36" stroke="{c}" stroke-width="6"
            stroke-linecap="round"/>
          <line x1="42" y1="10" x2="42" y2="36" stroke="{c}" stroke-width="6"
            stroke-linecap="round"/>""",

        "belt": f"""
          <rect x="2" y="10" width="60" height="10" rx="3"
            fill="{c}" stroke="{d}" stroke-width="1.5"/>
          <rect x="58" y="6" width="20" height="18" rx="2"
            fill="{c}" stroke="{d}" stroke-width="1.5"/>
          <rect x="63" y="11" width="10" height="8" rx="1" fill="{d}"/>""",

        "watch": f"""
          <rect x="16" y="18" width="18" height="44" rx="8"
            fill="{c}" stroke="{d}" stroke-width="2"/>
          <rect x="18" y="8" width="14" height="12" rx="2"
            fill="{c}" stroke="{d}" stroke-width="1.5"/>
          <rect x="18" y="60" width="14" height="12" rx="2"
            fill="{c}" stroke="{d}" stroke-width="1.5"/>
          <circle cx="25" cy="40" r="7" fill="white" stroke="{d}" stroke-width="1.5"/>
          <line x1="25" y1="40" x2="25" y2="34" stroke="{d}" stroke-width="1.5"/>
          <line x1="25" y1="40" x2="29" y2="40" stroke="{d}" stroke-width="1.5"/>""",

        "bag": f"""
          <rect x="8" y="24" width="54" height="42" rx="6"
            fill="{c}" stroke="{d}" stroke-width="2"/>
          <path d="M20,24 Q20,8 35,8 Q50,8 50,24"
            fill="none" stroke="{d}" stroke-width="2.5"/>
          <line x1="8" y1="40" x2="62" y2="40" stroke="{d}" stroke-width="1"/>""",

        "hat": f"""
          <ellipse cx="35" cy="54" rx="32" ry="8" fill="{c}" stroke="{d}" stroke-width="1.5"/>
          <path d="M18,54 L20,20 Q35,10 50,20 L52,54 Z"
            fill="{c}" stroke="{d}" stroke-width="2"/>""",

        "scarf": f"""
          <path d="M10,20 Q35,10 60,20 L58,34 Q35,24 12,34 Z"
            fill="{c}" stroke="{d}" stroke-width="1.5"/>
          <path d="M55,26 L60,50 Q54,56 50,50 L46,30"
            fill="{c}" stroke="{d}" stroke-width="1.5"/>""",

        "sunglasses": f"""
          <circle cx="22" cy="38" r="14" fill="{c}" stroke="{d}" stroke-width="2" opacity="0.85"/>
          <circle cx="48" cy="38" r="14" fill="{c}" stroke="{d}" stroke-width="2" opacity="0.85"/>
          <line x1="36" y1="38" x2="34" y2="38" stroke="{d}" stroke-width="2"/>
          <line x1="8" y1="36" x2="2" y2="32" stroke="{d}" stroke-width="2"/>
          <line x1="62" y1="36" x2="68" y2="32" stroke="{d}" stroke-width="2"/>""",
    }

    body = SHAPES.get(shape, SHAPES["tshirt"])
    vb = "0 0 80 80"
    if shape in ("dress",):         vb = "0 0 70 92"
    elif shape in ("sneaker", "loafer", "sandal"): vb = "0 0 84 56"
    elif shape in ("belt", "scarf", "sunglasses"): vb = "0 0 82 60"

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{size}" height="{size}" viewBox="{vb}" '
        f'style="display:block">{body}</svg>'
    )


# ── Shape lookup by category ──────────────────────────────────────────────────

CATEGORY_SHAPE = {
    "tops":        "tshirt",
    "bottoms":     "pants",
    "outerwear":   "jacket",
    "footwear":    "sneaker",
    "dresses":     "dress",
    "accessories": "bag",
}

NAME_SHAPE = {
    "t-shirt": "tshirt", "tshirt": "tshirt", "tee": "tshirt",
    "shirt": "shirt", "dress shirt": "shirt", "button-down": "shirt",
    "polo": "polo", "polo shirt": "polo",
    "sweater": "sweater", "knit": "sweater", "knitwear": "sweater",
    "hoodie": "hoodie", "sweatshirt": "hoodie",
    "tank": "tank", "tank top": "tank", "vest top": "tank",
    "jeans": "pants", "trousers": "pants", "chinos": "pants",
    "pants": "pants", "slacks": "pants",
    "shorts": "shorts",
    "skirt": "skirt", "mini skirt": "skirt",
    "leggings": "leggings",
    "blazer": "blazer", "sport coat": "blazer",
    "jacket": "jacket", "denim jacket": "jacket", "bomber": "jacket",
    "coat": "coat", "overcoat": "coat", "trench": "coat",
    "dress": "dress", "maxi dress": "dress", "midi dress": "dress",
    "mini dress": "minidress",
    "sneakers": "sneaker", "sneaker": "sneaker", "trainers": "sneaker",
    "boots": "boot", "boot": "boot", "chelsea boots": "boot",
    "loafers": "loafer", "loafer": "loafer", "oxford": "loafer",
    "sandals": "sandal", "sandal": "sandal",
    "belt": "belt",
    "watch": "watch",
    "bag": "bag", "handbag": "bag", "backpack": "bag", "tote": "bag",
    "hat": "hat", "cap": "hat", "beanie": "hat",
    "scarf": "scarf",
    "sunglasses": "sunglasses", "glasses": "sunglasses",
}

def shape_for(item: dict) -> str:
    """Pick the best SVG shape for a wardrobe item dict."""
    name_key = item.get("name", "").lower().strip()
    if name_key in NAME_SHAPE:
        return NAME_SHAPE[name_key]
    for key, shape in NAME_SHAPE.items():
        if key in name_key:
            return shape
    return CATEGORY_SHAPE.get(item.get("category", "tops"), "tshirt")


def item_svg_html(item: dict, size: int = 72) -> str:
    """Return full HTML for a clothing card visual (bg + svg centered)."""
    shape = shape_for(item)
    color = item.get("color", "gray")
    hex_c = resolve_color(color)
    bg    = bg_for(hex_c)
    svg   = clothing_svg(shape, color, size)
    return (
        f'<div style="background:{bg};border-radius:8px;'
        f'display:flex;align-items:center;justify-content:center;'
        f'width:{size+16}px;height:{size+16}px;margin:auto">'
        f'{svg}</div>'
    )


# ── Parallel product image fetcher ────────────────────────────────────────────

_fetch_lock      = threading.Lock()
_candidates_cache = {}   # item_id → list[bytes]  (multiple options)
_confirmed_cache  = {}   # item_id → bytes         (user-confirmed image)
_fetch_jobs       = set()


def _do_fetch(item_id, name, color, category):
    """Background thread: fetch multiple candidates, store all."""
    try:
        from garments import get_candidates
        results = get_candidates(name, color, category, max_candidates=4)
    except Exception:
        results = []

    with _fetch_lock:
        _candidates_cache[item_id] = results
        # Auto-select first as default (user can change)
        if results and item_id not in _confirmed_cache:
            _confirmed_cache[item_id] = results[0]
        _fetch_jobs.discard(item_id)


def start_fetch(item):
    """Kick off background fetch. Safe to call multiple times."""
    item_id = item.get("id", "")
    with _fetch_lock:
        if item_id in _candidates_cache or item_id in _fetch_jobs:
            return
        _fetch_jobs.add(item_id)

    t = threading.Thread(
        target=_do_fetch,
        args=(item_id, item.get("name",""), item.get("color",""), item.get("category","")),
        daemon=True
    )
    t.start()


def get_product_image(item_id):
    """Return confirmed image bytes, or None."""
    with _fetch_lock:
        return _confirmed_cache.get(item_id)


def get_candidates_cached(item_id):
    """Return all fetched candidate images for this item."""
    with _fetch_lock:
        return _candidates_cache.get(item_id, [])


def confirm_image(item_id, image_bytes):
    """User confirmed this image — store as the canonical one."""
    with _fetch_lock:
        _confirmed_cache[item_id] = image_bytes


def is_fetching(item_id):
    with _fetch_lock:
        return item_id in _fetch_jobs


def fetch_status(item_id):
    with _fetch_lock:
        if item_id in _candidates_cache:
            return "done"
        if item_id in _fetch_jobs:
            return "loading"
        return "pending"
