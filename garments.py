"""
OutfitAI — garments.py
Color-aware image search. Returns multiple candidates for user confirmation.
"""
import re
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _fetch_url(url):
    try:
        r = requests.get(url, timeout=12, headers=HEADERS, allow_redirects=True)
        ct = r.headers.get("content-type", "")
        if r.status_code == 200 and "image" in ct and len(r.content) > 4000:
            return r.content
    except Exception:
        pass
    return None


def _bing_search(query, max_results=5):
    """Scrape Bing Images. Returns list of image bytes."""
    encoded = query.replace(" ", "+")
    url = f"https://www.bing.com/images/search?q={encoded}&form=HDRSC2&first=1&count=20"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        urls = re.findall(
            r'"murl":"(https?://[^"]+?\.(?:jpg|jpeg|png))"',
            resp.text
        )
        for img_url in urls:
            if len(results) >= max_results:
                break
            data = _fetch_url(img_url)
            if data:
                results.append(data)
    except Exception:
        pass
    return results


def _unsplash_search(query, max_results=2):
    """Unsplash source API fallback."""
    results = []
    encoded = query.replace(" ", "+")
    tried = set()
    for _ in range(max_results):
        try:
            url = f"https://source.unsplash.com/400x500/?{encoded}"
            r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
            ct = r.headers.get("content-type", "")
            final_url = r.url
            if (r.status_code == 200 and "image" in ct
                    and final_url not in tried and len(r.content) > 4000):
                tried.add(final_url)
                results.append(r.content)
        except Exception:
            pass
    return results


def get_candidates(item_name, color, category, max_candidates=4):
    """
    Return up to max_candidates image bytes for user to confirm.
    All queries include the color for accuracy.
    """
    candidates = []

    # Query 1: color + item + flat lay (best for try-on)
    q1 = f"{color} {item_name} flat lay product photo white background"
    candidates += _bing_search(q1, max_results=3)

    # Query 2: color + item fashion photo
    if len(candidates) < max_candidates:
        q2 = f"{color} {item_name} fashion clothing"
        candidates += _bing_search(q2, max_results=2)

    # Fallback: Unsplash
    if len(candidates) < 2:
        q3 = f"{color}+{item_name}+{category}+fashion".replace(" ", "+")
        candidates += _unsplash_search(q3, max_results=2)

    # Deduplicate by file size
    seen = set()
    unique = []
    for c in candidates:
        if len(c) not in seen:
            seen.add(len(c))
            unique.append(c)
        if len(unique) >= max_candidates:
            break

    return unique


def get_garment_image(item_name, color, category):
    """Single best image for try-on engine."""
    candidates = get_candidates(item_name, color, category, max_candidates=1)
    return candidates[0] if candidates else None
