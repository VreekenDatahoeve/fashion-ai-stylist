# app.py — Fashion AI Stylist (panel mode + profile expander + schema-fix + matching chips)
import os, re, json, hashlib
import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import urlparse, quote
from html import escape as html_escape
from textwrap import dedent
from openai import OpenAI

# ========= Instellingen =========
APP_URL = "https://fashion-ai-stylis-ifidobqmkgjtn7gjxgrudb.streamlit.app"  # optioneel
MODEL   = "gpt-4o-mini"
# =================================

# --- API key ---
API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not API_KEY:
    st.error("Geen OpenAI API-sleutel gevonden. Zet OPENAI_API_KEY in Secrets.")
    st.stop()
client = OpenAI(api_key=API_KEY)

# ---------- Query params ----------
qp = st.query_params
def _get(name, default=""):
    v = qp.get(name, default)
    return (v[0] if isinstance(v, list) and v else v) or default

link_qs = _get("u").strip()
auto    = str(_get("auto","0")) == "1"
panel   = str(_get("panel","0")) == "1"

# ---------- Pagina ----------
st.set_page_config(page_title="Fashion AI Stylist", page_icon="👗", layout="centered", initial_sidebar_state="collapsed")

# ---------- CSS ----------
st.markdown(dedent("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"]{
  height:100%;
  font-family:"Inter", system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
}
[data-testid="stHeader"]{ display:none; }
footer { visibility:hidden; }

[data-testid="stAppViewContainer"]{
  background: radial-gradient(1200px 600px at 50% -120px, #C8B9FF 0%, #AA98FF 30%, #8F7DFF 60%, #7A66F7 100%);
}
.block-container{
  max-width: 860px;
  padding-top: 12px !important;
  padding-bottom: 80px !important;
}

/* ===== Cards ===== */
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

/* Chips */
.matching .btnrow{ display:flex; flex-wrap:wrap; gap:10px; margin-top:8px; }
.matching .chip{
  display:inline-flex; align-items:center; gap:8px;
  padding:8px 12px; border-radius:10px;
  background:#F3F4FF; border:1px solid #E3E6FF; text-decoration:none;
  font-weight:700; color:#1f2a5a; font-size:14px; line-height:1.25;
}
.matching .chip svg{ width:16px; height:16px; }
.matching .note{ color:#6B7280; font-size:13px; margin-top:10px; }

/* Profile tag chips */
.tagsrow{ display:flex; flex-wrap:wrap; gap:8px; margin: 6px 0 2px; }
.tag{
  background:#F7F7FF; border:1px solid #E8E9FF; color:#1f2a5a;
  padding:6px 10px; border-radius:10px; font-weight:700; font-size:13px;
}

/* ===== Compacte header voor panel modus ===== */
body[data-panel="1"] .compact-header{
  background:#ffffffcc; border:1px solid #EFEBFF; border-radius:12px;
  display:flex; align-items:center; gap:10px;
  padding:10px 12px; margin:6px 0 6px;
  box-shadow:0 10px 26px rgba(23,0,75,.18); backdrop-filter: blur(4px);
}
body[data-panel="1"] .compact-header .title{
  font-weight:800; font-size:18px; color:#1f2358; letter-spacing:-.01em; margin:0;
}
body[data-panel="1"] .compact-header .icon{
  width:22px; height:22px; display:inline-block;
}

/* ===== Popup/Panel-modus typografie ===== */
body[data-panel="1"] .block-container{ max-width: 560px; padding-top: 6px !important; padding-bottom: 24px !important; }
body[data-panel="1"] .card{ padding: 14px !important; border-radius: 16px !important; }
body[data-panel="1"] .card-title{ font-size: 20px !important; margin-bottom: 6px !important; }
body[data-panel="1"] .section-h{ font-size: 15px !important; margin:10px 0 4px !important; }
body[data-panel="1"] ul li{ font-size: 14px !important; line-height: 1.35 !important; margin: 3px 0 !important; }

/* ===== Expander (persoonlijke voorkeuren) in kaartstijl ===== */
[data-testid="stExpander"]{
  border: 1px solid #EFEBFF; border-radius: 22px; background:#fff;
  box-shadow: 0 16px 40px rgba(23,0,75,0.18); margin-top: 10px;
}
[data-testid="stExpander"] [data-testid="stExpanderToggleIcon"] svg{ color:#6F5BFF; }
[data-testid="stExpander"] .streamlit-expanderHeader p{
  font-size: 20px; font-weight: 800; color:#1f2358; margin: 6px 0;
}
</style>
"""), unsafe_allow_html=True)

# body attribuut zodat CSS panel-modus kan herkennen
if panel:
    st.markdown("<script>document.body.setAttribute('data-panel','1');</script>", unsafe_allow_html=True)

# ---------- Icons ----------
DRESS_SVG = """<svg viewBox="0 0 24 24" fill="#556BFF" width="22" height="22" xmlns="http://www.w3.org/2000/svg"><path d="M8 3l1.5 3-2 3 2 11h5l2-11-2-3L16 3h-2l-1 2-1-2H8z"/></svg>"""

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
    patterns = [f"/search?q={q}", f"/zoeken?query={q}", f"/s?searchTerm={q}",
                f"/search?text={q}", f"/catalogsearch/result/?q={q}"]
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

# veilige normalisatie
def _normalize_query_piece(p: str) -> str:
    if not isinstance(p, str):
        p = str(p or "")
    p = re.sub(r"[^\w\s-]+", "", p, flags=re.UNICODE)
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

# ---------- Profiel helpers ----------
DEFAULT_PROFILE = {
    "doelgroep": "",
    "maat_boven": "",
    "maat_beneden": "",
    "lengte_cm": "",
    "bouw": "",
    "fit": "",
    "huidtint": "",
    "kleuren": "",
    "stijl": "",
    "gelegenheid": "",
    "comfort": "",
    "notities": ""
}

def _profile_summary(profile: dict) -> str:
    p = {**DEFAULT_PROFILE, **(profile or {})}
    fields = []
    def add(lbl, key):
        v = (p.get(key) or "").strip()
        if v: fields.append(f"{lbl}: {v}")
    add("Doelgroep", "doelgroep")
    add("Maat boven", "maat_boven")
    add("Maat beneden", "maat_beneden")
    add("Lengte (cm)", "lengte_cm")
    add("Bouw", "bouw")
    add("Voorkeursfit", "fit")
    add("Huidtint", "huidtint")
    add("Kleuren", "kleuren")
    add("Stijl", "stijl")
    add("Gelegenheid", "gelegenheid")
    add("Comfort", "comfort")
    add("Notities", "notities")
    return "; ".join(fields)

def _profile_tags(profile: dict):
    p = {**DEFAULT_PROFILE, **(profile or {})}
    tags = []
    for key in ["doelgroep","fit","bouw","stijl","gelegenheid","huidtint"]:
        v = (p.get(key) or "").strip()
        if v: tags.append(v)
    if (p.get("maat_boven") or "").strip():
        tags.append(f"Boven: {p['maat_boven'].strip()}")
    if (p.get("maat_beneden") or "").strip():
        tags.append(f"Beneden: {p['maat_beneden'].strip()}")
    if (p.get("kleuren") or "").strip():
        k = p["kleuren"].split(",")[0].strip()
        if k: tags.append(f"Kleur: {k}")
    return tags

def _profile_hash(profile: dict) -> str:
    txt = _profile_summary(profile)
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()[:16]

# ---------- Schema & failsafe ----------
SCHEMA_HINT = {
  "headline": "max 8 woorden samenvatting",
  "personal_advice": {
    "for_you": ["exact 3 bullets met persoonlijk advies"],
    "avoid":   ["exact 2 bullets met wat te vermijden"],
    "colors":  ["exact 2 bullets met passende kleuren"],
    "combine": ["exact 2 bullets met combinaties (generieke items)"]
  }
}

def _ensure_schema(data: dict, product_name: str, keywords: str) -> dict:
    data = data or {}
    data.setdefault("headline", product_name or "Snel advies")
    pers = data.setdefault("personal_advice", {})

    def _coerce_list(value, want_n: int, fallback: list) -> list:
        if isinstance(value, list):
            lst = [str(x).strip() for x in value if str(x).strip()]
        elif isinstance(value, str) and value.strip():
            lst = [value.strip()]
        else:
            lst = []
        if len(lst) < want_n:
            lst += fallback[: (want_n - len(lst))]
        return lst[:want_n]

    kw = (keywords or "").split()[:2] or ["casual", "basic"]
    defaults = {
        "for_you": [
            f"Kies {kw[0]} pasvorm voor comfort",
            "Houd lijnen rustig en tijdloos",
            "Stem kleur af op je huidtint",
        ],
        "avoid": [
            "Vermijd te strakke of formele items",
            "Vermijd felle, schreeuwerige prints",
        ],
        "colors": [
            "Neutraal: ecru, navy",
            "Accent: olijf of bordeaux",
        ],
        "combine": [
            "Jeans of chino",
            "Basic t-shirt of hoodie",
        ],
    }

    pers["for_you"] = _coerce_list(pers.get("for_you"), 3, defaults["for_you"])
    pers["avoid"]   = _coerce_list(pers.get("avoid"),   2, defaults["avoid"])
    pers["colors"]  = _coerce_list(pers.get("colors"),  2, defaults["colors"])
    pers["combine"] = _coerce_list(pers.get("combine"), 2, defaults["combine"])
    return data

# ---------- LLM call (cached + strict schema + profile) ----------
@st.cache_data(ttl=3600, show_spinner=False)
def get_advice_json(link: str, profile: dict) -> dict:
    product_name = _product_name(link)
    keywords     = _keywords_from_url(link)
    prof_summary = _profile_summary(profile)
    prof_hash    = _profile_hash(profile)

    system_msg = (
        "Je bent een modieuze maar praktische personal stylist. "
        "Schrijf in helder Nederlands (B1), kort en concreet. "
        "Wees eerlijk over onzekerheid en speculeer niet. "
        "Respecteer het schema en beperk je tot zekere, generieke adviezen."
    )

    profile_note = (
        f"\nPersoonlijke voorkeuren (kort): {prof_summary}\n" if prof_summary else "\n"
    )

    user_msg = f"""
Analyseer dit product uitsluitend op basis van de URL-naam/keywords.
URL: {link}
Vermoedelijke productnaam: {product_name}
Keywords: {keywords}
{profile_note}
OPDRACHT:
- Houd expliciet rekening met relevante persoonlijke voorkeuren (fit/bouw/kleuren/gelegenheid), voor zover van toepassing.
- Geef ALLEEN JSON met exact deze velden (geen extra velden):
{json.dumps(SCHEMA_HINT, ensure_ascii=False)}

Schrijfregels:
- Alleen stijl-advies dat je ZEKER kunt geven zonder productdetails te raden.
- Max 8–10 woorden per bullet, geen emoji of merknamen.
- Maak elk punt praktisch (comfort, pasvorm, kleur, combineren).
- Als kleuren/fit in profiel staan: laat die voorkeur terugkomen.
"""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            response_format={"type":"json_object"},
            messages=[{"role":"system","content":system_msg},
                      {"role":"user","content":user_msg}],
            temperature=0.3, max_tokens=450,
        )
        raw = json.loads(resp.choices[0].message.content)
        data = _ensure_schema(raw, product_name, keywords)
        data["_cache_key"] = prof_hash
        return data
    except Exception:
        data = _ensure_schema({}, product_name, keywords)
        data["_cache_key"] = prof_hash
        return data

# ---------- UI: Persoonlijke voorkeuren ----------
def render_profile_expander():
    st.markdown("")  # kleine spacer
    with st.expander("Vertel iets over jezelf (persoonlijke voorkeuren)"):
        if "profile" not in st.session_state:
            st.session_state.profile = DEFAULT_PROFILE.copy()
        p = st.session_state.profile

        with st.form("profile_form", clear_on_submit=False):
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                p["doelgroep"] = st.selectbox("Doelgroep", ["","Man","Vrouw","Unisex"],
                                              index=["","Man","Vrouw","Unisex"].index(p.get("doelgroep","") or ""))
                p["fit"]       = st.selectbox("Voorkeursfit", ["","Slim","Regular","Relaxed"],
                                              index=["","Slim","Regular","Relaxed"].index(p.get("fit","") or ""))
                p["bouw"]      = st.selectbox("Lichaamsbouw",
                                              ["","Slank","Gemiddeld","Atletisch","Bredere schouders","Bredere heupen"],
                                              index=["","Slank","Gemiddeld","Atletisch","Bredere schouders","Bredere heupen"].index(p.get("bouw","") or ""))
            with c2:
                p["maat_boven"]   = st.text_input("Maat boven (bijv. M / 48)", p.get("maat_boven",""))
                p["maat_beneden"] = st.text_input("Maat beneden (bijv. 32/32)", p.get("maat_beneden",""))
                p["lengte_cm"]    = st.text_input("Lengte (cm)", p.get("lengte_cm",""))
            with c3:
                p["huidtint"]   = st.selectbox("Huidtint", ["","Koel","Neutraal","Warm"],
                                               index=["","Koel","Neutraal","Warm"].index(p.get("huidtint","") or ""))
                p["kleuren"]    = st.text_input("Kleurvoorkeuren (comma-sep.)", p.get("kleuren",""))
                p["stijl"]      = st.selectbox("Stijl", ["","Casual","Smart casual","Sportief","Zakelijk"],
                                               index=["","Casual","Smart casual","Sportief","Zakelijk"].index(p.get("stijl","") or ""))
            c4, c5 = st.columns([1,1])
            with c4:
                p["gelegenheid"] = st.selectbox("Gelegenheid", ["","Dagelijks","Werk","Feest"],
                                                index=["","Dagelijks","Werk","Feest"].index(p.get("gelegenheid","") or ""))
            with c5:
                p["comfort"] = st.text_input("Comfort (bv. stretch, ademend)", p.get("comfort",""))
            p["notities"] = st.text_area("Notities (optioneel)", p.get("notities",""), height=70)

            b1, b2 = st.columns([1,1])
            save  = b1.form_submit_button("Opslaan")
            clear = b2.form_submit_button("Wissen")

            if save:
                st.session_state.profile = {k: (v or "").strip() for k, v in p.items()}
                st.success("Voorkeuren opgeslagen.")
            if clear:
                st.session_state.profile = DEFAULT_PROFILE.copy()
                st.info("Voorkeuren gewist.")

        tags = _profile_tags(st.session_state.profile)
        if tags:
            st.markdown(
                '<div class="tagsrow">' + "".join([f'<span class="tag">{esc(t)}</span>' for t in tags]) + '</div>',
                unsafe_allow_html=True
            )

# ---------- RENDER UI ----------
def render_compact_header():
    st.markdown(
        '<div class="card"><div class="card-title">'
        f'{DRESS_SVG} Fashion AI Stylist'
        '</div></div>', unsafe_allow_html=True
    )

def render_single_card(data: dict, link: str, profile: dict):
    headline = esc(data.get("headline","Advies"))
    pers = data.get("personal_advice", {})
    for_you = as_list(pers.get("for_you"))[:3]
    avoid   = as_list(pers.get("avoid"))[:2]
    colors  = as_list(pers.get("colors"))[:2]
    combine = as_list(pers.get("combine"))[:2]
    tags = _profile_tags(profile)

    tags_html = ""
    if tags:
        tags_html = '<div class="tagsrow">' + "".join([f'<span class="tag">{esc(t)}</span>' for t in tags]) + '</div>'

    html = (
        '<div class="card">'
        f'<div class="card-title">{DRESS_SVG} {headline}</div>'
        '<div class="card-sub">'
        f'{tags_html}'
        '<div class="section-h">• Specifiek advies voor jou</div>'
        f'<ul>{"".join([f"<li>{esc(x)}</li>" for x in for_you])}</ul>'
        '<div class="section-h">• Kleur & combineren</div>'
        f'<ul>{"".join([f"<li>{esc(x)}</li>" for x in colors+combine])}</ul>'
        '<div class="section-h">• Liever vermijden</div>'
        f'<ul>{"".join([f"<li>{esc(x)}</li>" for x in avoid])}</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def render_matching_links_card(data: dict, link: str):
    pers = data.get("personal_advice", {})
    queries = _queries_from_combine(as_list(pers.get("combine")), max_links=4)

    LINK_SVG = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
<path d="M10 14l-1 1a4 4 0 105.7 5.7l2.6-2.6a4 4 0 00-5.7-5.7l-.6.6" stroke="#6F5BFF" stroke-width="2" stroke-linecap="round" fill="none"/>
<path d="M14 10l1-1a4 4 0 10-5.7-5.7L6.7 5.9a4 4 0 105.7 5.7l.6-.6" stroke="#6F5BFF" stroke-width="2" stroke-linecap="round" fill="none"/>
</svg>"""

    if not queries:
        return

    chips_html = []
    for q in queries:
        url = _build_link_or_fallback(link, q)
        chips_html.append(f'<a class="chip" href="{url}" target="_blank" rel="nofollow noopener">{LINK_SVG} Zoek: {esc(q)}</a>')

    html = (
        '<div class="card matching">'
        f'<div class="card-title">{DRESS_SVG} Bijpassende kleding (op deze shop)</div>'
        '<div class="card-sub">'
        f'<div class="btnrow">{"".join(chips_html)}</div>'
        '<div class="note">We zoeken eerst binnen deze shop; lukt dat niet, dan via Google.</div>'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

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

# ======================= MAIN FLOW =======================

if panel and link_qs and auto:
    # render_compact_header()  # optioneel
    render_profile_expander()
    data = get_advice_json(link_qs, st.session_state.get("profile", DEFAULT_PROFILE))
    render_single_card(data, link_qs, st.session_state.get("profile", DEFAULT_PROFILE))
    render_matching_links_card(data, link_qs)

else:
    components.html("""
    <div style="display:flex;align-items:center;gap:14px;margin:10px 0 8px;color:#fff;">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="#fff" xmlns="http://www.w3.org/2000/svg"><path d="M8 3l1.5 3-2 3 2 11h5l2-11-2-3L16 3h-2l-1 2-1-2H8z"/></svg>
      <h1 style="font:800 44px/1 'Inter',system-ui;letter-spacing:-.02em;margin:0;">Fashion AI Stylist</h1>
    </div>
    """, height=70)

    render_profile_expander()

    if "last_link" not in st.session_state:
        st.session_state.last_link = ""
    prefill = link_qs if (auto and link_qs) else st.session_state.last_link
    render_hero(prefill)

    active_link = link_qs if (auto and link_qs) else st.session_state.last_link
    if active_link:
        st.session_state.last_link = active_link
        data = get_advice_json(active_link, st.session_state.get("profile", DEFAULT_PROFILE))
        render_single_card(data, active_link, st.session_state.get("profile", DEFAULT_PROFILE))
        render_matching_links_card(data, active_link)
