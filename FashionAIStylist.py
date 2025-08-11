# app.py — Krachtiger adviesversie
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
  padding-bottom: 160px !important; /* ruimte onderin zodat CTA niet overlapt */
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
  font-weight:800; margin:12px 0 6px; color:#2d2a6c; display:flex; align-items:center; gap:8px;
}

/* Verdict badge */
.badge{ display:inline-flex; align-items:center; gap:8px; font-weight:800; padding:6px 10px; border-radius:999px; font-size:12px; }
.badge svg{ width:16px; height:16px; }
.badge.doen{ background:#E8FFF3; color:#046C4E; border:1px solid #C7F5DB; }
.badge.twijfel{ background:#FFF7E6; color:#92400E; border:1px solid #FFE0B2; }
.badge.overslaan{ background:#FFE8E8; color:#7F1D1D; border:1px solid #FFC9C9; }

/* CTA knoppen */
.btnrow{ display:flex; flex-wrap:wrap; gap:10px; margin-top:10px; }
.btn{
  display:inline-flex; align-items:center; gap:8px; padding:10px 14px; border-radius:12px;
  background:#F3F4FF; color:#2d2a6c; border:1px solid #E3E6FF; text-decoration:none; font-weight:700;
}
.btn svg{ width:18px; height:18px; }

/* Sticky CTA – rechtsonder */
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

# ---------- OpenAI: krachtig advies in één tekstwolk ----------
SCHEMA_HINT = {
  "headline": "max 10 woorden samenvatting",
  "item_observation": {
    "what_it_is": "kort wat voor item/categorie",
    "traits": ["exact 3 bullets met algemene, categorie-typische kenmerken (geen speculatie)"]
  },
  "personal_advice": {
    "for_you": ["exact 3 bullets met persoonlijk advies op basis van profiel"],
    "avoid": ["exact 2 bullets met wat te vermijden voor dit profiel"],
    "size_fit": {
      "size_tip": "kort maatadvies, refereer waar mogelijk aan opgegeven maten",
      "fit_tips": ["exact 2 bullets over pasvorm/lengte"]
    },
    "colors": ["exact 2 bullets over passende kleuren t.o.v. huidskleur"],
    "combine": ["exact 2 bullets met combinaties (generieke items), afgestemd op gelegenheid/vibe"]
  },
  "care_quality": ["exact 2 bullets over stof/kwaliteit/onderhoud (algemeen, niet-speculatief)"],
  "checks": ["exact 2 bullets met concrete checks op productpagina (samenstelling, lengte cm, voering, waslabel)"]
}


def get_advice_json(link: str) -> dict:
    # Defaults als sidebar dicht is
    fig = st.session_state.get("pf_l", "Weet ik niet")
    skin = st.session_state.get("pf_h", "Medium")
    hgt  = st.session_state.get("pf_len", "1.60 - 1.75m")
    occ  = st.session_state.get("pf_g", "Vrije tijd")
    vibe = st.session_state.get("pf_ge", "Casual")

    profile = f"figuur={fig}, huidskleur={skin}, lengte={hgt}, gelegenheid={occ}, stijlgevoel={vibe}"
    product_name = _product_name(link)
    keywords     = _keywords_from_url(link)
    domain       = urlparse(link).netloc
    detected_category = _detect_category(link)

    system_msg = (
        "Je bent een modieuze maar praktische personal stylist. Schrijf in helder Nederlands (B1), kort en concreet. "
        "Gebruik het profiel expliciet: noem lengte/pasvorm/kleuren/gelegenheid waar relevant. "
        "Wees eerlijk over onzekerheid: speculeer niet over details die je niet weet. "
        "Geen merknamen of emoji."
    )

    user_msg = f"""
Analyseer dit product uitsluitend op basis van URL-naam/keywords.
URL: {link}
Domein: {domain}
Vermoedelijke productnaam: {product_name}
Keywords: {keywords}
Gedetecteerde categorie: {detected_category}
Profiel: {profile}

Geef ALLEEN JSON met exact deze velden (geen extra velden):
{json.dumps(SCHEMA_HINT, ensure_ascii=False)}

Belangrijk:
- **Eerst algemene observatie**: beschrijf wat het is en 3 categorie-typische kenmerken. Gebruik neutrale taal ("meestal", "vaak"). Geen speculatie over merk-specifieke details.
- **Daarna persoonlijk advies**: verbind elk punt aan het profiel (lengte/fit/huidskleur/gelegenheid/vibe/maten). Kort en concreet.
- Combineer-advies: generieke items, afgestemd op gelegenheid en vibe.
- Colors: stem af op huidskleur; noem twee veilige keuzes.
- Care/quality: algemene, veilige richtlijnen per categorie (geen verzonnen cijfers of claims).
- Checks: 2 concrete dingen om op de productpagina te controleren.
"""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            response_format={"type":"json_object"},
            messages=[{"role":"system","content":system_msg},{"role":"user","content":user_msg}],
            temperature=0.4, max_tokens=600,
        )
        data = json.loads(resp.choices[0].message.content)
        # Minimale validatie + fallbacks voor nieuw schema
        data.setdefault("headline", product_name or "Snel advies")

        obs = data.setdefault("item_observation", {})
        obs.setdefault("what_it_is", detected_category.title())
        obs.setdefault("traits", [])

        pers = data.setdefault("personal_advice", {})
        pers.setdefault("for_you", [])
        pers.setdefault("avoid", [])

        sf = pers.setdefault("size_fit", {})
        sf.setdefault("size_tip", "Neem je normale maat, controleer maattabel.")
        sf.setdefault("fit_tips", [])

        pers.setdefault("colors", [])
        pers.setdefault("combine", [])

        data.setdefault("care_quality", [])
        data.setdefault("checks", [])
        return data
    except Exception:
        # Fallback — veilig en neutraal (nieuw schema)
        return {
            "headline": product_name or "Snel advies",
            "item_observation": {
                "what_it_is": detected_category.title(),
                "traits": [
                    "Tijdloos model, makkelijk te stylen.",
                    "Categorie-typische pasvormkenmerken.",
                    "Let op stof en afwerking."
                ]
            },
            "personal_advice": {
                "for_you": [
                    "Kies lengte passend bij jouw lengte.",
                    "Stem pasvorm af op fitvoorkeur.",
                    "Kleurkeuze afstemmen op huidskleur."
                ],
                "avoid": [
                    "Vermijd te strak bij comfortwens.",
                    "Vermijd glans als je het subtiel wilt."
                ],
                "size_fit": {
                    "size_tip": "Neem je normale maat.",
                    "fit_tips": ["Lengte tot heup is veilig", "Hou top relaxed-fit"]
                },
                "colors": ["Neutraal: wit, grijs, navy", "Accent: olijf of bordeaux"],
                "combine": ["Rechte jeans of chino", "Witte sneaker of loafer"]
            },
            "care_quality": ["Kies katoen 180–220 g/m²", "Was koud, binnenstebuiten"],
            "checks": ["Samenstelling en waslabel", "Lengte in cm/maattabel"]
        }

# ---------- Render: één sterke tekstwolk ----------

def verdict_class(v: str) -> str:
    v = (v or "").strip().lower()
    if v.startswith("doen"): return "doen"
    if v.startswith("over"): return "overslaan"
    return "twijfel"


def render_single_card(data: dict, link: str):
    product_name = _product_name(link)
    headline = esc(data.get("headline", product_name or "Kort advies"))

    obs = data.get("item_observation", {})
    what  = esc(obs.get("what_it_is",""))
    traits = [esc(x) for x in as_list(obs.get("traits"))][:3]

    pers = data.get("personal_advice", {})
    for_you = [esc(x) for x in as_list(pers.get("for_you"))][:3]
    avoid   = [esc(x) for x in as_list(pers.get("avoid"))][:2]

    fit_tips = [esc(x) for x in as_list(pers.get("size_fit",{}).get("fit_tips"))][:2]
    size_tip = esc(pers.get("size_fit",{}).get("size_tip", "Neem je normale maat."))
    colors   = [esc(x) for x in as_list(pers.get("colors"))][:2]
    combine  = [esc(x) for x in as_list(pers.get("combine"))][:2]

    care   = [esc(x) for x in as_list(data.get("care_quality"))][:2]
    checks = [esc(x) for x in as_list(data.get("checks"))][:2]

    # Alternatieven (site- of Google fallback)
    cheaper_q = f"{product_name} budget"
    premium_q = f"{product_name} premium"
    cheaper_url = _build_link_or_fallback(link, cheaper_q)
    premium_url = _build_link_or_fallback(link, premium_q)

    LINK_SVG2 = "<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'><path d='M3.9 12a5 5 0 015-5h3v2h-3a3 3 0 100 6h3v2h-3a5 5 0 01-5-5zm7-3h3a5 5 0 110 10h-3v-2h3a3 3 0 100-6h-3V9z'/></svg>"

    html = f"""
<div class="card">
  <div class="card-title">
    <svg class="icon" viewBox="0 0 24 24" width="22" height="22" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8 3l1.5 3-2 3 2 11h5l2-11-2-3L16 3h-2l-1 2-1-2H8z" fill="#556BFF"/></svg>
    {headline}
  </div>
  <div class="card-body">

    <div class="section-h">• Algemene observatie</div>
    <ul>
      <li><strong>Item:</strong> {what}</li>
      {''.join([f"<li>{x}</li>" for x in traits])}
    </ul>

    <div class="section-h">• Specifiek advies voor jou</div>
    <ul>
      {''.join([f"<li>{x}</li>" for x in for_you])}
    </ul>

    <div class="section-h">• Maat & pasvorm</div>
    <ul>
      <li><strong>Maat:</strong> {size_tip}</li>
      {''.join([f"<li>{x}</li>" for x in fit_tips])}
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

    <div class="section-h">• Kwaliteit & onderhoud</div>
    <ul>
      {''.join([f"<li>{x}</li>" for x in care])}
    </ul>

    <div class="section-h">• Snel checken op de productpagina</div>
    <ul>
      {''.join([f"<li>{x}</li>" for x in checks])}
    </ul>

    <div class="btnrow">
      <a class="btn" href="{cheaper_url}" target="_blank" rel="nofollow noopener">{LINK_SVG2} Bekijk goedkoper alternatief</a>
      <a class="btn" href="{premium_url}" target="_blank" rel="nofollow noopener">{LINK_SVG2} Bekijk premium alternatief</a>
    </div>

    <div class="small-note" style="margin-top:10px;">Advies gebaseerd op productnaam/keywords en jouw profiel (zonder website-scraping). Controleer altijd samenstelling en maattabel.</div>
  </div>
</div>
"""
    clean_html = dedent(html).strip("
")
    st.markdown(clean_html, unsafe_allow_html=True)

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
    render_single_card(data, active_link)

# Input-veld ONDERAAN in witte card
with st.form("manual_bottom", clear_on_submit=False):
    st.markdown(dedent(f"<div class='card-title'>{LINK_SVG} Plak hier de link van een ander product</div>"), unsafe_allow_html=True)
    link_in = st.text_input(label="", value="", placeholder="https://…")
    go = st.form_submit_button("Geef advies")

if go and link_in:
    st.session_state.last_link = link_in.strip()
    st.rerun()
