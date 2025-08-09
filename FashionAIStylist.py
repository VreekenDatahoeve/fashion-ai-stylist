# app.py (OpenAI SDK >= 1.0)
import os, re
import streamlit as st
from urllib.parse import urlparse, quote
from openai import OpenAI

# --- API key ---
API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not API_KEY:
    st.error("Geen OpenAI API-sleutel gevonden. Zet OPENAI_API_KEY in Secrets.")
    st.stop()
client = OpenAI(api_key=API_KEY)

# --- Pagina ---
st.set_page_config(page_title="AI Stylingadvies", page_icon="👗", layout="centered")

# --- Query params (bookmarklet) ---
qp = st.query_params
def _get(qname, default=""):
    v = qp.get(qname, default)
    return (v[0] if isinstance(v, list) and v else v) or default
link_qs = _get("u").strip()
auto = str(_get("auto","0")) == "1"

# --- Bookmarklet link (zelfde tab) ---
APP_URL = "https://fashion-ai-stylis-ifidobqmkgjtn7gjxgrudb.streamlit.app"
bm = f"javascript:(()=>{{location.href='{APP_URL}?u='+encodeURIComponent(location.href)+'&auto=1';}})();"
st.markdown(
    f'**Bookmarklet:** sleep deze <a href="{bm}">AI-stylist</a> naar je bladwijzerbalk en klik op een productpagina.',
    unsafe_allow_html=True
)
st.caption("Tip: bladwijzerbalk aan met Ctrl+Shift+B (Mac: Cmd+Shift+B).")

st.title("👗 AI Stylingadvies op basis van kledinglink")
st.write("Plak een link naar een kledingstuk of gebruik de bookmarklet. Korte, concrete feedback + alternatieven uit dezelfde webshop.")

# ---------- Helpers: alternatieve links in dezelfde shop ----------
def _keywords_from_url(u: str):
    try:
        slug = urlparse(u).path.rstrip("/").split("/")[-1]
        slug = re.sub(r"\d+", " ", slug)             # cijfers weg
        words = [w for w in re.split(r"[-_]+", slug) if w and len(w) > 1]
        return " ".join(words[:3]) or "mode"
    except Exception:
        return "mode"

def _category_candidates(u: str):
    p = urlparse(u)
    segs = [s for s in p.path.split("/") if s]
    cands = []
    if len(segs) >= 2:
        cands.append("/" + "/".join(segs[:-1]) + "/")
    if len(segs) >= 3:
        cands.append("/" + "/".join(segs[:-2]) + "/")
    # uniek
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            out.append(c); seen.add(c)
    return [f"{p.scheme}://{p.netloc}{c}" for c in out]

def _search_links(u: str, query: str):
    p = urlparse(u)
    host = f"{p.scheme}://{p.netloc}"
    q = quote(query)
    patterns = [
        f"/search?q={q}",
        f"/zoeken?query={q}",
        f"/s?searchTerm={q}",
        f"/search?text={q}",
    ]
    # uniek en geldig pad
    seen, out = set(), []
    for path in patterns:
        full = host + path
        if full not in seen:
            out.append(full); seen.add(full)
    return out

def build_shop_alternatives(u: str):
    if not u: return []
    kw = _keywords_from_url(u)
    cats = _category_candidates(u)         # 0..2 categorie-niveaus
    searches = _search_links(u, kw)[:2]    # 2 zoeklinks
    items = []
    if cats:
        items.append(("Categorie (zelfde shop)", cats[0]))
        if len(cats) > 1:
            items.append(("Bredere categorie", cats[1]))
    for s in searches:
        items.append((f"Zoek: {kw}", s))
    # uniek op url
    seen, out = set(), []
    for t, url in items:
        if url not in seen:
            out.append((t, url)); seen.add(url)
    return out[:3]  # max 3 links, compact houden
# -------------------------------------------------------------------

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
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Wees concreet, modern, vriendelijk en to-the-point."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=450,
        )
    st.markdown("### ✨ Resultaat")
    st.markdown(resp.choices[0].message.content)

    # Alternatieven uit dezelfde webshop (klikbare links)
    alts = build_shop_alternatives(link)
    if alts:
        st.markdown("### 🔁 Alternatieven uit deze webshop")
        for title, url in alts:
            st.markdown(f"- [{title}]({url})")

# --- UI ---
# Snelmodus (korte antwoorden)
colA, colB = st.columns([1,1])
with colA:
    korte_modus = st.checkbox("Korte feedback (aanbevolen)", value=True)
# Profiel-invoer optioneel
with st.expander("👤 Profiel (optioneel) – instellingen blijven meestal gelijk"):
    c1, c2, c3 = st.columns(3)
    with c1:
        lichaamsvorm = st.selectbox("Lichaamsvorm", ["Zandloper", "Peer", "Rechthoek", "Appel", "Weet ik niet"], index=4)
    with c2:
        huidskleur = st.selectbox("Huidskleur", ["Licht", "Medium", "Donker"], index=1)
    with c3:
        lengte = st.selectbox("Lengte", ["< 1.60m", "1.60 - 1.75m", "> 1.75m"], index=1)
    colx, coly = st.columns(2)
    with colx:
        gelegenheid = st.selectbox("Gelegenheid", ["Werk", "Feest", "Vrije tijd", "Bruiloft", "Date"], index=2)
    with coly:
        gevoel = st.selectbox("Gevoel", ["Zelfverzekerd", "Speels", "Elegant", "Casual", "Trendy"], index=3)

# Handmatige invoer
with st.form("kledingadvies_form"):
    link = st.text_input("🔗 Plak hier de link naar het kledingstuk", value=link_qs or "", placeholder="https://...")
    submitted = st.form_submit_button("Vraag AI om advies")

# Auto-run (bookmarklet/extensie) of handmatig
if (link_qs and auto) or (submitted and link):
    the_link = link_qs if (link_qs and auto) else link
    st.success("🔗 Link ontvangen via bookmarklet" if (link_qs and auto) else "✅ Link ontvangen")
    run_advice(
        the_link,
        lichaamsvorm if 'lichaamsvorm' in locals() else "Weet ik niet",
        huidskleur if 'huidskleur' in locals() else "Medium",
        lengte if 'lengte' in locals() else "1.60 - 1.75m",
        gelegenheid if 'gelegenheid' in locals() else "Vrije tijd",
        gevoel if 'gevoel' in locals() else "Casual",
        kort=korte_modus,
    )

st.caption("💡 Demo gebruikt gpt-4o-mini. Antwoorden kort & scanbaar; alternatieven linken naar dezelfde webshop.")
