import streamlit as st, random, io, base64

# ── Safe imports ──────────────────────────────────────────────────────────────
try:
    from engine import OutfitEngine, get_secret
except Exception as e:
    st.error(f"❌ engine.py import error: {e}")
    st.stop()

try:
    from tryon import TryOnEngine
    TRYON_OK = True
except Exception as e:
    TRYON_OK = False

try:
    import anthropic
    ANTHROPIC_OK = True
except Exception:
    ANTHROPIC_OK = False

# ── Use Claude vision to extract clothing from uploaded photo ─────────────────
def extract_clothing_from_photo(image_bytes: bytes, api_key: str) -> list:
    """
    Send photo to Claude Vision. Ask it to identify distinct clothing items.
    Returns list of dicts: {name, category, color, styles, occasions, formality}
    """
    if not api_key or not ANTHROPIC_OK:
        return []
    try:
        client = anthropic.Anthropic(api_key=api_key)
        b64 = base64.b64encode(image_bytes).decode()
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64",
                                "media_type": "image/jpeg",
                                "data": b64}},
                    {"type": "text",
                     "text": """Analyze this clothing photo and identify each distinct garment visible.
For EACH item return a JSON array (and nothing else) like:
[
  {
    "name": "White T-Shirt",
    "category": "tops",
    "color": "White",
    "styles": ["casual","minimal"],
    "occasions": ["casual","active"],
    "formality": 1
  }
]
Categories must be one of: tops, bottoms, outerwear, footwear, dresses, accessories
Formality: 1=very casual, 5=very formal
Return ONLY the JSON array, no explanation."""}
                ]
            }]
        )
        import json
        text = msg.content[0].text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        return []

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="OutfitAI", page_icon="👗", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp{background-color:#0f0f1a;color:#f0f0f0}
[data-testid="stSidebar"]{background-color:#1a1a2e}
.outfit-card{background:linear-gradient(135deg,#1e1e3a,#2a1a4a);
  border:1px solid #7C3AED44;border-radius:16px;padding:24px;margin:12px 0}
.wardrobe-card{background:#1e1e3a;border:1px solid #333;border-radius:12px;
  padding:12px;margin:6px 0;text-align:center}
.tag{display:inline-block;background:#7C3AED33;color:#c4b5fd;
  border:1px solid #7C3AED66;border-radius:20px;padding:2px 10px;font-size:12px;margin:2px}
.score-bar{background:#333;border-radius:10px;height:8px;margin:4px 0}
.score-fill{background:linear-gradient(90deg,#7C3AED,#a78bfa);border-radius:10px;height:8px}
.hero-text{font-size:2.4rem;font-weight:800;
  background:linear-gradient(135deg,#7C3AED,#a78bfa,#c4b5fd);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.subtitle{color:#9ca3af;font-size:1rem;margin-bottom:24px}
.stButton>button{border-radius:10px!important;font-weight:600!important}
.swipe-card{background:linear-gradient(160deg,#1e1e3a,#2d1b4e);
  border:2px solid #7C3AED;border-radius:20px;padding:32px 24px;text-align:center;
  min-height:300px;display:flex;flex-direction:column;align-items:center;justify-content:center}
.metric-box{background:#1e1e3a;border:1px solid #7C3AED44;border-radius:12px;
  padding:16px;text-align:center}
.metric-value{font-size:2rem;font-weight:800;color:#a78bfa}
.metric-label{font-size:0.8rem;color:#9ca3af;margin-top:4px}
</style>""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
DEFAULTS = {
    "wardrobe": [], "swipe_index": 0, "outfit_suggestions": [],
    "page": "home", "swipe_history": [], "occasion": "casual",
    "city": "New York", "person_photo": None, "tryon_results": {},
    "tryon_outfit_index": 0,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar ───────────────────────────────────────────────────────────────────
# Collect all sidebar interactions FIRST, handle navigation AFTER the with block
_nav_clicked   = None
_remove_photo  = False

with st.sidebar:
    st.markdown("## 👗 OutfitAI")
    st.markdown("---")

    anthropic_key = get_secret("ANTHROPIC_API_KEY")
    fashn_key     = get_secret("FASHN_API_KEY")

    if anthropic_key:
        st.success("✓ Claude AI connected")
    else:
        st.warning("⚠️ No Anthropic key in Secrets")

    if fashn_key:
        st.success("✓ FASHN Try-On connected")
    else:
        st.warning("⚠️ No FASHN key in Secrets")

    st.markdown("---")

    st.markdown("### 📸 Your Photo")
    up = st.file_uploader("Full-body photo", type=["jpg","jpeg","png"],
                           key="sidebar_photo_upload")
    if up:
        st.session_state.person_photo = up.read()
    if st.session_state.person_photo:
        st.image(st.session_state.person_photo, use_column_width=True)
        st.caption("✓ Ready for try-on")
        if st.button("🗑 Remove photo", use_container_width=True, key="remove_photo"):
            _remove_photo = True

    st.markdown("---")
    st.markdown("### Navigation")

    NAV = [
        ("🏠 Home",             "home"),
        ("👕 Build Wardrobe",   "wardrobe_builder"),
        ("🗃️ My Wardrobe",     "my_wardrobe"),
        ("✨ Get Outfit",       "outfit"),
        ("👗 Virtual Try-On",   "tryon"),
        ("📊 Style Profile",    "profile"),
    ]
    for label, pkey in NAV:
        t = "primary" if st.session_state.page == pkey else "secondary"
        if st.button(label, use_container_width=True, type=t, key=f"nav_{pkey}"):
            _nav_clicked = pkey   # just record — don't rerun inside sidebar

    st.markdown("---")
    wc = len(st.session_state.wardrobe)
    sc = len(st.session_state.outfit_suggestions)
    c1, c2 = st.columns(2)
    c1.markdown(f'<div class="metric-box"><div class="metric-value">{wc}</div>'
                f'<div class="metric-label">Items</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-box"><div class="metric-value">{sc}</div>'
                f'<div class="metric-label">Outfits</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.session_state.city = st.text_input("📍 City", value=st.session_state.city)
    occ_list = ["casual","work","date","formal","active","travel"]
    st.session_state.occasion = st.selectbox(
        "🎯 Occasion", occ_list,
        index=occ_list.index(st.session_state.occasion))

# ── Handle sidebar actions OUTSIDE the with block — safe to rerun here ────────
if _remove_photo:
    st.session_state.person_photo = None
    st.rerun()

if _nav_clicked:
    st.session_state.page = _nav_clicked
    st.rerun()



# ═══════════════════════════════════════════════════════════════════════════════
# HOME
# ═══════════════════════════════════════════════════════════════════════════════
def page_home():
    st.markdown('<div class="hero-text">👗 OutfitAI</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">What to wear tomorrow — finally solved.</div>',
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="outfit-card"><div style="font-size:2rem">👕</div>'
                    '<h3 style="color:#e9d5ff">Build Wardrobe</h3>'
                    '<p style="color:#9ca3af">Swipe cards or upload clothing photos '
                    '— AI extracts each item automatically.</p></div>',
                    unsafe_allow_html=True)
        btn_build = st.button("→ Build Wardrobe", key="home_build", use_container_width=True)
    with c2:
        st.markdown('<div class="outfit-card"><div style="font-size:2rem">🤖</div>'
                    '<h3 style="color:#e9d5ff">AI Styling</h3>'
                    '<p style="color:#9ca3af">Color theory, weather + occasion '
                    'intelligence combined into one outfit score.</p></div>',
                    unsafe_allow_html=True)
        btn_outfit = st.button("→ Get Outfit", key="home_outfit", use_container_width=True)
    with c3:
        st.markdown('<div class="outfit-card"><div style="font-size:2rem">👗</div>'
                    '<h3 style="color:#e9d5ff">Virtual Try-On</h3>'
                    '<p style="color:#9ca3af">See the outfit on your actual photo '
                    'powered by FASHN AI in ~15 seconds.</p></div>',
                    unsafe_allow_html=True)
        btn_tryon = st.button("→ Try-On", key="home_tryon", use_container_width=True)

    # Handle AFTER columns close — rerun is safe here
    if btn_build:
        st.session_state.page = "wardrobe_builder"; st.rerun()
    if btn_outfit:
        st.session_state.page = "outfit"; st.rerun()
    if btn_tryon:
        st.session_state.page = "tryon"; st.rerun()

    st.markdown("---")
    wc = len(st.session_state.wardrobe)
    if wc == 0:
        st.info("👈 Start by building your wardrobe in the sidebar navigation.")
    elif wc < 3:
        st.warning(f"You have {wc} item(s). Add at least 3 for outfit suggestions.")
    else:
        st.success(f"✅ {wc} items ready. Head to **Get Outfit** for today's look!")


# ═══════════════════════════════════════════════════════════════════════════════
# WARDROBE BUILDER
# ═══════════════════════════════════════════════════════════════════════════════
def page_wardrobe_builder():
    from catalog import CATALOG
    st.markdown("## 👕 Build Your Wardrobe")
    tab_swipe, tab_upload = st.tabs(["👆 Swipe Cards", "📷 Upload & Auto-Extract"])

    # ── TAB 1: SWIPE ──────────────────────────────────────────────────────────
    with tab_swipe:
        st.markdown("Swipe through clothing cards — tell us what you own.")
        idx = st.session_state.swipe_index
        total = len(CATALOG)

        if idx >= total:
            st.balloons()
            owned = [s for s in st.session_state.swipe_history
                     if s["action"] in ("own","love")]
            st.success(f"🎉 Done! {len(owned)} items added to your wardrobe.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Start Over", type="secondary", use_container_width=True):
                    st.session_state.swipe_index = 0
                    st.session_state.swipe_history = []
                    st.rerun()
            with col2:
                if st.button("✨ Get Outfit", type="primary", use_container_width=True):
                    st.session_state.page = "outfit"; st.rerun()
        else:
            item = CATALOG[idx]
            st.progress(idx/total, text=f"Card {idx+1} of {total} — {item['category']}")

            _, cc, _ = st.columns([1,2,1])
            with cc:
                st.markdown(
                    f'<div class="swipe-card">'
                    f'<div style="font-size:5rem">{item["emoji"]}</div>'
                    f'<div style="font-size:1.4rem;font-weight:700;color:#e9d5ff">{item["name"]}</div>'
                    f'<div style="color:#9ca3af;font-size:0.9rem">{item["description"]}</div><br>'
                    f'{"".join(f"<span class=tag>{s}</span>" for s in item["styles"])}'
                    f'</div>', unsafe_allow_html=True)

            st.markdown("")

            if st.session_state.get(f"show_colors_{idx}"):
                st.markdown("#### 🎨 Pick the color(s) you own:")
                picked = st.multiselect("Colors", item["colors"],
                                        label_visibility="collapsed",
                                        key=f"cp_{idx}")
                if st.button("✓ Add to Wardrobe", type="primary",
                             use_container_width=True, key=f"add_sw_{idx}"):
                    colors = picked if picked else [item["colors"][0]]
                    existing = {w["id"] for w in st.session_state.wardrobe}
                    for color in colors:
                        witem = {
                            "id": f"{item['id']}_{color}",
                            "name": item["name"], "category": item["category"],
                            "color": color, "emoji": item["emoji"],
                            "styles": item["styles"], "occasions": item["occasions"],
                            "formality": item["formality"],
                            "source": "swipe", "uploaded_image": None,
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
                    if st.button("👎 Skip", use_container_width=True,
                                 type="secondary", key=f"skip_{idx}"):
                        st.session_state.swipe_history.append({"item":item,"action":"skip"})
                        st.session_state.swipe_index += 1
                        st.rerun()
                with b2:
                    if st.button("👍 I Own This", use_container_width=True,
                                 type="primary", key=f"own_{idx}"):
                        st.session_state[f"show_colors_{idx}"] = True
                        st.rerun()
                with b3:
                    if st.button("❤️ Love It", use_container_width=True,
                                 type="primary", key=f"love_{idx}"):
                        st.session_state[f"show_colors_{idx}"] = True
                        st.rerun()
                st.caption("👎 Don't own  |  👍 Own it  |  ❤️ Favorite")

            with st.expander("⚡ Quick Add Basics"):
                if st.button("Add White T-Shirt + Black Jeans + White Sneakers",
                             key="quick_basics"):
                    basics = [
                        {"id":"tshirt_white","name":"T-Shirt","category":"tops",
                         "color":"White","emoji":"👕","styles":["casual","minimal"],
                         "occasions":["casual","active"],"formality":1,
                         "source":"quick","uploaded_image":None},
                        {"id":"jeans_black","name":"Jeans","category":"bottoms",
                         "color":"Black","emoji":"👖","styles":["casual","versatile"],
                         "occasions":["casual","work"],"formality":2,
                         "source":"quick","uploaded_image":None},
                        {"id":"sneakers_white","name":"Sneakers","category":"footwear",
                         "color":"White","emoji":"👟","styles":["casual","sporty"],
                         "occasions":["casual","active"],"formality":1,
                         "source":"quick","uploaded_image":None},
                    ]
                    existing = {w["id"] for w in st.session_state.wardrobe}
                    added = 0
                    for b in basics:
                        if b["id"] not in existing:
                            st.session_state.wardrobe.append(b)
                            added += 1
                    st.success(f"✅ Added {added} basic item(s)!")
                    st.rerun()

    # ── TAB 2: PHOTO UPLOAD + AUTO-EXTRACT ───────────────────────────────────
    with tab_upload:
        st.markdown("Upload a photo of a clothing item — "
                    "**Claude Vision extracts it automatically**.")

        if not anthropic_key:
            st.warning("⚠️ Anthropic API key required for auto-extraction. "
                       "Add it to Streamlit Secrets.")

        files = st.file_uploader(
            "Upload clothing photo(s)",
            type=["jpg","jpeg","png"],
            accept_multiple_files=True,
            key="wardrobe_upload"
        )

        if files:
            for f in files:
                img_bytes = f.read()
                st.markdown(f"---\n**{f.name}**")
                col_img, col_info = st.columns([1, 2])

                with col_img:
                    st.image(img_bytes, use_column_width=True)

                with col_info:
                    # Auto-extract button
                    extract_key = f"extracted_{f.name}"
                    if st.button(f"🤖 Auto-Extract with AI", key=f"extract_{f.name}",
                                 type="primary", use_container_width=True):
                        with st.spinner("Claude is analyzing your clothing…"):
                            items = extract_clothing_from_photo(img_bytes, anthropic_key)
                            if items:
                                st.session_state[extract_key] = items
                                st.success(f"✅ Found {len(items)} item(s)!")
                            else:
                                st.error("Could not extract items. "
                                         "Try manual entry below.")

                    # Show extracted items with confirm buttons
                    if extract_key in st.session_state:
                        for ei, extracted in enumerate(st.session_state[extract_key]):
                            with st.container():
                                st.markdown(f"**{extracted['name']}** — "
                                            f"{extracted['color']} | "
                                            f"{extracted['category']}")
                                if st.button(f"➕ Add to Wardrobe",
                                             key=f"add_ext_{f.name}_{ei}",
                                             use_container_width=True):
                                    item_id = f"photo_{f.name}_{ei}_{extracted['color']}"
                                    existing = {w["id"] for w in st.session_state.wardrobe}
                                    if item_id not in existing:
                                        st.session_state.wardrobe.append({
                                            "id":             item_id,
                                            "name":           extracted["name"],
                                            "category":       extracted["category"],
                                            "color":          extracted["color"],
                                            "emoji":          "📷",
                                            "styles":         extracted.get("styles",["versatile"]),
                                            "occasions":      extracted.get("occasions",["casual"]),
                                            "formality":      extracted.get("formality", 2),
                                            "source":         "photo_upload",
                                            "uploaded_image": img_bytes,
                                        })
                                        st.success(f"✅ {extracted['name']} added!")
                                        st.rerun()

                    st.markdown("**— or add manually —**")
                    name     = st.text_input("Name", value="My Item",
                                             key=f"mn_{f.name}")
                    cat      = st.selectbox("Category",
                                            ["tops","bottoms","outerwear",
                                             "footwear","dresses","accessories"],
                                            key=f"mc_{f.name}")
                    color    = st.text_input("Color", value="Black",
                                             key=f"mcol_{f.name}")
                    occasion = st.multiselect("Occasions",
                                             ["casual","work","date","formal",
                                              "active","travel"],
                                             default=["casual"],
                                             key=f"mocc_{f.name}")
                    formality = st.slider("Formality", 1, 5, 2, key=f"mf_{f.name}")

                    if st.button(f"➕ Add Manually", key=f"addm_{f.name}",
                                 use_container_width=True):
                        item_id = f"manual_{f.name}_{color}".replace(" ","_")
                        existing = {w["id"] for w in st.session_state.wardrobe}
                        if item_id not in existing:
                            st.session_state.wardrobe.append({
                                "id": item_id, "name": name,
                                "category": cat, "color": color,
                                "emoji": "📷", "styles": ["versatile"],
                                "occasions": occasion, "formality": formality,
                                "source": "photo_upload",
                                "uploaded_image": img_bytes,
                            })
                            st.success(f"✅ {name} added!")
                            st.rerun()
                        else:
                            st.warning("Already in wardrobe.")


# ═══════════════════════════════════════════════════════════════════════════════
# MY WARDROBE
# ═══════════════════════════════════════════════════════════════════════════════
def page_my_wardrobe():
    st.markdown("## 🗃️ My Wardrobe")
    wardrobe = st.session_state.wardrobe
    if not wardrobe:
        st.info("Wardrobe is empty — go to **Build Wardrobe**.")
        if st.button("👕 Build Wardrobe", type="primary"):
            st.session_state.page = "wardrobe_builder"; st.rerun()
        return

    st.markdown(f"**{len(wardrobe)} items** in your wardrobe")
    st.markdown("---")

    cats = {}
    for item in wardrobe:
        cats.setdefault(item["category"], []).append(item)

    for cat, items in cats.items():
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
                st.caption(f"{item['name']} · {item['color']}")
                if st.button("🗑", key=f"rm_{item['id']}", use_container_width=True):
                    st.session_state.wardrobe = [
                        w for w in wardrobe if w["id"] != item["id"]]
                    st.rerun()

    st.markdown("---")
    if st.button("🗑️ Clear All", type="secondary"):
        st.session_state.wardrobe = []
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# GET OUTFIT
# ═══════════════════════════════════════════════════════════════════════════════
def page_outfit():
    st.markdown("## ✨ Today's Outfit Suggestion")
    wardrobe = st.session_state.wardrobe

    if len(wardrobe) < 3:
        st.warning("Add at least 3 wardrobe items first.")
        if st.button("👕 Build Wardrobe"):
            st.session_state.page = "wardrobe_builder"; st.rerun()
        return

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-box"><div class="metric-value">🌤</div>'
                f'<div class="metric-label">{st.session_state.city}</div></div>',
                unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-box"><div class="metric-value">🎯</div>'
                f'<div class="metric-label">{st.session_state.occasion.title()}</div></div>',
                unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-box"><div class="metric-value">{len(wardrobe)}</div>'
                f'<div class="metric-label">Items</div></div>', unsafe_allow_html=True)
    st.markdown("")

    if st.button("🎲 Generate Outfit", type="primary", use_container_width=True):
        with st.spinner("🤖 Building your outfit…"):
            try:
                engine = OutfitEngine(
                    wardrobe=wardrobe,
                    occasion=st.session_state.occasion,
                    city=st.session_state.city,
                )
                suggestions = engine.generate(n=3)
                st.session_state.outfit_suggestions = suggestions
                st.session_state.tryon_results = {}
            except Exception as e:
                st.error(f"Outfit engine error: {e}")
                return
        st.rerun()

    if not st.session_state.outfit_suggestions:
        st.info("👆 Click **Generate Outfit** to get your suggestions.")
        return

    st.markdown("---")
    st.markdown("### Your Outfit Options")

    for i, outfit in enumerate(st.session_state.outfit_suggestions):
        rank = ["🥇","🥈","🥉"][i]
        with st.expander(f"{rank} Outfit {i+1}  —  Score: {outfit['score']}/100",
                         expanded=(i==0)):
            # Item thumbnails — real photo if uploaded, else emoji card
            icols = st.columns(max(len(outfit["items"]), 1))
            for j, item in enumerate(outfit["items"]):
                with icols[j]:
                    if item.get("uploaded_image"):
                        st.image(item["uploaded_image"], use_column_width=True)
                        st.caption(f"{item['name']} · {item['color']}")
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
                        f'<div class="score-bar"><div class="score-fill"'
                        f' style="width:{pct}%"></div></div>'
                        f'<small style="color:#9ca3af">{pct}/100</small>',
                        unsafe_allow_html=True)
            with cb:
                st.markdown("**Colors**")
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
                    f'<strong style="color:#a78bfa">🤖 AI Stylist Says</strong><br><br>'
                    f'<span style="color:#e9d5ff;line-height:1.7">'
                    f'{outfit["ai_explanation"]}</span></div>',
                    unsafe_allow_html=True)
            else:
                if st.button("💬 Get AI Explanation", key=f"exp_{i}"):
                    with st.spinner("Claude is styling…"):
                        try:
                            eng = OutfitEngine(wardrobe=wardrobe,
                                              occasion=st.session_state.occasion,
                                              city=st.session_state.city)
                            st.session_state.outfit_suggestions[i]["ai_explanation"] = \
                                eng.explain_outfit(outfit)
                        except Exception as e:
                            st.error(f"AI explanation error: {e}")
                    st.rerun()

            st.markdown("")
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("✅ Wearing This!", key=f"wear_{i}",
                             type="primary", use_container_width=True):
                    st.success("Great choice! 🎉")
            with b2:
                if st.button("🔄 Try Another", key=f"regen_{i}",
                             type="secondary", use_container_width=True):
                    st.session_state.outfit_suggestions = []
                    st.session_state.tryon_results = {}
                    st.rerun()
            with b3:
                if st.button("👗 Virtual Try-On", key=f"tryon_{i}",
                             type="primary", use_container_width=True):
                    if not st.session_state.person_photo:
                        st.warning("📸 Upload your photo in the sidebar first!")
                    else:
                        st.session_state.tryon_outfit_index = i
                        st.session_state.page = "tryon"; st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# VIRTUAL TRY-ON
# ═══════════════════════════════════════════════════════════════════════════════
def page_tryon():
    st.markdown("## 👗 Virtual Try-On")
    st.markdown("See the outfit on your photo — powered by FASHN AI.")
    st.markdown("---")

    fashn_key = get_secret("FASHN_API_KEY")

    if not fashn_key:
        st.error("⚠️ FASHN_API_KEY missing from Streamlit Secrets.")
        return
    if not st.session_state.person_photo:
        st.warning("📸 Upload your photo in the sidebar first!")
        return
    if not st.session_state.outfit_suggestions:
        st.warning("✨ Generate an outfit first.")
        if st.button("Go to Get Outfit"):
            st.session_state.page = "outfit"; st.rerun()
        return

    # Outfit picker
    outfits = st.session_state.outfit_suggestions
    labels  = [f"{'🥇🥈🥉'[i]} Outfit {i+1}  (score {outfits[i]['score']}/100)"
               for i in range(len(outfits))]
    sel = st.selectbox("Choose outfit:", labels,
                       index=min(st.session_state.tryon_outfit_index, len(labels)-1))
    oidx   = labels.index(sel)
    outfit = outfits[oidx]

    # Show items
    st.markdown("#### Selected outfit:")
    icols = st.columns(max(len(outfit["items"]), 1))
    for j, item in enumerate(outfit["items"]):
        with icols[j]:
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

    col_before, col_after = st.columns(2)
    with col_before:
        st.markdown("**📸 Your photo**")
        st.image(st.session_state.person_photo, use_column_width=True)

    result_key = f"tryon_{oidx}"
    cached     = st.session_state.tryon_results.get(result_key)

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
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("⬇️ Download", data=cached,
                               file_name=f"outfitai_outfit{oidx+1}.jpg",
                               mime="image/jpeg", use_container_width=True)
        with d2:
            if st.button("🔄 Re-generate", type="secondary", use_container_width=True):
                del st.session_state.tryon_results[result_key]
                st.rerun()
    else:
        tryable = [i for i in outfit["items"]
                   if i["category"] in ("tops","bottoms","dresses")]
        if not tryable:
            st.error("No tops or bottoms in this outfit to try on.")
        else:
            if st.button("✨ Generate Try-On", type="primary", use_container_width=True):
                prog = st.progress(0, text="🚀 Starting FASHN…")
                engine = TryOnEngine(fashn_key)
                result = engine.run_outfit(
                    person=st.session_state.person_photo,
                    items=tryable,
                    progress=lambda p, m: prog.progress(p, text=m),
                )
                if result["success"] and result["result_image"]:
                    st.session_state.tryon_results[result_key] = result["result_image"]
                    st.rerun()
                else:
                    st.error(f"Try-on failed: {result.get('error','Unknown')}")
                    st.caption("Check your credits at app.fashn.ai/api")

    if outfit.get("ai_explanation"):
        st.markdown("")
        st.markdown(
            f'<div class="outfit-card">'
            f'<strong style="color:#a78bfa">🤖 Why This Works</strong><br><br>'
            f'<span style="color:#e9d5ff;line-height:1.7">'
            f'{outfit["ai_explanation"]}</span></div>',
            unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE PROFILE
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
        for color, cnt in profile.get("dominant_colors",[])[:8]:
            st.markdown(f"**{color}** — {cnt} item{'s' if cnt>1 else ''}")
    with c2:
        st.markdown("### 💡 Wardrobe Gaps")
        for gap in profile.get("gaps",[]):
            st.markdown(f"- {gap}")


# ── Router ────────────────────────────────────────────────────────────────────
p = st.session_state.page
if   p == "home":             page_home()
elif p == "wardrobe_builder": page_wardrobe_builder()
elif p == "my_wardrobe":      page_my_wardrobe()
elif p == "outfit":           page_outfit()
elif p == "tryon":            page_tryon()
elif p == "profile":          page_profile()
