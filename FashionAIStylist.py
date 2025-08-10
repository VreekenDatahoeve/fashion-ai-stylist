# app.py
import os, re, random
import streamlit as st
from urllib.parse import urlparse, quote
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
html, body, [class*="stApp"]{
  font-family:"Inter", system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
}

/* Paarse gradient background */
[data-testid="stAppViewContainer"]{
  background: radial-gradient(1200px 600px at 50% -100px, #C8B9FF 0%, #AA98FF 30%, #8F7DFF 60%, #7A66F7 100%);
}
[data-testid="stHeader"] { display:none; }
footer { visibility:hidden; }

/* Layout breedte */
.block-container{ max-width: 860px; padding-top: 8px !important; padding-bottom: 96px !important; }

/* --- Tekstballon (licht transparant) --- */
.balloon{
  background: rgba(255,255,255,0.82);
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

/* Bullets (voor AI-output) */
.section-label{ color:#2d2a6c; font-weight:800; margin-top:10px; margin-bottom:4px; }
ul.clean{ list-style:none; padding-left:0; margin:0; }
ul.clean li{ position:relative; padding-left:26px; margin:8px 0; color:#2b2b46; font-size:16px; }
ul.clean li::before{ content:"•"; position:absolute; left:6px; top:-1px; color:#5d59f6; font-size:24px; line-height:1; }

/* Alternatieven - pills */
.pills{ display:flex; gap:10px; flex-wrap:wrap; }
.pill{
  background:#F4F3FF; color:#2b2b46; border:1px solid #E5E4FF;
  padding:10px 14px; border-radius: 999px; font-weight:700; text-decoration:none;
  box-shadow: 0 6px 14px rgba(23,0,75,0.10);
}
.pill:hover{ transform: translateY(-1px); }

/* Sticky CTA onderin, gecentreerd */
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

/* Verberg helperknop voor CTA toggle */
button[id="_pf_toggle"]{ display:none !important; }

/* Typografie */
h1, h2, h3 { letter-spacing:-.02em; }
</style>
""", unsafe_allow_html=True)

# ---------- Query params ----------
qp = st.query_params
def _get(name, default=""):
    v = qp.get(name, default)
    return (v[0] if isinstance(v, list) and v else v) or default

link_qs = _get("u").strip()
auto    = str(_get("auto","0")) == "1"

# ---------- Floating CTA -> opent sidebar ----------
if "show_prefs" not in st.session_state:
    st.session_state.show_prefs = False

st.markdown("""
<button class="cta" onClick="window.parent.postMessage({fab:1},'*')">
  <span class="dot"></span> Vertel iets over jezelf
</button>
""", unsafe_allow_html=True)

st.components.v1.html("""
<script>
window.addEventListener('message',(e)=>{
  if(e.data && e.data.fab){
    const b = window.parent.document.querySelector('button[id="_pf_toggle"]');
    if(b) b.click();
  }
});
</script>
""", height=0)

# ---------- Sidebar voorkeuren ----------
if st.session_state.show_prefs:
    with st.sidebar:
        st.markdown("### 👤 Vertel iets over jezelf")
        lichaamsvorm = st.selectbox("Lichaamsvorm", ["Zandloper","Peer","Rechthoek","Appel","Weet ik niet"], index=4, key="pf_l")
        huidskleur   = st.selectbox("Huidskleur",   ["Licht","Medium","Donker"], index=1, key="pf_h")
        lengte       = st.selectbox("Lengte",       ["< 1.60m","1.60 - 1.75m","> 1.75m"], index=1, key="pf_len")
        gelegenheid  = st.selectbox("Gelegenheid",  ["Werk","Feest","Vrije tijd","Bruiloft","Date"], index=2, key="pf_g")
        gevoel       = st.selectbox("Gevoel",       ["Zelfverzekerd","Speels","Elegant","Casual","Trendy"], index=3, key="pf_ge")
        st.button("Sluiten", use_container_width=True, on_click=lambda: st.session_state.update(show_prefs=False))
else:
    lichaamsvorm = "Weet ik niet"; huidskleur="Medium"; lengte="1.60 - 1.75m"; gelegenheid="Vrije tijd"; gevoel="Casual"

# ---------- Helpers ----------
def _keywords_from_url(u: str):
    try:
        slug = urlparse(u).path.rstrip("/").split("/")[-1]
        slug = re.sub(r"\d+", " ", slug)
        words = [w for w in re.split(r"[-_]+", slug) if w and len(w) > 1]
        return " ".join(words[:4]) or "fashion"
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

def _search_links(u: str, query: str):
    p = urlparse(u); host = f"{p.scheme}://{p.netloc}"
    q = quote(query)
    patterns = [f"/search?q={q}", f"/zoeken?query={q}", f"/s?searchTerm={q}", f"/search?text={q}"]
    seen, out = set(), []
    for path in patterns:
        full = host + path
        if full not in seen:
            out.append(full); seen.add(full)
    return out

def build_shop_alternatives(u: str):
    if not u: return []
    kw = _keywords_from_url(u)
    cats = _category_candidates(u)
    searches = _search_links(u, kw)[:2]
    items = []
    if cats:
        items.append(("Categorie (zelfde shop)", cats[0]))
        if len(cats) > 1: items.append(("Bredere categorie", cats[1]))
    for s in searches[:1]:
        items.append((f"Zoek: {kw}", s))
    seen, out = set(), []
    for t, url in items:
        if url not in seen:
            out.append((t, url)); seen.add(url)
    return out[:3]

# ---------- OpenAI calls (eenvoudige taal) ----------
def get_advice_md(link: str, kort=True) -> str:
    # Bullets kort en simpel in het Nederlands
    stijl = (
        "Maak het superkort. Schrijf in eenvoudig Nederlands (B1). "
        "Gebruik 3–5 bullets. Max 8 woorden per bullet."
        if kort else
        "Gebruik eenvoudige woorden (B1) en korte zinnen."
    )
    prompt = f"""
Je bent een vriendelijke fashion stylist. Analyseer dit kledingstuk: {link}
Profiel: figuur={lichaamsvorm}, huidskleur={huidskleur}, lengte={lengte},
gelegenheid={gelegenheid}, stijlgevoel={gevoel}.
{stijl}

Schrijf ALLEEN dit, in het Nederlands:

## Korte beoordeling
- ...

## Combineer met
- ...

## Kleur & pasvorm
- ...
"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role":"system","content":"Wees concreet, modern en to-the-point. Vermijd moeilijke woorden en jargon."},
            {"role":"user","content":prompt},
        ],
        temperature=0.5, max_tokens=450,
    )
    return resp.choices[0].message.content

def get_quick_blurb(link: str, item_name: str) -> str:
    """1 zin, max 20 woorden, Engels, start met 'This <item_name>', simpele woorden."""
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

# ---------- UI ----------
# geen checkbox / geen success — direct naar content
korte_modus = True

# Advies/ballon voorbereiden
rendered = False
advies_md = ""
balloon_html = ""

OPENERS = ["Looks nice!", "Great pick!", "Nice choice!", "Love the vibe!", "Stylish pick!"]

if link_qs and auto:
    item_name = _product_name(link_qs)
    quick = get_quick_blurb(link_qs, item_name)
    opener = random.choice(OPENERS)
    balloon_html = f"<div class='balloon'>{opener} {quick}</div>"
    advies_md = get_advice_md(link_qs, kort=korte_modus)
    rendered = True

# Tekstballon (alleen als er een link is)
if balloon_html:
    st.markdown(balloon_html, unsafe_allow_html=True)

# Kaart 1: Kort advies
st.markdown(f"""
<div class="card">
  <div class="card-title">Kort advies</div>
  <div class="card-body">
    {advies_md if rendered else ""}
  </div>
</div>
""", unsafe_allow_html=True)

# Kaart 2: Alternatieven
alts = build_shop_alternatives(link_qs) if rendered else []
pills_html = "".join([f"<a class='pill' href='{u}' target='_blank'>{t}</a>" for t, u in alts])
st.markdown(f"""
<div class="card">
  <div class="card-title">Alternatieven uit deze webshop</div>
  <div class="card-body">
    {pills_html if pills_html else "<span class='note' style='color:#6B7280;'>Er verschijnen alternatieven zodra je een productlink gebruikt.</span>"}
  </div>
</div>
""", unsafe_allow_html=True)

# Handmatige invoer
with st.form("manual"):
    link = st.text_input("🔗 Of plak hier een link", value=link_qs or "", placeholder="https://…")
    go = st.form_submit_button("Vraag AI om advies")

if go and link:
    item_name = _product_name(link)
    quick = get_quick_blurb(link, item_name)
    opener = random.choice(OPENERS)
    st.markdown(f"<div class='balloon'>{opener} {quick}</div>", unsafe_allow_html=True)

    advies2 = get_advice_md(link, kort=korte_modus)
    a2 = build_shop_alternatives(link)
    pills2 = "".join([f"<a class='pill' href='{u}' target='_blank'>{t}</a>" for t, u in a2])

    st.markdown(f"""
    <div class="card">
      <div class="card-title">Kort advies</div>
      <div class="card-body">{advies2}</div>
    </div>
    <div class="card">
      <div class="card-title">Alternatieven uit deze webshop</div>
      <div class="card-body">
        {pills2 if pills2 else "<span class='note' style='color:#6B7280;'>Geen alternatieven gevonden.</span>"}
      </div>
    </div>
    """, unsafe_allow_html=True)
