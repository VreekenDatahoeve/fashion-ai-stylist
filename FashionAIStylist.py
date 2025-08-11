# app.py
import os, re, random, json
import streamlit as st
from urllib.parse import urlparse, quote
from html import escape as html_escape
from openai import OpenAI

# ========= Instellingen =========
APP_URL = "https://fashion-ai-stylis-ifidobqmkgjtn7gjxgrudb.streamlit.app"  # <-- JOUW URL (geen trailing slash)
MODEL   = "gpt-4o-mini"
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

/* Chips / ballonnen */
.note-chip{
  display:block;
  margin: 6px 0 14px;
  padding: 10px 14px;
  border-radius: 14px;
  background: rgba(255,255,255,0.60);
  border: 1px solid rgba(255,255,255,0.75);
  color:#2d2a6c;
  font-weight:600;
  box-shadow: 0 10px 24px rgba(40,12,120,0.15);
  backdrop-filter: blur(4px);
}

.balloon{
  display:block;
  margin: 0 0 14px;
  padding: 12px 16px;
  border-radius: 16px;
  background: rgba(255,255,255,0.42); /* iets transparanter */
  border: 1px solid rgba(255,255,255,0.7);
  color:#2d2a6c;
  font-weight:800;
  box-shadow: 0 12px 28px rgba(40,12,120,0.16);
  backdrop-filter: blur(4px);
}

/* Cards */
.card{
  background:#ffffff;
  border-radius: 22px;
  padding: 18px;
  box-shadow: 0 16px 40px rgba(23,0,75,0.18);
  border: 1px solid #EFEBFF;
  margin-top: 12px;
}
.card-title{
  font-size: 22px; font-weight: 800; color:#2d2a6c; margin:0 0 10px;
  display:flex; gap:10px; align-items:center;
}
.card-body{ color:#2b2b46; }

/* Lijsten */
ul{ margin: 0 0 0 1.15rem; padding:0; }
li{ margin: 4px 0; }

/* Pills */
.pills{ display:flex; gap:10px; flex-wrap:wrap; margin-top: 10px; }
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

.stTextInput > div > div > input, .stSelectbox > div > div { border-radius:12px !important; min-height:42px; }

h1, h2, h3 { letter-spacing:-.02em; }
.small-note{ color:#6B7280; font-size: 13px; }
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

# ---------- CTA onderin ----------
st.markdown("""
<button class="cta" onclick="
  const u = new URL(window.location);
  u.searchParams.set('prefs','1');
  window.location.replace(u.toString());
">
  <span class="dot"></span> Vertel iets over jezelf
</button>
""", unsafe_allow_html=True)

# ---------- Icons ----------
INFO_SVG = """<svg class="icon" viewBox="0 0 24 24" width="22" height="22" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" stroke="#556BFF" stroke-width="2"/><path d="M12 8h.01M11 11h2v5h-2z" stroke="#556BFF" stroke-width="2" stroke-linecap="round"/></svg>"""
HANGER_SVG = """<svg class="icon" viewBox="0 0 24 24" width="22" height="22" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M9 7a3 3 0 116 0c0 1.5-1 2-2 2v2" stroke="#7B61FF" stroke-width="2" stroke-linecap="round"/><path d="M3 17h18l-9-5-9 5z" stroke="#7B61FF" stroke-width="2" stroke-linecap="round"/></svg>"""

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

# ---------- OpenAI: gestructureerd advies ----------
def get_advice_json(link: str) -> dict:
    """
    Verwacht JSON:
    {
      "general": {"intro":"max 2 korte zinnen","bullets":["exact 3 bullets"]},
      "wear": {"blurb":"1 korte zin","combine_with":[{"label":"...","query":"..."}]}
    }
    """
    profile = f"figuur={lichaamsvorm}, huidskleur={huidskleur}, lengte={lengte}, gelegenheid={gelegenheid}, stijlgevoel={gevoel}"
    system = "Je bent een modieuze maar praktische personal stylist. Schrijf in helder Nederlands (B1). Kort en concreet."
    user = f"""
Analyseer dit kledingstuk (URL): {link}
Profiel: {profile}

Geef ALLEEN JSON met exact dit schema:
{{
  "general": {{
    "intro": "max 2 korte zinnen met eerste observatie (pasvorm, materiaal, vibe).",
    "bullets": ["3 kernpunten: kwaliteit/details", "waarom het werkt", "wanneer te dragen"]
  }},
  "wear": {{
    "blurb": "1 korte zin met draagadvies (hoe te stylen voor de gelegenheid).",
    "combine_with": [
      {{"label":"rechte jeans","query":"straight jeans"}},
      {{"label":"oversized blazer","query":"oversized blazer"}},
      {{"label":"basic sneakers","query":"witte leren sneakers"}}
    ]
  }}
}}

Regels:
- Geen uitleg buiten JSON.
- Gebruik B1 Nederlands, korte zinnen.
- Max 2 zinnen in "general.intro". Precies 3 bullets in "general.bullets".
- "combine_with" items moeten generiek genoeg zijn om binnen dezelfde webshop te zoeken.
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
        return json.loads(resp.choices[0].message.content)
    except Exception:
        # Fallback
        return {
            "general": {
                "intro": "Stijlvol item met moderne look. Valt comfortabel en is makkelijk te combineren.",
                "bullets": ["Tijdloos ontwerp", "Neutrale kleur werkt overal bij", "Fijn voor werk en weekend"]
            },
            "wear": {
                "blurb": "Houd de rest simpel en laat het item spreken.",
                "combine_with": [
                    {"label":"Rechte jeans","query":"straight jeans"},
                    {"label":"Oversized blazer","query":"oversized blazer"},
                    {"label":"Basic sneakers","query":"witte leren sneakers"}
                ]
            }
        }

# ---------- Render ----------
def render_general(data: dict):
    g = data.get("general", {}) or {}
    intro = esc(g.get("intro","")).strip()
    bullets = [esc(x) for x in as_list(g.get("bullets"))][:3]

    st.markdown(f"""
    <div class="card">
      <div class="card-title">{INFO_SVG} Algemeen</div>
      <div class="card-body">
        <p style="margin:0 0 8px; line-height:1.45;">{intro}</p>
        <ul>
          {''.join([f"<li>{b}</li>" for b in bullets])}
        </ul>
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_wear(link: str, data: dict):
    w = data.get("wear", {}) or {}
    blurb = esc(w.get("blurb",""))
    combos = as_list(w.get("combine_with"))

    pills_html = ""
    for c in combos:
        if isinstance(c, dict):
            label = esc(c.get("label","Shop"))
            query = c.get("query", c.get("label","Shop"))
        else:
            label = esc(str(c)); query = str(c)
        url = _build_link_or_fallback(link, query)
        pills_html += f"<a class='pill' href='{url}' target='_blank'>{label}</a>"

    st.markdown(f"""
    <div class="card">
      <div class="card-title">{HANGER_SVG} Draagadvies</div>
      <div class="card-body">
        <p style="margin:0 0 8px; line-height:1.45;">{blurb}</p>
        <div class="pills">{pills_html}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ---------- UI ----------
# Info-chip (bookmarklet tekst)
st.markdown("<span class='note-chip'>Bookmarklet: sleep deze AI-stylist naar je bladwijzerbalk en klik op een productpagina.</span>", unsafe_allow_html=True)

rendered = False
advice = None

# Productnaam-ballon (alleen als er een link is)
def product_balloon(u: str):
    if not u: return
    name = _product_name(u)
    st.markdown(f"<div class='balloon'>{esc(name)}</div>", unsafe_allow_html=True)

# Auto-run
if link_qs and auto:
    product_balloon(link_qs)
    advice = get_advice_json(link_qs)
    rendered = True

# Handmatige invoer
with st.form("manual"):
    link = st.text_input("🔗 Plak een productlink", value=link_qs or "", placeholder="https://…")
    go = st.form_submit_button("Vraag AI om advies")

if go and link:
    product_balloon(link)
    try:
        advice = get_advice_json(link)
        rendered = True
    except Exception as e:
        st.error(f"Er ging iets mis bij het ophalen van advies: {e}")

# Render secties
if rendered and advice:
    render_general(advice)
    render_wear(link_qs if auto else link, advice)
