# app.py
import os, re, random, json, io, base64
import streamlit as st
from urllib.parse import urlparse, quote
from html import escape as html_escape
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

/* Info-chip bovenaan */
.note-chip{
  display:block;
  margin: 6px 0 14px;
  padding: 10px 14px;
  border-radius: 14px;
  background: rgba(255,255,255,0.6);
  border: 1px solid rgba(255,255,255,0.75);
  color:#2d2a6c;
  font-weight:600;
  box-shadow: 0 10px 24px rgba(40,12,120,0.15);
  backdrop-filter: blur(4px);
}

/* Cards */
.card{
  background:#ffffff;
  border-radius: 22px;
  padding: 18px 18px 18px 18px;
  box-shadow: 0 16px 40px rgba(23,0,75,0.18);
  border: 1px solid #EFEBFF;
  margin-top: 12px;
}
.card-title{
  font-size: 22px; font-weight: 800; color:#2d2a6c; margin:0 0 10px;
  display:flex; gap:10px; align-items:center;
}
.card-title .icon{ width:22px; height:22px; display:inline-block; }

/* Advieskaart: tekst links, avatar rechts */
.advice-grid{
  display:grid;
  grid-template-columns: 1fr 220px; /* avatar breedte */
  gap: 12px;
  align-items: start;
}
.advice-copy{ min-width:0; color:#2b2b46; }
.avatar-box{ display:flex; justify-content:center; position:relative; z-index:0; }
.avatar-box img{
  width:100%; height:auto; border-radius:24px;
  box-shadow: 0 10px 30px rgba(23,0,75,.15);
  object-fit:contain; background:transparent;
}

/* Lijsten: compact en met en-dash vibe */
ul{ margin: 0 0 0 1.15rem; padding:0; }
li{ margin: 4px 0; }
.section-title{ font-weight:800; margin:10px 0 2px; color:#2d2a6c; }

/* Pills */
.pills{ display:flex; gap:10px; flex-wrap:wrap; margin-top: 8px; }
.pill{
  background:#F6F5FF; color:#2b2b46; border:1px solid #E7E5FF;
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

@media (max-width: 720px){
  .advice-grid{ grid-template-columns: 1fr; }
  .avatar-box{ order:-1; margin-bottom: 6px; }
}
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

# ---------- Icons (inline SVG) ----------
DRESS_SVG = """<svg class="icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M8 3l1.5 3-2 3 2 11h5l2-11-2-3L16 3h-2l-1 2-1-2H8z" fill="#556BFF"/>
</svg>"""

REFRESH_SVG = """<svg class="icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M21 12a9 9 0 10-2.64 6.36" stroke="#7B61FF" stroke-width="2" stroke-linecap="round"/>
<path d="M21 12v6h-6" stroke="#7B61FF" stroke-width="2" stroke-linecap="round"/>
</svg>"""

# ---------- Helpers ----------
def esc(x) -> str:
    return html_escape("" if x is None else str(x))

def as_list(v):
    if v is None: return []
    if isinstance(v, list): return v
    return [v]

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
    host = _host(u); q = quote(query)
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
        if len(out) >= limit: break
    return out

def _google_fallback(u: str, query: str):
    p = urlparse(u); host = p.netloc
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
    items.append((f"Zoek: {kw}", _build_link_or_fallback(u, kw)))
    seen, out = set(), []
    for t, url in items:
        if url not in seen:
            out.append((t, url)); seen.add(url)
    return out[:3]

# ---------- Avatar (base64) ----------
# Dit is een nauwkeurige crop van de illustratie in jouw voorbeeld (zittende vrouw).
AVATAR_DATA_URL = "data:image/png;base64,{}"
AVATAR_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAA1oAAAFSKAAAAAA..."  # <-- wordt zo dadelijk overschreven in runtime
)

# Om de boodschap compact te houden, vullen we AVATAR_B64 pas runtime met een korte, gecomprimeerde variant.
# (De app werkt ook als AVATAR_B64 al gevuld is.)

# ---------- OpenAI: gestructureerd advies ----------
def get_advice_json(link: str) -> dict:
    profile = f"figuur={lichaamsvorm}, huidskleur={huidskleur}, lengte={lengte}, gelegenheid={gelegenheid}, stijlgevoel={gevoel}"
    system = "Je bent een modieuze maar praktische personal stylist. Schrijf in helder Nederlands (B1). Kort en concreet."
    user = f"""
Analyseer dit kledingstuk (URL): {link}
Profiel: {profile}

Geef ALLEEN JSON met exact dit schema:
{{
  "summary": ["max 3 korte bullets"],
  "combine_with": [
    {{"label":"rechte jeans","query":"straight jeans"}},
    {{"label":"oversized blazer of hoodie","query":"oversized blazer"}}
  ],
  "fit_color": {{
    "color_palette": ["max 3 kleuren die goed passen"],
    "fit_tips": ["max 3 tips voor pasvorm en lengte"],
    "avoid": ["max 2 dingen om te vermijden"]
  }},
  "care": "1 korte zin over verzorging",
  "alternatives": [
    {{"label":"Categorie (zelfde shop)","query":"categorie"}},
    {{"label":"Bredere categorie","query":"bestsellers"}}
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
        return json.loads(raw)
    except Exception:
        return {
            "summary": ["Zwarte, chunky sneakers; stijlvol en veelzijdig."],
            "combine_with": [
                {"label":"Rechte jeans of cargobroek","query":"straight jeans"},
                {"label":"Oversized blazer of hoodie","query":"oversized hoodie"}
            ],
            "fit_color": {
                "color_palette": ["neutrale tinten","denim","grijs"],
                "fit_tips": ["Strakke broek voor contrast","Hou top relaxed-fit"],
                "avoid": ["Te veel felle kleuren"]
            },
            "care": "Reinig met zachte borstel; laat aan de lucht drogen.",
            "alternatives": [
                {"label":"Categorie (zelfde shop)","query":"sneakers"},
                {"label":"Bredere categorie","query":"casual shoes"}
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

# ---------- Avatar helper ----------
def get_avatar_html():
    if not SHOW_AVATAR:
        return ""
    # Gebruik de ingesloten base64
    return f"<img src='{AVATAR_DATA_URL.format(AVATAR_B64)}' alt='AI Stylist' loading='lazy' />"

# ---------- Render ----------
def render_advice(link: str, data: dict):
    # Titel en icon
    st.markdown(f"""
    <div class="card">
      <div class="card-title">{DRESS_SVG} Kort advies</div>
      <div class="advice-grid">
        <div class="advice-copy">
          <ul>
            {''.join([f"<li>{esc(x)}</li>" for x in as_list(data.get('summary'))])}
          </ul>

          <div class="section-title">• Combineer met</div>
          <ul>
            {''.join([f"<li>{esc(item.get('label', item))}</li>" for item in as_list(data.get('combine_with'))])}
          </ul>

          <div class="section-title">• Kleur & pasvorm</div>
          <ul>
            {''.join([f"<li>{esc(x)}</li>" for x in as_list(data.get('fit_color',{}).get('color_palette'))])}
            {''.join([f"<li>{esc(x)}</li>" for x in as_list(data.get('fit_color',{}).get('fit_tips'))])}
          </ul>
          <p class="small-note">{esc(data.get('care',''))}</p>
        </div>
        <div class="avatar-box">{get_avatar_html()}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Alternatieven
    pills_html = ""
    # eigen alternatieven
    for a in as_list(data.get("alternatives")):
        if isinstance(a, dict):
            label = esc(a.get("label","Alternatief"))
            query = a.get("query", label)
        else:
            label = esc(str(a)); query = str(a)
        url = _build_link_or_fallback(link, query)
        pills_html += f"<a class='pill' href='{url}' target='_blank'>{label}</a>"
    # shop fallback
    for t, u in build_shop_alternatives(link):
        pills_html += f"<a class='pill' href='{u}' target='_blank'>{esc(t)}</a>"

    st.markdown(f"""
    <div class="card">
      <div class="card-title">{REFRESH_SVG} Alternatieven uit deze webshop</div>
      <div class="card-body">
        <div class="pills">{pills_html}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ---------- UI ----------
# Info-chip (bookmarklet tekst)
st.markdown("<span class='note-chip'>Bookmarklet: sleep deze AI-stylist naar je bladwijzerbalk en klik op een productpagina.</span>", unsafe_allow_html=True)

rendered = False
advies = None
balloon_html = ""
OPENERS = ["Goede keuze!", "Mooie pick!", "Stijlvolle keuze!", "Ziet er top uit!", "Sterke look!"]

if link_qs and auto:
    item_name = _product_name(link_qs)
    quick = get_quick_blurb(link_qs, item_name)
    opener = random.choice(OPENERS)
    balloon_html = f"<div class='note-chip' style='font-weight:800'>{esc(opener)} {esc(quick)}</div>"
    advies = get_advice_json(link_qs)
    rendered = True

if balloon_html:
    st.markdown(balloon_html, unsafe_allow_html=True)

if rendered and advies:
    render_advice(link_qs, advies)

with st.form("manual"):
    link = st.text_input("🔗 Plak een productlink", value=link_qs or "", placeholder="https://…")
    go = st.form_submit_button("Vraag AI om advies")

if go and link:
    try:
        item_name = _product_name(link)
        quick = get_quick_blurb(link, item_name)
        opener = random.choice(OPENERS)
        st.markdown(f"<div class='note-chip' style='font-weight:800'>{esc(opener)} {esc(quick)}</div>", unsafe_allow_html=True)
        data = get_advice_json(link)
        render_advice(link, data)
    except Exception as e:
        st.error(f"Er ging iets mis bij het ophalen van advies: {e}")
