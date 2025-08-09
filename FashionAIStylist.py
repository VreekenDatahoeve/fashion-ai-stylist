# app.py (OpenAI SDK >= 1.0)
import os, re
import streamlit as st
from urllib.parse import urlparse, quote
from openai import OpenAI

# ---------- SETTINGS ----------
APP_URL = "https://fashion-ai-stylis-ifidobqmkgjtn7gjxgrudb.streamlit.app"  # jouw URL
MODEL = "gpt-4o-mini"
# ------------------------------

# --- API key ---
API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not API_KEY:
    st.error("Geen OpenAI API-sleutel gevonden. Zet OPENAI_API_KEY in Secrets.")
    st.stop()
client = OpenAI(api_key=API_KEY)

# --- Pagina ---
st.set_page_config(page_title="AI Stylingadvies", page_icon="👗", layout="centered")

# --- UI styling ---
def inject_ui():
    st.markdown(
        """
        <style>
        /* Font (lichtgewicht, cached door Google) */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

        html, body, [class*="stApp"] {
          font-family: "Inter", system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif;
        }

        /* Container breedte + lucht */
        .block-container {max-width: 920px; padding-top: 1.25rem; padding-bottom: 4rem;}

        /* Hero spacing */
        h1 { letter-spacing: -0.02em; }

        /* Cards */
        .card {
          background: var(--secondary-bg, #F6F7FB);
          border: 1px solid rgba(0,0,0,0.06);
          border-radius: 18px;
          padding: 18px 18px;
          box-shadow: 0 8px 28px rgba(17, 24, 39, .06);
        }

        /* Inputs */
        .stTextInput > div > div > input,
        .stSelectbox > div > div {
          border-radius: 12px !important;
          min-height: 42px;
        }

        /* Buttons */
        .stButton > button {
          background: linear-gradient(90deg,#7C3AED,#6D28D9);
          color: #fff;
          border: 0;
          border-radius: 12px;
          padding: 10px 16px;
          font-weight: 600;
          box-shadow: 0 8px 18px rgba(124,58,237,.25);
        }
        .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 12px 22px rgba(124,58,237,.32); }

        /* Pills (voor alternatieven) */
        .pill {
          display:inline-block;
          padding:8px 12px;
          border-radius:999px;
          background:#fff;
          border:1px solid rgba(0,0,0,.08);
          margin: 6px 8px 0 0;
          box-shadow: 0 2px 8px rgba(0,0,0,.05);
          text-decoration:none;
          color:#111827 !important;
          font-size: 0.92rem;
        }
        .pill:hover { border-color:#7C3AED; }

        /* Expander header subtieler */
        details > summary { font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )

inject_ui()

# --- Query params (bookmarklet/extensie) ---
qp = st.query_params
def _get(name, default=""):
    v = qp.get(name, default)
    return (v[0] if isinstance(v, list) and v else v) or default

link_qs = _get("u").strip()
auto    = str(_get("auto","0")) == "1"

# --- Bookmarklet link (zelfde tab – werkt altijd) ---
bm = f"javascript:(()=>{{location.href='{APP_URL}?u='+encodeURIComponent(location.href)+'&auto=1';}})();"
st.markdown(
    f'**Bookmarklet:** sleep deze <a href="{bm}">AI-stylist</a> naar je bladwijzerbalk en klik op een productpagina.',
    unsafe_allow_html=True
)
st.caption("Tip: bladwijzerbalk aan met Ctrl+Shift+B (Mac: Cmd+Shift+B).")

# --- Hero ---
st.markdown("# 👗 AI Stylingadvies op basis van kledinglink")
st.write("Plak een link of gebruik de bookmarklet. Je krijgt **korte, concrete feedback** en **alternatieven uit dezelfde webshop**.")

# ---------- Helpers: alternatieve links binnen dezelfde shop ----------
import re
def _keywords_from_url(u: str):
    try:
        slug = urlparse(u).path.rstrip("/").split("/")[-1]
        slug = re.sub(r"\\d+", " ", slug)
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
    for s in searches: items.append((f"Zoek: {kw}", s))
    seen, out = set(), []
    for t, url in items:
        if url not in seen:
            out.append((t, url)); seen.add(url)
    return out[:3]
# ---------------------------------------------------------------------

# --- Advies-call ---
def run_advice(link, lichaamsvorm, huidskleur, lengte, gelegenheid, gevoel, kort=True):
    stijl = "Maak het superkort: max 70 woorden. Gebruik 3–5 bullets." if kort else "Houd het beknopt."
    prompt = f"""
Je bent een ervaren fashion stylist. Analyseer dit kledingstuk: {link}
Profiel: figuur={lichaamsvorm}, huidskleur={huidskleur}, lengte={lengte},
gelegenheid={gelegenheid}, intentie={gevoel}.
{stijl}

Schrijf ALLEEN deze secties in markdown, zonder extra tekst:
## Korte beoordeling
- ...

## Combineer met
- ...

## Kleur & pasvorm
- ...
"""
    with st.spinner("AI is je persoonlijke stylingadvies aan het genereren..."):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Wees concreet, modern, vriendelijk en to-the-point."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=450,
        )

    # Resultaat in een card
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### ✨ Resultaat")
        st.markdown(resp.choices[0].message.content)
        st.markdown("</div>", unsafe_allow_html=True)

    # Alternatieven als “pills”
    alts = build_shop_alternatives(link)
    if alts:
        st.markdown("### 🔁 Alternatieven uit deze webshop")
        pill_html = "".join([f'<a class="pill" href="{u}" target="_blank">🔗 {t}</a>' for t, u in alts])
        st.markdown(pill_html, unsafe_allow_html=True)

# --- UI: snelle modus + optioneel profiel in expander ---
cA, cB = st.columns([1,1])
with cA:
    korte_modus = st.checkbox("Korte feedback (aanbevolen)", value=True)

with st.expander("👤 Profiel (optioneel) – dit hoef je meestal niet te veranderen"):
    c1, c2, c3 = st.columns(3)
    with c1:
        lichaamsvorm = st.selectbox("Lichaamsvorm", ["Zandloper", "Peer", "Rechthoek", "Appel", "Weet ik niet"], index=4)
    with c2:
        huidskleur = st.selectbox("Huidskleur", ["Licht", "Medium", "Donker"], index=1)
    with c3:
        lengte = st.selectbox("Lengte", ["< 1.60m", "1.60 - 1.75m", "> 1.75m"], index=1)
    c4, c5 = st.columns(2)
    with c4:
        gelegenheid = st.selectbox("Gelegenheid", ["Werk", "Feest", "Vrije tijd", "Bruiloft", "Date"], index=2)
    with c5:
        gevoel = st.selectbox("Gevoel", ["Zelfverzekerd", "Speels", "Elegant", "Casual", "Trendy"], index=3)

# Handmatige invoer in een card
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.form("kledingadvies_form", clear_on_submit=False):
        link = st.text_input("🔗 Plak hier de link naar het kledingstuk", value=link_qs or "", placeholder="https://...")
        submitted = st.form_submit_button("Vraag AI om advies")
    st.markdown("</div>", unsafe_allow_html=True)

# Auto-run of handmatig
if (link_qs and auto) or (submitted and link):
    the_link = link_qs if (link_qs and auto) else link
    st.success("🔗 Link ontvangen via bookmarklet" if (link_qs and auto) else "✅ Link ontvangen")
    run_advice(
        the_link,
        lichaamsvorm if 'lichaamsvorm' in locals() else "Weet ik niet",
        huidskleur   if 'huidskleur'   in locals() else "Medium",
        lengte       if 'lengte'       in locals() else "1.60 - 1.75m",
        gelegenheid  if 'gelegenheid'  in locals() else "Vrije tijd",
        gevoel       if 'gevoel'       in locals() else "Casual",
        kort=korte_modus,
    )

st.caption("💡 Demo gebruikt gpt-4o-mini. Antwoorden kort & scanbaar; alternatieven linken naar dezelfde webshop.")
