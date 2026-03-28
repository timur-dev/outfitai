"""
OutfitAI — Garment Image Database
Pre-built map of item_type → reliable flat-lay image URLs (Unsplash).
Used as first lookup before web search fallback.
"""

import requests

# ── Pre-built DB: item_type → list of Unsplash photo IDs ─────────────────────
# Format: https://images.unsplash.com/photo-{ID}?w=400&h=500&fit=crop
_DB = {
    # TOPS
    "t-shirt":       ["1521572163474-6864f9cf17ab", "1618354691373-d851c5c3a990"],
    "shirt":         ["1596755094514-f87e34085b2c", "1603252109303-2751441dd157"],
    "polo shirt":    ["1625910513014-4a0f47b3a0e2", "1622470953794-aa9c70b0fb9d"],
    "blouse":        ["1598554747436-c9293d6a588f", "1603189343302-0a61e33fde0b"],
    "hoodie":        ["1556821840-3a63f10be5b3", "1620799140408-edb98bfae0a5"],
    "sweatshirt":    ["1572635196237-14b3f281503f", "1578587018452-892bacefd3bf"],
    "tank top":      ["1503341504248-4f7f66f6c3e6", "1571513722275-4b41940f54b8"],
    "crop top":      ["1567401893414-76b7b1e5a7a5", "1503342217505-b0a15ec3261c"],

    # BOTTOMS
    "jeans":         ["1542272454-0f711a8e26de", "1555689502-c4b22d76c56f"],
    "trousers":      ["1473966968600-fa801b869a1a", "1624378439432-ae55985ad9c3"],
    "chinos":        ["1624378439432-ae55985ad9c3", "1473966968600-fa801b869a1a"],
    "shorts":        ["1591195853828-11db59a44f43", "1506629082955-511b1aa562c8"],
    "skirt":         ["1583496661160-fb5218afa9a3", "1572804013427-4d7ca7268217"],
    "sweatpants":    ["1584464491033-f628b5c1e9e6", "1556905055-8f358a7a47b2"],
    "leggings":      ["1506629082955-511b1aa562c8", "1519681393784-d120267933ba"],

    # OUTERWEAR
    "jacket":        ["1591047139829-d91aecb6caea", "1548126032-079a0fb0099d"],
    "coat":          ["1548126032-079a0fb0099d", "1591047139829-d91aecb6caea"],
    "blazer":        ["1507679799987-c73779587ccf", "1594938298603-9e22a49b6dc4"],
    "denim jacket":  ["1542272654-6418fca8fd16", "1594938298603-9e22a49b6dc4"],
    "bomber jacket": ["1548126032-079a0fb0099d", "1591047139829-d91aecb6caea"],
    "puffer jacket": ["1548126032-079a0fb0099d", "1591047139829-d91aecb6caea"],

    # DRESSES
    "dress":         ["1623609163841-5e69d8c62cc7", "1515372392861-e34a2cef7f66"],
    "maxi dress":    ["1515372392861-e34a2cef7f66", "1623609163841-5e69d8c62cc7"],
    "mini dress":    ["1567401893414-76b7b1e5a7a5", "1623609163841-5e69d8c62cc7"],
    "sundress":      ["1515372392861-e34a2cef7f66", "1623609163841-5e69d8c62cc7"],

    # FOOTWEAR
    "sneakers":      ["1542291026-7eec264c27ff", "1600269452121-4f2416e55c28"],
    "shoes":         ["1542291026-7eec264c27ff", "1600269452121-4f2416e55c28"],
    "boots":         ["1608256246200-d8f5b3b0a0e5", "1520639888713-7851133b1ed0"],
    "loafers":       ["1600269452121-4f2416e55c28", "1542291026-7eec264c27ff"],
    "sandals":       ["1603487742131-4160ec999306", "1542291026-7eec264c27ff"],
    "heels":         ["1596703263926-eb0762ee17e4", "1603487742131-4160ec999306"],

    # ACCESSORIES
    "bag":           ["1548036161-61f5a0f0e6f2", "1584917865442-2f7e8c27d567"],
    "belt":          ["1603560863952-4f5f4f8a5ec5", "1548036161-61f5a0f0e6f2"],
    "hat":           ["1588850561407-ed78c282e89b", "1521369909449-6ddb3b4d8c55"],
    "scarf":         ["1520903920907-b3c0bccae58f", "1577401239170-897942555fb3"],
    "sunglasses":    ["1572635196237-14b3f281503f", "1521369909449-6ddb3b4d8c55"],
    "watch":         ["1523275335684-37898b6baf30", "1548036161-61f5a0f0e6f2"],
}

# Category fallbacks
_CATEGORY_FALLBACK = {
    "tops":        "t-shirt",
    "bottoms":     "jeans",
    "outerwear":   "jacket",
    "dresses":     "dress",
    "footwear":    "sneakers",
    "accessories": "bag",
}


def _unsplash_url(photo_id: str, w=400, h=500) -> str:
    return f"https://images.unsplash.com/photo-{photo_id}?w={w}&h={h}&fit=crop&auto=format"


def _fetch_url(url: str) -> bytes | None:
    try:
        r = requests.get(url, timeout=12,
                         headers={"User-Agent": "OutfitAI/1.0"})
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            return r.content
    except Exception:
        pass
    return None


def get_garment_image(item_name: str, color: str, category: str) -> bytes | None:
    """
    Returns image bytes for a garment.
    Order: pre-built DB → web search → None
    """
    name_lower = item_name.lower().strip()

    # 1. Exact match in DB
    photo_ids = _DB.get(name_lower)

    # 2. Partial match
    if not photo_ids:
        for key, ids in _DB.items():
            if key in name_lower or name_lower in key:
                photo_ids = ids
                break

    # 3. Category fallback
    if not photo_ids:
        fallback_key = _CATEGORY_FALLBACK.get(category, "t-shirt")
        photo_ids = _DB.get(fallback_key, [])

    # Try each photo ID
    for pid in photo_ids:
        data = _fetch_url(_unsplash_url(pid))
        if data:
            return data

    # 4. Web search fallback (Bing scrape)
    return _web_search_image(item_name, color, category)


def _web_search_image(item_name: str, color: str, category: str) -> bytes | None:
    """Bing image search scrape as last resort."""
    import re
    query = f"{color} {item_name} fashion flat lay white background"
    encoded = query.replace(" ", "+")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(
            f"https://www.bing.com/images/search?q={encoded}&form=HDRSC2&first=1",
            headers=headers, timeout=10)
        matches = re.findall(
            r'"murl":"(https?://[^"]+?\.(?:jpg|jpeg|png))"', resp.text)
        for url in matches[:3]:
            data = _fetch_url(url)
            if data and len(data) > 5000:   # skip tiny/corrupt images
                return data
    except Exception:
        pass

    # Last resort: Unsplash source
    try:
        q = f"{color}+{item_name}+{category}+fashion".replace(" ", "+")
        r = requests.get(f"https://source.unsplash.com/400x500/?{q}",
                         timeout=10, allow_redirects=True)
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            return r.content
    except Exception:
        pass

    return None
