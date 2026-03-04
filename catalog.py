"""
OutfitAI Clothing Catalog
64 clothing cards across 7 categories for the swipe wardrobe builder.
"""

CATALOG = [

    # ── TOPS (Round 1) ────────────────────────────────────────────────────────
    {"id": "tshirt",    "name": "T-Shirt",          "emoji": "👕", "category": "tops",
     "description": "Classic crew-neck or V-neck tee", "formality": 1,
     "styles": ["casual", "minimal", "versatile"],
     "occasions": ["casual", "active", "travel"],
     "colors": ["White", "Black", "Grey", "Navy", "Olive", "Burgundy", "Sky Blue", "Pink", "Yellow", "Green"]},

    {"id": "shirt",     "name": "Button-Down Shirt", "emoji": "👔", "category": "tops",
     "description": "Classic collared shirt, casual or formal", "formality": 3,
     "styles": ["classic", "smart", "versatile"],
     "occasions": ["work", "casual", "formal", "date"],
     "colors": ["White", "Light Blue", "Navy", "Pink", "Black", "Olive", "Burgundy", "Cream", "Grey", "Mustard"]},

    {"id": "blouse",    "name": "Blouse",            "emoji": "👚", "category": "tops",
     "description": "Elegant or casual women's top", "formality": 3,
     "styles": ["feminine", "classic", "smart"],
     "occasions": ["work", "date", "casual", "formal"],
     "colors": ["White", "Black", "Navy", "Blush", "Sage", "Burgundy", "Cream", "Lavender", "Teal"]},

    {"id": "hoodie",    "name": "Hoodie",            "emoji": "🧥", "category": "tops",
     "description": "Casual pullover or zip-up hoodie", "formality": 1,
     "styles": ["casual", "street", "sporty", "relaxed"],
     "occasions": ["casual", "active", "travel"],
     "colors": ["Grey", "Black", "Navy", "Olive", "Burgundy", "White", "Brown", "Teal"]},

    {"id": "sweater",   "name": "Sweater / Knitwear","emoji": "🧶", "category": "tops",
     "description": "Cozy knit sweater or jumper", "formality": 2,
     "styles": ["classic", "casual", "smart", "preppy"],
     "occasions": ["casual", "work", "date", "travel"],
     "colors": ["Cream", "Grey", "Navy", "Camel", "Burgundy", "Green", "Black", "Mustard", "White"]},

    {"id": "polo",      "name": "Polo Shirt",        "emoji": "👕", "category": "tops",
     "description": "Smart-casual collared polo", "formality": 2,
     "styles": ["preppy", "smart", "casual", "classic"],
     "occasions": ["casual", "work", "travel"],
     "colors": ["White", "Navy", "Black", "Grey", "Burgundy", "Sky Blue", "Green", "Yellow"]},

    {"id": "tank",      "name": "Tank Top / Cami",   "emoji": "🩱", "category": "tops",
     "description": "Sleeveless top, great for layering", "formality": 1,
     "styles": ["casual", "minimal", "sporty"],
     "occasions": ["casual", "active", "travel"],
     "colors": ["White", "Black", "Grey", "Blush", "Cream", "Navy", "Teal", "Burgundy"]},

    {"id": "crop",      "name": "Crop Top",          "emoji": "👕", "category": "tops",
     "description": "Cropped top, trendy and versatile", "formality": 1,
     "styles": ["street", "casual", "bold", "trendy"],
     "occasions": ["casual", "date"],
     "colors": ["White", "Black", "Grey", "Pink", "Lavender", "Cream", "Teal", "Yellow"]},

    # ── BOTTOMS (Round 2) ─────────────────────────────────────────────────────
    {"id": "jeans",     "name": "Jeans",             "emoji": "👖", "category": "bottoms",
     "description": "Classic denim jeans — slim, straight, or wide", "formality": 2,
     "styles": ["casual", "versatile", "classic"],
     "occasions": ["casual", "work", "date", "travel"],
     "colors": ["Navy", "Black", "Light Blue", "White", "Grey", "Indigo"]},

    {"id": "chinos",    "name": "Chinos / Trousers", "emoji": "👖", "category": "bottoms",
     "description": "Smart casual trousers", "formality": 3,
     "styles": ["smart", "classic", "preppy", "versatile"],
     "occasions": ["work", "casual", "date", "formal"],
     "colors": ["Beige", "Navy", "Olive", "Black", "Grey", "Camel", "Burgundy", "White"]},

    {"id": "suit_trousers","name": "Suit Trousers",  "emoji": "🎽", "category": "bottoms",
     "description": "Formal tailored trousers", "formality": 5,
     "styles": ["formal", "classic", "tailored"],
     "occasions": ["formal", "work"],
     "colors": ["Black", "Charcoal", "Navy", "Grey"]},

    {"id": "shorts",    "name": "Shorts",            "emoji": "🩳", "category": "bottoms",
     "description": "Casual or smart shorts", "formality": 1,
     "styles": ["casual", "sporty", "relaxed"],
     "occasions": ["casual", "active", "travel"],
     "colors": ["Navy", "Black", "Beige", "White", "Olive", "Grey", "Burgundy"]},

    {"id": "skirt_midi","name": "Midi Skirt",        "emoji": "👗", "category": "bottoms",
     "description": "Elegant mid-length skirt", "formality": 3,
     "styles": ["feminine", "classic", "boho", "smart"],
     "occasions": ["work", "date", "casual", "formal"],
     "colors": ["Black", "White", "Navy", "Camel", "Burgundy", "Sage", "Blush", "Cream"]},

    {"id": "skirt_mini","name": "Mini Skirt",        "emoji": "🩱", "category": "bottoms",
     "description": "Short playful skirt", "formality": 2,
     "styles": ["feminine", "bold", "trendy", "street"],
     "occasions": ["casual", "date"],
     "colors": ["Black", "White", "Plaid", "Navy", "Pink", "Burgundy"]},

    {"id": "leggings",  "name": "Leggings",          "emoji": "🩱", "category": "bottoms",
     "description": "Comfortable leggings for sport or casual", "formality": 1,
     "styles": ["sporty", "casual", "minimal"],
     "occasions": ["active", "casual"],
     "colors": ["Black", "Grey", "Navy", "Burgundy", "Olive"]},

    # ── OUTERWEAR (Round 3) ───────────────────────────────────────────────────
    {"id": "jacket",    "name": "Casual Jacket",     "emoji": "🧥", "category": "outerwear",
     "description": "Denim, bomber, or casual jacket", "formality": 2,
     "styles": ["casual", "street", "cool", "versatile"],
     "occasions": ["casual", "date", "travel"],
     "colors": ["Black", "Navy", "Denim Blue", "Khaki", "Olive", "Brown", "Grey", "Burgundy"]},

    {"id": "blazer",    "name": "Blazer",            "emoji": "🥼", "category": "outerwear",
     "description": "Structured blazer for smart looks", "formality": 4,
     "styles": ["smart", "formal", "classic", "power"],
     "occasions": ["work", "formal", "date"],
     "colors": ["Black", "Navy", "Grey", "Camel", "White", "Burgundy", "Charcoal", "Olive"]},

    {"id": "coat",      "name": "Coat / Overcoat",   "emoji": "🧥", "category": "outerwear",
     "description": "Long coat for colder days", "formality": 3,
     "styles": ["classic", "elegant", "smart"],
     "occasions": ["work", "formal", "casual", "date"],
     "colors": ["Black", "Camel", "Grey", "Navy", "Charcoal", "Cream", "Burgundy"]},

    {"id": "raincoat",  "name": "Raincoat / Trench", "emoji": "🌧", "category": "outerwear",
     "description": "Waterproof or trench coat", "formality": 3,
     "styles": ["classic", "smart", "practical"],
     "occasions": ["work", "casual", "travel"],
     "colors": ["Beige", "Black", "Navy", "Olive", "Khaki", "Burgundy"]},

    {"id": "puffer",    "name": "Puffer Jacket",     "emoji": "🧥", "category": "outerwear",
     "description": "Warm quilted puffer for cold days", "formality": 1,
     "styles": ["casual", "sporty", "practical"],
     "occasions": ["casual", "active", "travel"],
     "colors": ["Black", "Navy", "Olive", "Burgundy", "Grey", "White", "Teal"]},

    {"id": "cardigan",  "name": "Cardigan",          "emoji": "🧶", "category": "outerwear",
     "description": "Open-front knit cardigan", "formality": 2,
     "styles": ["casual", "cosy", "classic", "layered"],
     "occasions": ["casual", "work", "travel"],
     "colors": ["Cream", "Grey", "Camel", "Navy", "Black", "Sage", "Mustard", "Burgundy"]},

    # ── FOOTWEAR (Round 4) ────────────────────────────────────────────────────
    {"id": "sneakers",  "name": "Sneakers",          "emoji": "👟", "category": "footwear",
     "description": "Classic trainers or fashion sneakers", "formality": 1,
     "styles": ["casual", "sporty", "street", "versatile"],
     "occasions": ["casual", "active", "travel"],
     "colors": ["White", "Black", "Grey", "Navy", "Multicolor", "Beige"]},

    {"id": "loafers",   "name": "Loafers",           "emoji": "🥿", "category": "footwear",
     "description": "Slip-on loafers — smart or casual", "formality": 3,
     "styles": ["smart", "preppy", "classic", "versatile"],
     "occasions": ["work", "casual", "date"],
     "colors": ["Black", "Brown", "Tan", "Navy", "Burgundy", "White"]},

    {"id": "boots",     "name": "Boots",             "emoji": "👢", "category": "footwear",
     "description": "Ankle boots, Chelsea, or knee-high", "formality": 3,
     "styles": ["edgy", "classic", "versatile", "cool"],
     "occasions": ["casual", "work", "date", "travel"],
     "colors": ["Black", "Brown", "Tan", "Burgundy", "Grey", "Camel"]},

    {"id": "heels",     "name": "Heels / Pumps",     "emoji": "👠", "category": "footwear",
     "description": "Dress heels or block heels", "formality": 4,
     "styles": ["formal", "feminine", "elegant"],
     "occasions": ["formal", "date", "work"],
     "colors": ["Black", "Nude", "White", "Red", "Navy", "Camel", "Blush"]},

    {"id": "oxfords",   "name": "Oxford / Derby Shoes","emoji":"👞", "category": "footwear",
     "description": "Classic leather dress shoes", "formality": 4,
     "styles": ["formal", "classic", "professional"],
     "occasions": ["formal", "work"],
     "colors": ["Black", "Brown", "Tan", "Burgundy", "Navy"]},

    {"id": "sandals",   "name": "Sandals",           "emoji": "👡", "category": "footwear",
     "description": "Open sandals for warm weather", "formality": 1,
     "styles": ["casual", "boho", "summer", "relaxed"],
     "occasions": ["casual", "travel", "date"],
     "colors": ["Tan", "Black", "White", "Brown", "Beige", "Gold"]},

    {"id": "sport_shoes","name": "Running / Sport Shoes","emoji":"🏃", "category": "footwear",
     "description": "Athletic performance shoes", "formality": 1,
     "styles": ["sporty", "active", "technical"],
     "occasions": ["active"],
     "colors": ["Black", "White", "Grey", "Navy", "Neon", "Multicolor"]},

    # ── DRESSES & JUMPSUITS (Round 5) ─────────────────────────────────────────
    {"id": "dress_casual","name": "Casual Dress",    "emoji": "👗", "category": "dresses",
     "description": "Easy everyday dress", "formality": 2,
     "styles": ["feminine", "casual", "boho", "minimal"],
     "occasions": ["casual", "date", "travel"],
     "colors": ["Black", "White", "Navy", "Floral", "Blush", "Olive", "Teal", "Burgundy"]},

    {"id": "dress_midi", "name": "Midi Dress",       "emoji": "👗", "category": "dresses",
     "description": "Elegant mid-length dress", "formality": 3,
     "styles": ["feminine", "classic", "elegant"],
     "occasions": ["date", "work", "formal", "casual"],
     "colors": ["Black", "Navy", "Burgundy", "Cream", "Blush", "Forest Green", "Cobalt"]},

    {"id": "dress_formal","name": "Formal Dress",    "emoji": "👘", "category": "dresses",
     "description": "Evening or occasion dress", "formality": 5,
     "styles": ["formal", "elegant", "glamorous"],
     "occasions": ["formal"],
     "colors": ["Black", "Navy", "Burgundy", "Emerald", "Gold", "Red", "Royal Blue"]},

    {"id": "jumpsuit",  "name": "Jumpsuit / Romper", "emoji": "🩱", "category": "dresses",
     "description": "One-piece jumpsuit — effortlessly chic", "formality": 2,
     "styles": ["trendy", "minimal", "cool", "versatile"],
     "occasions": ["casual", "date", "travel"],
     "colors": ["Black", "White", "Navy", "Olive", "Cream", "Burgundy", "Rust"]},

    # ── ACCESSORIES (Round 6) ─────────────────────────────────────────────────
    {"id": "bag_tote",  "name": "Tote / Handbag",    "emoji": "👜", "category": "accessories",
     "description": "Everyday bag or tote", "formality": 2,
     "styles": ["casual", "minimal", "versatile"],
     "occasions": ["work", "casual", "travel"],
     "colors": ["Black", "Brown", "Tan", "Navy", "White", "Camel", "Beige"]},

    {"id": "bag_crossbody","name": "Crossbody Bag",  "emoji": "👛", "category": "accessories",
     "description": "Compact crossbody for going out", "formality": 2,
     "styles": ["casual", "cool", "street"],
     "occasions": ["casual", "date", "travel"],
     "colors": ["Black", "Brown", "Tan", "White", "Burgundy", "Navy"]},

    {"id": "belt",      "name": "Belt",              "emoji": "🔗", "category": "accessories",
     "description": "Leather or fabric belt", "formality": 3,
     "styles": ["classic", "smart", "versatile"],
     "occasions": ["work", "casual", "formal"],
     "colors": ["Black", "Brown", "Tan", "White", "Burgundy"]},

    {"id": "scarf",     "name": "Scarf",             "emoji": "🧣", "category": "accessories",
     "description": "Neck scarf or wrap", "formality": 2,
     "styles": ["classic", "boho", "layered", "elegant"],
     "occasions": ["casual", "work", "travel"],
     "colors": ["Navy", "Burgundy", "Camel", "Grey", "Black", "Plaid", "Cream"]},

    {"id": "hat_cap",   "name": "Cap / Hat",         "emoji": "🧢", "category": "accessories",
     "description": "Baseball cap, beanie, or fedora", "formality": 1,
     "styles": ["casual", "street", "sporty"],
     "occasions": ["casual", "active", "travel"],
     "colors": ["Black", "Navy", "White", "Grey", "Olive", "Beige"]},

    {"id": "sunglasses","name": "Sunglasses",        "emoji": "🕶️", "category": "accessories",
     "description": "Everyday or statement sunglasses", "formality": 1,
     "styles": ["cool", "casual", "bold", "classic"],
     "occasions": ["casual", "travel", "active"],
     "colors": ["Black", "Tortoiseshell", "Gold", "Clear", "Brown"]},

    {"id": "watch",     "name": "Watch",             "emoji": "⌚", "category": "accessories",
     "description": "Classic or smart watch", "formality": 3,
     "styles": ["classic", "smart", "minimal", "elegant"],
     "occasions": ["work", "casual", "formal", "date"],
     "colors": ["Silver", "Gold", "Black", "Brown", "Rose Gold"]},

    # ── TRADITIONAL / CULTURAL (Round 7) ─────────────────────────────────────
    {"id": "traditional_top","name": "Traditional Top/Tunic","emoji":"🥻","category":"tops",
     "description": "Embroidered or cultural heritage top", "formality": 3,
     "styles": ["traditional", "cultural", "elegant"],
     "occasions": ["casual", "formal", "cultural"],
     "colors": ["White", "Black", "Multicolor", "Red", "Blue", "Gold"]},

    {"id": "abaya",     "name": "Abaya / Long Robe", "emoji": "🥻", "category": "dresses",
     "description": "Modest full-length garment", "formality": 3,
     "styles": ["modest", "elegant", "traditional"],
     "occasions": ["casual", "formal", "cultural", "work"],
     "colors": ["Black", "Navy", "Grey", "Olive", "Burgundy", "White", "Camel"]},

    {"id": "linen_shirt","name": "Linen Shirt",      "emoji": "👕", "category": "tops",
     "description": "Breathable linen shirt for warm climates", "formality": 2,
     "styles": ["casual", "mediterranean", "relaxed", "classic"],
     "occasions": ["casual", "travel", "date"],
     "colors": ["White", "Cream", "Sky Blue", "Olive", "Beige", "Navy", "Pink", "Sage"]},

    {"id": "kurta",     "name": "Kurta / Tunic",     "emoji": "👘", "category": "tops",
     "description": "South Asian style long tunic", "formality": 3,
     "styles": ["traditional", "cultural", "elegant", "festive"],
     "occasions": ["casual", "formal", "cultural"],
     "colors": ["White", "Navy", "Cream", "Saffron", "Emerald", "Burgundy", "Gold", "Teal"]},
]
