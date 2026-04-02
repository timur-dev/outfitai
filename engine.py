"""
OutfitAI — engine.py
Outfit scoring engine + Claude AI explanations.

Scoring breakdown (100 pts total):
  - Color harmony:   35 pts
  - Occasion fit:    35 pts
  - Formality match: 20 pts
  - Variety bonus:   10 pts
"""
import itertools, os
try:
    import streamlit as st
    def get_secret(key, fallback=None):
        try:
            return st.secrets.get(key, os.environ.get(key, fallback))
        except Exception:
            return os.environ.get(key, fallback)
except ImportError:
    def get_secret(key, fallback=None):
        return os.environ.get(key, fallback)


# ── Color theory ──────────────────────────────────────────────────────────────

WARM   = {"red","rust","orange","coral","yellow","gold","camel","tan","brown","burgundy","maroon"}
COOL   = {"blue","navy","teal","green","olive","purple","lavender","gray","grey","charcoal","silver","denim"}
NEUTRAL= {"white","black","beige","cream","khaki","camel","tan","brown","gray","grey","charcoal","silver"}

COLOR_WHEEL = {
    "red":0,"rust":15,"orange":30,"gold":45,"yellow":60,
    "olive":80,"green":120,"teal":165,"blue":210,"navy":225,
    "purple":270,"lavender":285,"pink":330,"coral":15,
    "burgundy":345,"maroon":345,"camel":35,"tan":35,"brown":30,
    "beige":40,"cream":50,"khaki":45,"white":0,"black":0,
    "gray":0,"grey":0,"charcoal":0,"silver":0,"denim":210,
}

def _hue(color):
    return COLOR_WHEEL.get(color.lower(), 180)

def _is_neutral(color):
    return color.lower() in NEUTRAL

def color_harmony_score(colors):
    """Score 0-35 based on how well colors harmonize."""
    if not colors or len(colors) < 2:
        return 25

    c = [x.lower() for x in colors]
    neutrals = [x for x in c if _is_neutral(x)]
    chromatic = [x for x in c if not _is_neutral(x)]

    # All neutral = always works
    if not chromatic:
        return 32

    # One color + neutrals = very safe
    if len(chromatic) == 1:
        return 35

    if len(chromatic) >= 2:
        hues = [_hue(x) for x in chromatic]
        diffs = [abs(hues[i]-hues[j]) for i in range(len(hues))
                 for j in range(i+1,len(hues))]
        diffs = [min(d, 360-d) for d in diffs]
        avg_diff = sum(diffs)/len(diffs)

        # Monochromatic (same hue ±20)
        if avg_diff <= 20:
            return 33
        # Analogous (close hues 20-60)
        if avg_diff <= 60:
            return 30
        # Complementary (opposite ~180)
        if 150 <= avg_diff <= 210:
            return 28
        # Triadic (~120 apart)
        if 100 <= avg_diff <= 140:
            return 22
        # Clash (random)
        return 10

    return 20

COLOR_RULES = {
    (35,35): "Perfect monochromatic",
    (35,30): "Analogous harmony",
    (35,28): "Classic complementary",
    (35,22): "Triadic balance",
    (32,32): "Clean neutrals",
}

def get_color_rule(score):
    if score >= 33: return "Monochromatic / tonal"
    if score >= 30: return "Analogous harmony"
    if score >= 28: return "Complementary"
    if score >= 22: return "Triadic"
    if score >= 18: return "Neutral base"
    return "Bold contrast"


# ── Occasion + formality ──────────────────────────────────────────────────────

OCCASION_FORMALITY = {
    "casual": 1.5, "active": 1, "travel": 2,
    "work": 3.5,   "date": 3,   "formal": 4.5,
}

def occasion_score(items, occasion):
    """Score 0-35: how well items suit the occasion."""
    if not items:
        return 0
    total = 0
    for item in items:
        occ = item.get("occasions", [])
        if occasion in occ:
            total += 35
        elif any(o in occ for o in _adjacent_occasions(occasion)):
            total += 22
        else:
            total += 8
    return int(total / len(items))

def _adjacent_occasions(occ):
    adj = {
        "casual":  ["travel","active"],
        "active":  ["casual"],
        "work":    ["formal","date"],
        "date":    ["casual","work","formal"],
        "formal":  ["work","date"],
        "travel":  ["casual","active"],
    }
    return adj.get(occ, [])

def formality_score(items, occasion):
    """Score 0-20: formality of items matches occasion expectation."""
    if not items:
        return 10
    target = OCCASION_FORMALITY.get(occasion, 2.5)
    avg_formality = sum(i.get("formality", 2) for i in items) / len(items)
    diff = abs(avg_formality - target)
    if diff <= 0.5:   return 20
    if diff <= 1.0:   return 16
    if diff <= 1.5:   return 12
    if diff <= 2.0:   return 7
    return 3

def variety_bonus(items):
    """Score 0-10: reward style variety."""
    styles = set()
    for item in items:
        styles.update(item.get("styles", []))
    return min(10, len(styles) * 2)


# ── Main engine ───────────────────────────────────────────────────────────────

class OutfitEngine:
    def __init__(self, wardrobe, occasion="casual", city="New York", api_key=None):
        self.wardrobe  = wardrobe
        self.occasion  = occasion
        self.city      = city
        self.api_key   = api_key or get_secret("ANTHROPIC_API_KEY")

    def _by_cat(self, cat):
        return [i for i in self.wardrobe if i["category"] == cat]

    def _score_outfit(self, items):
        colors    = [i["color"] for i in items]
        c_score   = color_harmony_score(colors)
        o_score   = occasion_score(items, self.occasion)
        f_score   = formality_score(items, self.occasion)
        v_score   = variety_bonus(items)
        total     = c_score + o_score + f_score + v_score
        return {
            "score":      min(100, total),
            "score_breakdown": {
                "Color harmony":    c_score,
                "Occasion fit":     o_score,
                "Formality match":  f_score,
                "Style variety":    v_score,
            },
            "color_palette": colors,
            "color_rule":   get_color_rule(c_score),
        }

    def generate(self, n=3):
        """Generate top-N outfit combinations."""
        tops      = self._by_cat("tops")
        bottoms   = self._by_cat("bottoms")
        dresses   = self._by_cat("dresses")
        outerwear = self._by_cat("outerwear")
        footwear  = self._by_cat("footwear")
        acc       = self._by_cat("accessories")

        combos = []

        # Dresses (no top/bottom needed)
        for d in dresses:
            items = [d]
            if footwear: items.append(footwear[0])
            scored = self._score_outfit(items)
            scored["items"] = items
            combos.append(scored)

        # Tops + Bottoms
        for top, bot in itertools.product(tops, bottoms):
            # Skip same-item duplicates
            if top["id"] == bot["id"]:
                continue
            items = [top, bot]
            # Add outerwear for formal/work occasions
            if self.occasion in ("work","formal","date") and outerwear:
                best_outer = max(outerwear,
                                 key=lambda o: occasion_score([o], self.occasion))
                items.append(best_outer)
            if footwear:
                best_shoe = max(footwear,
                                key=lambda f: occasion_score([f], self.occasion))
                items.append(best_shoe)
            scored = self._score_outfit(items)
            scored["items"] = items
            combos.append(scored)

        if not combos:
            return []

        # Sort by score, deduplicate by top+bottom pair
        combos.sort(key=lambda x: x["score"], reverse=True)
        seen, unique = set(), []
        for c in combos:
            key = tuple(sorted(i["id"] for i in c["items"]
                               if i["category"] in ("tops","bottoms","dresses")))
            if key not in seen:
                seen.add(key)
                unique.append(c)
            if len(unique) >= n:
                break

        # Add AI explanation to top outfit automatically
        if unique and self.api_key:
            try:
                unique[0]["ai_explanation"] = self.explain_outfit(unique[0])
            except Exception:
                pass

        return unique

    def explain_outfit(self, outfit):
        """Ask Claude to explain why this outfit works."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            items_desc = ", ".join(
                f"{i['color']} {i['name']}" for i in outfit["items"])
            prompt = (
                f"You are a professional fashion stylist. Explain in 2-3 sentences "
                f"why this outfit works for a {self.occasion} occasion in {self.city}: "
                f"{items_desc}. Color rule: {outfit.get('color_rule','—')}. "
                f"Be specific, warm, and practical. No bullet points."
            )
            msg = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=200,
                messages=[{"role":"user","content":prompt}]
            )
            return msg.content[0].text
        except Exception:
            return ""

    def analyze_style_profile(self):
        """Analyze wardrobe and return style archetype."""
        if not self.wardrobe:
            return {"archetype":"Unknown","description":"Add items to get your profile",
                    "emoji":"👗","dominant_colors":[],"gaps":[]}

        # Count styles
        style_counts = {}
        for item in self.wardrobe:
            for s in item.get("styles",[]):
                style_counts[s] = style_counts.get(s,0) + 1

        # Count colors
        color_counts = {}
        for item in self.wardrobe:
            c = item.get("color","")
            color_counts[c] = color_counts.get(c,0) + 1
        dominant = sorted(color_counts.items(), key=lambda x:-x[1])

        # Dominant style
        top_style = max(style_counts, key=style_counts.get) if style_counts else "casual"

        ARCHETYPES = {
            "formal":   ("The Professional", "Sharp, polished, boardroom-ready.", "💼"),
            "casual":   ("The Everyday Chic","Relaxed but always put-together.","👕"),
            "minimal":  ("The Minimalist",   "Clean lines, neutral palette, timeless.","🖤"),
            "streetwear":("The Streetwear Icon","Bold, urban, always on-trend.","🧢"),
            "elegant":  ("The Elegant One",  "Refined taste, classic silhouettes.","✨"),
            "smart":    ("The Smart Casual Expert","The perfect work-to-weekend wardrobe.","👔"),
            "sporty":   ("The Athleisure Pro","Comfort meets style effortlessly.","👟"),
            "versatile":("The Chameleon",    "Adaptable style for any occasion.","🌟"),
        }
        arch = ARCHETYPES.get(top_style, ARCHETYPES["casual"])

        # Find wardrobe gaps
        cats = {i["category"] for i in self.wardrobe}
        gaps = []
        if "tops"      not in cats: gaps.append("Add some tops")
        if "bottoms"   not in cats and "dresses" not in cats:
            gaps.append("Add bottoms or dresses")
        if "outerwear" not in cats: gaps.append("A jacket or coat would complete your look")
        if "footwear"  not in cats: gaps.append("Add shoes for complete outfits")
        if len(self.wardrobe) < 5:  gaps.append("Add more variety for better outfit combinations")
        n_neutrals = sum(1 for i in self.wardrobe if _is_neutral(i.get("color","")))
        if n_neutrals < 2:          gaps.append("Add neutral basics (white, black, gray)")

        return {
            "archetype":       arch[0],
            "description":     arch[1],
            "emoji":           arch[2],
            "dominant_colors": dominant[:6],
            "gaps":            gaps,
        }
