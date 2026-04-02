"""
OutfitAI — garments.py
Generates color-accurate garment images from bundled base shapes.
Uses PIL to tint each base image to the exact item color.
Zero network calls needed. Works on Streamlit Cloud.
"""
import io, base64
from PIL import Image


# ── Color map ─────────────────────────────────────────────────────────────────

COLOR_RGB = {
    "white":    (245, 245, 245),
    "black":    (30,  30,  30),
    "navy":     (25,  50,  100),
    "blue":     (40,  90,  180),
    "gray":     (130, 130, 130),
    "grey":     (130, 130, 130),
    "charcoal": (60,  65,  70),
    "beige":    (210, 190, 155),
    "cream":    (240, 235, 210),
    "brown":    (100, 65,  35),
    "tan":      (185, 150, 105),
    "khaki":    (185, 170, 120),
    "green":    (45,  110, 65),
    "olive":    (100, 115, 55),
    "red":      (185, 35,  35),
    "burgundy": (110, 25,  40),
    "maroon":   (110, 25,  40),
    "pink":     (230, 150, 175),
    "purple":   (110, 55,  180),
    "yellow":   (235, 195, 40),
    "orange":   (220, 110, 30),
    "camel":    (195, 155, 95),
    "rust":     (175, 75,  30),
    "teal":     (20,  145, 135),
    "lavender": (175, 155, 215),
    "coral":    (225, 105, 95),
    "gold":     (200, 160, 40),
    "silver":   (190, 190, 195),
    "denim":    (55,  80,  130),
}

def resolve_rgb(color_name: str) -> tuple:
    return COLOR_RGB.get(color_name.lower().strip(), (140, 140, 140))


# ── Shape → garment_images key ────────────────────────────────────────────────

NAME_TO_SHAPE = {
    "t-shirt": "tshirt", "tshirt": "tshirt", "tee": "tshirt",
    "shirt": "shirt", "dress shirt": "shirt", "button-down": "shirt",
    "polo": "polo", "polo shirt": "polo",
    "sweater": "sweater", "knit": "sweater",
    "hoodie": "hoodie", "sweatshirt": "hoodie",
    "tank top": "tank_top", "tank": "tank_top", "vest top": "tank_top",
    "jeans": "jeans", "denim jeans": "jeans",
    "trousers": "trousers", "slacks": "trousers", "pants": "trousers",
    "chinos": "chinos",
    "shorts": "shorts",
    "skirt": "skirt", "mini skirt": "skirt",
    "blazer": "blazer", "sport coat": "blazer",
    "jacket": "jacket", "denim jacket": "jacket", "bomber": "jacket",
    "coat": "coat", "overcoat": "coat", "trench coat": "coat",
    "dress": "dress", "maxi dress": "dress", "midi dress": "dress",
    "mini dress": "dress",
    "sneakers": "sneakers", "trainers": "sneakers",
    "boots": "boots", "chelsea boots": "boots",
    "loafers": "loafers", "oxford": "loafers", "shoes": "loafers",
    "bag": "bag", "handbag": "bag", "backpack": "bag", "tote": "bag",
}

CAT_FALLBACK = {
    "tops": "tshirt", "bottoms": "jeans", "outerwear": "jacket",
    "dresses": "dress", "footwear": "sneakers", "accessories": "bag",
}

def _shape_key(item_name: str, category: str) -> str:
    n = item_name.lower().strip()
    if n in NAME_TO_SHAPE:
        return NAME_TO_SHAPE[n]
    for key, shape in NAME_TO_SHAPE.items():
        if key in n or n in key:
            return shape
    return CAT_FALLBACK.get(category, "tshirt")


# ── Core: tint a base image to a target color ─────────────────────────────────

def _tint_image(base_b64: str, target_rgb: tuple) -> bytes:
    """
    Tint base image to target_rgb using numpy (fast, ~20ms per image).
    White background stays white. Clothing pixels get the target color with shading.
    Zero API calls, zero tokens.
    """
    import numpy as np
    raw = base64.b64decode(base_b64)
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    arr = np.array(img, dtype=np.float32)

    # Luminance: 0=black, 1=white
    lum = (0.299*arr[:,:,0] + 0.587*arr[:,:,1] + 0.114*arr[:,:,2]) / 255.0

    # White pixels (background) stay white
    mask = lum < 0.94  # True = clothing pixel

    result = np.ones_like(arr) * 255.0  # white canvas
    factor = lum[:,:,np.newaxis]        # shape (H,W,1)
    tint   = np.array(target_rgb, dtype=np.float32)

    # Shading: dark pixels → dark tint, light pixels → lighter tint
    shaded = tint[np.newaxis, np.newaxis, :] * (0.25 + 0.75 * factor)
    result[mask] = np.clip(shaded[mask], 0, 255)

    out = Image.fromarray(result.astype(np.uint8))
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


# ── Public API ────────────────────────────────────────────────────────────────

def get_garment_image(item_name: str, color: str, category: str) -> bytes | None:
    """
    Generate a color-accurate garment image.
    Returns JPEG bytes. Never makes network calls.
    """
    try:
        from garment_images import GARMENT_IMAGES
        shape = _shape_key(item_name, category)
        base  = GARMENT_IMAGES.get(shape) or GARMENT_IMAGES.get("tshirt")
        if not base:
            return None
        rgb = resolve_rgb(color)
        return _tint_image(base, rgb)
    except Exception as e:
        return None


def get_candidates(item_name: str, color: str, category: str,
                   max_candidates: int = 4) -> list:
    """
    Return candidate images — here we generate slight variations (hue shifts).
    Always returns at least 1 result if shape exists.
    """
    try:
        from garment_images import GARMENT_IMAGES
        shape = _shape_key(item_name, category)
        base  = GARMENT_IMAGES.get(shape) or GARMENT_IMAGES.get("tshirt")
        if not base:
            return []

        rgb   = resolve_rgb(color)
        r, g, b = rgb

        # Generate up to 4 slight variations of the same color
        variations = [
            (r, g, b),                                          # exact
            (min(255,r+20), min(255,g+20), min(255,b+20)),      # lighter
            (max(0,r-20),   max(0,g-20),   max(0,b-20)),        # darker
            (min(255,r+10), max(0,g-10),   max(0,b-5)),         # warm shift
        ]

        results = []
        for v in variations[:max_candidates]:
            img = _tint_image(base, v)
            if img:
                results.append(img)
        return results
    except Exception:
        return []
