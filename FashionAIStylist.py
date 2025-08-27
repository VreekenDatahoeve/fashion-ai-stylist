# app.py — MVP: Advies + Bijpassende links (inline CTA onder tweede kaart)
import os, re, json
import streamlit as st
from urllib.parse import urlparse, quote, urlencode
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

/* Layout breedte + extra onderruimte */
.block-container{
  max-width: 860px;
  padding-top: 8px !important;
  padding-bottom: 80px !important;
}

/* Bookmarklet chip */
.note-chip{
  display:block; margin: 6px 0 14px; padding: 10px 14px;
  border-radius: 14px; background: rgba(255,255,255,0.60);
  border: 1px solid rgba(255,255,255,0.75); color:#2d2a6c; font-weight:600;
  box-shadow: 0 10px 24px rgba(40,12,120,0.15); backdrop-filter: blur(4px);
}

/* Kaarten */
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

/* Subkopjes */
.section-h{
  font-weight:800; margin:12px 0 6px; color:#2d2a6c; display:flex; align-items:center; gap:8px;
}

/* Knoppenrij */
.btnrow{ display:flex; flex-wrap:wrap; gap:10px; margin-top:10px; }
.btn{
  display:inline-flex; align-items:center; gap:8px; padding:10px 14px; border-radius:12px;
  background:#F3F4FF; color:#2d2a6c; border:1px solid #E3E6FF; text-decoration:none; font-weight:700;
}
.btn svg{ width:18px; height:18px; }

/* Inline CTA (geen JS; we gebruiken een <a> link) */
.cta-inline{
  display:flex;
  justify-content:center;
  margin-top: 12px;
}
.cta-btn{
  background: linear-gradient(180deg, #8C72FF 0%, #6F5BFF 100%);
  color:#ffffff; border:none; border-radius:999px;
  padding: 14px 22px; font-weight:800;
  box-shadow: 0 16px 36px rgba(23,0,75,0.40);
  display:inline-flex; align-items:center; gap:12px; cursor:pointer;
  line-height: 1; text-decoration:none;
}
.cta-btn .icon{
  width:28px; height:28px;
  display:inline-flex; align-items:center;
  justify-content:center;
}
.cta-btn .icon svg{
  width:22px; height:22px; fill:#fff;
}

/* Input-card */
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

# ---------- Profiel in query params ----------
DEFAULT_PROFILE = {
    "pf_l":   "Weet ik niet",         # lichaamsvorm
    "pf_h":   "Medium",                # huidskleur
    "pf_len": "1.60 - 1.75m",          # lengte
    "pf_g":   "Vrije tijd",            # gelegenheid
    "pf_ge":  "Casual",                # gevoel
}

def _qp_get_one(name, default):
    v = st.query_params.get(name, default)
    if isinstance(v, list):
        return v[0] if v else default
    return v

def _qp_to_dict():
    out = {}
    for k, v in st.query_params.items():
        out[k] = v[0] if isinstance(v, list) and v else v
    return out

def load_profile_from_params():
    return {
        "pf_l":   _qp_get_one("pf_l",   DEFAULT_PROFILE["pf_l"]),
        "pf_h":   _qp_get_one("pf_h",   DEFAULT_PROFILE["pf_h"]),
        "pf_len": _qp_get_one("pf_len", DEFAULT_PROFILE["pf_len"]),
        "pf_g":   _qp_get_one("pf_g",   DEFAULT_PROFILE["pf_g"]),
        "pf_ge":  _qp_get_one("pf_ge",  DEFAULT_PROFILE["pf_ge"]),
    }

def save_profile_to_params(prof: dict, keep_prefs_open: bool):
    new_qp = _qp_to_dict()
    new_qp.update({
        "pf_l":   prof.get("pf_l",   DEFAULT_PROFILE["pf_l"]),
        "pf_h":   prof.get("pf_h",   DEFAULT_PROFILE["pf_h"]),
        "pf_len": prof.get("pf_len", DEFAULT_PROFILE["pf_len"]),
        "pf_g":   prof.get("pf_g",   DEFAULT_PROFILE["pf_g"]),
        "pf_ge":  prof.get("pf_ge",  DEFAULT_PROFILE["pf_ge"]),
        "prefs":  "1" if keep_prefs_open else "0",
    })
    st.query_params.clear()
    st.query_params.update(new_qp)

def build_url_with_params(updates: dict) -> str:
    d = _qp_to_dict()
    d.update(updates)
    return APP_URL + "?" + urlencode(d)

PROFILE = load_profile_from_params()

# ---------- Sidebar voorkeuren ----------
if "show_prefs" not in st.session_state:
    st.session_state.show_prefs = (_get("prefs","0") == "1")

opt_l   = ["Zandloper","Peer","Rechthoek","Appel","Weet ik niet"]
opt_h   = ["Licht","Medium","Donker"]
opt_len = ["< 1.60m","1.60 - 1.75m","> 1.75m"]
opt_g   = ["Werk","Feest","Vrije tijd","Bruiloft","Date"]
opt_ge  = ["Zelfverzekerd","Speels","Elegant","Casual","Trendy"]

def _safe_index(options, value):
    return options.index(value) if value in options else 0

if st.session_state.show_prefs:
    with st.sidebar:
        st.markdown("### 👤 Vertel iets over jezelf")
        lichaamsvorm = st.selectbox("Lichaamsvorm", opt_l,
            index=_safe_index(opt_l, PROFILE["pf_l"]), key="pf_l")
        huidskleur = st.selectbox("Huidskleur", opt_h,
            index=_safe_index(opt_h, PROFILE["pf_h"]), key="pf_h")
        lengte = st.selectbox("Lengte", opt_len,
            index=_safe_index(opt_len, PROFILE["pf_len"]), key="pf_len")
        gelegenheid = st.selectbox("Gelegenheid", opt_g,
            index=_safe_index(opt_g, PROFILE["pf_g"]), key="pf_g")
        gevoel = st.selectbox("Gevoel", opt_ge,
            index=_safe_index(opt_ge, PROFILE["pf_ge"]), key="pf_ge")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Bewaar als standaard", use_container_width=True):
                prof = {
                    "pf_l": st.session_state.pf_l,
                    "pf_h": st.session_state.pf_h,
                    "pf_len": st.session_state.pf_len,
                    "pf_g": st.session_state.pf_g,
                    "pf_ge": st.session_state.pf_ge,
                }
                save_profile_to_params(prof, keep_prefs_open=True)
                st.success("Profiel opgeslagen als standaard.")
        with c2:
            if st.button("Sluiten", use_container_width=True):
                st.session_state.show_prefs = False
                save_profile_to_params({
                    "pf_l": st.session_state.pf_l,
                    "pf_h": st.session_state.pf_h,
                    "pf_len": st.session_state.pf_len,
                    "pf_g": st.session_state.pf_g,
                    "pf_ge": st.session_state.pf_ge,
                }, keep_prefs_open=False)
                st.rerun()
else:
    # Gebruik profiel uit params als 'gesloten' is
    lichaamsvorm = PROFILE["pf_l"]; huidskleur = PROFILE["pf_h"]
    lengte = PROFILE["pf_len"]; gelegenheid = PROFILE["pf_g"]; gevoel = PROFILE["pf_ge"]
    # ook in session_state zetten (voor de LLM call)
    st.session_state.pf_l   = lichaamsvorm
    st.session_state.pf_h   = huidskleur
    st.session_state.pf_len = lengte
    st.session_state.pf_g   = gelegenheid
    st.session_state.pf_ge  = gevoel

# ---------- Icons ----------
DRESS_SVG = """<svg class="icon" viewBox="0 0 24 24" width="22" height="22" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8 3l1.5 3-2 3 2 11h5l2-11-2-3L16 3h-2l-1 2-1-2H8z" fill="#556BFF"/></svg>"""
LINK_SVG  = """<svg class="icon" viewBox="0 0 24 24" width="22" height="22" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M10 14l-1 1a4 4 0 105.7 5.7l2.6-2.6a4 4 0 00-5.7-5.7l-.6.6" stroke="#6F5BFF" stroke-width="2" stroke-linecap="round"/><path d="M14 10l1-1a4 4 0 10-5.7-5.7L6.7 5.9a4 4 0 105.7 5.7l.6-.6" stroke="#6F5BFF" stroke-width="2" stroke-linecap="round"/></svg>"""
CHAT_SVG = """<span class="icon"><svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M4 12c0-4.4 3.6-8 8-8s8 3.6 8 8-3.6 8-8 8H9l-4 3v-3.5C4.7 18.3 4 15.3 4 12z" fill="white" opacity="0.9"/></svg></span>"""

# ---------- Helpers ----------
def esc(x) -> str:
    return html_escape("" if x is None else str(x))

def as_list(v):
    if v is None: return []
    if isinstance(v, list): return v
    return [v]

def _html_noindent(s: str) -> str:
    return "\n".join(line.lstrip() for line in s.splitlines())

def _keywords_from_url(u: str):
    try:
        slug = urlparse(u).path.rstrip("/").split("/")[-1]
        slug = re.sub(r"\d+", " ", slug)
        words = [w for w in re.split(r"[-_]+", slug) if w and len(w) > 1]
        return " ".join(words[:8]) or "fashion"
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

# Combine bullets → zoekqueries (robuuster)
_STOPWORDS_RE = re.compile(
    r"\b(?:combineer met|draag|voor|met|op|onder|bij|een|de|het|je|jouw|casual|look|outfit|relaxte?|ontspannen|vibe)\b",
    re.IGNORECASE,
)
_SEP_RE = re.compile(r"\b(?:of|en|,|/|\+|&)\b", re.IGNORECASE)

def _normalize_query_piece(p: str) -> str:
    p = re.sub(r"[^0-9A-Za-zÀ-ÿ\- ]+", "", p)
    p = re.sub(r"\s+", " ", p).strip()
    return p

def _query_from_bullet(text: str):
    s = str(text or "")
    s = _STOPWORDS_RE.sub(" ", s)
    parts = _SEP_RE.split(s)
    out = []
    for p in parts:
        p = _normalize_query_piece(p)
        if len(p) >= 3 and p.lower() not in {"kleur", "kleuren", "top", "bovenstuk"}:
            out.append(p)
    return out[:2]

def _queries_from_combine(bullets, max_links=4):
    seen, out = set(), []
    for b in as_list(bullets):
        for q in _query_from_bullet(b):
            qn = q.lower()
            if qn not in seen:
                out.append(q); seen.add(qn)
            if len(out) >= max_links:
                return out
    return out

# ---------- JSON schema ----------
SCHEMA_HINT = {
  "headline": "max 8 woorden samenvatting",
  "personal_advice": {
    "for_you": ["exact 3 bullets met persoonlijk advies op basis van profiel"],
    "avoid":   ["exact 2 bullets met wat te vermijden voor dit profiel"],
    "colors":  ["exact 2 bullets met passende kleuren t.o.v. huidskleur"],
    "combine": ["exact 2 bullets met combinaties (generieke items), afgestemd op gelegenheid/vibe"]
  }
}

# ---------- OpenAI call ----------
def get_advice_json(link: str) -> dict:
    fig = st.session_state.get("pf_l", "Weet ik niet")
    skin = st.session_state.get("pf_h", "Medium")
    hgt  = st.session_state.get("pf_len", "1.60 - 1.75m")
    occ  = st.session_state.get("pf_g", "Vrije tijd")
    vibe = st.session_state.get("pf_ge", "Casual")

    profile = f"figuur={fig}, huidskleur={skin}, lengte={hgt}, gelegenheid={occ}, stijlgevoel={vibe}"
    product_name = _product_name(link)
    keywords     = _keywords_from_url(link)
    domain       = urlparse(link).netloc

    system_msg = (
        "Je bent een modieuze maar praktische personal stylist. Schrijf in helder Nederlands (B1), kort en concreet. "
        "Gebruik het profiel expliciet: noem lengte/pasvorm/kleuren/gelegenheid waar relevant. "
        "Wees eerlijk over onzekerheid: speculeer niet over details die je niet weet. "
        "Geen merknamen of emoji."
    )

    user_msg = f"""
Analyseer dit product uitsluitend op basis van de URL-naam/keywords.
URL: {link}
Domein: {domain}
Vermoedelijke productnaam: {product_name}
Keywords: {keywords}
Profiel: {profile}

Geef ALLEEN JSON met exact deze velden (geen extra velden):
{json.dumps(SCHEMA_HINT, ensure_ascii=False)}

Schrijfregels:
- Beperk je tot stijl-advies dat je ZEKER kunt geven zonder productdetails te raden.
- Geen maatadvies, stofclaims, lengteclaims of merkspecifieke aannames.
- Maak elk punt persoonlijk: koppel aan lengte/figuur/huidskleur/gelegenheid/gevoel.
- B1 Nederlands, kort en concreet (max 8–10 woorden per bullet), geen emoji of merknamen.
"""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            response_format={"type":"json_object"},
            messages=[{"role":"system","content":system_msg},{"role":"user","content":user_msg}],
            temperature=0.4, max_tokens=600,
        )
        data = json.loads(resp.choices[0].message.content)
        data.setdefault("headline", product_name or "Snel advies")

        pers = data.setdefault("personal_advice", {})
        pers.setdefault("for_you", [])
        pers.setdefault("avoid", [])
        pers.setdefault("colors", [])
        pers.setdefault("combine", [])

        return data
    except Exception:
        # Fallback — veilig en neutraal
        return {
            "headline": product_name or "Snel advies",
            "personal_advice": {
                "for_you": [
                    "Kies silhouet passend bij jouw lengte",
                    "Houd lijnen rustig voor casual look",
                    "Laat kleur aansluiten op jouw vibe"
                ],
                "avoid": [
                    "Vermijd te druk als je minimal wil",
                    "Vermijd harde contrasten bij zachte vibe"
                ],
                "colors": [
                    "Neutraal: ecru, zand, navy",
                    "Accent: olijf of bordeaux"
                ],
                "combine": [
                    "Rechte jeans of chino",
                    "Witte sneaker of loafer"
                ]
            }
        }

# ---------- Render kaart 1: advies ----------
def render_single_card(data: dict, link: str):
    product_name = _product_name(link)
    headline = esc(data.get("headline", product_name or "Kort advies"))

    pers = data.get("personal_advice", {})
    for_you = [esc(x) for x in as_list(pers.get("for_you"))][:3]
    avoid   = [esc(x) for x in as_list(pers.get("avoid"))][:2]
    colors  = [esc(x) for x in as_list(pers.get("colors"))][:2]
    combine = [esc(x) for x in as_list(pers.get("combine"))][:2]

    html = f"""
<div class="card">
  <div class="card-title">
    <svg class="icon" viewBox="0 0 24 24" width="22" height="22" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8 3l1.5 3-2 3 2 11h5l2-11-2-3L16 3h-2l-1 2-1-2H8z" fill="#556BFF"/></svg>
    {headline}
  </div>
  <div class="card-body">

    <div class="section-h">• Specifiek advies voor jou</div>
    <ul>
      {''.join([f"<li>{x}</li>" for x in for_you])}
    </ul>

    <div class="section-h">• Kleur & combineren</div>
    <ul>
      {''.join([f"<li>{x}</li>" for x in colors])}
      {''.join([f"<li>{x}</li>" for x in combine])}
    </ul>

    <div class="section-h">• Liever vermijden</div>
    <ul>
      {''.join([f"<li>{x}</li>" for x in avoid])}
    </ul>

  </div>
</div>
"""
    st.markdown(_html_noindent(html), unsafe_allow_html=True)

# ---------- Render kaart 2: bijpassende links + inline CTA ----------
def render_matching_links_card(data: dict, link: str):
    pers = data.get("personal_advice", {})
    combine_raw = as_list(pers.get("combine"))
    queries = _queries_from_combine(combine_raw, max_links=4)

    prefs_url = build_url_with_params({"prefs": "1"})

    if not queries:
        # Toon alleen inline CTA (zonder JS; gewoon een link met params)
        html_only_cta = f"""
<div class="cta-inline">
  <a class="cta-btn" href="{prefs_url}">
    {CHAT_SVG} <span>Vertel iets over jezelf</span>
  </a>
</div>
"""
        st.markdown(_html_noindent(html_only_cta), unsafe_allow_html=True)
        return

    LINK_SVG2 = "<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'><path d='M3.9 12a5 5 0 015-5h3v2h-3a3 3 0 100 6h3v2h-3a5 5 0 01-5-5zm7-3h3a5 5 0 110 10h-3v-2h3a3 3 0 100-6h-3V9z'/></svg>"

    buttons = []
    for q in queries:
        url = _build_link_or_fallback(link, q)
        label = f'Zoek: {html_escape(q)}'
        buttons.append(f'<a class="btn" href="{url}" target="_blank" rel="nofollow noopener">{LINK_SVG2} {label}</a>')

    html = f"""
<div class="card">
  <div class="card-title">
    <svg class="icon" viewBox="0 0 24 24" width="22" height="22" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8 3l1.5 3-2 3 2 11h5l2-11-2-3L16 3h-2l-1 2-1-2H8z" fill="#556BFF"/></svg>
    Bijpassende kleding (op deze shop)
  </div>
  <div class="card-body">
    <div class="btnrow" style="margin-top:4px;">
      {''.join(buttons)}
    </div>
    <div class="small-note" style="margin-top:12px;">
      We zoeken eerst binnen deze shop; lukt dat niet, dan via Google.
    </div>
  </div>
</div>

<!-- Inline CTA direct onder de kaart -->
<div class="cta-inline">
  <a class="cta-btn" href="{prefs_url}">
    {CHAT_SVG} <span>Vertel iets over jezelf</span>
  </a>
</div>
"""
    st.markdown(_html_noindent(html), unsafe_allow_html=True)

# ---------- UI ----------

# State voor handmatige link
if "last_link" not in st.session_state:
    st.session_state.last_link = ""

active_link = link_qs if (auto and link_qs) else st.session_state.last_link

if active_link:
    data = get_advice_json(active_link)
    render_single_card(data, active_link)          # Kaart 1: advies
    render_matching_links_card(data, active_link)  # Kaart 2: bijpassende links (+ inline CTA)

# Input-veld ONDERAAN in witte card
with st.form("manual_bottom", clear_on_submit=False):
    st.markdown(dedent(f"<div class='card-title'>{LINK_SVG} Plak hier de link van een ander product</div>"), unsafe_allow_html=True)
    link_in = st.text_input(label="", value="", placeholder="https://…")
    go = st.form_submit_button("Geef advies")

if go and link_in:
    st.session_state.last_link = link_in.strip()
    st.rerun()
