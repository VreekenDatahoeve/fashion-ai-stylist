# app.py
import os, re, random, json
import streamlit as st
from urllib.parse import urlparse, quote
from openai import OpenAI

# ========= Instellingen =========
APP_URL = "https://fashion-ai-stylis-ifidobqmkgjtn7gjxgrudb.streamlit.app"  # <-- JOUW URL (geen trailing slash)
MODEL   = "gpt-4o-mini"
SHOW_AVATAR = True   # zet False om te verbergen
# =================================

# --- API key ---
API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not API_KEY:
    st.error("Geen OpenAI API-sleutel gevonden. Zet OPENAI_API_KEY in Secrets.")
    st.stop()
client = OpenAI(api_key=API_KEY)

# --- Pagina ---
st.set_page_config(
    page_title="Fashion AI Stylist",
    page_icon="👗",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ---------- CSS ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"]{ height:100%; }
html, body, [class*="stApp"]{ font-family:"Inter", system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }

/* Paarse gradient background */
[data-testid="stAppViewContainer"]{
  background: radial-gradient(1200px 600px at 50% -100px, #C8B9FF 0%, #AA98FF 30%, #8F7DFF 60%, #7A66F7 100%);
}
[data-testid="stHeader"] { display:none; }
footer { visibility:hidden; }

/* Layout breedte */
.block-container{ max-width: 860px; padding-top: 8px !important; padding-bottom: 96px !important; }

/* Tekstballon */
.balloon{
  background: rgba(255,255,255,0.85);
  border: 1px solid rgba(255,255,255,0.75);
  border-radius: 18px;
  padding: 14px 18px;
  box-shadow: 0 12px 32px rgba(40,12,120,0.18);
  backdrop-filter: blur(4px);
  color:#2d2a6c;
  font-weight: 700;
  line-height:1.35;
  margin-top: 6px;
}

/* Cards */
.card{
  background:#fff;
  border-radius: 22px;
  padding: 22px;
  box-shadow: 0 16px 40px rgba(23,0,75,0.18);
  border: 1px solid #F1ECFF;
  margin-top: 18px;
}
.card-title{
  font-size: 24px; font-weight: 800; color:#2d2a6c; margin:0 0 8px;
  display:flex; gap:10px; align-items:center;
}
.card-body{ color:#2b2b46; }

/* Advieskaart: tekst links, avatar rechts */
.advice-grid{
  display:grid;
  grid-template-columns: 1fr 220px;
  gap: 12px;
  align-items: start;
}
.advice-copy{ min-width:0; }
.avatar-box{ display:flex; justify-content:center; position:relative; z-index:0; }
.avatar-box svg{
  width:100%; height:auto; border-radius:24px;
  box-shadow: 0 10px 30px rgba(23,0,75,.15);
}

/* Responsive */
@media (max-width: 720px){
  .advice-grid{ grid-template-columns: 1fr; }
  .avatar-box{ order:-1; margin-bottom: 8px; }
}

/* Pills */
.pills{ display:flex; gap:10px; flex-wrap:wrap; }
.pill{
  background:#F4F3FF; color:#2b2b46; border:1px solid #E5E4FF;
  padding:10px 14px; border-radius: 999px; font-weight:700; text-decoration:none;
  box-shadow: 0 6px 14px rgba(23,0,75,0.10);
}
.pill:hover{ transform: translateY(-1px); }

/* Sticky CTA onderin */
.cta{
  position: fixed; left:50%; transform:translateX(-50%);
  bottom: 18px; z-index: 1000;
  background:#ffffff; color:#2d2a6c;
  border:1px solid #ECE9FF; border-radius: 24px;
  padding: 12px 16px; font-weight:800;
  box-shadow: 0 18px 40px rgba(23,0,75,0.25);
  display:flex; align-items:center; gap:10px;
}
.cta .dot{ width:10px; height:10px; border-radius:50%; background:#6F5BFF; box-shadow:0 0 0 6px rgba(111,91,255,.15); }

/* Inputs */
.stTextInput > div > div > input, .stSelectbox > div > div {
  border-radius:12px !important; min-height:42px;
}

h1, h2, h3 { letter-spacing:-.02em; }
.small-note{ color:#6B7280; font-size: 13px; }
ul{ margin: 0 0 0 1.2rem; }
</style>
""", unsafe_allow_html=True)

# ---------- Query params ----------
qp = st.query_params
def _get(name, default=""):
    v = qp.get(name, default)
    return (v[0] if isinstance(v, list) and v else v) or default

link_qs = _get("u").strip()
auto    = str(_get("auto","0")) == "1"
prefs_q = _get("prefs","0") == "1"

# ---------- Sidebar voorkeuren ----------
if "show_prefs" not in st.session_state:
    st.session_state.show_prefs = prefs_q  # open als ?prefs=1

if st.session_state.show_prefs:
    with st.sidebar:
        st.markdown("### 👤 Vertel iets over jezelf")
        lichaamsvorm = st.selectbox("Lichaamsvorm", ["Zandloper","Peer","Rechthoek","Appel","Weet ik niet"], index=4, key="pf_l")
        huidskleur   = st.selectbox("Huidskleur",   ["Licht","Medium","Donker"], index=1, key="pf_h")
        lengte       = st.selectbox("Lengte",       ["< 1.60m","1.60 - 1.75m","> 1.75m"], index=1, key="pf_len")
        gelegenheid  = st.selectbox("Gelegenheid",  ["Werk","Feest","Vrije tijd","Bruiloft","Date"], index=2, key="pf_g")
        gevoel       = st.selectbox("Gevoel",       ["Zelfverzekerd","Speels","Elegant","Casual","Trendy"], index=3, key="pf_ge")
        if st.button("Sluiten", use_container_width=True):
            st.session_state.show_prefs = False
            st.experimental_set_query_params(**{k:v for k,v in qp.items() if k!="prefs"})
            st.rerun()
else:
    lichaamsvorm = "Weet ik niet"; huidskleur="Medium"; lengte="1.60 - 1.75m"; gelegenheid="Vrije tijd"; gevoel="Casual"

# ---------- CTA onderin -> zet prefs=1 en reload ----------
st.markdown("""
<button class="cta" onclick="
  const u = new URL(window.location);
  u.searchParams.set('prefs','1');
  window.location.replace(u.toString());
">
  <span class="dot"></span> Vertel iets over jezelf
</button>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
def _keywords_from_url(u: str):
    try:
        slug = urlparse(u).path.rstrip("/").split("/")[-1]
        slug = re.sub(r"\d+", " ", slug)
        words = [w for w in re.split(r"[-_]+", slug) if w and len(w) > 1]
        return " ".join(words[:6]) or "fashion"
    except Exception:
        return "fashion"

def _product_name(u: str):
    kw = _keywords_from_url(u)
    return re.sub(r"\s+", " ", kw).strip().title()

def _category_candidates(u: str):
    p = urlparse(u)
    segs = [s for s in p.path.split("/") if s]
    cands = []
    if len(segs) >= 2: cands.append("/" + "/".join(segs[:-1]) + "/")
    if len(segs) >= 3: cands.append("/" + "/".join(segs[:-2]) + "/")
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            out.append(c); seen.add(c)
    return [f"{p.scheme}://{p.netloc}{c}" for c in out]

def _host(u: str) -> str:
    p = urlparse(u)
    return f"{p.scheme}://{p.netloc}"

def _shop_searches(u: str, query: str, limit=1):
    """
    Bouw shop-specifieke zoek-URL's op basis van gangbare patronen.
    """
    host = _host(u)
    q = quote(query)
    patterns = [
        f"/search?q={q}", f"/zoeken?query={q}", f"/s?searchTerm={q}",
        f"/search?text={q}", f"/catalogsearch/result/?q={q}",
        f"/nl/search?q={q}", f"/zoeken?q={q}"
    ]
    seen, out = set(), []
    for path in patterns:
        full = host + path
        if full not in seen:
            out.append(full); seen.add(full)
        if len(out) >= limit:
            break
    return out

def _google_fallback(u: str, query: str):
    """
    Fallback naar Google Shopping/site search als de shop geen known pattern heeft.
    """
    p = urlparse(u)
    host = p.netloc
    q = quote(f"site:{host} {query}")
    return f"https://www.google.com/search?q={q}"

def _build_link_or_fallback(u: str, query: str):
    found = _shop_searches(u, query, limit=1)
    return found[0] if found else _google_fallback(u, query)

def build_shop_alternatives(u: str):
    if not u: return []
    kw = _keywords_from_url(u)
    cats = _category_candidates(u)
    items = []
    if cats:
        items.append(("Categorie (zelfde shop)", cats[0]))
        if len(cats) > 1: items.append(("Bredere categorie", cats[1]))
    # Voeg ook een gerichte zoekopdracht toe
    items.append((f"Zoek: {kw}", _build_link_or_fallback(u, kw)))
    seen, out = set(), []
    for t, url in items:
        if url not in seen:
            out.append((t, url)); seen.add(url)
    return out[:3]

# ---------- OpenAI: gestructureerd advies ----------
def get_advice_json(link: str) -> dict:
    """
    Vraagt de LLM om kort, NL B1 en gestructureerd advies met:
    - summary (3 bullets)
    - combine_with: lijst van {label, query} om te zoeken binnen dezelfde shop
    - fit_color: bullets (kleurpalet, pasvorm, tip/avoid)
    - care: 1 korte zin
    - alternatives: lijst van {label, query}
    """
    profile = f"figuur={lichaamsvorm}, huidskleur={huidskleur}, lengte={lengte}, gelegenheid={gelegenheid}, stijlgevoel={gevoel}"
    system = "Je bent een modieuze maar praktische personal stylist. Schrijf in helder Nederlands (B1). Kort en concreet."
    user = f"""
Analyseer dit kledingstuk (URL): {link}
Profiel: {profile}

Geef ALLEEN JSON met exact dit schema:
{{
  "summary": ["max 3 korte bullets"],
  "combine_with": [
    {{"label":"witte sneakers","query":"witte leren sneakers"}},
    {{"label":"broek","query":"donkerblauwe straight jeans"}}
  ],
  "fit_color": {{
    "color_palette": ["max 3 kleuren die goed passen"],
    "fit_tips": ["max 3 tips voor pasvorm en lengte"],
    "avoid": ["max 2 dingen om te vermijden"]
  }},
  "care": "1 korte zin over verzorging",
  "alternatives": [
    {{"label":"alternatief 1","query":"zelfde item in navy"}},
    {{"label":"alternatief 2","query":"duurzamer materiaal"}}
  ]
}}

Regels:
- Geen uitleg buiten JSON.
- Combineer-suggesties moeten generiek genoeg zijn om te zoeken op dezelfde webshop (gebruik zoekwoorden, geen merk).
- Korte, duidelijke tekst. Geen emoji.
"""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            response_format={"type":"json_object"},
            messages=[
                {"role":"system","content":system},
                {"role":"user","content":user},
            ],
            temperature=0.5,
            max_tokens=500,
        )
        raw = resp.choices[0].message.content
        data = json.loads(raw)
        return data
    except Exception as e:
        # Fallback minimal advies
        return {
            "summary": ["Stijlvol item.", "Makkelijk te combineren.", "Tijdloos."],
            "combine_with": [
                {"label":"witte sneakers","query":"witte sneakers"},
                {"label":"donkerblauwe jeans","query":"donkerblauwe straight jeans"},
                {"label":"licht jasje","query":"licht overshirt of blazer"}
            ],
            "fit_color": {
                "color_palette": ["wit","donkerblauw","taupe"],
                "fit_tips": ["Kies je normale maat.","Rol mouwen voor casual look.","Draag in- of over de broek."],
                "avoid": ["Te strakke pasvorm.","Te felle contrasterende riemen."]
            },
            "care": "Wassen op 30°C, binnenstebuiten.",
            "alternatives": [
                {"label":"Donkerblauwe variant","query":"donkerblauw"},
                {"label":"Biologisch katoen","query":"organic cotton"}
            ]
        }

def get_quick_blurb(link: str, item_name: str) -> str:
    prompt = f"""
Item: {item_name}
Link: {link}
User profile -> figure:{lichaamsvorm}, skin:{huidskleur}, height:{lengte}, occasion:{gelegenheid}, vibe:{gevoel}.
Write ONE short English sentence (max 20 words) starting with:
This {item_name}
Use only simple, clear words (B1). No jargon. No emojis.
"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role":"system","content":"Return exactly one friendly, simple sentence."},
            {"role":"user","content":prompt},
        ],
        temperature=0.6, max_tokens=60,
    )
    return resp.choices[0].message.content.strip().rstrip()

# ---------- UI logic ----------
rendered = False
advies = None
balloon_html = ""
OPENERS = ["Looks nice!", "Great pick!", "Nice choice!", "Love the vibe!", "Stylish pick!"]

# Auto-run via querystring
if link_qs and auto:
    item_name = _product_name(link_qs)
    quick = get_quick_blurb(link_qs, item_name)
    opener = random.choice(OPENERS)
    balloon_html = f"<div class='balloon'>{opener} {quick}</div>"
    advies = get_advice_json(link_qs)
    rendered = True

# Tekstballon (alleen als er een link is)
if balloon_html:
    st.markdown(balloon_html, unsafe_allow_html=True)

# --- Mockup-achtige avatar (inline SVG) ---
AVATAR_SVG = """
<svg viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg" aria-label="AI Stylist Avatar" role="img">
  <defs>
    <radialGradient id="bg" cx="60%" cy="30%" r="80%">
      <stop offset="0%" stop-color="#c9d4ff"/>
      <stop offset="60%" stop-color="#9fb0ff"/>
      <stop offset="100%" stop-color="#7a86ff"/>
    </radialGradient>
  </defs>
  <g>
    <rect x="0" y="0" width="220" height="220" rx="36" fill="url(#bg)"/>
    <!-- simpele zittende figuur -->
    <circle cx="120" cy="72" r="24" fill="#F6C8A7"/>
    <rect x="76" y="98" width="110" height="70" rx="32" fill="#6F79FF"/>
    <path d="M92 158 Q120 170 148 158" fill="#4C55D8"/>
    <circle cx="112" cy="70" r="4" fill="#5a3b2e"/>
    <circle cx="130" cy="70" r="4" fill="#5a3b2e"/>
    <path d="M112 82 Q121 88 130 82" stroke="#5a3b2e" stroke-width="3" fill="none" stroke-linecap="round"/>
  </g>
</svg>
"""

def render_advice(link: str, data: dict):
    # --- Kaart 1: Samenvatting + Fit & Kleur (met avatar)
    summary_html = ""
    if data.get("summary"):
        lis = "".join([f"<li>{st._escape_html(x)}</li>" for x in data["summary"]])
        summary_html = f"<ul>{lis}</ul>"

    fit_color = data.get("fit_color", {})
    color_ul = "".join([f"<li>{st._escape_html(x)}</li>" for x in fit_color.get("color_palette", [])])
    tips_ul  = "".join([f"<li>{st._escape_html(x)}</li>" for x in fit_color.get("fit_tips", [])])
    avoid_ul = "".join([f"<li>{st._escape_html(x)}</li>" for x in fit_color.get("avoid", [])])

    st.markdown(f"""
    <div class="card">
      <div class="card-title">Kort advies</div>
      <div class="advice-grid">
        <div class="advice-copy">
          <div class="card-body">
            <h4 style="margin:0 0 6px;">Korte beoordeling</h4>
            {summary_html if summary_html else '<p class="small-note">Geen samenvatting.</p>'}
            <h4 style="margin:12px 0 6px;">Kleur & pasvorm</h4>
            {"<b>Kleuren</b><ul>"+color_ul+"</ul>" if color_ul else ""}
            {"<b>Tips</b><ul>"+tips_ul+"</ul>" if tips_ul else ""}
            {"<b>Vermijden</b><ul>"+avoid_ul+"</ul>" if avoid_ul else ""}
            <p class="small-note" style="margin-top:8px;">{st._escape_html(data.get("care",""))}</p>
          </div>
        </div>
        <div class="avatar-box">
          {AVATAR_SVG if SHOW_AVATAR else ""}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Kaart 2: Combineer met (met shop-zoeklinks)
    combos = data.get("combine_with", [])
    if combos:
        pills_html = ""
        for c in combos:
            label = c.get("label","Shop")
            query = c.get("query", label)
            url = _build_link_or_fallback(link, query)
            pills_html += f"<a class='pill' href='{url}' target='_blank'>{st._escape_html(label)}</a>"
        st.markdown(f"""
        <div class="card">
          <div class="card-title">Combineer met</div>
          <div class="card-body">
            <div class="pills">{pills_html}</div>
            <p class="small-note" style="margin-top:10px;">Links zoeken binnen dezelfde webshop waar mogelijk; anders Google-zoekresultaten.</p>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # --- Kaart 3: Alternatieven (zelfde shop / zoek)
    alts = data.get("alternatives", [])
    pills_html = ""
    for a in alts:
        label = a.get("label","Alternatief")
        query = a.get("query", label)
        url = _build_link_or_fallback(link, query)
        pills_html += f"<a class='pill' href='{url}' target='_blank'>{st._escape_html(label)}</a>"

    # voeg ook je oude categorie/zoek fallback toe
    shop_alts = build_shop_alternatives(link)
    for t, u in shop_alts:
        pills_html += f"<a class='pill' href='{u}' target='_blank'>{st._escape_html(t)}</a>"

    st.markdown(f"""
    <div class="card">
      <div class="card-title">Alternatieven</div>
      <div class="card-body">
        {pills_html if pills_html else "<span class='small-note'>Er verschijnen alternatieven zodra je een productlink gebruikt.</span>"}
      </div>
    </div>
    """, unsafe_allow_html=True)

# ---------- UI RENDER ----------
# Auto-run render
if rendered and advies:
    render_advice(link_qs, advies)

# Handmatige invoer
with st.form("manual"):
    link = st.text_input("🔗 Plak een productlink", value=link_qs or "", placeholder="https://…")
    go = st.form_submit_button("Vraag AI om advies")

if go and link:
    try:
        item_name = _product_name(link)
        quick = get_quick_blurb(link, item_name)
        opener = random.choice(["Looks nice!", "Great pick!", "Nice choice!", "Love the vibe!", "Stylish pick!"])
        st.markdown(f"<div class='balloon'>{opener} {quick}</div>", unsafe_allow_html=True)

        data = get_advice_json(link)
        render_advice(link, data)
    except Exception as e:
        st.error(f"Er ging iets mis bij het ophalen van advies: {e}")
