import streamlit as st
import random
import base64
import json

# ── Safe imports ──────────────────────────────────────────────────────────────
try:
    from engine import OutfitEngine, get_secret
except ImportError as _e:
    st.error(f"engine.py import error: {_e}")
    st.stop()

try:
    from tryon import TryOnEngine
    TRYON_OK = True
except ImportError:
    TRYON_OK = False

try:
    import anthropic
    ANTHROPIC_OK = True
except ImportError:
    ANTHROPIC_OK = False


def fetch_product_image(item_name, color, category):
    """
    Generate a real clothing product image using Pollinations.ai (free, no API key).
    URL format: https://image.pollinations.ai/prompt/{prompt}&width=400&height=500&model=flux
    """
    import requests
    from urllib.parse import quote

    # Craft a detailed prompt for a clean product shot
    prompt = (
        f"{color} {item_name}, fashion product photo, "
        f"flat lay on white background, studio lighting, "
        f"high quality clothing photography, no people"
    )
    encoded = quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=400&height=500&model=flux&nologo=true&enhance=true"
    )

    try:
        r = requests.get(url, timeout=30)
        ct = r.headers.get("content-type", "")
        if r.status_code == 200 and "image" in ct and len(r.content) > 5000:
            return r.content
    except Exception:
        pass

    return None




def _parse_claude_json(text):
    text = text.strip()
    if "```" in text:
        for part in text.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("[") or part.startswith("{"):
                return json.loads(part)
    return json.loads(text)


def extract_clothing_from_photo(image_bytes, api_key):
    if not api_key or not ANTHROPIC_OK:
        return [], "Anthropic API key missing or library not installed"
    prompt = (
        "Analyze this clothing photo. Identify every distinct garment. "
        "Return ONLY a raw JSON array — no markdown, no explanation. Format:\n"
        '[{"name":"White T-Shirt","category":"tops","color":"White",'
        '"styles":["casual"],"occasions":["casual"],"formality":1}]\n'
        "category: tops | bottoms | outerwear | footwear | dresses | accessories\n"
        "formality: 1=casual to 5=formal"
    )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        b64 = base64.b64encode(image_bytes).decode()
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": prompt}
            ]}]
        )
        items = _parse_claude_json(msg.content[0].text)
        return items, None
    except Exception as err:
        return [], str(err)


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
for _k, _v in DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Sidebar — collect clicks, rerun AFTER the with block ─────────────────────
_nav_clicked  = None
_remove_photo = False

with st.sidebar:
    st.markdown("## 👗 OutfitAI")
    st.markdown("---")

    anthropic_key = get_secret("ANTHROPIC_API_KEY")
    fashn_key     = get_secret("FASHN_API_KEY")

    if anthropic_key:
        st.success("✓ Claude AI connected")
    else:
        st.warning("⚠️ Add ANTHROPIC_API_KEY to Secrets")

    if fashn_key:
        st.success("✓ FASHN Try-On connected")
    else:
        st.warning("⚠️ Add FASHN_API_KEY to Secrets")

    st.markdown("---")
    st.markdown("### 📸 Your Photo")
    _up = st.file_uploader("Full-body photo", type=["jpg","jpeg","png"],
                            key="sidebar_photo_upload")
    if _up:
        st.session_state.person_photo = _up.read()
    if st.session_state.person_photo:
        st.image(st.session_state.person_photo, width=250)
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
    for _label, _pkey in NAV:
        _t = "primary" if st.session_state.page == _pkey else "secondary"
        if st.button(_label, use_container_width=True, type=_t, key=f"nav_{_pkey}"):
            _nav_clicked = _pkey   # record only — NO rerun inside sidebar

    st.markdown("---")
    _wc = len(st.session_state.wardrobe)
    _sc = len(st.session_state.outfit_suggestions)
    _c1, _c2 = st.columns(2)
    _c1.markdown(f'<div class="metric-box"><div class="metric-value">{_wc}</div>'
                 f'<div class="metric-label">Items</div></div>', unsafe_allow_html=True)
    _c2.markdown(f'<div class="metric-box"><div class="metric-value">{_sc}</div>'
                 f'<div class="metric-label">Outfits</div></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.session_state.city = st.text_input("📍 City", value=st.session_state.city)
    _occ_list = ["casual","work","date","formal","active","travel"]
    st.session_state.occasion = st.selectbox(
        "🎯 Occasion", _occ_list,
        index=_occ_list.index(st.session_state.occasion))

# ── Handle sidebar actions AFTER the with block (safe to rerun here) ─────────
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
                    '— AI auto-extracts each item.</p></div>', unsafe_allow_html=True)
        _b1 = st.button("→ Build Wardrobe", key="home_build", use_container_width=True)
    with c2:
        st.markdown('<div class="outfit-card"><div style="font-size:2rem">🤖</div>'
                    '<h3 style="color:#e9d5ff">AI Styling</h3>'
                    '<p style="color:#9ca3af">Color theory + occasion intelligence '
                    'combined into one outfit score.</p></div>', unsafe_allow_html=True)
        _b2 = st.button("→ Get Outfit", key="home_outfit", use_container_width=True)
    with c3:
        st.markdown('<div class="outfit-card"><div style="font-size:2rem">👗</div>'
                    '<h3 style="color:#e9d5ff">Virtual Try-On</h3>'
                    '<p style="color:#9ca3af">See the outfit on your actual photo '
                    'via FASHN AI in ~15 seconds.</p></div>', unsafe_allow_html=True)
        _b3 = st.button("→ Try-On", key="home_tryon", use_container_width=True)

    # Rerun AFTER columns close
    if _b1:
        st.session_state.page = "wardrobe_builder"; st.rerun()
    if _b2:
        st.session_state.page = "outfit"; st.rerun()
    if _b3:
        st.session_state.page = "tryon"; st.rerun()

    st.markdown("---")
    wc = len(st.session_state.wardrobe)
    if wc == 0:
        st.info("👈 Start by building your wardrobe.")
    elif wc < 3:
        st.warning(f"You have {wc} item(s) — add at least 3 for outfit suggestions.")
    else:
        st.success(f"✅ {wc} items ready. Go to **Get Outfit** for today's look!")


# ═══════════════════════════════════════════════════════════════════════════════
# WARDROBE BUILDER
# ═══════════════════════════════════════════════════════════════════════════════
def page_wardrobe_builder():
    from catalog import CATALOG
    st.markdown("## 👕 Build Your Wardrobe")
    tab_swipe, tab_upload = st.tabs(["👆 Swipe Cards", "📷 Upload & AI Extract"])

    # ── TAB 1: SWIPE ──────────────────────────────────────────────────────────
    with tab_swipe:
        st.markdown("Swipe through clothing cards — tell us what you own.")
        idx   = st.session_state.swipe_index
        total = len(CATALOG)

        if idx >= total:
            st.balloons()
            owned = [s for s in st.session_state.swipe_history
                     if s["action"] in ("own","love")]
            st.success(f"🎉 Done! {len(owned)} items in your wardrobe.")
            c1, c2 = st.columns(2)
            _s1 = c1.button("🔄 Start Over", type="secondary",
                             use_container_width=True, key="swipe_restart")
            _s2 = c2.button("✨ Get Outfit", type="primary",
                             use_container_width=True, key="swipe_get_outfit")
            if _s1:
                st.session_state.swipe_index = 0
                st.session_state.swipe_history = []
                st.rerun()
            if _s2:
                st.session_state.page = "outfit"; st.rerun()
        else:
            item = CATALOG[idx]
            st.progress(idx / total, text=f"Card {idx+1} of {total} — {item['category']}")
            _, cc, _ = st.columns([1, 2, 1])
            with cc:
                # Show real product image if already fetched, else fetch now
                img_cache_key = f"catalog_img_{item['id']}"
                if img_cache_key not in st.session_state:
                    with st.spinner("Loading product image…"):
                        img = fetch_product_image(item["name"], item["colors"][0], item["category"])
                        st.session_state[img_cache_key] = img

                cached_img = st.session_state.get(img_cache_key)
                if cached_img:
                    st.image(cached_img, width='stretch')
                else:
                    st.markdown(
                        f'<div class="swipe-card">'
                        f'<div style="font-size:5rem">{item["emoji"]}</div>'
                        f'</div>', unsafe_allow_html=True)

                st.markdown(
                    f'<div style="text-align:center;padding:12px 0">'
                    f'<div style="font-size:1.3rem;font-weight:700;color:#e9d5ff">'
                    f'{item["name"]}</div>'
                    f'<div style="color:#9ca3af;font-size:0.9rem;margin:4px 0">'
                    f'{item["description"]}</div>'
                    f'{"".join(f"<span class=tag>{s}</span>" for s in item["styles"])}'
                    f'</div>', unsafe_allow_html=True)

            if st.session_state.get(f"show_colors_{idx}"):
                st.markdown("#### 🎨 Which color(s) do you own?")
                picked = st.multiselect("Colors", item["colors"],
                                        label_visibility="collapsed",
                                        key=f"cp_{idx}")
                if st.button("✓ Add to Wardrobe", type="primary",
                             use_container_width=True, key=f"add_sw_{idx}"):
                    colors = picked if picked else [item["colors"][0]]
                    existing = {w["id"] for w in st.session_state.wardrobe}
                    added_names = []
                    for color in colors:
                        witem = {
                            "id": f"{item['id']}_{color}",
                            "name": item["name"], "category": item["category"],
                            "color": color, "emoji": item["emoji"],
                            "styles": item["styles"], "occasions": item["occasions"],
                            "formality": item["formality"],
                            "source": "swipe",
                            # Store the real product image we already fetched
                            "uploaded_image": st.session_state.get(img_cache_key),
                        }
                        if witem["id"] not in existing:
                            st.session_state.wardrobe.append(witem)
                            added_names.append(f"{color} {item['name']}")
                    st.session_state.swipe_history.append({"item": item, "action": "own"})
                    st.session_state[f"show_colors_{idx}"] = False
                    st.session_state.swipe_index += 1
                    if added_names:
                        st.toast(f"✅ Added: {', '.join(added_names)}", icon="👕")
                    st.rerun()
            else:
                b1, b2, b3 = st.columns(3)
                _skip  = b1.button("👎 Skip",       use_container_width=True,
                                    type="secondary", key=f"skip_{idx}")
                _own   = b2.button("👍 I Own This",  use_container_width=True,
                                    type="primary",   key=f"own_{idx}")
                _love  = b3.button("❤️ Love It",     use_container_width=True,
                                    type="primary",   key=f"love_{idx}")
                if _skip:
                    st.session_state.swipe_history.append({"item": item, "action": "skip"})
                    st.session_state.swipe_index += 1
                    st.rerun()
                if _own or _love:
                    st.session_state[f"show_colors_{idx}"] = True
                    st.rerun()
                st.caption("👎 Don't own  |  👍 Own it  |  ❤️ Favorite")

            with st.expander("⚡ Quick Add Basics"):
                if st.button("Add White T-Shirt + Black Jeans + White Sneakers",
                             key="quick_basics"):
                    basics = [
                        {"id": "tshirt_white", "name": "T-Shirt", "category": "tops",
                         "color": "White", "emoji": "👕", "styles": ["casual", "minimal"],
                         "occasions": ["casual", "active"], "formality": 1,
                         "source": "quick", "uploaded_image": None},
                        {"id": "jeans_black", "name": "Jeans", "category": "bottoms",
                         "color": "Black", "emoji": "👖", "styles": ["casual", "versatile"],
                         "occasions": ["casual", "work"], "formality": 2,
                         "source": "quick", "uploaded_image": None},
                        {"id": "sneakers_white", "name": "Sneakers", "category": "footwear",
                         "color": "White", "emoji": "👟", "styles": ["casual", "sporty"],
                         "occasions": ["casual", "active"], "formality": 1,
                         "source": "quick", "uploaded_image": None},
                    ]
                    existing = {w["id"] for w in st.session_state.wardrobe}
                    added = sum(1 for b in basics
                                if b["id"] not in existing
                                and not st.session_state.wardrobe.append(b))
                    st.success(f"✅ Basics added!")
                    st.rerun()

    # ── TAB 2: PHOTO UPLOAD + AI EXTRACT ─────────────────────────────────────
    with tab_upload:
        st.markdown("Upload a clothing photo — **Claude Vision identifies each item, "
                    "then fetches a real product image for each one.**")
        if not anthropic_key:
            st.warning("⚠️ ANTHROPIC_API_KEY needed for AI extraction.")

        files = st.file_uploader(
            "Upload clothing photo(s)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="wardrobe_upload"
        )

        if files:
            for f in files:
                img_bytes = f.read()
                st.markdown(f"---")
                st.markdown(f"**📷 {f.name}**")

                # Show the uploaded photo small, as reference only
                col_ref, col_btn = st.columns([1, 3])
                with col_ref:
                    st.image(img_bytes, width=120, caption="Your photo")
                with col_btn:
                    st.markdown("This is the reference photo Claude will analyze.")
                    extract_btn = st.button("🤖 Extract Items with AI",
                                            key=f"extract_{f.name}",
                                            type="primary",
                                            use_container_width=True)

                extract_key = f"extracted_{f.name}"

                if extract_btn:
                    with st.spinner("🔍 Claude is identifying clothing items…"):
                        items, err = extract_clothing_from_photo(img_bytes, anthropic_key)
                    if items:
                        # Fetch real product image for each item
                        with st.spinner(f"🌐 Fetching product images for {len(items)} item(s)…"):
                            for item in items:
                                prod_img = fetch_product_image(
                                    item["name"], item["color"],
                                    item["category"], anthropic_key)
                                item["product_image"] = prod_img
                        st.session_state[extract_key] = items
                        st.success(f"✅ Found {len(items)} item(s)!")
                        st.rerun()
                    else:
                        st.error(f"Extraction failed: {err}")

                # Show extracted items — each with its OWN product image
                if extract_key in st.session_state:
                    st.markdown(f"#### Extracted Items — click to add:")
                    extracted = st.session_state[extract_key]
                    item_cols = st.columns(min(len(extracted), 3))
                    for ei, ex in enumerate(extracted):
                        with item_cols[ei % 3]:
                            if ex.get("product_image"):
                                st.image(ex["product_image"], width='stretch')
                            else:
                                cat_emoji = {
                                    "tops": "👕", "bottoms": "👖", "dresses": "👗",
                                    "outerwear": "🧥", "footwear": "👟",
                                    "accessories": "👜"
                                }.get(ex["category"], "👕")
                                st.markdown(
                                    f'<div class="wardrobe-card">'
                                    f'<div style="font-size:3rem">{cat_emoji}</div>'
                                    f'</div>', unsafe_allow_html=True)

                            st.markdown(f"**{ex['name']}**")
                            st.caption(f"{ex['color']} · {ex['category']}")

                            item_id  = f"photo_{f.name}_{ei}_{ex['color']}".replace(" ","_")
                            existing = {w["id"] for w in st.session_state.wardrobe}
                            add_key  = f"add_ext_{f.name}_{ei}"

                            if item_id in existing:
                                st.success("✅ In wardrobe")
                            else:
                                if st.button("➕ Add", key=add_key,
                                             use_container_width=True, type="primary"):
                                    st.session_state.wardrobe.append({
                                        "id":             item_id,
                                        "name":           ex["name"],
                                        "category":       ex["category"],
                                        "color":          ex["color"],
                                        "emoji":          "📷",
                                        "styles":         ex.get("styles", ["versatile"]),
                                        "occasions":      ex.get("occasions", ["casual"]),
                                        "formality":      ex.get("formality", 2),
                                        "source":         "photo_upload",
                                        "uploaded_image": ex.get("product_image") or img_bytes,
                                        "original_photo": img_bytes,
                                    })
                                    st.toast(f"✅ {ex['name']} added to wardrobe!", icon="👕")
                                    st.rerun()

                    if st.button("➕ Add All Items", key=f"add_all_{f.name}",
                                 use_container_width=True):
                        existing = {w["id"] for w in st.session_state.wardrobe}
                        added = 0
                        for ei, ex in enumerate(extracted):
                            item_id = f"photo_{f.name}_{ei}_{ex['color']}".replace(" ","_")
                            if item_id not in existing:
                                st.session_state.wardrobe.append({
                                    "id":             item_id,
                                    "name":           ex["name"],
                                    "category":       ex["category"],
                                    "color":          ex["color"],
                                    "emoji":          "📷",
                                    "styles":         ex.get("styles", ["versatile"]),
                                    "occasions":      ex.get("occasions", ["casual"]),
                                    "formality":      ex.get("formality", 2),
                                    "source":         "photo_upload",
                                    "uploaded_image": ex.get("product_image") or img_bytes,
                                    "original_photo": img_bytes,
                                })
                                added += 1
                        st.success(f"✅ Added {added} items to wardrobe!")
                        st.rerun()

                    st.markdown("---")

                # Manual add option
                with st.expander("➕ Add manually instead"):
                    m_name = st.text_input("Name", value="My Item", key=f"mn_{f.name}")
                    m_cat  = st.selectbox("Category",
                                          ["tops","bottoms","outerwear",
                                           "footwear","dresses","accessories"],
                                          key=f"mc_{f.name}")
                    m_col  = st.text_input("Color", value="Black", key=f"mcol_{f.name}")
                    m_occ  = st.multiselect("Occasions",
                                            ["casual","work","date","formal","active","travel"],
                                            default=["casual"], key=f"mocc_{f.name}")
                    m_form = st.slider("Formality", 1, 5, 2, key=f"mf_{f.name}")
                    if st.button("➕ Add Manually", key=f"addm_{f.name}",
                                 use_container_width=True):
                        item_id = f"manual_{f.name}_{m_col}".replace(" ","_")
                        existing = {w["id"] for w in st.session_state.wardrobe}
                        if item_id not in existing:
                            prod_img = fetch_product_image(m_name, m_col, m_cat)
                            st.session_state.wardrobe.append({
                                "id": item_id, "name": m_name, "category": m_cat,
                                "color": m_col, "emoji": "📷", "styles": ["versatile"],
                                "occasions": m_occ, "formality": m_form,
                                "source": "photo_upload",
                                "uploaded_image": prod_img or img_bytes,
                                "original_photo": img_bytes,
                            })
                            st.success(f"✅ {m_name} added!")
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
        st.info("Wardrobe is empty.")
        if st.button("👕 Build Wardrobe", type="primary"):
            st.session_state.page = "wardrobe_builder"; st.rerun()
        return

    st.markdown(f"**{len(wardrobe)} items**")
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
                    st.image(item["uploaded_image"], width=140)
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
    if st.button("🗑️ Clear All Wardrobe", type="secondary"):
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
    c1.markdown(f'<div class="metric-box"><div class="metric-value">📍</div>'
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
                results = engine.generate(n=3)
                if not results:
                    st.warning("⚠️ No outfit combinations found. "
                               "Make sure you have tops AND bottoms (or a dress) in your wardrobe.")
                    st.stop()
                st.session_state.outfit_suggestions = results
                st.session_state.tryon_results = {}
            except Exception as _err:
                import traceback
                st.error(f"Outfit engine error: {_err}")
                st.code(traceback.format_exc())
                st.stop()
        st.rerun()

    if not st.session_state.outfit_suggestions:
        st.info("👆 Click **Generate Outfit** above.")
        return

    st.markdown("---")
    for i, outfit in enumerate(st.session_state.outfit_suggestions):
        rank = ["🥇","🥈","🥉"][i]
        with st.expander(f"{rank} Outfit {i+1}  —  Score: {outfit['score']}/100",
                         expanded=(i == 0)):
            icols = st.columns(max(len(outfit["items"]), 1))
            for j, item in enumerate(outfit["items"]):
                with icols[j]:
                    if item.get("uploaded_image"):
                        st.image(item["uploaded_image"], width=130)
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
                for lbl, val in outfit.get("score_breakdown", {}).items():
                    pct = int(val)
                    st.markdown(f"<small>{lbl}</small>", unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="score-bar"><div class="score-fill" '
                        f'style="width:{pct}%"></div></div>'
                        f'<small style="color:#9ca3af">{pct}/100</small>',
                        unsafe_allow_html=True)
            with cb:
                st.markdown("**Colors**")
                st.markdown("".join(
                    f'<span class="tag">🎨 {c}</span> '
                    for c in outfit.get("color_palette", [])),
                    unsafe_allow_html=True)
                st.markdown(
                    f'<span class="tag">✓ {outfit.get("color_rule","—")}</span>',
                    unsafe_allow_html=True)

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
                        except Exception as _e2:
                            st.error(f"AI error: {_e2}")
                    st.rerun()

            b1, b2, b3 = st.columns(3)
            _wear  = b1.button("✅ Wearing This!", key=f"wear_{i}",
                                type="primary", use_container_width=True)
            _regen = b2.button("🔄 Try Another",  key=f"regen_{i}",
                                type="secondary", use_container_width=True)
            _tryon = b3.button("👗 Virtual Try-On", key=f"vto_{i}",
                                type="primary", use_container_width=True)

            if _wear:
                st.success("Great choice! 🎉")
            if _regen:
                st.session_state.outfit_suggestions = []
                st.session_state.tryon_results = {}
                st.rerun()
            if _tryon:
                if not st.session_state.person_photo:
                    st.warning("📸 Upload your photo in the sidebar first!")
                else:
                    st.session_state.tryon_outfit_index = i
                    st.session_state.page = "tryon"
                    st.rerun()




# ═══════════════════════════════════════════════════════════════════════════════
# VIRTUAL TRY-ON
# ═══════════════════════════════════════════════════════════════════════════════
def page_tryon():
    st.markdown('<div class="hero-text">👗 Virtual Try-On</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Upload your photo. Pick your outfit. See it on you.</div>', unsafe_allow_html=True)

    fashn_key = get_secret("FASHN_API_KEY")
    if not fashn_key:
        st.error("⚠️ FASHN_API_KEY missing from Streamlit Secrets.")
        return

    # ── STEP 1: Your Photo ────────────────────────────────────────────────────
    st.markdown("### Step 1 — Upload Your Photo")
    st.caption("Stand facing forward, full body visible. Plain background works best.")

    col_upload, col_preview = st.columns([2, 1])
    with col_upload:
        tryon_photo = st.file_uploader(
            "Upload your full-body photo",
            type=["jpg","jpeg","png"],
            key="tryon_photo_upload",
            label_visibility="collapsed"
        )
        if tryon_photo:
            st.session_state.person_photo = tryon_photo.read()
            st.success("✅ Photo ready!")

    with col_preview:
        if st.session_state.person_photo:
            st.image(st.session_state.person_photo, width=150, caption="Your photo ✓")
        else:
            st.markdown(
                '<div class="wardrobe-card" style="min-height:160px;display:flex;'                'align-items:center;justify-content:center">'                '<div style="color:#9ca3af;text-align:center">'                '<div style="font-size:2rem">📸</div>Upload above</div>'                '</div>', unsafe_allow_html=True)

    if not st.session_state.person_photo:
        st.info("👆 Upload your full-body photo above to continue.")
        return

    st.markdown("---")

    # ── STEP 2: Pick Outfit ───────────────────────────────────────────────────
    st.markdown("### Step 2 — Choose Your Outfit")

    wardrobe = st.session_state.wardrobe
    if not wardrobe:
        st.warning("Your wardrobe is empty. Add items first.")
        if st.button("👕 Build Wardrobe"):
            st.session_state.page = "wardrobe_builder"; st.rerun()
        return

    pick_mode = st.radio("How to pick outfit:",
                         ["From AI suggestions", "Pick manually from wardrobe"],
                         horizontal=True)
    selected_items = []

    if pick_mode == "From AI suggestions":
        if not st.session_state.outfit_suggestions:
            st.info("No outfit suggestions yet.")
            if st.button("✨ Generate Outfit First"):
                st.session_state.page = "outfit"; st.rerun()
            return
        outfits = st.session_state.outfit_suggestions
        labels  = [f"{'🥇🥈🥉'[i]} Outfit {i+1} — Score {outfits[i]['score']}/100"
                   for i in range(len(outfits))]
        sel     = st.selectbox("Select outfit:", labels,
                               index=min(st.session_state.tryon_outfit_index, len(labels)-1))
        oidx    = labels.index(sel)
        outfit  = outfits[oidx]
        selected_items = [it for it in outfit["items"]
                          if it["category"] in ("tops","bottoms","dresses")]
        result_key = f"tryon_{oidx}"

        if selected_items:
            icols = st.columns(len(selected_items))
            for j, item in enumerate(selected_items):
                with icols[j]:
                    if item.get("uploaded_image"):
                        st.image(item["uploaded_image"], width='stretch')
                    else:
                        st.markdown(
                            f'<div class="wardrobe-card">'                            f'<div style="font-size:2rem">{item["emoji"]}</div>'                            f'<div style="font-weight:600;color:#e9d5ff;font-size:0.85rem">{item["name"]}</div>'                            f'<div style="color:#9ca3af;font-size:0.75rem">{item["color"]}</div>'                            f'</div>', unsafe_allow_html=True)
    else:
        result_key = "tryon_manual"
        tops_items    = [it for it in wardrobe if it["category"] in ("tops","dresses")]
        bottoms_items = [it for it in wardrobe if it["category"] == "bottoms"]

        mc1, mc2 = st.columns(2)
        with mc1:
            st.markdown("**Top / Dress**")
            top_labels = [f"{it['name']} ({it['color']})" for it in tops_items]
            if top_labels:
                sel_top = st.selectbox("Select top:", top_labels, key="manual_top")
                chosen_top = tops_items[top_labels.index(sel_top)]
                if chosen_top.get("uploaded_image"):
                    st.image(chosen_top["uploaded_image"], width=120)
                else:
                    st.markdown(f'<div class="wardrobe-card"><div style="font-size:2.5rem">{chosen_top["emoji"]}</div></div>', unsafe_allow_html=True)
                selected_items.append(chosen_top)
            else:
                st.warning("No tops in wardrobe")

        with mc2:
            if not any(it["category"] == "dresses" for it in selected_items):
                st.markdown("**Bottom**")
                bot_labels = [f"{it['name']} ({it['color']})" for it in bottoms_items]
                if bot_labels:
                    sel_bot = st.selectbox("Select bottom:", bot_labels, key="manual_bot")
                    chosen_bot = bottoms_items[bot_labels.index(sel_bot)]
                    if chosen_bot.get("uploaded_image"):
                        st.image(chosen_bot["uploaded_image"], width=120)
                    else:
                        st.markdown(f'<div class="wardrobe-card"><div style="font-size:2.5rem">{chosen_bot["emoji"]}</div></div>', unsafe_allow_html=True)
                    selected_items.append(chosen_bot)

    if not selected_items:
        st.warning("No wearable items selected.")
        return

    st.markdown("---")

    # ── STEP 3: Generate ──────────────────────────────────────────────────────
    st.markdown("### Step 3 — Try It On")

    col_before, col_after = st.columns(2)
    with col_before:
        st.markdown("**📸 You**")
        st.image(st.session_state.person_photo, width='stretch')

    cached = st.session_state.tryon_results.get(result_key)

    with col_after:
        st.markdown("**✨ You wearing the outfit**")
        if cached:
            st.image(cached, width='stretch')
        else:
            st.markdown(
                '<div class="outfit-card" style="text-align:center;min-height:350px;'                'display:flex;align-items:center;justify-content:center">'                '<div><div style="font-size:4rem">👗</div>'                '<div style="color:#9ca3af;margin-top:16px">Your try-on will appear here</div>'                '</div></div>', unsafe_allow_html=True)

    st.markdown("")
    if cached:
        c1, c2, c3 = st.columns(3)
        c1.download_button("⬇️ Save Photo", data=cached,
                           file_name="outfitai_tryon.jpg",
                           mime="image/jpeg", use_container_width=True)
        if c2.button("🔄 Try Again", type="secondary", use_container_width=True):
            del st.session_state.tryon_results[result_key]
            st.rerun()
        if c3.button("✨ New Outfit", type="primary", use_container_width=True):
            st.session_state.page = "outfit"; st.rerun()
    else:
        if st.button("🚀 Try On Now", type="primary", use_container_width=True):
            prog_bar  = st.progress(0)
            prog_text = st.empty()

            def update_progress(pct, msg):
                try:
                    prog_bar.progress(min(int(pct), 100))
                    prog_text.markdown(f'<div style="color:#a78bfa;text-align:center">{msg}</div>', unsafe_allow_html=True)
                except Exception:
                    pass

            update_progress(5, "🔌 Connecting to FASHN AI…")
            try:
                engine = TryOnEngine(fashn_key)
                result = engine.run_outfit(
                    person=st.session_state.person_photo,
                    items=selected_items,
                    progress=update_progress,
                )
            except Exception as _te:
                st.error(f"Try-on error: {_te}")
                result = {"success": False, "error": str(_te)}

            if result.get("success") and result.get("result_image"):
                st.session_state.tryon_results[result_key] = result["result_image"]
                st.rerun()
            else:
                st.error(f"❌ Try-on failed: {result.get('error','Unknown error')}")
                st.caption("Check your FASHN API credits at app.fashn.ai")

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
        for color, cnt in profile.get("dominant_colors", [])[:8]:
            st.markdown(f"**{color}** — {cnt} item{'s' if cnt > 1 else ''}")
    with c2:
        st.markdown("### 💡 Wardrobe Gaps")
        for gap in profile.get("gaps", []):
            st.markdown(f"- {gap}")


# ── Router ────────────────────────────────────────────────────────────────────
_p = st.session_state.page
if   _p == "home":              page_home()
elif _p == "wardrobe_builder":  page_wardrobe_builder()
elif _p == "my_wardrobe":       page_my_wardrobe()
elif _p == "outfit":            page_outfit()
elif _p == "tryon":             page_tryon()
elif _p == "profile":           page_profile()
