import streamlit as st
import random, base64, json, threading

try:
    from engine import OutfitEngine, get_secret
except ImportError as _e:
    st.error(f"engine.py import error: {_e}"); st.stop()

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

from visuals import (
    item_svg_html, shape_for, clothing_svg, resolve_color,
    start_fetch, get_product_image, get_candidates_cached,
    confirm_image, is_fetching, fetch_status
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_json(text):
    text = text.strip()
    if "```" in text:
        for part in text.split("```"):
            part = part.strip()
            if part.startswith("json"): part = part[4:].strip()
            if part.startswith("[") or part.startswith("{"): return json.loads(part)
    return json.loads(text)


def extract_clothing_from_photo(image_bytes, api_key):
    if not api_key or not ANTHROPIC_OK:
        return [], "Anthropic API key missing"
    prompt = (
        "Analyze this clothing photo. Identify every distinct garment visible. "
        "Return ONLY a raw JSON array — no markdown, no explanation:\n"
        '[{"name":"White T-Shirt","category":"tops","color":"White",'
        '"styles":["casual"],"occasions":["casual"],"formality":1}]\n'
        "category must be one of: tops | bottoms | outerwear | footwear | dresses | accessories\n"
        "formality: 1=very casual to 5=very formal"
    )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        b64 = base64.b64encode(image_bytes).decode()
        msg = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1000,
            messages=[{"role":"user","content":[
                {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":b64}},
                {"type":"text","text":prompt}
            ]}]
        )
        return _parse_json(msg.content[0].text), None
    except Exception as err:
        return [], str(err)


def best_image(item):
    """
    Return image bytes. Always falls back to sync fetch so try-on never blocks.
    Writes result onto item dict so it survives Streamlit reruns.
    """
    item_id = item.get("id", "")

    # 1. Already written on the item dict (survives reruns — most reliable)
    stored = item.get("uploaded_image") or item.get("original_photo")
    if stored:
        return stored

    # 2. In-memory confirmed cache (only lives in current session run)
    fetched = get_product_image(item_id)
    if fetched:
        # Write back so next rerun finds it on the dict
        item["uploaded_image"] = fetched
        return fetched

    # 3. Sync fetch — always try regardless of background fetch status
    #    This is the guaranteed fallback for try-on
    try:
        from garments import get_garment_image
        img = get_garment_image(
            item.get("name", ""), item.get("color", ""), item.get("category", ""))
        if img:
            write_confirmed_image_to_item(item_id, img)
            item["uploaded_image"] = img  # write directly onto item
            return img
    except Exception:
        pass

    return None


def show_item_visual(item, width=100):
    """Show real product image if ready, else SVG silhouette."""
    img = best_image(item)
    if img:
        st.image(img, width=width)
    else:
        st.markdown(item_svg_html(item, size=width - 16), unsafe_allow_html=True)
        if is_fetching(item.get("id","")):
            st.caption("⏳ loading…")


def add_to_wardrobe(item, ask_confirm=True):
    """Add item, kick off background fetch, queue for confirmation."""
    existing = {w["id"] for w in st.session_state.wardrobe}
    if item["id"] not in existing:
        st.session_state.wardrobe.append(item)
        start_fetch(item)
        if ask_confirm:
            st.session_state.pending_confirm = item["id"]
        return True
    return False


def write_confirmed_image_to_item(item_id, image_bytes):
    """
    Write confirmed image directly onto the wardrobe item dict so it
    survives Streamlit reruns (thread cache doesn't persist across reruns).
    Also updates visuals cache.
    """
    confirm_image(item_id, image_bytes)
    for w in st.session_state.wardrobe:
        if w["id"] == item_id:
            w["uploaded_image"] = image_bytes
            break


# ─────────────────────────────────────────────────────────────────────────────
# Page config + CSS
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="OutfitAI", page_icon="👗", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp{background:#0f0f1a;color:#f0f0f0}
[data-testid="stSidebar"]{background:#1a1a2e}
.outfit-card{background:linear-gradient(135deg,#1e1e3a,#2a1a4a);
  border:1px solid #7C3AED44;border-radius:16px;padding:20px;margin:10px 0}
.item-card{background:#1e1e3a;border:1px solid #333;border-radius:12px;
  padding:10px;text-align:center;transition:border-color .2s}
.item-card:hover{border-color:#7C3AED}
.item-card.added{border:2px solid #7C3AED;background:#1e1e3a}
.tag{display:inline-block;background:#7C3AED33;color:#c4b5fd;
  border:1px solid #7C3AED66;border-radius:20px;padding:2px 10px;font-size:12px;margin:2px}
.score-bar{background:#333;border-radius:10px;height:8px;margin:4px 0}
.score-fill{background:linear-gradient(90deg,#7C3AED,#a78bfa);border-radius:10px;height:8px}
.hero-text{font-size:2.2rem;font-weight:800;
  background:linear-gradient(135deg,#7C3AED,#a78bfa,#c4b5fd);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.subtitle{color:#9ca3af;font-size:1rem;margin-bottom:20px}
.stButton>button{border-radius:10px!important;font-weight:600!important}
.metric-box{background:#1e1e3a;border:1px solid #7C3AED44;border-radius:12px;
  padding:16px;text-align:center}
.metric-value{font-size:2rem;font-weight:800;color:#a78bfa}
.metric-label{font-size:0.8rem;color:#9ca3af;margin-top:4px}
.cat-pills{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
.cloth-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:12px}
</style>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────

DEFAULTS = {
    "wardrobe":[], "page":"home", "occasion":"casual", "city":"New York",
    "outfit_suggestions":[], "person_photo":None, "tryon_results":{},
    "tryon_outfit_index":0, "wardrobe_cat_filter":"All", "pending_confirm":None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
_nav_clicked = None

with st.sidebar:
    st.markdown("## 👗 OutfitAI")
    st.markdown("---")

    anthropic_key = get_secret("ANTHROPIC_API_KEY")
    fashn_key     = get_secret("FASHN_API_KEY")

    if anthropic_key: st.success("✓ Claude AI connected")
    else:             st.warning("⚠️ No Anthropic key")
    if fashn_key:     st.success("✓ FASHN Try-On connected")
    else:             st.warning("⚠️ No FASHN key")

    st.markdown("---")
    st.markdown("### Navigation")
    NAV = [
        ("🏠 Home",           "home"),
        ("👕 Build Wardrobe", "wardrobe_builder"),
        ("🗃️ My Wardrobe",   "my_wardrobe"),
        ("✨ Get Outfit",     "outfit"),
        ("👗 Virtual Try-On", "tryon"),
        ("📊 Style Profile",  "profile"),
    ]
    for label, pkey in NAV:
        t = "primary" if st.session_state.page == pkey else "secondary"
        if st.button(label, use_container_width=True, type=t, key=f"nav_{pkey}"):
            _nav_clicked = pkey

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

if _nav_clicked:
    st.session_state.page = _nav_clicked
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Catalog — full item list with shapes
# ─────────────────────────────────────────────────────────────────────────────

CATALOG = [
    # TOPS
    {"id":"wt1","name":"T-Shirt","category":"tops","color":"White","styles":["casual","minimal"],"occasions":["casual","active"],"formality":1},
    {"id":"bt1","name":"T-Shirt","category":"tops","color":"Black","styles":["casual","minimal"],"occasions":["casual","active"],"formality":1},
    {"id":"gt1","name":"T-Shirt","category":"tops","color":"Gray","styles":["casual","minimal"],"occasions":["casual","active"],"formality":1},
    {"id":"nt1","name":"T-Shirt","category":"tops","color":"Navy","styles":["casual"],"occasions":["casual"],"formality":1},
    {"id":"ws1","name":"Shirt","category":"tops","color":"White","styles":["smart","formal"],"occasions":["work","formal","date"],"formality":4},
    {"id":"bs1","name":"Shirt","category":"tops","color":"Navy","styles":["smart"],"occasions":["work","date"],"formality":3},
    {"id":"ls1","name":"Shirt","category":"tops","color":"Blue","styles":["smart","casual"],"occasions":["work","casual"],"formality":3},
    {"id":"pp1","name":"Polo Shirt","category":"tops","color":"Green","styles":["smart casual"],"occasions":["casual","work"],"formality":2},
    {"id":"pw1","name":"Polo Shirt","category":"tops","color":"White","styles":["smart casual"],"occasions":["casual","work"],"formality":2},
    {"id":"sw1","name":"Sweater","category":"tops","color":"Brown","styles":["casual","cozy"],"occasions":["casual","date"],"formality":2},
    {"id":"sgr","name":"Sweater","category":"tops","color":"Gray","styles":["casual","minimal"],"occasions":["casual"],"formality":2},
    {"id":"hd1","name":"Hoodie","category":"tops","color":"Charcoal","styles":["casual","streetwear"],"occasions":["casual","active"],"formality":1},
    {"id":"hdb","name":"Hoodie","category":"tops","color":"Black","styles":["casual","streetwear"],"occasions":["casual","active"],"formality":1},
    {"id":"tk1","name":"Tank Top","category":"tops","color":"White","styles":["casual","sporty"],"occasions":["active","casual"],"formality":1},
    # BOTTOMS
    {"id":"bj1","name":"Jeans","category":"bottoms","color":"Blue","styles":["casual","versatile"],"occasions":["casual","date"],"formality":2},
    {"id":"kj1","name":"Jeans","category":"bottoms","color":"Black","styles":["casual","versatile"],"occasions":["casual","date","work"],"formality":2},
    {"id":"gj1","name":"Jeans","category":"bottoms","color":"Gray","styles":["casual"],"occasions":["casual"],"formality":2},
    {"id":"ch1","name":"Chinos","category":"bottoms","color":"Beige","styles":["smart casual"],"occasions":["work","casual","date"],"formality":3},
    {"id":"chk","name":"Chinos","category":"bottoms","color":"Khaki","styles":["smart casual"],"occasions":["work","casual"],"formality":3},
    {"id":"tr1","name":"Trousers","category":"bottoms","color":"Gray","styles":["formal","smart"],"occasions":["work","formal"],"formality":4},
    {"id":"trn","name":"Trousers","category":"bottoms","color":"Navy","styles":["formal","smart"],"occasions":["work","formal"],"formality":4},
    {"id":"sh1","name":"Shorts","category":"bottoms","color":"Navy","styles":["casual","summer"],"occasions":["casual","active"],"formality":1},
    {"id":"shk","name":"Shorts","category":"bottoms","color":"Khaki","styles":["casual"],"occasions":["casual"],"formality":1},
    {"id":"sk1","name":"Skirt","category":"bottoms","color":"Black","styles":["feminine","versatile"],"occasions":["casual","date","work"],"formality":3},
    {"id":"skb","name":"Skirt","category":"bottoms","color":"Beige","styles":["feminine","casual"],"occasions":["casual","date"],"formality":2},
    # OUTERWEAR
    {"id":"jk1","name":"Blazer","category":"outerwear","color":"Black","styles":["formal","smart"],"occasions":["work","formal","date"],"formality":4},
    {"id":"jkn","name":"Blazer","category":"outerwear","color":"Navy","styles":["formal","smart"],"occasions":["work","formal"],"formality":4},
    {"id":"jc1","name":"Jacket","category":"outerwear","color":"Black","styles":["casual","streetwear"],"occasions":["casual","date"],"formality":2},
    {"id":"jcb","name":"Jacket","category":"outerwear","color":"Brown","styles":["casual"],"occasions":["casual","date"],"formality":2},
    {"id":"ct1","name":"Coat","category":"outerwear","color":"Camel","styles":["elegant","versatile"],"occasions":["work","date","formal"],"formality":4},
    {"id":"ctg","name":"Coat","category":"outerwear","color":"Gray","styles":["minimal","elegant"],"occasions":["work","formal"],"formality":4},
    # FOOTWEAR
    {"id":"sn1","name":"Sneakers","category":"footwear","color":"White","styles":["casual","versatile"],"occasions":["casual","active"],"formality":1},
    {"id":"snb","name":"Sneakers","category":"footwear","color":"Black","styles":["casual","streetwear"],"occasions":["casual","active"],"formality":1},
    {"id":"bts","name":"Boots","category":"footwear","color":"Brown","styles":["casual","smart"],"occasions":["casual","date","work"],"formality":3},
    {"id":"btb","name":"Boots","category":"footwear","color":"Black","styles":["versatile","smart"],"occasions":["work","date","formal"],"formality":3},
    {"id":"lf1","name":"Loafers","category":"footwear","color":"Brown","styles":["smart casual"],"occasions":["work","date"],"formality":3},
    {"id":"lfb","name":"Loafers","category":"footwear","color":"Black","styles":["formal","smart"],"occasions":["work","formal"],"formality":4},
    {"id":"sd1","name":"Sandals","category":"footwear","color":"Brown","styles":["casual","summer"],"occasions":["casual","travel"],"formality":1},
    # DRESSES
    {"id":"dr1","name":"Dress","category":"dresses","color":"Black","styles":["versatile","elegant"],"occasions":["date","formal","work"],"formality":4},
    {"id":"drb","name":"Dress","category":"dresses","color":"Burgundy","styles":["elegant"],"occasions":["date","formal"],"formality":4},
    {"id":"drw","name":"Dress","category":"dresses","color":"White","styles":["feminine","summer"],"occasions":["casual","date"],"formality":3},
    # ACCESSORIES
    {"id":"be1","name":"Belt","category":"accessories","color":"Black","styles":["versatile"],"occasions":["casual","work","formal"],"formality":2},
    {"id":"beb","name":"Belt","category":"accessories","color":"Brown","styles":["casual","smart"],"occasions":["casual","work"],"formality":2},
    {"id":"wt_","name":"Watch","category":"accessories","color":"Gold","styles":["elegant","smart"],"occasions":["work","formal","date"],"formality":4},
    {"id":"wts","name":"Watch","category":"accessories","color":"Silver","styles":["minimal","smart"],"occasions":["work","formal"],"formality":4},
    {"id":"bg1","name":"Bag","category":"accessories","color":"Black","styles":["versatile"],"occasions":["work","travel","casual"],"formality":3},
    {"id":"bg2","name":"Bag","category":"accessories","color":"Brown","styles":["casual","smart"],"occasions":["casual","work"],"formality":2},
]


# ─────────────────────────────────────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────────────────────────────────────

def page_home():
    st.markdown('<div class="hero-text">👗 OutfitAI</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Your AI stylist — build your wardrobe, get outfit ideas, try them on.</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="outfit-card"><div style="font-size:1.5rem">👕</div>'
                    '<h3 style="color:#e9d5ff">Build Wardrobe</h3>'
                    '<p style="color:#9ca3af">Browse our catalog. Click to add items. '
                    'Product photos load in the background.</p></div>', unsafe_allow_html=True)
        btn_build = st.button("→ Build Wardrobe", key="home_build", use_container_width=True)
    with c2:
        st.markdown('<div class="outfit-card"><div style="font-size:1.5rem">🤖</div>'
                    '<h3 style="color:#e9d5ff">AI Outfit Ideas</h3>'
                    '<p style="color:#9ca3af">Color theory + occasion scoring. '
                    'Claude explains why each outfit works.</p></div>', unsafe_allow_html=True)
        btn_outfit = st.button("→ Get Outfit", key="home_outfit", use_container_width=True)
    with c3:
        st.markdown('<div class="outfit-card"><div style="font-size:1.5rem">✨</div>'
                    '<h3 style="color:#e9d5ff">Virtual Try-On</h3>'
                    '<p style="color:#9ca3af">Upload your photo. See the outfit on you '
                    'powered by FASHN AI.</p></div>', unsafe_allow_html=True)
        btn_tryon = st.button("→ Try-On", key="home_tryon", use_container_width=True)

    if btn_build:  st.session_state.page = "wardrobe_builder"; st.rerun()
    if btn_outfit: st.session_state.page = "outfit";           st.rerun()
    if btn_tryon:  st.session_state.page = "tryon";            st.rerun()

    st.markdown("---")
    wc = len(st.session_state.wardrobe)
    if wc == 0:
        st.info("👈 Start by building your wardrobe.")
    elif wc < 3:
        st.warning(f"You have {wc} item(s). Add at least 3 tops + bottoms for outfit suggestions.")
    else:
        st.success(f"✅ {wc} items ready. Go to **Get Outfit** for today's look!")


# ─────────────────────────────────────────────────────────────────────────────
# WARDROBE BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def page_wardrobe_builder():
    st.markdown("## 👕 Build Your Wardrobe")
    tab_browse, tab_upload = st.tabs(["🛍️ Browse Catalog", "📷 Upload & AI Extract"])

    # ── TAB 1: CATALOG BROWSER ───────────────────────────────────────────────
    with tab_browse:
        st.markdown("Click any item to add it. Product photos load automatically in the background.")

        # Category filter
        cats = ["All","Tops","Bottoms","Outerwear","Footwear","Dresses","Accessories"]
        cf = st.session_state.wardrobe_cat_filter
        cols_cats = st.columns(len(cats))
        for i, cat in enumerate(cats):
            with cols_cats[i]:
                active = cf == cat
                if st.button(cat,
                             key=f"catf_{cat}",
                             type="primary" if active else "secondary",
                             use_container_width=True):
                    st.session_state.wardrobe_cat_filter = cat
                    st.rerun()

        st.markdown("")
        cf = st.session_state.wardrobe_cat_filter
        filtered = CATALOG if cf == "All" else [
            i for i in CATALOG if i["category"] == cf.lower()
        ]

        existing_ids = {w["id"] for w in st.session_state.wardrobe}

        # Color filter
        all_colors = sorted(set(i["color"] for i in filtered))
        color_filter = st.selectbox("Filter by color:", ["Any"] + all_colors,
                                     key="color_filter_sel")
        if color_filter != "Any":
            filtered = [i for i in filtered if i["color"] == color_filter]

        st.markdown(f"**{len(filtered)} items** | "
                    f"{len(existing_ids)} in wardrobe")
        st.markdown("---")

        # Grid — 5 columns
        COLS = 5
        rows = [filtered[i:i+COLS] for i in range(0, len(filtered), COLS)]
        for row in rows:
            cols = st.columns(COLS)
            for j, item in enumerate(row):
                with cols[j]:
                    is_added = item["id"] in existing_ids
                    status   = fetch_status(item["id"])

                    # Visual: real photo > SVG silhouette
                    img = get_product_image(item["id"])
                    if img:
                        st.image(img, use_container_width=True)
                    else:
                        st.markdown(
                            item_svg_html(item, size=80),
                            unsafe_allow_html=True)
                        if status == "loading":
                            st.caption("⏳")

                    st.markdown(
                        f'<div style="font-size:0.8rem;font-weight:600;'
                        f'color:#e9d5ff;text-align:center">{item["name"]}</div>'
                        f'<div style="font-size:0.72rem;color:#9ca3af;text-align:center">'
                        f'{item["color"]}</div>',
                        unsafe_allow_html=True)

                    if is_added:
                        st.button("✓ Added", key=f"cat_{item['id']}",
                                  use_container_width=True,
                                  type="primary", disabled=True)
                    else:
                        if st.button("+ Add", key=f"cat_{item['id']}",
                                     use_container_width=True):
                            add_to_wardrobe(item)
                            st.rerun()

        # ── CONFIRMATION DIALOG ───────────────────────────────────────────────
        confirm_id = st.session_state.get("pending_confirm")
        if confirm_id:
            # Find the item
            item_obj = next((w for w in st.session_state.wardrobe
                             if w["id"] == confirm_id), None)
            if item_obj:
                st.markdown("---")
                st.markdown("### 🔍 Is this the right photo?")
                st.caption(f"Showing results for **{item_obj['color']} {item_obj['name']}** — "
                           f"confirm or pick a better match.")

                status = fetch_status(confirm_id)
                if status == "loading":
                    st.info("⏳ Fetching photos… please wait a moment then refresh.")
                else:
                    candidates = get_candidates_cached(confirm_id)
                    if not candidates:
                        st.warning("No photos found. You can upload your own below.")
                        candidates = []

                    # Show up to 4 candidates in a row
                    if candidates:
                        cand_cols = st.columns(min(len(candidates), 4))
                        for ci, cand in enumerate(candidates):
                            with cand_cols[ci]:
                                st.image(cand, use_container_width=True)
                                if st.button(f"✓ This one", key=f"pick_{confirm_id}_{ci}",
                                             type="primary", use_container_width=True):
                                    write_confirmed_image_to_item(confirm_id, cand)
                                    st.session_state.pending_confirm = None
                                    st.success(f"✅ {item_obj['name']} confirmed!")
                                    st.rerun()

                    # Upload own photo option
                    st.markdown("**None match? Upload your own:**")
                    own_photo = st.file_uploader(
                        "Upload photo of this item",
                        type=["jpg","jpeg","png"],
                        key=f"own_{confirm_id}"
                    )
                    if own_photo:
                        img_bytes = own_photo.read()
                        write_confirmed_image_to_item(confirm_id, img_bytes)
                        st.session_state.pending_confirm = None
                        st.success(f"✅ {item_obj['name']} photo saved!")
                        st.rerun()

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🔄 Search Again", key=f"retry_{confirm_id}",
                                     use_container_width=True):
                            # Clear cache and re-fetch
                            from visuals import _fetch_lock, _candidates_cache, _confirmed_cache
                            with _fetch_lock:
                                _candidates_cache.pop(confirm_id, None)
                                _confirmed_cache.pop(confirm_id, None)
                            start_fetch(item_obj)
                            st.rerun()
                    with c2:
                        if st.button("Skip — use SVG silhouette", key=f"skip_{confirm_id}",
                                     type="secondary", use_container_width=True):
                            st.session_state.pending_confirm = None
                            st.rerun()

        st.markdown("---")
        # Quick-add basics
        if st.button("⚡ Quick Add: White T-Shirt + Black Jeans + White Sneakers",
                     use_container_width=True):
            basics = [i for i in CATALOG if i["id"] in ("wt1","kj1","sn1")]
            for b in basics:
                add_to_wardrobe(b)
            st.success("✅ Basics added!")
            st.rerun()

    # ── TAB 2: UPLOAD + AI EXTRACT ───────────────────────────────────────────
    with tab_upload:
        st.markdown("Upload a clothing photo — Claude Vision identifies each item "
                    "and fetches a product image automatically.")
        if not anthropic_key:
            st.warning("⚠️ ANTHROPIC_API_KEY needed for AI extraction.")

        files = st.file_uploader("Upload clothing photo(s)",
                                  type=["jpg","jpeg","png"],
                                  accept_multiple_files=True,
                                  key="wardrobe_upload")
        if files:
            for f in files:
                img_bytes = f.read()
                st.markdown(f"---")
                col_ref, col_btn = st.columns([1,3])
                with col_ref:
                    st.image(img_bytes, width=120, caption="Reference")
                with col_btn:
                    extract_key = f"extracted_{f.name}"
                    extract_btn = st.button("🤖 Extract Items with AI",
                                            key=f"extract_{f.name}",
                                            type="primary",
                                            use_container_width=True)
                    if extract_btn:
                        with st.spinner("🔍 Identifying clothing items…"):
                            items, err = extract_clothing_from_photo(img_bytes, anthropic_key)
                        if items:
                            # Immediately kick off background fetches
                            for ei, ex in enumerate(items):
                                ex["id"] = f"upload_{f.name}_{ei}_{ex.get('color','')}".replace(" ","_")
                                ex.setdefault("styles",["versatile"])
                                ex.setdefault("occasions",["casual"])
                                ex.setdefault("formality",2)
                                ex["source"]         = "photo_upload"
                                ex["original_photo"] = img_bytes
                                start_fetch(ex)  # ← starts NOW
                            st.session_state[extract_key] = items
                            st.success(f"✅ Found {len(items)} item(s)! Product images loading…")
                            st.rerun()
                        else:
                            st.error(f"Extraction failed: {err}")

                if f"extracted_{f.name}" in st.session_state:
                    extracted = st.session_state[f"extracted_{f.name}"]
                    st.markdown(f"#### {len(extracted)} items found:")
                    ecols = st.columns(min(len(extracted), 4))
                    for ei, ex in enumerate(extracted):
                        with ecols[ei % 4]:
                            img = get_product_image(ex["id"])
                            if img:
                                st.image(img, use_container_width=True)
                            else:
                                st.markdown(item_svg_html(ex, size=80),
                                            unsafe_allow_html=True)
                                if is_fetching(ex["id"]):
                                    st.caption("⏳ loading…")
                            st.markdown(f"**{ex['name']}**")
                            st.caption(f"{ex['color']} · {ex['category']}")
                            already = ex["id"] in {w["id"] for w in st.session_state.wardrobe}
                            if already:
                                st.button("✓ Added", key=f"add_ex_{f.name}_{ei}",
                                          disabled=True, use_container_width=True)
                            else:
                                if st.button("+ Add", key=f"add_ex_{f.name}_{ei}",
                                             type="primary", use_container_width=True):
                                    add_to_wardrobe(ex)
                                    st.rerun()

                    if st.button("➕ Add All", key=f"addall_{f.name}",
                                 use_container_width=True):
                        added = sum(1 for ex in extracted if add_to_wardrobe(ex))
                        st.success(f"✅ Added {added} items!")
                        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MY WARDROBE
# ─────────────────────────────────────────────────────────────────────────────

def page_my_wardrobe():
    st.markdown("## 🗃️ My Wardrobe")
    wardrobe = st.session_state.wardrobe
    if not wardrobe:
        st.info("Wardrobe is empty — go to **Build Wardrobe**.")
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
        cols = st.columns(min(len(items), 5))
        for i, item in enumerate(items):
            with cols[i % 5]:
                img = best_image(item)
                if img:
                    st.image(img, use_container_width=True)
                else:
                    st.markdown(item_svg_html(item, size=80), unsafe_allow_html=True)
                    if is_fetching(item.get("id","")):
                        st.caption("⏳")
                st.markdown(
                    f'<div style="font-size:0.8rem;font-weight:600;color:#e9d5ff;'
                    f'text-align:center">{item["name"]}</div>'
                    f'<div style="font-size:0.72rem;color:#9ca3af;text-align:center">'
                    f'{item["color"]}</div>',
                    unsafe_allow_html=True)
                if st.button("🗑", key=f"rm_{item['id']}", use_container_width=True):
                    st.session_state.wardrobe = [
                        w for w in wardrobe if w["id"] != item["id"]]
                    st.rerun()

    st.markdown("---")
    if st.button("🗑️ Clear All Wardrobe", type="secondary"):
        st.session_state.wardrobe = []
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# GET OUTFIT
# ─────────────────────────────────────────────────────────────────────────────

def page_outfit():
    st.markdown("## ✨ Get Outfit")
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
                engine = OutfitEngine(wardrobe=wardrobe,
                                      occasion=st.session_state.occasion,
                                      city=st.session_state.city)
                results = engine.generate(n=3)
                if not results:
                    st.warning("No outfit combinations found. Make sure you have tops AND bottoms.")
                    st.stop()
                st.session_state.outfit_suggestions = results
                st.session_state.tryon_results = {}
            except Exception as _err:
                import traceback
                st.error(f"Error: {_err}")
                st.code(traceback.format_exc())
                st.stop()
        st.rerun()

    if not st.session_state.outfit_suggestions:
        st.info("👆 Click **Generate Outfit** above.")
        return

    st.markdown("---")
    for i, outfit in enumerate(st.session_state.outfit_suggestions):
        rank = ["🥇","🥈","🥉"][i]
        with st.expander(f"{rank} Outfit {i+1} — Score: {outfit['score']}/100",
                          expanded=(i==0)):
            icols = st.columns(max(len(outfit["items"]),1))
            for j, item in enumerate(outfit["items"]):
                with icols[j]:
                    img = best_image(item)
                    if img:
                        st.image(img, use_container_width=True)
                    else:
                        st.markdown(item_svg_html(item, size=80), unsafe_allow_html=True)
                    st.markdown(
                        f'<div style="font-size:0.8rem;font-weight:600;color:#e9d5ff;'
                        f'text-align:center">{item["name"]}</div>'
                        f'<div style="font-size:0.72rem;color:#9ca3af;text-align:center">'
                        f'{item["color"]}</div>',
                        unsafe_allow_html=True)

            st.markdown("")
            ca, cb = st.columns(2)
            with ca:
                st.markdown("**Score Breakdown**")
                for lbl, val in outfit.get("score_breakdown",{}).items():
                    pct = int(val)
                    st.markdown(f"<small>{lbl}</small>", unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="score-bar"><div class="score-fill" '
                        f'style="width:{pct}%"></div></div>'
                        f'<small style="color:#9ca3af">{pct}/100</small>',
                        unsafe_allow_html=True)
            with cb:
                st.markdown("**Colors**")
                st.markdown("".join(f'<span class="tag">🎨 {c}</span> '
                                    for c in outfit.get("color_palette",[])),
                            unsafe_allow_html=True)
                st.markdown(f'<span class="tag">✓ {outfit.get("color_rule","—")}</span>',
                            unsafe_allow_html=True)

            if outfit.get("ai_explanation"):
                st.markdown(
                    f'<div class="outfit-card">'
                    f'<strong style="color:#a78bfa">🤖 AI Stylist</strong><br><br>'
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
                            st.error(f"AI error: {e}")
                    st.rerun()

            b1, b2, b3 = st.columns(3)
            _regen = b2.button("🔄 Try Another", key=f"regen_{i}",
                                type="secondary", use_container_width=True)
            _tryon = b3.button("👗 Virtual Try-On", key=f"vto_{i}",
                                type="primary", use_container_width=True)
            if _regen:
                st.session_state.outfit_suggestions = []
                st.session_state.tryon_results = {}
                st.rerun()
            if _tryon:
                st.session_state.tryon_outfit_index = i
                st.session_state.page = "tryon"
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# VIRTUAL TRY-ON
# ─────────────────────────────────────────────────────────────────────────────

def page_tryon():
    st.markdown('<div class="hero-text">👗 Virtual Try-On</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Upload your photo. Pick outfit. See it on you.</div>',
                unsafe_allow_html=True)

    fashn_key = get_secret("FASHN_API_KEY")
    if not fashn_key:
        st.error("⚠️ FASHN_API_KEY missing from Streamlit Secrets.")
        return

    # Step 1 — photo
    st.markdown("### Step 1 — Your Photo")
    st.caption("Full body, facing forward, plain background.")
    cu, cp = st.columns([2,1])
    with cu:
        up = st.file_uploader("Full-body photo", type=["jpg","jpeg","png"],
                               key="tryon_upload", label_visibility="collapsed")
        if up:
            st.session_state.person_photo = up.read()
            st.success("✅ Photo ready!")
    with cp:
        if st.session_state.person_photo:
            st.image(st.session_state.person_photo, width=140)
        else:
            st.markdown('<div class="outfit-card" style="text-align:center;min-height:120px;'
                        'display:flex;align-items:center;justify-content:center">'
                        '<div style="color:#9ca3af">📸<br>Upload above</div>'
                        '</div>', unsafe_allow_html=True)

    if not st.session_state.person_photo:
        st.info("👆 Upload your full-body photo above.")
        return

    st.markdown("---")

    # Step 2 — outfit
    st.markdown("### Step 2 — Choose Outfit")
    wardrobe = st.session_state.wardrobe
    if not wardrobe:
        st.warning("Wardrobe is empty.")
        if st.button("👕 Build Wardrobe"):
            st.session_state.page = "wardrobe_builder"; st.rerun()
        return

    pick_mode = st.radio("Pick from:", ["AI suggestions","My wardrobe manually"],
                          horizontal=True)
    selected_items = []

    if pick_mode == "AI suggestions":
        if not st.session_state.outfit_suggestions:
            st.info("No outfit suggestions yet.")
            if st.button("✨ Generate Outfit"):
                st.session_state.page = "outfit"; st.rerun()
            return
        outfits = st.session_state.outfit_suggestions
        labels  = [f"{'🥇🥈🥉'[i]} Outfit {i+1} — {outfits[i]['score']}/100"
                   for i in range(len(outfits))]
        sel    = st.selectbox("Select:", labels,
                               index=min(st.session_state.tryon_outfit_index,len(labels)-1))
        oidx   = labels.index(sel)
        outfit = outfits[oidx]
        selected_items = [it for it in outfit["items"]
                          if it["category"] in ("tops","bottoms","dresses")]
        result_key = f"tryon_{oidx}"

        if selected_items:
            ic = st.columns(len(selected_items))
            for j, item in enumerate(selected_items):
                with ic[j]:
                    img = best_image(item)
                    if img:
                        st.image(img, use_container_width=True)
                    else:
                        st.markdown(item_svg_html(item, size=72), unsafe_allow_html=True)
                    st.caption(f"{item['name']} · {item['color']}")
    else:
        result_key = "tryon_manual"
        tops_items    = [it for it in wardrobe if it["category"] in ("tops","dresses")]
        bottoms_items = [it for it in wardrobe if it["category"] == "bottoms"]
        mc1, mc2 = st.columns(2)
        with mc1:
            st.markdown("**Top / Dress**")
            top_labels = [f"{it['name']} ({it['color']})" for it in tops_items]
            if top_labels:
                st_top = st.selectbox("Top:", top_labels, key="mt")
                ct = tops_items[top_labels.index(st_top)]
                img = best_image(ct)
                if img: st.image(img, width=120)
                else:   st.markdown(item_svg_html(ct, size=72), unsafe_allow_html=True)
                selected_items.append(ct)
            else:
                st.warning("No tops")
        with mc2:
            if not any(it["category"]=="dresses" for it in selected_items):
                st.markdown("**Bottom**")
                bot_labels = [f"{it['name']} ({it['color']})" for it in bottoms_items]
                if bot_labels:
                    st_bot = st.selectbox("Bottom:", bot_labels, key="mb")
                    cb_ = bottoms_items[bot_labels.index(st_bot)]
                    img = best_image(cb_)
                    if img: st.image(img, width=120)
                    else:   st.markdown(item_svg_html(cb_, size=72), unsafe_allow_html=True)
                    selected_items.append(cb_)

    if not selected_items:
        st.warning("No items selected.")
        return

    st.markdown("---")
    st.markdown("### Step 3 — Try It On")

    col_b, col_a = st.columns(2)
    with col_b:
        st.markdown("**📸 You**")
        st.image(st.session_state.person_photo, use_container_width=True)

    cached = st.session_state.tryon_results.get(result_key)
    with col_a:
        st.markdown("**✨ You wearing the outfit**")
        if cached:
            st.image(cached, use_container_width=True)
        else:
            st.markdown(
                '<div class="outfit-card" style="text-align:center;min-height:350px;'
                'display:flex;align-items:center;justify-content:center">'
                '<div style="color:#9ca3af;font-size:1.1rem">'
                '👗<br>Your try-on will appear here</div>'
                '</div>', unsafe_allow_html=True)

    st.markdown("")
    if cached:
        cc1, cc2, cc3 = st.columns(3)
        cc1.download_button("⬇️ Save", data=cached,
                            file_name="outfitai_tryon.jpg",
                            mime="image/jpeg", use_container_width=True)
        if cc2.button("🔄 Redo", type="secondary", use_container_width=True):
            del st.session_state.tryon_results[result_key]; st.rerun()
        if cc3.button("✨ New Outfit", type="primary", use_container_width=True):
            st.session_state.page = "outfit"; st.rerun()
    else:
        if st.button("🚀 Try On Now", type="primary", use_container_width=True):
            prog_bar  = st.progress(0)
            prog_text = st.empty()

            def upd(pct, msg):
                try:
                    prog_bar.progress(min(int(pct), 100))
                    prog_text.markdown(
                        f'<div style="color:#a78bfa;text-align:center">{msg}</div>',
                        unsafe_allow_html=True)
                except Exception:
                    pass

            upd(5, "🔍 Preparing garment images…")

            # Resolve images for all items — sync fetch if not already on dict
            for it in selected_items:
                if not it.get("uploaded_image"):
                    upd(10, f"🌐 Fetching {it['color']} {it['name']}…")
                    best_image(it)   # writes onto it["uploaded_image"] as side effect
                # Final assignment for tryon.py
                if not it.get("uploaded_image"):
                    it["uploaded_image"] = None   # tryon.py will handle missing

            upd(15, "🔌 Connecting to FASHN AI…")

            try:
                engine = TryOnEngine(fashn_key)
                result = engine.run_outfit(
                    person=st.session_state.person_photo,
                    items=selected_items,
                    progress=upd,
                )

            except Exception as _te:
                st.error(f"Try-on error: {_te}")
                result = {"success":False,"error":str(_te)}

            if result.get("success") and result.get("result_image"):
                st.session_state.tryon_results[result_key] = result["result_image"]
                st.rerun()
            else:
                st.error(f"❌ Try-on failed: {result.get('error','Unknown')}")
                st.caption("Check FASHN credits at app.fashn.ai")


# ─────────────────────────────────────────────────────────────────────────────
# STYLE PROFILE
# ─────────────────────────────────────────────────────────────────────────────

def page_profile():
    st.markdown("## 📊 Style Profile")
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

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🎨 Dominant Colors")
        for color, cnt in profile.get("dominant_colors",[])[:6]:
            hex_c = resolve_color(color)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin:6px 0">'
                f'<div style="width:20px;height:20px;border-radius:50%;background:{hex_c};'
                f'border:1px solid #444"></div>'
                f'<span style="color:#e9d5ff">{color}</span>'
                f'<span style="color:#9ca3af;font-size:0.85rem">× {cnt}</span>'
                f'</div>', unsafe_allow_html=True)
    with c2:
        st.markdown("### 💡 Wardrobe Gaps")
        for gap in profile.get("gaps",[]):
            st.markdown(f"- {gap}")


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

_p = st.session_state.page
if   _p == "home":             page_home()
elif _p == "wardrobe_builder": page_wardrobe_builder()
elif _p == "my_wardrobe":      page_my_wardrobe()
elif _p == "outfit":           page_outfit()
elif _p == "tryon":            page_tryon()
elif _p == "profile":          page_profile()
