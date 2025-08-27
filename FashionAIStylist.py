# app.py — Fashion AI Stylist (hero component + matching chips + regex fix + caching)
import os, re, json
import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import urlparse, quote
from html import escape as html_escape
from textwrap import dedent
from openai import OpenAI

# ========= Instellingen =========
APP_URL = "https://fashion-ai-stylis-ifidobqmkgjtn7gjxgrudb.streamlit.app"  # <-- vervang met jouw URL
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
st.set_page_config(page_title="Fashion AI Stylist", page_icon="👗", layout="centered", initial_sidebar_state="collapsed")

# ---------- CSS ----------
st.markdown(dedent("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"]{ height:100%; }
html, body, [class*="stApp"]{ font-family:"Inter", system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
[data-testid="stHeader"]{ display:none; } footer { visibility:hidden; }

[data-testid="stAppViewContainer"]{
  background: radial-gradient(1200px 600px at 50% -120px, #C8B9FF 0%, #AA98FF 30%, #8F7DFF 60%, #7A66F7 100%);
}
.block-container{ max-width: 860px; padding-top: 12px !important; padding-bottom: 90px !important; }

/* ===== Cards ===== */
.card{ background:#fff; border-radius:22px; padding:22px; box-shadow:0 16px 40px rgba(23,0,75,0.18); border:1px solid #EFEBFF; margin-top:16px; }
.card-title{ font-size:26px; font-weight:800; color:#1f2358; margin:0 0 12px; display:flex; gap:12px; align-items:center; letter-spacing:-.01em; }
.card-sub{ color:#2b2b46; }
.section-h{ font-weight:800; margin:14px 0 6px; color:#1f2358; }
ul{ margin:0 0 0 1.15rem; padding:0; line-height:1.6; } li{ margin:6px 0; }

/* Chips */
.matching .btnrow{ display:flex; flex-wrap:wrap; gap:10px; margin-top:8px; }
.matching .chip{ display:inline-flex; align-items:center; gap:8px; padding:10px 14px; border-radius:12px;
  background:#F3F4FF; border:1px solid #E3E6FF; text-decoration:none; font-weight:700; color:#1f2a5a;
  box-shadow:0 4px 14px rgba(23,0,75,0.12); transition:transform .04s ease; }
.matching .chip:hover{ transform: translateY(-1px); }
.matching .chip svg{ width:18px; height:18px; }
.matching .note{ color:#6B7280; font-size:13px; margin-top:10px; }

/* CTA */
.cta-inline{ display:flex; justify-content:center; margin-top:16px; }
.cta-btn{ background:linear-gradient(180deg,#8C72FF 0%,#6F5BFF 100%); color:#fff; border:none; border-radius:999px;
  padding:14px 22px; font-weight:800; box-shadow:0 16px 36px rgba(23,0,75,0.40); display:inline-flex; align-items:center; gap:12px; cursor:pointer; line-height:1; }
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
        st.selectbox("Lichaamsvorm", ["Zandloper","Peer","Rechthoek","Appel","Weet ik niet"], index=["Zandloper","Peer","Rechthoek","Appel","Weet ik niet"].index(PROFILE["pf_l"]), key="pf_l")
        st.selectbox("Huidskleur", ["Licht","Medium","Donker"], index=["Licht","Medium","Donker"].index(PROFILE["pf_h"]), key="pf_h")
        st.selectbox("Lengte", ["< 1.60m","1.60 - 1.75m","> 1.75m"], index=["< 1.60m","1.60 - 1.75m","> 1.75m"].index(PROFILE["pf_len"]), key="pf_len")
        st.selectbox("Gelegenheid", ["Werk","Feest","Vrije tijd","Bruiloft","Date"], index=["Werk","Feest","Vrije tijd","Bruiloft","Date"].index(PROFILE["pf_g"]), key="pf_g")
        st.selectbox("Gevoel", ["Zelfverzekerd","Speels","Elegant","Casual","Trendy"], index=["Zelfverzekerd","Speels","Elegant","Casual","Trendy"].index(PROFILE["pf_ge"]), key="pf_ge")

# ---------- Icons ----------
DRESS_SVG = """<svg viewBox="0 0 24 24" fill="#556BFF" width="22" height="22"><path d="M8 3l1.5 3-2 3 2 11h5l2-11-2-3L16 3h-2l-1 2-1-2H8z"/></svg>"""
CHAT_SVG = """<span class="icon"><svg viewBox="0 0 24 24"><path d="M4 12c0-4.4 3.6-8 8-8s8 3.6 8 8-3.6 8-8 8H9l-4 3v-3.5C4.7 18.3 4 15.3 4 12z" fill="white" opacity="0.9"/></svg></span>"""

# ---------- Helpers ----------
def esc(x) -> str: return html_escape("" if x is None else str(x))
def as_list(v): return v if isinstance(v, list) else ([] if v is None else [v])

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
    patterns = [f"/search?q={q}", f"/zoeken?query={q}", f"/s?searchTerm={q}", f"/search?text={q}", f"/catalogsearch/result/?q={q}"]
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

# ✅ regex-fix: normaliseer stukjes zoekterm
def _normalize_query_piece(p: str) -> str:
    if not isinstance(p, str): p = str(p or "")
    p = re.sub(r"[^\w\s-]+", "", p, flags=re.UNICODE)  # alleen letters/cijfers/underscore/spaties/-
    p = re.sub(r"\s+", " ", p).strip()
    return p

_SEP_RE = re.compile(r"\b(?:of|en|,|/|\+|&)\b", re.IGNORECASE)

def _query_from_bullet(text: str):
    s = str(text or "")
    parts = _SEP_RE.split(s)
    out = []
    for p in parts:
        p = _normalize_query_piece(p)
        if len(p) >= 3:
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

# ---------- LLM call + caching ----------
def _profile_cache_key() -> str:
    return "|".join([
        st.session_state.get("pf_l", DEFAULT_PROFILE["pf_l"]),
        st.session_state.get("pf_h", DEFAULT_PROFILE["pf_h"]),
        st.session_state.get("pf_len", DEFAULT_PROFILE["pf_len"]),
        st.session_state.get("pf_g", DEFAULT_PROFILE["pf_g"]),
        st.session_state.get("pf_ge", DEFAULT_PROFILE["pf_ge"]),
    ])

@st.cache_data(ttl=3600, show_spinner=False)
def cached_advice(link: str, profile_key: str) -> dict:
    """Cache AI-advies per (link + profiel) 1 uur."""
    product_name = _product_name(link)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            response_format={"type":"json_object"},
            messages=[
                {"role":"system","content":"Je bent een stylist. Schrijf kort en concreet in B1-Nederlands."},
                {"role":"user","content":f"URL: {link}\nProfiel-key: {profile_key}\nGeef JSON met velden: headline, personal_advice{{for_you(3),avoid(2),colors(2),combine(2)}}"}
            ],
            temperature=0.4, max_tokens=600,
        )
        data = json.loads(resp.choices[0].message.content)
        data.setdefault("headline", product_name or "Snel advies")
        return data
    except Exception:
        return {
            "headline": product_name or "Snel advies",
            "personal_advice": {
                "for_you": ["Kies casual", "Houd lijnen rustig", "Kies zachte tinten"],
                "avoid": ["Vermijd te druk", "Vermijd contrasten"],
                "colors": ["Neutraal: ecru", "Accent: olijf"],
                "combine": ["Jeans", "Sneakers"],
            },
        }

# ---------- HEADER ----------
def render_header():
    components.html("""
    <div style="display:flex;align-items:center;gap:14px;margin:10px 0 8px;color:#fff;">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="#fff" xmlns="http://www.w3.org/2000/svg"><path d="M8 3l1.5 3-2 3 2 11h5l2-11-2-3L16 3h-2l-1 2-1-2H8z"/></svg>
      <h1 style="font:800 44px/1 'Inter',system-ui;letter-spacing:-.02em;margin:0;">Fashion AI Stylist</h1>
    </div>
    """, height=70)

# ---------- HERO ----------
def render_hero(link_prefill: str = ""):
    components.html(f"""
<!doctype html><html><head><meta charset="utf-8"/>
<style>
  body{{margin:0;font-family:Inter,system-ui}}
  .hero{{background:#fff;border:1px solid #EFEBFF;border-radius:22px;box-shadow:0 16px 40px rgba(23,0,75,.18);padding:22px;margin-top:8px;}}
  .hero-title{{font:800 34px/1.2 Inter,system-ui;color:#1f2358;letter-spacing:-.02em;margin:0 0 14px}}
  .row{{display:flex;gap:12px;align-items:center}}
  .inp{{flex:1;background:#fff;border:1px solid #E3E6FF;border-radius:14px;height:52px;padding:0 14px;font:500 16px Inter,system-ui;outline:none}}
  .btn{{border:0;border-radius:14px;padding:14px 20px;font:800 16px Inter,system-ui;cursor:pointer;color:#fff;background:linear-gradient(180deg,#8C72FF 0%,#6F5BFF 100%);box-shadow:0 12px 28px rgba(23,0,75,.35)}}
</style>
<div class="hero">
  <div class="hero-title">Plak een productlink en krijg direct stijl-advies</div>
  <div class="row">
    <input id="hero-url" class="inp" type="text" placeholder="https://…" value="{html_escape(link_prefill)}"/>
    <button class="btn" onclick="
      const v=document.getElementById('hero-url').value.trim();
      if(v && /^https?:\\/\\//i.test(v)){{
        const u=new URL(window.parent.location.href);
        u.searchParams.set('auto','1'); u.searchParams.set('u',v);
        window.parent.location=u.toString();
      }} else {{ alert('Plak eerst een geldige URL'); }}
    ">Advies ophalen</button>
  </div>
</div>
</html>
""", height=140, scrolling=False)

# ---------- RENDER ADVIES ----------
def render_single_card(data: dict, link: str):
    headline = esc(data.get("headline","Advies"))
    pers = data.get("personal_advice", {})
    for_you = as_list(pers.get("for_you"))[:3]
    avoid   = as_list(pers.get("avoid"))[:2]
    colors  = as_list(pers.get("colors"))[:2]
    combine = as_list(pers.get("combine"))[:2]
    st.markdown(f"""
<div class="card">
  <div class="card-title">{DRESS_SVG} {headline}</div>
  <div class="card-sub">
    <div class="section-h">• Specifiek advies voor jou</div>
    <ul>{''.join([f"<li>{esc(x)}</li>" for x in for_you])}</ul>
    <div class="section-h">• Kleur & combineren</div>
    <ul>{''.join([f"<li>{esc(x)}</li>" for x in colors+combine])}</ul>
    <div class="section-h">• Liever vermijden</div>
    <ul>{''.join([f"<li>{esc(x)}</li>" for x in avoid])}</ul>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------- RENDER MATCHING LINKS ----------
def render_matching_links_card(data: dict, link: str):
    pers = data.get("personal_advice", {})
    queries = _queries_from_combine(as_list(pers.get("combine")), max_links=4)

    LINK_SVG = """<svg viewBox="0 0 24 24"><path d="M10 14l-1 1a4 4 0 105.7 5.7l2.6-2.6a4 4 0 00-5.7-5.7l-.6.6" stroke="#6F5BFF" stroke-width="2" stroke-linecap="round" fill="none"/><path d="M14 10l1-1a4 4 0 10-5.7-5.7L6.7 5.9a4 4 0 105.7 5.7l.6-.6" stroke="#6F5BFF" stroke-width="2" stroke-linecap="round" fill="none"/></svg>"""

    if not queries:  # geen suggesties → niets tonen (of je kunt hier CTA plaatsen)
        return

    chips_html = []
    for q in queries:
        url = _build_link_or_fallback(link, q)
        chips_html.append(f'<a class="chip" href="{url}" target="_blank" rel="nofollow noopener">{LINK_SVG} Zoek: {esc(q)}</a>')

    st.markdown(f"""
<div class="card matching">
  <div class="card-title">{DRESS_SVG} Bijpassende kleding (op deze shop)</div>
  <div class="card-sub">
    <div class="btnrow">{''.join(chips_html)}</div>
    <div class="note">We zoeken eerst binnen deze shop; lukt dat niet, dan via Google.</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ======================= MAIN FLOW =======================

# 1) Header
render_header()

# 2) State init
if "last_link" not in st.session_state:
    st.session_state.last_link = ""

# 3) Hero (prefill = laatst gebruikte of uit query)
prefill = link_qs if (auto and link_qs) else st.session_state.last_link
render_hero(link_prefill=prefill)

# 4) Actieve link bepalen (na klik in hero komt hij via ?auto=1&u=...)
active_link = link_qs if (auto and link_qs) else st.session_state.last_link

# 5) Render advies + matching chips (met caching om traagheid te voorkomen)
if active_link:
    st.session_state.last_link = active_link
    profile_key = _profile_cache_key()
    data = cached_advice(active_link, profile_key)
    render_single_card(data, active_link)
    render_matching_links_card(data, active_link)
