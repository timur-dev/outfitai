import streamlit as st
import random
from engine import OutfitEngine, get_secret
from tryon import TryOnEngine

st.set_page_config(page_title="OutfitAI", page_icon="👗", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp{background-color:#0f0f1a;color:#f0f0f0}
[data-testid="stSidebar"]{background-color:#1a1a2e}
.outfit-card{background:linear-gradient(135deg,#1e1e3a 0%,#2a1a4a 100%);
  border:1px solid #7C3AED44;border-radius:16px;padding:24px;margin:12px 0}
.wardrobe-card{background:#1e1e3a;border:1px solid #333;border-radius:12px;
  padding:16px;margin:8px 0;text-align:center}
.tag{display:inline-block;background:#7C3AED33;color:#c4b5fd;
  border:1px solid #7C3AED66;border-radius:20px;padding:2px 10px;font-size:12px;margin:2px}
.score-bar{background:#333;border-radius:10px;height:8px;margin:4px 0}
.score-fill{background:linear-gradient(90deg,#7C3AED,#a78bfa);border-radius:10px;height:8px}
.hero-text{font-size:2.4rem;font-weight:800;
  background:linear-gradient(135deg,#7C3AED,#a78bfa,#c4b5fd);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px}
.subtitle{color:#9ca3af;font-size:1rem;margin-bottom:24px}
.stButton>button{border-radius:10px!important;font-weight:600!important}
.swipe-card{background:linear-gradient(160deg,#1e1e3a 0%,#2d1b4e 100%);
  border:2px solid #7C3AED;border-radius:20px;padding:32px 24px;text-align:center;
  min-height:320px;display:flex;flex-direction:column;align-items:center;justify-content:center}
.item-emoji{font-size:5rem;margin-bottom:12px}
.item-name{font-size:1.4rem;font-weight:700;color:#e9d5ff}
.item-desc{color:#9ca3af;font-size:0.9rem;margin-top:6px}
.metric-box{background:#1e1e3a;border:1px solid #7C3AED44;border-radius:12px;
  padding:16px;text-align:center}
.metric-value{font-size:2rem;font-weight:800;color:#a78bfa}
.metric-label{font-size:0.8rem;color:#9ca3af;margin-top:4px}
.photo-uploaded{border:2px solid #7C3AED;border-radius:12px;padding:8px;
  background:#1e1e3a;text-align:center}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "wardrobe": [],
        "swipe_index": 0,
        "outfit_suggestions": [],
        "page": "home",
        "swipe_history": [],
        "occasion": "casual",
        "city": "New York",
        "person_photo": None,       # bytes — user body photo
        "tryon_results": {},        # key → result image bytes
        "tryon_outfit_index": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 👗 OutfitAI")
    st.markdown("---")

    # API status
    anthropic_key = get_secret("ANTHROPIC_API_KEY")
    fashn_key     = get_secret("FASHN_API_KEY")
    st.success("✓ Claude AI connected") if anthropic_key else st.warning("⚠️ No Anthropic key")
    st.success("✓ FASHN Try-On connected") if fashn_key else st.warning("⚠️ No FASHN key")

    st.markdown("---")

    # Photo upload — persists across pages
    st.markdown("### 📸 Your Photo")
    uploaded_photo = st.file_uploader(
        "Full-body photo for try-on",
        type=["jpg","jpeg","png"],
        help="Stand facing forward, full body visible, plain background works best",
        key="sidebar_photo_upload"
    )
    if uploaded_photo:
        st.session_state.person_photo = uploaded_photo.read()

    if st.session_state.person_photo:
        st.image(st.session_state.person_photo, use_column_width=True)
        st.caption("✓ Photo ready")
        if st.button("🗑 Remove photo", use_container_width=True):
            st.session_state.person_photo = None
            st.rerun()

    st.markdown("---")

    # Navigation
    st.markdown("### Navigation")
    pages = {
        "🏠 Home":             "home",
        "👕 Build Wardrobe":   "wardrobe_builder",
        "🗃️ My Wardrobe":     "my_wardrobe",
        "✨ Get Outfit":       "outfit",
        "👗 Virtual Try-On":   "tryon",
        "📊 Style Profile":    "profile",
    }
    for label, page_key in pages.items():
        if st.button(label, use_container_width=True,
                     type="primary" if st.session_state.page == page_key else "secondary"):
            st.session_state.page = page_key
            st.rerun()

    st.markdown("---")
    wc = len(st.session_state.wardrobe)
    sc = len(st.session_state.outfit_suggestions)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{wc}</div>'
                    f'<div class="metric-label">Items</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{sc}</div>'
                    f'<div class="metric-label">Outfits</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Settings")
    st.session_state.city = st.text_input("📍 City", value=st.session_state.city)
    occ_list = ["casual","work","date","formal","active","travel"]
    st.session_state.occasion = st.selectbox(
        "🎯 Occasion", occ_list,
        index=occ_list.index(st.session_state.occasion))


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ═══════════════════════════════════════════════════════════════════════════════
def page_home():
    st.markdown('<div class="hero-text">👗 OutfitAI</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">What to wear tomorrow — finally solved.</div>',
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    cards = [
        ("👕","Build Wardrobe","Swipe clothing cards or upload photos to build your wardrobe."),
        ("🤖","AI Styling","Color theory, occasion + weather intelligence combined."),
        ("👗","Virtual Try-On","See the outfit on your actual photo via FASHN AI."),
    ]
    for col, (emoji, title, desc) in zip([c1,c2,c3], cards):
        with col:
            st.markdown(f'<div class="outfit-card"><div style="font-size:2rem">{emoji}</div>'
                        f'<h3 style="color:#e9d5ff">{title}</h3>'
                        f'<p style="color:#9ca3af">{desc}</p></div>', unsafe_allow_html=True)

    st.markdown("---")
    wc = len(st.session_state.wardrobe)
    if wc == 0:
        st.info("👈 Start by building your wardrobe — go to **Build Wardrobe** in the sidebar.")
    elif wc < 5:
        st.warning(f"You have {wc} item(s). Add a few more for better suggestions!")
    else:
        st.success(f"✅ {wc} wardrobe items ready. Head to **Get Outfit** for today's look!")

    st.markdown("### How It Works")
    for n, t in [
        ("1","Upload your photo in the sidebar (once, used for every try-on)"),
        ("2","Build wardrobe: swipe cards or upload clothing photos"),
        ("3","Get Outfit — AI picks the best combination + Claude explains why"),
        ("4","Virtual Try-On — see it on your body in ~15 seconds"),
    ]:
        st.markdown(f"**{n}.** {t}")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: WARDROBE BUILDER (swipe + upload)
# ═══════════════════════════════════════════════════════════════════════════════
def page_wardrobe_builder():
    from catalog import CATALOG
    st.markdown("## 👕 Build Your Wardrobe")

    tab_swipe, tab_upload = st.tabs(["👆 Swipe Cards", "📷 Upload Photos"])

    # ── TAB 1: SWIPE ──────────────────────────────────────────────────────────
    with tab_swipe:
        st.markdown("Swipe through clothing items — tell us what you own.")
        idx   = st.session_state.swipe_index
        total = len(CATALOG)

        if idx >= total:
            st.balloons()
            st.success("🎉 Done! You've gone through all the clothing cards.")
            owned = [s for s in st.session_state.swipe_history
                     if s["action"] in ("own","love")]
            st.markdown(f"**{len(owned)} items added to your wardrobe.**")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Start Over", type="secondary", use_container_width=True):
                    st.session_state.swipe_index = 0
                    st.session_state.swipe_history = []
                    st.rerun()
            with col2:
                if st.button("✨ Get Outfit", type="primary", use_container_width=True):
                    st.session_state.page = "outfit"
                    st.rerun()
        else:
            item = CATALOG[idx]
            st.progress(idx/total, text=f"Card {idx+1} of {total} — {item['category']}")
            st.markdown("")

            _, card_col, _ = st.columns([1,2,1])
            with card_col:
                st.markdown(f"""
                <div class="swipe-card">
                    <div class="item-emoji">{item['emoji']}</div>
                    <div class="item-name">{item['name']}</div>
                    <div class="item-desc">{item['description']}</div>
                    <br>
                    {''.join(f'<span class="tag">{s}</span>' for s in item['styles'])}
                </div>""", unsafe_allow_html=True)

            st.markdown("")

            # Color picker after "own" tap
            if st.session_state.get(f"show_colors_{idx}"):
                st.markdown("#### 🎨 Pick the color(s) you own:")
                selected = st.multiselect("Colors", item["colors"],
                                          label_visibility="collapsed",
                                          key=f"color_pick_{idx}")
                if st.button("✓ Add to Wardrobe", type="primary", use_container_width=True):
                    colors = selected if selected else [item["colors"][0]]
                    existing = {w["id"] for w in st.session_state.wardrobe}
                    for color in colors:
                        witem = {
                            "id": f"{item['id']}_{color}",
                            "name": item["name"],
                            "category": item["category"],
                            "color": color,
                            "emoji": item["emoji"],
                            "styles": item["styles"],
                            "occasions": item["occasions"],
                            "formality": item["formality"],
                            "source": "swipe",
                            "uploaded_image": None,
                        }
                        if witem["id"] not in existing:
                            st.session_state.wardrobe.append(witem)
                    st.session_state.swipe_history.append({"item":item,"action":"own"})
                    st.session_state[f"show_colors_{idx}"] = False
                    st.session_state.swipe_index += 1
                    st.rerun()
            else:
                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.button("👎  Skip", use_container_width=True, type="secondary"):
                        st.session_state.swipe_history.append({"item":item,"action":"skip"})
                        st.session_state.swipe_index += 1
                        st.rerun()
                with b2:
                    if st.button("👍  I Own This!", use_container_width=True, type="primary"):
                        st.session_state[f"show_colors_{idx}"] = True
                        st.rerun()
                with b3:
                    if st.button("❤️  Love It", use_container_width=True, type="primary"):
                        st.session_state[f"show_colors_{idx}"] = True
                        st.rerun()

                st.caption("👎 Skip = don't own  |  👍 Own  |  ❤️ Love = favorite")

            with st.expander("⚡ Quick Add Basics"):
                if st.button("Add White T-Shirt + Black Jeans + White Sneakers"):
                    basics = [
                        {"id":"tshirt_white","name":"T-Shirt","category":"tops",
                         "color":"White","emoji":"👕","styles":["casual","minimal"],
                         "occasions":["casual","active"],"formality":1,
                         "source":"quick_add","uploaded_image":None},
                        {"id":"jeans_black","name":"Jeans","category":"bottoms",
                         "color":"Black","emoji":"👖","styles":["casual","versatile"],
                         "occasions":["casual","work"],"formality":2,
                         "source":"quick_add","uploaded_image":None},
                        {"id":"sneakers_white","name":"Sneakers","category":"footwear",
                         "color":"White","emoji":"👟","styles":["casual","sporty"],
                         "occasions":["casual","active"],"formality":1,
                         "source":"quick_add","uploaded_image":None},
                    ]
                    existing = {w["id"] for w in st.session_state.wardrobe}
                    for b in basics:
                        if b["id"] not in existing:
                            st.session_state.wardrobe.append(b)
                    st.success("✅ Basics added!")
                    st.rerun()

    # ── TAB 2: PHOTO UPLOAD ───────────────────────────────────────────────────
    with tab_upload:
        st.markdown("Upload photos of your actual clothes — AI classifies them automatically.")
        st.markdown("")

        upload_mode = st.radio(
            "Upload mode",
            ["📸 Full outfit photo (AI extracts each item)",
             "👕 Single item photo (one garment at a time)"],
            horizontal=True
        )

        uploaded_files = st.file_uploader(
            "Choose photo(s)",
            type=["jpg","jpeg","png"],
            accept_multiple_files=True,
            key="wardrobe_photo_upload"
        )

        if uploaded_files:
            st.markdown(f"**{len(uploaded_files)} photo(s) selected**")
            for f in uploaded_files:
                img_bytes = f.read()
                col_img, col_form = st.columns([1,2])

                with col_img:
                    st.image(img_bytes, use_column_width=True)

                with col_form:
                    st.markdown(f"**{f.name}**")
                    item_name     = st.text_input("Item name", value="My item",
                                                  key=f"name_{f.name}")
                    item_category = st.selectbox("Category",
                                                 ["tops","bottoms","outerwear",
                                                  "footwear","dresses","accessories"],
                                                 key=f"cat_{f.name}")
                    item_color    = st.text_input("Main color", value="Black",
                                                  key=f"color_{f.name}")
                    item_occasion = st.multiselect("Occasions",
                                                   ["casual","work","date","formal","active","travel"],
                                                   default=["casual"],
                                                   key=f"occ_{f.name}")
                    item_formality= st.slider("Formality", 1, 5, 2, key=f"form_{f.name}")

                    if st.button(f"➕ Add to Wardrobe", key=f"add_{f.name}", type="primary"):
                        item_id = f"upload_{f.name}_{item_color}".replace(" ","_")
                        existing = {w["id"] for w in st.session_state.wardrobe}
                        if item_id not in existing:
                            st.session_state.wardrobe.append({
                                "id":             item_id,
                                "name":           item_name,
                                "category":       item_category,
                                "color":          item_color,
                                "emoji":          "📷",
                                "styles":         ["versatile"],
                                "occasions":      item_occasion,
                                "formality":      item_formality,
                                "source":         "photo_upload",
                                "uploaded_image": img_bytes,  # ← real photo stored
                            })
                            st.success(f"✅ {item_name} added!")
                            st.rerun()
                        else:
                            st.warning("This item is already in your wardrobe.")

                st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: MY WARDROBE
# ═══════════════════════════════════════════════════════════════════════════════
def page_my_wardrobe():
    st.markdown("## 🗃️ My Wardrobe")
    wardrobe = st.session_state.wardrobe
    if not wardrobe:
        st.info("Your wardrobe is empty — go to **Build Wardrobe** to add items.")
        return

    st.markdown(f"**{len(wardrobe)} items** in your wardrobe")
    st.markdown("---")

    categories = {}
    for item in wardrobe:
        categories.setdefault(item["category"], []).append(item)

    for cat, items in categories.items():
        st.markdown(f"### {cat.title()} ({len(items)})")
        cols = st.columns(min(len(items), 4))
        for i, item in enumerate(items):
            with cols[i % 4]:
                if item.get("uploaded_image"):
                    st.image(item["uploaded_image"], use_column_width=True)
                else:
                    st.markdown(
                        f'<div class="wardrobe-card">'
                        f'<div style="font-size:2.5rem">{item["emoji"]}</div>'
                        f'<div style="font-weight:700;color:#e9d5ff">{item["name"]}</div>'
                        f'<div style="color:#9ca3af;font-size:0.85rem">{item["color"]}</div>'
                        f'</div>', unsafe_allow_html=True)
                st.caption(f"{item['name']} — {item['color']}")
                if st.button("🗑️ Remove", key=f"rm_{item['id']}", use_container_width=True):
                    st.session_state.wardrobe = [
                        w for w in wardrobe if w["id"] != item["id"]]
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

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="metric-box"><div class="metric-value">🌤</div>'
                    f'<div class="metric-label">{st.session_state.city}</div></div>',
                    unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-box"><div class="metric-value">🎯</div>'
                    f'<div class="metric-label">{st.session_state.occasion.title()}</div></div>',
                    unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{len(wardrobe)}</div>'
                    f'<div class="metric-label">Items</div></div>', unsafe_allow_html=True)

    st.markdown("")

    if st.button("🎲 Generate Outfit", type="primary", use_container_width=True):
        with st.spinner("🤖 Styling your outfit..."):
            engine = OutfitEngine(wardrobe=wardrobe,
                                  occasion=st.session_state.occasion,
                                  city=st.session_state.city)
            st.session_state.outfit_suggestions = engine.generate(n=3)
            st.session_state.tryon_results = {}
        st.rerun()

    if not st.session_state.outfit_suggestions:
        st.markdown("---")
        st.markdown("👆 Click **Generate Outfit** above to get your suggestions.")
        return

    st.markdown("---")
    st.markdown("### Your Outfit Options")

    for i, outfit in enumerate(st.session_state.outfit_suggestions):
        rank = ["🥇","🥈","🥉"][i]
        with st.expander(f"{rank} Outfit {i+1} — Score: {outfit['score']}/100",
                         expanded=(i==0)):
            # Item thumbnails
            item_cols = st.columns(len(outfit["items"]))
            for j, item in enumerate(outfit["items"]):
                with item_cols[j]:
                    if item.get("uploaded_image"):
                        st.image(item["uploaded_image"], use_column_width=True)
                    else:
                        st.markdown(
                            f'<div class="wardrobe-card">'
                            f'<div style="font-size:2.5rem">{item["emoji"]}</div>'
                            f'<div style="font-weight:700;color:#e9d5ff">{item["name"]}</div>'
                            f'<div style="color:#9ca3af;font-size:0.85rem">{item["color"]}</div>'
                            f'</div>', unsafe_allow_html=True)

            st.markdown("")
            ca, cb = st.columns(2)
            with ca:
                st.markdown("**Score Breakdown**")
                for label, val in outfit.get("score_breakdown",{}).items():
                    pct = int(val)
                    st.markdown(f"<small>{label}</small>", unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="score-bar"><div class="score-fill" '
                        f'style="width:{pct}%"></div></div>'
                        f'<small style="color:#9ca3af">{pct}/100</small>',
                        unsafe_allow_html=True)
            with cb:
                st.markdown("**Color Palette**")
                st.markdown("".join(f'<span class="tag">🎨 {c}</span> '
                                    for c in outfit.get("color_palette",[])),
                            unsafe_allow_html=True)
                st.markdown("**Rule**")
                st.markdown(f'<span class="tag">✓ {outfit.get("color_rule","—")}</span>',
                            unsafe_allow_html=True)

            st.markdown("")
            if outfit.get("ai_explanation"):
                st.markdown(
                    f'<div class="outfit-card">'
                    f'<div style="font-size:1.1rem;margin-bottom:8px">🤖 '
                    f'<strong style="color:#a78bfa">AI Stylist Says</strong></div>'
                    f'<div style="color:#e9d5ff;line-height:1.7">'
                    f'{outfit["ai_explanation"]}</div></div>', unsafe_allow_html=True)
            else:
                if st.button("💬 Get AI Explanation", key=f"explain_{i}"):
                    with st.spinner("Claude is styling..."):
                        engine = OutfitEngine(wardrobe=wardrobe,
                                             occasion=st.session_state.occasion,
                                             city=st.session_state.city)
                        st.session_state.outfit_suggestions[i]["ai_explanation"] = \
                            engine.explain_outfit(outfit)
                    st.rerun()

            st.markdown("")
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("✅ Wearing This!", key=f"wear_{i}", type="primary",
                             use_container_width=True):
                    st.success("Great choice! 🎉")
            with b2:
                if st.button("🔄 Try Another", key=f"skip_{i}", type="secondary",
                             use_container_width=True):
                    st.session_state.outfit_suggestions = []
                    st.session_state.tryon_results = {}
                    st.rerun()
            with b3:
                if st.button("👗 Virtual Try-On", key=f"tryon_btn_{i}", type="primary",
                             use_container_width=True):
                    if not st.session_state.person_photo:
                        st.warning("📸 Upload your photo in the sidebar first!")
                    else:
                        st.session_state.page = "tryon"
                        st.session_state.tryon_outfit_index = i
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: VIRTUAL TRY-ON
# ═══════════════════════════════════════════════════════════════════════════════
def page_tryon():
    st.markdown("## 👗 Virtual Try-On")
    st.markdown("See the outfit on your photo — powered by FASHN AI.")
    st.markdown("---")

    fashn_key = get_secret("FASHN_API_KEY")

    if not fashn_key:
        st.error("⚠️ FASHN_API_KEY not found in Streamlit Secrets.")
        return
    if not st.session_state.person_photo:
        st.warning("📸 Upload your photo in the sidebar first!")
        return
    if not st.session_state.outfit_suggestions:
        st.warning("✨ Generate an outfit first — go to **Get Outfit**.")
        if st.button("Go to Get Outfit"):
            st.session_state.page = "outfit"
            st.rerun()
        return

    # Outfit selector
    labels = [f"🥇 Outfit 1 (score {st.session_state.outfit_suggestions[0]['score']}/100)"]
    if len(st.session_state.outfit_suggestions) > 1:
        labels.append(f"🥈 Outfit 2 (score {st.session_state.outfit_suggestions[1]['score']}/100)")
    if len(st.session_state.outfit_suggestions) > 2:
        labels.append(f"🥉 Outfit 3 (score {st.session_state.outfit_suggestions[2]['score']}/100)")

    default = min(st.session_state.tryon_outfit_index, len(labels)-1)
    sel_label = st.selectbox("Choose outfit to try on:", labels, index=default)
    outfit_idx = labels.index(sel_label)
    outfit = st.session_state.outfit_suggestions[outfit_idx]

    # Show chosen outfit items
    st.markdown("#### Outfit selected:")
    item_cols = st.columns(max(len(outfit["items"]), 1))
    for j, item in enumerate(outfit["items"]):
        with item_cols[j]:
            if item.get("uploaded_image"):
                st.image(item["uploaded_image"], use_column_width=True)
            else:
                st.markdown(
                    f'<div class="wardrobe-card">'
                    f'<div style="font-size:2rem">{item["emoji"]}</div>'
                    f'<div style="font-weight:700;color:#e9d5ff;font-size:0.9rem">'
                    f'{item["name"]}</div>'
                    f'<div style="color:#9ca3af;font-size:0.8rem">{item["color"]}</div>'
                    f'</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Before / After columns
    col_before, col_after = st.columns(2)
    with col_before:
        st.markdown("**📸 Your photo**")
        st.image(st.session_state.person_photo, use_column_width=True)

    result_key = f"tryon_{outfit_idx}"
    cached = st.session_state.tryon_results.get(result_key)

    with col_after:
        st.markdown("**✨ With outfit**")
        if cached:
            st.image(cached, use_column_width=True)
        else:
            st.markdown(
                '<div class="outfit-card" style="text-align:center;min-height:300px;'
                'display:flex;align-items:center;justify-content:center">'
                '<div><div style="font-size:3rem">👗</div>'
                '<div style="color:#9ca3af;margin-top:12px">Click Generate below</div>'
                '</div></div>', unsafe_allow_html=True)

    st.markdown("")

    if cached:
        dc1, dc2 = st.columns(2)
        with dc1:
            st.download_button("⬇️ Download", data=cached,
                               file_name=f"outfitai_tryon_{outfit_idx+1}.jpg",
                               mime="image/jpeg", use_container_width=True)
        with dc2:
            if st.button("🔄 Re-generate", type="secondary", use_container_width=True):
                del st.session_state.tryon_results[result_key]
                st.rerun()
    else:
        if st.button("✨ Generate Try-On", type="primary", use_container_width=True):
            tryable = [i for i in outfit["items"]
                       if i["category"] in ("tops","bottoms","dresses")]
            if not tryable:
                st.error("No tops or bottoms in this outfit to try on.")
                return

            prog = st.progress(0, text="🚀 Starting FASHN pipeline...")
            engine = TryOnEngine(fashn_api_key=fashn_key)
            result = engine.run_outfit(
                person_bytes=st.session_state.person_photo,
                outfit_items=tryable,
                progress_cb=lambda pct, msg: prog.progress(pct, text=msg),
            )
            if result["success"] and result["result_image"]:
                st.session_state.tryon_results[result_key] = result["result_image"]
                st.rerun()
            else:
                st.error(f"Try-on failed: {result.get('error','Unknown error')}")
                st.caption("Check your credits at app.fashn.ai")

    # AI explanation if available
    if outfit.get("ai_explanation"):
        st.markdown("")
        st.markdown(
            f'<div class="outfit-card">'
            f'<div style="font-size:1rem;margin-bottom:8px">🤖 '
            f'<strong style="color:#a78bfa">Why This Works</strong></div>'
            f'<div style="color:#e9d5ff;line-height:1.7">'
            f'{outfit["ai_explanation"]}</div></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: STYLE PROFILE
# ═══════════════════════════════════════════════════════════════════════════════
def page_profile():
    st.markdown("## 📊 Your Style Profile")
    wardrobe = st.session_state.wardrobe
    if not wardrobe:
        st.info("Build your wardrobe first.")
        return

    engine  = OutfitEngine(wardrobe=wardrobe, occasion="casual",
                           city=st.session_state.city)
    profile = engine.analyze_style_profile()

    st.markdown(
        f'<div class="outfit-card" style="text-align:center">'
        f'<div style="font-size:3rem">{profile["emoji"]}</div>'
        f'<div style="font-size:1.8rem;font-weight:800;color:#e9d5ff;margin:12px 0">'
        f'{profile["archetype"]}</div>'
        f'<div style="color:#9ca3af">{profile["description"]}</div>'
        f'</div>', unsafe_allow_html=True)

    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🎨 Dominant Colors")
        for color, count in profile.get("dominant_colors",[])[:8]:
            st.markdown(f"**{color}** — {count} item{'s' if count>1 else ''}")
        st.markdown("### 👔 Wardrobe Breakdown")
        cats = {}
        for item in wardrobe:
            cats[item["category"]] = cats.get(item["category"],0)+1
        for cat, cnt in sorted(cats.items(), key=lambda x:-x[1]):
            pct = int(cnt/len(wardrobe)*100)
            st.markdown(f"<small>{cat.title()}</small>", unsafe_allow_html=True)
            st.markdown(
                f'<div class="score-bar"><div class="score-fill" style="width:{pct}%">'
                f'</div></div><small style="color:#9ca3af">{cnt} items ({pct}%)</small>',
                unsafe_allow_html=True)
    with c2:
        st.markdown("### 💡 Wardrobe Gaps")
        for gap in profile.get("gaps",[]):
            st.markdown(f"- {gap}")


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════
p = st.session_state.page
if   p == "home":            page_home()
elif p == "wardrobe_builder":page_wardrobe_builder()
elif p == "my_wardrobe":     page_my_wardrobe()
elif p == "outfit":          page_outfit()
elif p == "tryon":           page_tryon()
elif p == "profile":         page_profile()
