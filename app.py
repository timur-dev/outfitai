import streamlit as st
import json
import os
import random
from datetime import datetime
from engine import OutfitEngine

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OutfitAI",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0f0f1a; color: #f0f0f0; }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #1a1a2e; }

    /* Cards */
    .outfit-card {
        background: linear-gradient(135deg, #1e1e3a 0%, #2a1a4a 100%);
        border: 1px solid #7C3AED44;
        border-radius: 16px;
        padding: 24px;
        margin: 12px 0;
    }
    .wardrobe-card {
        background: #1e1e3a;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        text-align: center;
    }
    .color-dot {
        display: inline-block;
        width: 20px; height: 20px;
        border-radius: 50%;
        margin: 2px;
        border: 1px solid #555;
    }
    .tag {
        display: inline-block;
        background: #7C3AED33;
        color: #c4b5fd;
        border: 1px solid #7C3AED66;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 12px;
        margin: 2px;
    }
    .score-bar {
        background: #333;
        border-radius: 10px;
        height: 8px;
        margin: 4px 0;
    }
    .score-fill {
        background: linear-gradient(90deg, #7C3AED, #a78bfa);
        border-radius: 10px;
        height: 8px;
    }
    .hero-text {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #7C3AED, #a78bfa, #c4b5fd);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }
    .subtitle { color: #9ca3af; font-size: 1rem; margin-bottom: 24px; }

    /* Buttons */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
    }

    /* Swipe card */
    .swipe-card {
        background: linear-gradient(160deg, #1e1e3a 0%, #2d1b4e 100%);
        border: 2px solid #7C3AED;
        border-radius: 20px;
        padding: 32px 24px;
        text-align: center;
        min-height: 320px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    .item-emoji { font-size: 5rem; margin-bottom: 12px; }
    .item-name { font-size: 1.4rem; font-weight: 700; color: #e9d5ff; }
    .item-desc { color: #9ca3af; font-size: 0.9rem; margin-top: 6px; }

    /* Metric boxes */
    .metric-box {
        background: #1e1e3a;
        border: 1px solid #7C3AED44;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: 800; color: #a78bfa; }
    .metric-label { font-size: 0.8rem; color: #9ca3af; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "wardrobe": [],
        "swipe_index": 0,
        "outfit_suggestions": [],
        "page": "home",
        "api_key": "",
        "style_profile": None,
        "swipe_history": [],   # list of {"item": {...}, "action": "own"/"skip"/"love"}
        "occasion": "casual",
        "city": "New York",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 👗 OutfitAI")
    st.markdown("---")

    # API Key input
    api_key = st.text_input(
        "🔑 Anthropic API Key",
        value=st.session_state.api_key,
        type="password",
        placeholder="sk-ant-...",
        help="Get yours at console.anthropic.com"
    )
    if api_key:
        st.session_state.api_key = api_key
        st.success("✓ Key saved")

    st.markdown("---")

    # Navigation
    st.markdown("### Navigation")
    pages = {
        "🏠 Home": "home",
        "👕 Build Wardrobe": "wardrobe_builder",
        "🗃️ My Wardrobe": "my_wardrobe",
        "✨ Get Outfit": "outfit",
        "📊 Style Profile": "profile",
    }
    for label, page_key in pages.items():
        if st.button(label, use_container_width=True,
                     type="primary" if st.session_state.page == page_key else "secondary"):
            st.session_state.page = page_key
            st.rerun()

    st.markdown("---")

    # Quick stats
    st.markdown("### My Stats")
    wc = len(st.session_state.wardrobe)
    sc = len(st.session_state.outfit_suggestions)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{wc}</div><div class="metric-label">Items</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{sc}</div><div class="metric-label">Outfits</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Settings")
    st.session_state.city = st.text_input("📍 Your City", value=st.session_state.city)
    st.session_state.occasion = st.selectbox(
        "🎯 Today's Occasion",
        ["casual", "work", "date", "formal", "active", "travel"],
        index=["casual", "work", "date", "formal", "active", "travel"].index(st.session_state.occasion)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ═══════════════════════════════════════════════════════════════════════════════
def page_home():
    st.markdown('<div class="hero-text">👗 OutfitAI</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">What to wear tomorrow — finally solved.</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="outfit-card">
            <div style="font-size:2rem">👕</div>
            <h3 style="color:#e9d5ff">Build Wardrobe</h3>
            <p style="color:#9ca3af">Swipe through clothing cards to tell us what you own. No photos needed.</p>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="outfit-card">
            <div style="font-size:2rem">🤖</div>
            <h3 style="color:#e9d5ff">AI Styling</h3>
            <p style="color:#9ca3af">Color theory, occasion intelligence, and geo-fashion rules combined.</p>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="outfit-card">
            <div style="font-size:2rem">✨</div>
            <h3 style="color:#e9d5ff">Daily Outfit</h3>
            <p style="color:#9ca3af">Get your perfect outfit every morning in under 30 seconds.</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🚀 Quick Start")

    wc = len(st.session_state.wardrobe)
    if wc == 0:
        st.info("👈 Start by building your wardrobe — go to **Build Wardrobe** in the sidebar.")
    elif wc < 5:
        st.warning(f"You have {wc} item(s). Add a few more for better suggestions!")
    else:
        st.success(f"✅ You have {wc} wardrobe items. Head to **Get Outfit** for today's suggestion!")

    # How it works
    st.markdown("---")
    st.markdown("### How It Works")
    steps = [
        ("1", "Swipe clothing cards to build your wardrobe — takes 3 minutes"),
        ("2", "Set your city and today's occasion in the sidebar"),
        ("3", "Go to Get Outfit — AI generates your perfect look"),
        ("4", "Claude explains why the outfit works using color theory"),
    ]
    for num, text in steps:
        st.markdown(f"**{num}.** {text}")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: WARDROBE BUILDER (Swipe)
# ═══════════════════════════════════════════════════════════════════════════════
def page_wardrobe_builder():
    from catalog import CATALOG

    st.markdown("## 👕 Build Your Wardrobe")
    st.markdown("Swipe through clothing items — tell us what you own. No photos needed.")
    st.markdown("---")

    idx = st.session_state.swipe_index
    total = len(CATALOG)

    if idx >= total:
        st.balloons()
        st.success("🎉 You've gone through all the clothing cards!")
        owned = [s for s in st.session_state.swipe_history if s["action"] in ("own", "love")]
        st.markdown(f"**{len(owned)} items added to your wardrobe.**")
        if st.button("🔄 Start Over", type="secondary"):
            st.session_state.swipe_index = 0
            st.session_state.swipe_history = []
            st.rerun()
        if st.button("✨ Get Outfit Suggestion", type="primary"):
            st.session_state.page = "outfit"
            st.rerun()
        return

    item = CATALOG[idx]
    progress = idx / total

    # Progress bar
    st.progress(progress, text=f"Card {idx + 1} of {total} — {item['category']}")
    st.markdown("")

    # Main swipe card
    left_col, card_col, right_col = st.columns([1, 2, 1])

    with card_col:
        st.markdown(f"""
        <div class="swipe-card">
            <div class="item-emoji">{item['emoji']}</div>
            <div class="item-name">{item['name']}</div>
            <div class="item-desc">{item['description']}</div>
            <br>
            <div>
                {''.join(f'<span class="tag">{s}</span>' for s in item['styles'])}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # Color picker (shown when user says they own it)
    if f"show_colors_{idx}" in st.session_state and st.session_state[f"show_colors_{idx}"]:
        st.markdown("#### 🎨 Pick the color(s) you own:")
        selected_colors = st.multiselect(
            "Colors",
            item["colors"],
            label_visibility="collapsed",
            key=f"color_pick_{idx}"
        )
        if st.button("✓ Add to Wardrobe", type="primary", use_container_width=True):
            colors = selected_colors if selected_colors else [item["colors"][0]]
            for color in colors:
                wardrobe_item = {
                    "id": f"{item['id']}_{color}",
                    "name": item["name"],
                    "category": item["category"],
                    "color": color,
                    "emoji": item["emoji"],
                    "styles": item["styles"],
                    "occasions": item["occasions"],
                    "formality": item["formality"],
                    "source": "swipe"
                }
                # Don't add duplicates
                existing_ids = [w["id"] for w in st.session_state.wardrobe]
                if wardrobe_item["id"] not in existing_ids:
                    st.session_state.wardrobe.append(wardrobe_item)

            st.session_state.swipe_history.append({"item": item, "action": "own"})
            st.session_state[f"show_colors_{idx}"] = False
            st.session_state.swipe_index += 1
            st.rerun()
        return

    # Action buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("👎  Skip", use_container_width=True, type="secondary"):
            st.session_state.swipe_history.append({"item": item, "action": "skip"})
            st.session_state.swipe_index += 1
            st.rerun()
    with col2:
        if st.button("👍  I Own This!", use_container_width=True, type="primary"):
            st.session_state[f"show_colors_{idx}"] = True
            st.rerun()
    with col3:
        if st.button("❤️  I Love This", use_container_width=True, type="primary"):
            st.session_state[f"show_colors_{idx}"] = True
            st.rerun()

    st.markdown("")
    st.caption("👎 Skip = don't own it  |  👍 Own it = adds to wardrobe  |  ❤️ Love it = adds as favorite")

    # Shortcut buttons
    with st.expander("⚡ Quick Add Basics"):
        st.markdown("Add common basics to your wardrobe instantly:")
        if st.button("Add White T-Shirt + Black Jeans + White Sneakers", type="secondary"):
            basics = [
                {"id": "tshirt_white", "name": "T-Shirt", "category": "tops", "color": "White",
                 "emoji": "👕", "styles": ["casual", "minimal"], "occasions": ["casual", "active"],
                 "formality": 1, "source": "quick_add"},
                {"id": "jeans_black", "name": "Jeans", "category": "bottoms", "color": "Black",
                 "emoji": "👖", "styles": ["casual", "versatile"], "occasions": ["casual", "work"],
                 "formality": 2, "source": "quick_add"},
                {"id": "sneakers_white", "name": "Sneakers", "category": "footwear", "color": "White",
                 "emoji": "👟", "styles": ["casual", "sporty"], "occasions": ["casual", "active"],
                 "formality": 1, "source": "quick_add"},
            ]
            for b in basics:
                if b["id"] not in [w["id"] for w in st.session_state.wardrobe]:
                    st.session_state.wardrobe.append(b)
            st.success("✅ Basics added!")
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: MY WARDROBE
# ═══════════════════════════════════════════════════════════════════════════════
def page_my_wardrobe():
    st.markdown("## 🗃️ My Wardrobe")

    wardrobe = st.session_state.wardrobe
    if not wardrobe:
        st.info("Your wardrobe is empty. Go to **Build Wardrobe** to add items.")
        return

    st.markdown(f"**{len(wardrobe)} items** in your wardrobe")
    st.markdown("---")

    # Group by category
    categories = {}
    for item in wardrobe:
        cat = item["category"]
        categories.setdefault(cat, []).append(item)

    for cat, items in categories.items():
        st.markdown(f"### {cat.title()} ({len(items)})")
        cols = st.columns(min(len(items), 4))
        for i, item in enumerate(items):
            with cols[i % 4]:
                st.markdown(f"""
                <div class="wardrobe-card">
                    <div style="font-size:2.5rem">{item['emoji']}</div>
                    <div style="font-weight:700;color:#e9d5ff;margin-top:8px">{item['name']}</div>
                    <div style="color:#9ca3af;font-size:0.85rem">{item['color']}</div>
                    <div style="margin-top:8px">
                        {''.join(f'<span class="tag">{s}</span>' for s in item.get('styles', [])[:2])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("🗑️ Remove", key=f"remove_{item['id']}", use_container_width=True):
                    st.session_state.wardrobe = [w for w in wardrobe if w["id"] != item["id"]]
                    st.rerun()

    st.markdown("---")
    if st.button("🗑️ Clear Entire Wardrobe", type="secondary"):
        st.session_state.wardrobe = []
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: GET OUTFIT
# ═══════════════════════════════════════════════════════════════════════════════
def page_outfit():
    st.markdown("## ✨ Today's Outfit Suggestion")

    wardrobe = st.session_state.wardrobe
    if len(wardrobe) < 3:
        st.warning("Add at least 3 items to your wardrobe first!")
        if st.button("👕 Build Wardrobe"):
            st.session_state.page = "wardrobe_builder"
            st.rerun()
        return

    if not st.session_state.api_key:
        st.warning("⚠️ Add your Anthropic API key in the sidebar to get AI styling explanations.")

    # Settings summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-box"><div class="metric-value">🌤</div><div class="metric-label">{st.session_state.city}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><div class="metric-value">🎯</div><div class="metric-label">{st.session_state.occasion.title()}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{len(wardrobe)}</div><div class="metric-label">Wardrobe Items</div></div>', unsafe_allow_html=True)

    st.markdown("")

    if st.button("🎲 Generate Outfit", type="primary", use_container_width=True):
        with st.spinner("🤖 Styling your outfit..."):
            engine = OutfitEngine(
                wardrobe=wardrobe,
                occasion=st.session_state.occasion,
                city=st.session_state.city,
                api_key=st.session_state.api_key
            )
            suggestions = engine.generate(n=3)
            st.session_state.outfit_suggestions = suggestions
        st.rerun()

    if not st.session_state.outfit_suggestions:
        st.markdown("---")
        st.markdown("👆 Click the button above to generate your outfit suggestions.")
        return

    st.markdown("---")
    st.markdown("### Your Outfit Options")

    for i, outfit in enumerate(st.session_state.outfit_suggestions):
        rank_emoji = ["🥇", "🥈", "🥉"][i]
        with st.expander(f"{rank_emoji} Outfit {i+1} — Score: {outfit['score']}/100", expanded=(i == 0)):

            # Items row
            item_cols = st.columns(len(outfit["items"]))
            for j, item in enumerate(outfit["items"]):
                with item_cols[j]:
                    st.markdown(f"""
                    <div class="wardrobe-card">
                        <div style="font-size:2.5rem">{item['emoji']}</div>
                        <div style="font-weight:700;color:#e9d5ff">{item['name']}</div>
                        <div style="color:#9ca3af;font-size:0.85rem">{item['color']}</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("")

            # Score breakdown
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Score Breakdown**")
                scores = outfit.get("score_breakdown", {})
                for label, val in scores.items():
                    pct = int(val)
                    st.markdown(f"<small>{label}</small>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="score-bar">
                        <div class="score-fill" style="width:{pct}%"></div>
                    </div>
                    <small style="color:#9ca3af">{pct}/100</small>
                    """, unsafe_allow_html=True)

            with col_b:
                st.markdown("**Color Palette**")
                colors = outfit.get("color_palette", [])
                color_html = ""
                for c in colors:
                    color_html += f'<span class="tag">🎨 {c}</span> '
                st.markdown(color_html, unsafe_allow_html=True)

                st.markdown("**Color Rule Applied**")
                st.markdown(f'<span class="tag">✓ {outfit.get("color_rule", "Coordinated")}</span>', unsafe_allow_html=True)

                st.markdown("**Occasion Fit**")
                st.markdown(f'<span class="tag">✓ {outfit.get("occasion_fit", "Good match")}</span>', unsafe_allow_html=True)

            # AI Explanation
            st.markdown("")
            if outfit.get("ai_explanation"):
                st.markdown(f"""
                <div class="outfit-card">
                    <div style="font-size:1.1rem;margin-bottom:8px">🤖 <strong style="color:#a78bfa">AI Stylist Says</strong></div>
                    <div style="color:#e9d5ff;line-height:1.7">{outfit['ai_explanation']}</div>
                </div>
                """, unsafe_allow_html=True)
            elif st.session_state.api_key:
                if st.button(f"💬 Get AI Explanation", key=f"explain_{i}"):
                    with st.spinner("Claude is styling..."):
                        engine = OutfitEngine(
                            wardrobe=wardrobe,
                            occasion=st.session_state.occasion,
                            city=st.session_state.city,
                            api_key=st.session_state.api_key
                        )
                        explanation = engine.explain_outfit(outfit)
                        st.session_state.outfit_suggestions[i]["ai_explanation"] = explanation
                    st.rerun()
            else:
                st.caption("🔑 Add API key in sidebar for AI styling explanation")

            # Action buttons
            st.markdown("")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Wearing This!", key=f"wear_{i}", type="primary", use_container_width=True):
                    st.success("Great choice! Outfit saved to your history. 🎉")
            with c2:
                if st.button("🔄 Try Another", key=f"skip_{i}", type="secondary", use_container_width=True):
                    st.session_state.outfit_suggestions = []
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: STYLE PROFILE
# ═══════════════════════════════════════════════════════════════════════════════
def page_profile():
    st.markdown("## 📊 Your Style Profile")

    wardrobe = st.session_state.wardrobe
    if not wardrobe:
        st.info("Build your wardrobe first to see your style profile.")
        return

    # Analyze wardrobe
    from engine import OutfitEngine
    engine = OutfitEngine(wardrobe=wardrobe, occasion="casual", city=st.session_state.city)
    profile = engine.analyze_style_profile()

    st.markdown(f"""
    <div class="outfit-card" style="text-align:center">
        <div style="font-size:3rem">{profile['emoji']}</div>
        <div style="font-size:1.8rem;font-weight:800;color:#e9d5ff;margin:12px 0">{profile['archetype']}</div>
        <div style="color:#9ca3af">{profile['description']}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🎨 Your Color Palette")
        colors = profile.get("dominant_colors", [])
        for color, count in colors[:8]:
            st.markdown(f"**{color}** — {count} item{'s' if count > 1 else ''}")

        st.markdown("### 👔 Wardrobe Breakdown")
        categories = {}
        for item in wardrobe:
            categories[item["category"]] = categories.get(item["category"], 0) + 1
        for cat, cnt in sorted(categories.items(), key=lambda x: -x[1]):
            pct = int(cnt / len(wardrobe) * 100)
            st.markdown(f"<small>{cat.title()}</small>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class="score-bar">
                <div class="score-fill" style="width:{pct}%"></div>
            </div>
            <small style="color:#9ca3af">{cnt} items ({pct}%)</small>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("### 🏷️ Your Style Tags")
        all_styles = []
        for item in wardrobe:
            all_styles.extend(item.get("styles", []))
        style_counts = {}
        for s in all_styles:
            style_counts[s] = style_counts.get(s, 0) + 1
        tags_html = ""
        for style, count in sorted(style_counts.items(), key=lambda x: -x[1])[:12]:
            tags_html += f'<span class="tag">{style} ({count})</span> '
        st.markdown(tags_html, unsafe_allow_html=True)

        st.markdown("### 🎯 Occasion Coverage")
        all_occasions = []
        for item in wardrobe:
            all_occasions.extend(item.get("occasions", []))
        occasion_counts = {}
        for o in all_occasions:
            occasion_counts[o] = occasion_counts.get(o, 0) + 1
        for occ, cnt in sorted(occasion_counts.items(), key=lambda x: -x[1]):
            pct = min(int(cnt / len(wardrobe) * 150), 100)
            st.markdown(f"<small>{occ.title()}</small>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class="score-bar">
                <div class="score-fill" style="width:{pct}%"></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### 💡 Wardrobe Gaps")
        for gap in profile.get("gaps", []):
            st.markdown(f"- {gap}")


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════
page = st.session_state.page
if page == "home":
    page_home()
elif page == "wardrobe_builder":
    page_wardrobe_builder()
elif page == "my_wardrobe":
    page_my_wardrobe()
elif page == "outfit":
    page_outfit()
elif page == "profile":
    page_profile()
