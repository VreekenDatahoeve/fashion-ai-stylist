# app.py — Fashion AI Stylist (mockup-accurate UI)
import os, re, json
import streamlit as st
from urllib.parse import urlparse, quote
from html import escape as html_escape
from textwrap import dedent
from openai import OpenAI

# ========= Instellingen =========
APP_URL = "https://fashion-ai-stylis-ifidobqmkgjtn7gjxgrudb.streamlit.app"  # <-- jouw publieke URL
MODEL   = "gpt-4o-mini"
# =================================

# --- API key ---
API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not API_KEY:
    st.error("Geen OpenAI API-sleutel gevonden. Zet OPENAI_API_KEY in Secrets.")
    st.stop()
client = OpenAI(api_key=API_KEY)

# ---------- Profiel (query params) ----------
DEFAULT_PROFILE = {"pf_l":"Weet ik niet","pf_h":"Medium","pf_len":"1.60 - 1.75m","pf_g":"Vrije tijd","pf_ge":"Casual"}

def get_params_profile():
    qp = st.query_params
    out = DEFAULT_PROFILE.copy()
    for k in DEFAULT_PROFILE.keys():
        v = qp.get(k, out[k])
        out[k] = (v[0] if isinstance(v, list) and v else v) or out[k]
    return out

def save_profile_to_params(p: dict, keep_prefs_open: bool = True):
    u = st.query_params
    for k, v in p.items():
        u[k] = v
    u["prefs"] = "1" if keep_prefs_open else "0"
    st.query_params = u

PROFILE = get_params_profile()

# ---------- Pagina ----------
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

[data-testid="stHeader"]{ display:none; }
footer { visibility:hidden; }

[data-testid="stAppViewContainer"]{
  background: radial-gradient(1200px 600px at 50% -120px, #C8B9FF 0%, #AA98FF 30%, #8F7DFF 60%, #7A66F7 100%);
}
.block-container{
  max-width: 860px;
  padding-top: 12px !important;
  padding-bottom: 90px !important;
}

/* ===== App title ===== */
.app-title{
  display:flex; align-items:center; gap:14px;
  color:#ffffff; margin: 10px 0 8px;
}
.app-title h1{
  font-size: 44px; font-weight: 800; letter-spacing:-.02em;
  margin: 0;
  text-shadow: 0 4px 24px rgba(0,0,0,.18);
}
.app-title .icon{
  width:40px; height:40px; filter: drop-shadow(0 6px 22px rgba(0,0,0,.25));
}

/* ===== Hero card ===== */
.hero{
  background:#ffffff; border:1px solid #EFEBFF; border-radius:22px;
  box-shadow: 0 16px 40px rgba(23,0,75,0.18); padding: 22px; margin-top: 8px;
}
.hero-title{
  font-size: 34px; font-weight: 800; color:#1f2358; margin: 0 0 14px;
  letter-spacing:-.02em;
}
.hero-row{ display:flex; gap:12px; align-items:center; }
.hero-input{
  flex:1;
  background:#fff; border:1px solid #E3E6FF; border-radius:14px;
  height:52px; padding: 0 14px; font-size:16px; outline:none;
}
.hero-input:focus{ border-color:#8C72FF; box-shadow: 0 0 0 3px rgba(140,114,255,.20); }
.hero-btn{
  border:none; border-radius:14px; padding:14px 20px; font-weight:800; cursor:pointer;
  background: linear-gradient(180deg, #8C72FF 0%, #6F5BFF 100%); color:#fff;
  box-shadow: 0 12px 28px rgba(23,0,75,0.35);
}

/* Bookmarklet chip */
.note-chip{
  display:inline-flex; align-items:center; gap:8px;
  margin-top:12px; padding:10px 14px; border-radius:12px;
  background: rgba(255,255,255,0.70);
  border:1px solid rgba(255,255,255,0.85);
  color:#2d2a6c; font-weight:700; text-decoration:none;
  box-shadow: 0 10px 24px rgba(40,12,120,0.15); backdrop-filter: blur(4px);
}

/* ===== Generic cards (advies / links) ===== */
.card{
  background:#ffffff; border-radius: 22px; padding: 22px;
  box-shadow: 0 16px 40px rgba(23,0,75,0.18);
  border: 1px solid #EFEBFF; margin-top: 16px;
}
.card-title{
  font-size: 26px; font-weight: 800; color:#1f2358; margin:0 0 12px;
  display:flex; gap:12px; align-items:center; letter-spacing:-.01em;
}
.card-sub{ color:#2b2b46; }
.section-h{ font-weight:800; margin:14px 0 6px; color:#1f2358; }
ul{ margin: 0 0 0 1.15rem; padding:0; line-height:1.6; }
li{ margin: 6px 0; }

.btnrow{ display:flex; flex-wrap:wrap; gap:10px; margin-top:8px; }
.btn{
  display:inline-flex; align-items:center; gap:8px; padding:10px 14px; border-radius:12px;
  background:#F3F4FF; color:#2d2a6c; border:1px solid #E3E6FF; text-decoration:none; font-weight:700;
}

/* Inline CTA */
.cta-inline{ display:flex; justify-content:center; margin-top: 16px; }
.cta-btn{
  background: linear-gradient(180deg, #8C72FF 0%, #6F5BFF 100%);
  color:#ffffff; border:none; border-radius:999px; padding: 14px 22px; font-weight:800;
  box-shadow: 0 16px 36px rgba(23,0,75,0.40);
  display:inline-flex; align-items:center; gap:12px; cursor:pointer; line-height:1;
}
.cta-btn .icon svg{ width:22px; height:22px; fill:#fff; }
.small-note{ color:#6B7280; font-size: 13px; }

.title-icon{ width:22px; height:22px; }
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
    st.session_state.show_prefs = (prefs_q or _get("prefs","0") == "1")

if st.session_state.show_prefs:
    with st.sidebar:
        st.markdown("### 👤 Vertel iets over jezelf")
        st.selectbox("Lichaamsvorm", ["Zandloper","Peer","Rechthoek","Appel","Weet ik niet"],
                     index=["Zandloper","Peer","Rechthoek","Appel","Weet ik niet"].index(PROFILE["pf_l"]), key="pf_l")
        st.selectbox("Huidskleur", ["Licht","Medium","Donker"],
                     index=["Licht","Medium","Donker"].index(PROFILE["pf_h"]), key="pf_h")
        st.selectbox("Lengte", ["< 1.60m","1.60 - 1.75m","> 1.75m"],
                     index=["< 1.60m","1.60 - 1.75m","> 1.75m"].index(PROFILE["pf_len"]), key="pf_len")
        st.selectbox("Gelegenheid", ["Werk","Feest","Vrije tijd","Bruiloft","Date"],
                     index=["Werk","Feest","Vrije tijd","Bruiloft","Date"].index(PROFILE["pf_g"]), key="pf_g")
        st.selectbox("Gevoel", ["Zelfverzekerd","Speels","Elegant","Casual","Trendy"],
                     index=["Zelfverzekerd","Speels","Elegant","Casual","Trendy"].index(PROFILE["pf_ge"]), key="pf_ge")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Bewaar als standaard", use_container_width=True):
                prof = {k: st.session_state[k] for k in ["pf_l","pf_h","pf_len","pf_g","pf_ge"]}
                save_profile_to_params(prof, keep_prefs_open=True)
                st.success("Profiel opgeslagen als standaard.")
        with c2:
            if st.button("Sluiten", use_container_width=True):
                st.session_state.show_prefs = False
                prof = {k: st.session_state[k] for k in ["pf_l","pf_h","pf_len","pf_g","pf_ge"]}
                save_profile_to_params(prof, keep_prefs_open=False)
                st.rerun()
else:
    # Gebruik profiel uit params
    for k,v in PROFILE.items():
        st.session_state[k] = v

# ---------- Icons ----------
DRESS_SVG = """<svg class="title-icon" viewBox="0 0 24 24" fill="#556BFF"><path d="M8 3l1.5 3-2 3 2 11h5l2-11-2-3L16 3h-2l-1 2-1-2H8z"/></svg>"""
CHAT_SVG = """<span class="icon"><svg viewBox="0 0 24 24"><path d="M4 12c0-4.4 3.6-8 8-8s8 3.6 8 8-3.6 8-8 8H9l-4 3v-3.5C4.7 18.3 4 15.3 4 12z" fill="white" opacity="0.9"/></svg></span>"""

# ---------- Helpers ----------
def esc(x) -> str: return html_escape("" if x is None else str(x))
def as_list(v): return v if isinstance(v, list) else ([] if v is None else [v])
def _html_noindent(s: str) -> str: return "\n".join(line.lstrip() for line in s.splitlines())

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

# ---------- LLM schema ----------
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
        pers.setdefault("for_you", []); pers.setdefault("avoid", [])
        pers.setdefault("colors", []);  pers.setdefault("combine", [])
        return data
    except Exception:
        return {
            "headline": product_name or "Snel advies",
            "personal_advice": {
                "for_you": ["Kies silhouet passend bij jouw lengte","Houd lijnen rustig voor casual look","Laat kleur aansluiten op jouw vibe"],
                "avoid": ["Vermijd te druk als je minimal wil","Vermijd harde contrasten bij zachte vibe"],
                "colors": ["Neutraal: ecru, zand, navy","Accent: olijf of bordeaux"],
                "combine": ["Rechte jeans of chino","Witte sneaker of loafer"]
            }
        }

# ---------- UI: header + hero ----------
def render_header():
    dress_svg = """<svg class="icon" viewBox="0 0 24 24" fill="#fff" xmlns="http://www.w3.org/2000/svg"><path d="M8 3l1.5 3-2 3 2 11h5l2-11-2-3L16 3h-2l-1 2-1-2H8z"/></svg>"""
    st.markdown(f'''
    <div class="app-title">
        {dress_svg}
        <h1>Fashion AI Stylist</h1>
    </div>
    ''', unsafe_allow_html=True)

def render_hero(link_prefill: str = ""):
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Plak een productlink en krijg direct stijl-advies</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="hero-row">
        <input id="hero-url" class="hero-input" type="text" placeholder="https://…" value="{html_escape(link_prefill)}" />
        <button class="hero-btn" onclick="
            const v = document.getElementById('hero-url').value.trim();
            if(v && /^https?:\\/\\//i.test(v)){{
                const u = new URL(window.location.href);
                u.searchParams.set('auto','1');
                u.searchParams.set('u', v);
                window.location = u.toString();
            }} else {{
                alert('Plak eerst een geldige URL (https://...)');
            }}
        ">Advies ophalen</button>
    </div>
    <a class="note-chip" href="javascript:(function(){{window.open('{APP_URL}?auto=1&u='+encodeURIComponent(location.href),'_blank');}})();" title="Sleep naar je favorietenbalk en klik tijdens het shoppen.">
        ➕ Gebruik onze bookmarklet
    </a>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

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
  <div class="card-title">{DRESS_SVG} {headline}</div>
  <div class="card-sub">
    <div class="section-h">• Specifiek advies voor jou</div>
    <ul>{''.join([f"<li>{x}</li>" for x in for_you])}</ul>

    <div class="section-h">• Kleur & combineren</div>
    <ul>{''.join([f"<li>{x}</li>" for x in colors])}{''.join([f"<li>{x}</li>" for x in combine])}</ul>

    <div class="section-h">• Liever vermijden</div>
    <ul>{''.join([f"<li>{x}</li>" for x in avoid])}</ul>
  </div>
</div>
"""
    st.markdown(_html_noindent(html), unsafe_allow_html=True)

# ---------- Render kaart 2: bijpassende links + inline CTA ----------
def render_matching_links_card(data: dict, link: str):
    pers = data.get("personal_advice", {})
    combine_raw = as_list(pers.get("combine"))
    queries = _queries_from_combine(combine_raw, max_links=4)

    if not queries:
        st.markdown(_html_noindent(f"""
<div class="cta-inline">
  <button class="cta-btn" onclick="
    const u = new URL(window.location);
    u.searchParams.set('prefs','1'); window.location.replace(u.toString());
  ">{CHAT_SVG} <span>Vertel iets over jezelf</span></button>
</div>"""), unsafe_allow_html=True)
        return

    LINK_SVG2 = "<svg viewBox='0 0 24 24'><path d='M3.9 12a5 5 0 015-5h3v2h-3a3 3 0 100 6h3v2h-3a5 5 0 01-5-5zm7-3h3a5 5 0 110 10h-3v-2h3a3 3 0 100-6h-3V9z'/></svg>"

    buttons = []
    for q in queries:
        url = _build_link_or_fallback(link, q)
        label = f'Zoek: {html_escape(q)}'
        buttons.append(f'<a class="btn" href="{url}" target="_blank" rel="nofollow noopener">{LINK_SVG2} {label}</a>')

    html = f"""
<div class="card">
  <div class="card-title">{DRESS_SVG} Bijpassende kleding (op deze shop)</div>
  <div class="card-sub">
    <div class="btnrow">{''.join(buttons)}</div>
    <div class="small-note" style="margin-top:10px;">
      We zoeken eerst binnen deze shop; lukt dat niet, dan via Google.
    </div>
  </div>
</div>

<div class="cta-inline">
  <button class="cta-btn" onclick="
    const u = new URL(window.location);
    u.searchParams.set('prefs','1'); window.location.replace(u.toString());
  ">{CHAT_SVG} <span>Vertel iets over jezelf</span></button>
</div>
"""
    st.markdown(_html_noindent(html), unsafe_allow_html=True)

# ======================= UI FLOW =======================

render_header()

# State
if "last_link" not in st.session_state:
    st.session_state.last_link = ""

# Hero (bovenaan)
prefill = link_qs if (auto and link_qs) else st.session_state.last_link
render_hero(link_prefill=prefill)

# Actieve link bepalen (na hero-redirect komt hij via query param binnen)
active_link = link_qs if (auto and link_qs) else st.session_state.last_link

# Als user al eerder iets heeft ingevoerd via oude flow, behoud
if not active_link and st.session_state.last_link:
    active_link = st.session_state.last_link

# Render advies
if active_link:
    st.session_state.last_link = active_link
    data = get_advice_json(active_link)
    render_single_card(data, active_link)
    render_matching_links_card(data, active_link)
