# app.py
import os, re
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
st.set_page_config(page_title="Fashion AI Stylist", page_icon="👗", layout="centered")

# --- UI / CSS (speels, modern) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="stApp"]{
  font-family:"Inter", system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
}
.block-container{max-width:920px;padding-top:1rem;padding-bottom:3rem;}
h1{letter-spacing:-.02em}

.card{
  background:#fff; border:1px solid #EAEAF0; border-radius:18px;
  padding:18px 18px; box-shadow:0 8px 28px rgba(17,24,39,.06); margin:.5rem 0 1rem 0;
}
.pill{
  display:inline-block; padding:8px 12px; border-radius:999px; background:#fff;
  border:1px solid #E5E7EB; margin:6px 8px 0 0; box-shadow:0 2px 8px rgba(0,0,0,.05);
  text-decoration:none; color:#111827; font-size:.95rem;
}
.pill:hover{ border-color:#7C3AED }
.fab{
  position:fixed; right:22px; bottom:22px;
  background:linear-gradient(90deg,#7C3AED,#6D28D9); color:#fff; border:0; border-radius:999px;
  padding:.75rem 1rem; font-weight:700; box-shadow:0 10px 24px rgba(124,58,237,.35);
  cursor:pointer; z-index:9999;
}
.fab:hover{ transform:translateY(-1px) }
.note{ color:#6B7280; font-size:.925rem }

/* inputs wat ronder */
.stTextInput > div > div > input, .stSelectbox > div > div { border-radius:12px !important; min-height:42px; }
</style>
""", unsafe_allow_html=True)

# --- Bookmarklet hint (optioneel zichtbaar) ---
bm = f"javascript:(()=>{{location.href='{APP_URL}?u='+encodeURIComponent(location.href)+'&auto=1';}})();"
st.markdown(
    f'**Bookmarklet:** sleep deze <a href="{bm}">AI-stylist</a> naar je bladwijzerbalk en klik op een productpagina.',
    unsafe_allow_html=True
)
st.caption("Tip: bladwijzerbalk aanzetten met Ctrl+Shift+B (Mac: Cmd+Shift+B).")

st.markdown("# 👗 AI Stylingadvies op basis van kledinglink")
st.write("Supersnel: **kort advies** en **alternatieven**. Optionele voorkeuren vind je bij _‘Vertel iets over jezelf’_.")

# ---------- Query params ----------
qp = st.query_params
def _get(name, default=""):
    v = qp.get(name, default)
    return (v[0] if isinstance(v, list) and v else v) or default

link_qs = _get("u").strip()
auto    = str(_get("auto","0")) == "1"

# ---------- Floating FAB -> opent sidebar ----------
if "show_prefs" not in st.session_state:
    st.session_state.show_prefs = False

# knop die via JS wordt geklikt (onzichtbaar)
st.button("_", key="_pf_toggle", help="", on_click=lambda: st.session_state.update(show_prefs=not st.session_state.show_prefs), type="secondary")
# eigenlijke FAB
st.markdown("<button class='fab' onClick=\"window.parent.postMessage({fab:1},'*')\">💬 Vertel iets over jezelf</button>", unsafe_allow_html=True)
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

# Sidebar met voorkeuren (opt.)
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
    # defaults als sidebar dicht is
    lichaamsvorm = "Weet ik niet"; huidskleur="Medium"; lengte="1.60 - 1.75m"; gelegenheid="Vrije tijd"; gevoel="Casual"

# ---------- Alternatieven-helper (zelfde shop) ----------
def _keywords_from_url(u: str):
    try:
        slug = urlparse(u).path.rstrip("/").split("/")[-1]
        slug = re.sub(r"\d+", " ", slug)
        words = [w for w in re.split(r"[-_]+", slug) if w and len(w) > 1]
        return " ".join(words[:3]) or "mode"
    except Exception:
        return "mode"

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
    for s in searches:
        items.append((f"Zoek: {kw}", s))
    # uniek + max 3
    seen, out = set(), []
    for t, url in items:
        if url not in seen:
            out.append((t, url)); seen.add(url)
    return out[:3]

# ---------- Advies-call ----------
def get_advice_md(link: str, kort=True) -> str:
    stijl = "Maak het superkort: max 70 woorden. Gebruik 3–5 bullets." if kort else "Houd het beknopt."
    prompt = f"""
Je bent een ervaren fashion stylist. Analyseer dit kledingstuk: {link}
Profiel: figuur={lichaamsvorm}, huidskleur={huidskleur}, lengte={lengte},
gelegenheid={gelegenheid}, intentie={gevoel}.
{stijl}

Schrijf ALLEEN:
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
            {"role":"system","content":"Wees concreet, modern, vriendelijk en to-the-point."},
            {"role":"user","content":prompt},
        ],
        temperature=0.5, max_tokens=450,
    )
    return resp.choices[0].message.content

# ---------- Toggle korte modus ----------
korte_modus = st.checkbox("Korte feedback (aanbevolen)", value=True)

# ---------- Blok 1: Advies ----------
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("### ✨ Kort advies")

# Auto-run (via bookmarklet/extensie) of handmatig
rendered = False
if link_qs and auto:
    st.success("🔗 Link ontvangen via bookmarklet")
    advies_md = get_advice_md(link_qs, kort=korte_modus)
    st.markdown(advies_md)
    rendered = True
st.markdown("</div>", unsafe_allow_html=True)

# ---------- Blok 2: Alternatieven ----------
st.markdown("### 🔁 Alternatieven uit deze webshop")
if rendered:
    alts = build_shop_alternatives(link_qs)
else:
    alts = []

if not alts and not rendered:
    st.markdown("<span class='note'>Er verschijnen alternatieven zodra je een productlink gebruikt.</span>", unsafe_allow_html=True)
else:
    pills_html = "".join([f"<a class='pill' href='{u}' target='_blank'>🔗 {t}</a>" for t, u in alts])
    st.markdown(pills_html, unsafe_allow_html=True)

# ---------- Fallback: handmatige invoer ----------
with st.form("manual"):
    link = st.text_input("🔗 Of plak hier een link", value=link_qs or "", placeholder="https://…")
    go = st.form_submit_button("Vraag AI om advies")

if go and link:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### ✨ Kort advies")
    advies_md = get_advice_md(link, kort=korte_modus)
    st.markdown(advies_md)
    st.markdown("</div>", unsafe_allow_html=True)

    a2 = build_shop_alternatives(link)
    if a2:
        pills_html = "".join([f"<a class='pill' href='{u}' target='_blank'>🔗 {t}</a>" for t, u in a2])
        st.markdown("### 🔁 Alternatieven uit deze webshop")
        st.markdown(pills_html, unsafe_allow_html=True)
