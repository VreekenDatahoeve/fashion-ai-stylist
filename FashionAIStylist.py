# app.py
import os, re, json
import streamlit as st
from urllib.parse import urlparse, quote
from html import escape as html_escape
from textwrap import dedent
from openai import OpenAI

# ========= Instellingen =========
APP_URL = "https://fashion-ai-stylis-ifidobqmkgjtn7gjxgrudb.streamlit.app"
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
st.markdown(dedent("""
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

/* Layout breedte + extra onderruimte voor de floating CTA */
.block-container{
  max-width: 860px;
  padding-top: 8px !important;
  padding-bottom: 140px !important; /* ruimte onderin zodat CTA niet overlapt */
}

/* Bookmarklet chip */
.note-chip{
  display:block; margin: 6px 0 14px; padding: 10px 14px;
  border-radius: 14px; background: rgba(255,255,255,0.60);
  border: 1px solid rgba(255,255,255,0.75); color:#2d2a6c; font-weight:600;
  box-shadow: 0 10px 24px rgba(40,12,120,0.15); backdrop-filter: blur(4px);
}

/* Eén tekstwolk (card) */
.card{
  background:#ffffff; border-radius: 22px; padding: 18px;
  box-shadow: 0 16px 40px rgba(23,0,75,0.18); border: 1px solid #EFEBFF;
  margin-top: 12px;
}
.card-title{
  font-size: 24px; font-weight: 800; color:#2d2a6c; margin:0 0 10px;
  display:flex; gap:10px; align-items:center;
}
.card-body{ color:#2b2b46; }
ul{ margin: 0 0 0 1.15rem; padding:0; }
li{ margin: 6px 0; }

/* “Subkopjes” in dezelfde card */
.section-h{
  font-weight:800; margin:10px 0 2px; color:#2d2a6c;
}

/* Sticky CTA – rechtsonder met ruimte */
.cta{
  position: fixed; right: 22px; bottom: 22px; z-index: 1000;
  background: linear-gradient(180deg, #8C72FF 0%, #6F5BFF 100%);
  color:#ffffff; border:none; border-radius: 999px;
  padding: 12px 18px; font-weight:800;
  box-shadow: 0 16px 36px rgba(23,0,75,0.40);
  display:flex; align-items:center; gap:10px;
}
.cta .icon{ width:18px; height:18px; display:inline-block; }
.cta .icon svg{ width:18px; height:18px; fill:#fff; }

/* Input-card onderaan in dezelfde stijl */
div[data-testid="stForm"]{
  background:#ffffff !important;
  border:1px solid #EFEBFF !important;
  box-shadow: 0 16px 40px rgba(23,0,75,0.18) !important;
  border-radius:22px !important;
  padding: 16px !important;
  margin-top: 12px !important;
}
.stTextInput > div > div > input{ border-radius:12px !important; min-height:42px; }

h1, h2, h3 { letter-spacing:-.02em; }
.small-note{ color:#6B7280; font-size: 13px; }
</style>
"""), unsafe_allow_html=True)

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
    st.session_state.show_prefs = prefs_q

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

# ---------- Sticky CTA (rechtsonder) ----------
CHAT_SVG = """<span class="icon"><svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M4 12c0-4.4 3.6-8 8-8s8 3.6 8 8-3.6 8-8 8H9l-4 3v-3.5C4.7 18.3 4 15.3 4 12z" fill="white" opacity="0.9"/></svg></span>"""
st.markdown(dedent(f"""
<button class="cta" onclick="
  const u = new URL(window.location);
  u.searchParams.set('prefs','1');
  window.location.replace(u.toString());
">
  {CHAT_SVG} <span>Vertel iets over jezelf</span>
</button>
"""), unsafe_allow_html=True)

# ---------- Icons ----------
DRESS_SVG = """<svg class="icon" viewBox="0 0 24 24" width="22" height="22" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8 3l1.5 3-2 3 2 11h5l2-11-2-3L16 3h-2l-1 2-1-2H8z" fill="#556BFF"/></svg>"""
LINK_SVG  = """<svg class="icon" viewBox="0 0 24 24" width="22" height="22" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M10 14l-1 1a4 4 0 105.7 5.7l2.6-2.6a4 4 0 00-5.7-5.7l-.6.6" stroke="#6F5BFF" stroke-width="2" stroke-linecap="round"/><path d="M14 10l1-1a4 4 0 10-5.7-5.7L6.7 5.9a4 4 0 105.7 5.7l.6-.6" stroke="#6F5BFF" stroke-width="2" stroke-linecap="round"/></svg>"""

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
    p = urlparse(u); return f"{p.scheme}://{p.netloc}"
def _shop_searches(u: str, query: str, limit=1):
    host = _host(u); q = quote(query)
    patterns = [f"/search?q={q}", f"/zoeken?query={q}", f"/s?searchTerm={q}",
                f"/search?text={q}", f"/catalogsearch/result/?q={q}",
                f"/nl/search?q={q}", f"/zoeken?q={q}"]
    seen, out = set(), []
    for path in patterns:
        full = host + path
        if full not in seen: out.append(full); seen.add(full)
        if len(out) >= limit: break
    return out
def _google_fallback(u: str, query: str):
    p = urlparse(u); host = p.netloc
    q = quote(f"site:{host} {query}")
    return f"https://www.google.com/search?q={q}"
def _build_link_or_fallback(u: str, query: str):
    found = _shop_searches(u, query, limit=1)
    return found[0] if found else _google_fallback(u, query)

# ---------- OpenAI: advies voor één tekstwolk ----------
def get_advice_json(link: str) -> dict:
    """
    Verwacht JSON:
    {
      "intro_lines": ["1 of 2 zinnen"],
      "combine": ["2 bullets"],
      "fit_color": {"color":["2 bullets"], "fit":["2 bullets"]}
    }
    """
    # Defaults als sidebar dicht is
    fig = st.session_state.get("pf_l", "Weet ik niet")
    skin = st.session_state.get("pf_h", "Medium")
    hgt  = st.session_state.get("pf_len", "1.60 - 1.75m")
    occ  = st.session_state.get("pf_g", "Vrije tijd")
    vibe = st.session_state.get("pf_ge", "Casual")

    profile = f"figuur={fig}, huidskleur={skin}, lengte={hgt}, gelegenheid={occ}, stijlgevoel={vibe}"
    system = "Je bent een modieuze maar praktische personal stylist. Schrijf in helder Nederlands (B1), kort en concreet."
    user = f"""
Analyseer dit kledingstuk (URL): {link}
Profiel: {profile}

Geef ALLEEN JSON met exact dit schema:
{{
  "intro_lines": ["max 2 korte zinnen over stijl/pasvorm/materiaal"],
  "combine": ["exact 2 bullets waarmee te combineren (generieke items)"],
  "fit_color": {{
    "color": ["exact 2 bullets over passende kleuren"],
    "fit": ["exact 2 bullets over pasvorm/lengte"]
  }}
}}

Regels:
- Geen uitleg buiten JSON.
- B1 Nederlands; geen emoji; geen merknamen.
- Bullets kort (max 8–10 woorden).
"""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            response_format={"type":"json_object"},
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            temperature=0.5, max_tokens=450,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception:
        # Fallback
        return {
            "intro_lines": ["Zwarte, chunky sneakers; stijlvol en veelzijdig."],
            "combine": ["Rechte jeans of cargobroek", "Oversized blazer of hoodie"],
            "fit_color": {"color": ["Neutrale kleuren voor balans","Denim en grijs werken goed"],
                          "fit": ["Strakke broeken voor contrast","Hou top relaxed-fit"]}
        }

# ---------- Render: één tekstwolk ----------
def render_single_card(data: dict):
    intro_lines = [esc(x) for x in as_list(data.get("intro_lines"))][:2]
    combine = [esc(x) for x in as_list(data.get("combine"))][:2]
    colors  = [esc(x) for x in as_list(data.get("fit_color",{}).get("color"))][:2]
    fits    = [esc(x) for x in as_list(data.get("fit_color",{}).get("fit"))][:2]

    html = dedent(f"""
    <div class="card">
      <div class="card-title">
        <svg class="icon" viewBox="0 0 24 24" width="22" height="22" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8 3l1.5 3-2 3 2 11h5l2-11-2-3L16 3h-2l-1 2-1-2H8z" fill="#556BFF"/></svg>
        Kort advies
      </div>
      <div class="card-body">
        <ul>
          {''.join([f"<li>{x}</li>" for x in intro_lines])}
        </ul>

        <div class="section-h">• Combineer met</div>
        <ul>{''.join([f"<li>{x}</li>" for x in combine])}</ul>

        <div class="section-h">• Kleur & pasvorm</div>
        <ul>
          {''.join([f"<li>{x}</li>" for x in colors])}
          {''.join([f"<li>{x}</li>" for x in fits])}
        </ul>
      </div>
    </div>
    """)
    st.markdown(html, unsafe_allow_html=True)

# ---------- UI ----------
# (optioneel) bookmarklet-tekst zoals in de mock
st.markdown(dedent("""
<span class='note-chip'>Bookmarklet: sleep deze AI-stylist naar je bladwijzerbalk en klik op een productpagina.</span>
"""), unsafe_allow_html=True)

# State voor handmatige link
if "last_link" not in st.session_state:
    st.session_state.last_link = ""

active_link = link_qs if (auto and link_qs) else st.session_state.last_link

if active_link:
    data = get_advice_json(active_link)
    render_single_card(data)

# Input-veld ONDERAAN in witte card
with st.form("manual_bottom", clear_on_submit=False):
    st.markdown(dedent(f"<div class='card-title'>{LINK_SVG} Plak hier de link van een ander product</div>"), unsafe_allow_html=True)
    link_in = st.text_input(label="", value="", placeholder="https://…")
    go = st.form_submit_button("Geef advies")

if go and link_in:
    st.session_state.last_link = link_in.strip()
    st.rerun()
