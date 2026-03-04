"""
OutfitAI Engine
Handles outfit scoring, color theory, and Claude API calls.
"""
import random
from collections import Counter

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# ── Color Theory Data ─────────────────────────────────────────────────────────

# Map color names to rough hue buckets (0–11 on color wheel)
COLOR_WHEEL = {
    "Red": 0, "Burgundy": 0, "Crimson": 0, "Wine": 0,
    "Orange": 1, "Rust": 1, "Terracotta": 1, "Copper": 1,
    "Yellow": 2, "Mustard": 2, "Gold": 2, "Amber": 2,
    "Olive": 3, "Khaki": 3, "Lime": 3,
    "Green": 4, "Forest Green": 4, "Sage": 4, "Mint": 4, "Emerald": 4,
    "Teal": 5, "Cyan": 5, "Turquoise": 5,
    "Light Blue": 6, "Sky Blue": 6, "Baby Blue": 6,
    "Blue": 7, "Navy": 7, "Cobalt": 7, "Royal Blue": 7,
    "Indigo": 8, "Purple": 8, "Lavender": 8, "Violet": 8,
    "Pink": 9, "Blush": 9, "Rose": 9, "Mauve": 9,
    "Brown": 10, "Camel": 10, "Tan": 10, "Beige": 10, "Cream": 10,
    "Black": 11, "White": 11, "Grey": 11, "Gray": 11, "Charcoal": 11,
    "Off-White": 11, "Ivory": 11,
}

NEUTRALS = {"Black", "White", "Grey", "Gray", "Charcoal", "Beige", "Cream", "Ivory", "Off-White", "Camel", "Tan"}

COLOR_RULES = {
    "Monochromatic":    "Same hue family in different shades — clean and sophisticated",
    "Analogous":        "3 adjacent colors on the wheel — harmonious and natural",
    "Complementary":    "Opposite colors — bold but balanced with a neutral anchor",
    "Neutral Base":     "All neutrals — timeless, always works",
    "Neutral + Pop":    "Neutral base with one pop of color — effortlessly stylish",
    "Triadic":          "Three evenly spaced colors — vibrant, needs careful balancing",
}

# Occasion formality requirements
OCCASION_FORMALITY = {
    "casual":  (1, 3),
    "work":    (2, 4),
    "date":    (2, 4),
    "formal":  (4, 5),
    "active":  (1, 2),
    "travel":  (1, 3),
}

# Style archetypes
ARCHETYPES = [
    {"name": "Urban Minimalist",  "emoji": "🖤", "tags": ["minimal", "monochrome", "clean"],
     "description": "You prefer clean lines, neutral tones, and quality over quantity. Less is always more."},
    {"name": "Casual Cool",       "emoji": "😎", "tags": ["casual", "relaxed", "sporty"],
     "description": "Effortlessly stylish — you look great without trying too hard. Comfort meets cool."},
    {"name": "Classic Professional", "emoji": "👔", "tags": ["formal", "classic", "tailored"],
     "description": "Polished and put-together. You dress for the job you want and it shows."},
    {"name": "Boho Chic",         "emoji": "🌸", "tags": ["bohemian", "earthy", "layered"],
     "description": "Free-spirited and eclectic. You mix textures, prints, and earthy tones with ease."},
    {"name": "Streetwear Edge",   "emoji": "🔥", "tags": ["street", "bold", "graphic"],
     "description": "You wear attitude. Sneakers, oversized fits, and bold statements are your language."},
    {"name": "Smart Casual",      "emoji": "✨", "tags": ["versatile", "smart", "classic"],
     "description": "The perfect balance — never overdressed, never underdressed. Always appropriate."},
]


class OutfitEngine:
    def __init__(self, wardrobe, occasion="casual", city="New York", api_key=None):
        self.wardrobe = wardrobe
        self.occasion = occasion
        self.city = city
        self.api_key = api_key

    # ── Wardrobe grouping ────────────────────────────────────────────────────
    def _group_by_category(self):
        groups = {}
        for item in self.wardrobe:
            groups.setdefault(item["category"], []).append(item)
        return groups

    def _can_build_outfit(self):
        groups = self._group_by_category()
        has_top = bool(groups.get("tops") or groups.get("dresses"))
        has_bottom = bool(groups.get("bottoms") or groups.get("dresses"))
        return has_top and has_bottom

    # ── Color scoring ────────────────────────────────────────────────────────
    def _color_score(self, items):
        colors = [item["color"] for item in items]
        neutral_colors = [c for c in colors if c in NEUTRALS]
        accent_colors = [c for c in colors if c not in NEUTRALS]

        # All neutrals — always works
        if len(accent_colors) == 0:
            return 85, "Neutral Base", colors

        # One accent on neutral base
        if len(accent_colors) == 1 and len(neutral_colors) >= 1:
            return 92, "Neutral + Pop", colors

        # Check wheel relationships for accent colors
        if len(accent_colors) >= 2:
            hues = []
            for c in accent_colors:
                for name, hue in COLOR_WHEEL.items():
                    if name.lower() in c.lower() or c.lower() in name.lower():
                        hues.append(hue)
                        break

            if len(hues) >= 2:
                diff = abs(hues[0] - hues[1])
                diff = min(diff, 12 - diff)  # wrap around

                if diff == 0:
                    return 88, "Monochromatic", colors
                elif diff <= 2:
                    return 82, "Analogous", colors
                elif diff == 6:
                    return 78, "Complementary", colors
                elif diff == 4:
                    return 74, "Triadic", colors
                else:
                    return 55, "Mixed — consider simplifying", colors

        return 65, "Coordinated", colors

    # ── Occasion scoring ─────────────────────────────────────────────────────
    def _occasion_score(self, items):
        min_f, max_f = OCCASION_FORMALITY.get(self.occasion, (1, 5))
        scores = []
        for item in items:
            f = item.get("formality", 2)
            if min_f <= f <= max_f:
                scores.append(100)
            elif f < min_f:
                scores.append(max(0, 100 - (min_f - f) * 25))
            else:
                scores.append(max(0, 100 - (f - max_f) * 25))

        # Also check occasion tags
        occasion_match = sum(
            1 for item in items
            if self.occasion in item.get("occasions", [])
        )
        tag_bonus = (occasion_match / len(items)) * 20 if items else 0

        base = sum(scores) / len(scores) if scores else 50
        return min(100, int(base + tag_bonus)), f"Suitable for {self.occasion}"

    # ── Build outfit candidates ──────────────────────────────────────────────
    def _build_candidates(self):
        groups = self._group_by_category()
        candidates = []

        tops     = groups.get("tops", [])
        bottoms  = groups.get("bottoms", [])
        dresses  = groups.get("dresses", [])
        outerwear= groups.get("outerwear", [])
        footwear = groups.get("footwear", [])
        accessories = groups.get("accessories", [])

        def make_combo(base_items):
            combo = list(base_items)
            if footwear:
                combo.append(random.choice(footwear))
            if outerwear and random.random() > 0.5:
                combo.append(random.choice(outerwear))
            if accessories and random.random() > 0.6:
                combo.append(random.choice(accessories))
            return combo

        # Top + bottom combos
        for top in tops:
            for bottom in bottoms:
                candidates.append(make_combo([top, bottom]))

        # Dress combos
        for dress in dresses:
            candidates.append(make_combo([dress]))

        # Shuffle and limit to 30 candidates for performance
        random.shuffle(candidates)
        return candidates[:30]

    # ── Score a single outfit ────────────────────────────────────────────────
    def _score_outfit(self, items):
        color_score, color_rule, palette = self._color_score(items)
        occ_score, occ_label = self._occasion_score(items)

        # Variety bonus: penalize outfits with only 1-2 items
        variety = min(100, len(items) * 25)

        # Weighted total
        total = int(color_score * 0.40 + occ_score * 0.40 + variety * 0.20)

        return {
            "items": items,
            "score": total,
            "score_breakdown": {
                "Color Harmony": color_score,
                "Occasion Fit": occ_score,
                "Variety": variety,
            },
            "color_rule": color_rule,
            "color_palette": list(set(i["color"] for i in items)),
            "occasion_fit": occ_label,
            "ai_explanation": None,
        }

    # ── Generate top N outfits ───────────────────────────────────────────────
    def generate(self, n=3):
        if not self._can_build_outfit():
            return []

        candidates = self._build_candidates()
        scored = [self._score_outfit(c) for c in candidates]
        scored.sort(key=lambda x: -x["score"])

        # De-duplicate: avoid showing very similar outfits
        seen_tops = set()
        unique = []
        for outfit in scored:
            top_ids = frozenset(i["id"] for i in outfit["items"])
            if top_ids not in seen_tops:
                seen_tops.add(top_ids)
                unique.append(outfit)
            if len(unique) >= n:
                break

        # Get AI explanation for best outfit if API key available
        if self.api_key and unique:
            unique[0]["ai_explanation"] = self.explain_outfit(unique[0])

        return unique

    # ── Claude explanation ───────────────────────────────────────────────────
    def explain_outfit(self, outfit):
        if not self.api_key or not ANTHROPIC_AVAILABLE:
            return self._mock_explanation(outfit)

        items_desc = ", ".join(
            f"{item['color']} {item['name']}" for item in outfit["items"]
        )
        color_rule = outfit.get("color_rule", "coordinated")
        score = outfit.get("score", 0)

        prompt = f"""You are a professional fashion stylist. Explain why this outfit works in 2–3 sentences.
Be specific about the color theory, the occasion suitability, and one practical styling tip.
Keep it warm, encouraging, and under 80 words.

Outfit: {items_desc}
Color rule applied: {color_rule}
Occasion: {self.occasion}
City: {self.city}
Style score: {score}/100

Give ONLY the explanation, no preamble."""

        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            return self._mock_explanation(outfit)

    def _mock_explanation(self, outfit):
        items_desc = ", ".join(f"{i['color']} {i['name']}" for i in outfit["items"])
        rule = outfit.get("color_rule", "coordinated palette")
        templates = [
            f"This {rule.lower()} combination works beautifully — the {items_desc} create a balanced, put-together look that's perfect for {self.occasion}. The colors complement each other naturally without competing for attention.",
            f"A strong {rule.lower()} choice. The {items_desc} flow together with confidence and intention. This is exactly the kind of outfit that looks effortless but is actually well-considered.",
            f"The {rule.lower()} approach here is spot-on for {self.occasion}. Your {items_desc} hit the right balance of style and practicality — you'll feel comfortable and look sharp all day.",
        ]
        return random.choice(templates)

    # ── Style profile analysis ───────────────────────────────────────────────
    def analyze_style_profile(self):
        if not self.wardrobe:
            return {"archetype": "Unknown", "emoji": "❓", "description": "Add items to discover your style.", "dominant_colors": [], "gaps": []}

        # Count style tags
        all_tags = []
        for item in self.wardrobe:
            all_tags.extend(item.get("styles", []))
        tag_counts = Counter(all_tags)

        # Find best matching archetype
        best_archetype = ARCHETYPES[1]  # default: casual cool
        best_score = 0
        for arch in ARCHETYPES:
            score = sum(tag_counts.get(tag, 0) for tag in arch["tags"])
            if score > best_score:
                best_score = score
                best_archetype = arch

        # Dominant colors
        color_counts = Counter(item["color"] for item in self.wardrobe)
        dominant_colors = color_counts.most_common(8)

        # Wardrobe gaps
        gaps = []
        groups = self._group_by_category()
        if "footwear" not in groups:
            gaps.append("👟 No footwear added — shoes complete every outfit")
        if "outerwear" not in groups:
            gaps.append("🧥 No outerwear — consider adding a jacket or coat")
        if len(groups.get("tops", [])) < 3:
            gaps.append("👕 More tops would give you more outfit combinations")
        if len(groups.get("bottoms", [])) < 2:
            gaps.append("👖 More bottoms would double your outfit options")
        if not groups.get("accessories"):
            gaps.append("👜 Accessories can elevate any outfit significantly")

        return {
            "archetype": best_archetype["name"],
            "emoji": best_archetype["emoji"],
            "description": best_archetype["description"],
            "dominant_colors": dominant_colors,
            "gaps": gaps,
        }
