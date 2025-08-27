# app.py — Fashion AI Stylist met popup-modus (panel=1)
import os, re, json
import streamlit as st
import streamlit.components.v1 as components
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

# ---------- Query params ----------
qp = st.query_params

def _get(name, default=""):
    v = qp.get(name, default)
    return (v[0] if isinstance(v, list) and v else v) or default

link_qs = _get("u").strip()
auto    = str(_get("auto","0")) == "1"
panel   = str(_get("panel","0")) == "1"

# ---------- Pagina ----------
st.set_page_config(
    page_title="Fashion AI Stylist",
    page_icon="👗",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ---------- CSS ----------
base_css = """
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
  padding-bottom: 90px !important;
}

/* Cards */
.card{
  background:#ffffff; border-radius: 22px; padding: 22px;
  box-shadow: 0 16px 40px rgba(23,0,75,0.18);
  border: 1px solid #EFEBFF; margin-top: 16px;
}
.card-title{
  font-size: 26px; font-weight: 800; color:#1f2358;
  margin:0 0 12px; display:flex; gap:12px; align-items:center;
}
.card-sub{ color:#2b2b46; }
.section-h{ font-weight:800; margin:14px 0 6px; color:#1f2358; }
ul{ margin: 0 0 0 1.15rem; padding:0; line-height:1.6; }
li{ margin: 6px 0; }

/* Chips */
.matching .btnrow{ display:flex; flex-wrap:wrap; gap:10px; margin-top:8px; }
.matching .chip{
  display:inline-flex; align-items:center; gap:6px;
  padding:8px 12px; border-radius:10px;
  background:#F3F4FF; border:1px solid #E3E6FF;
  text-decoration:none; font-weight:600; color:#1f2a5a;
  font-size:14px; line-height:1.3;
}
.matching .note{ color:#6B7280; font-size:13px; margin-top:10px; }

/* ===== Compacte popup modus ===== */
body[data-panel="1"] .card{
  padding: 14px !important; border-radius: 14px !important;
}
body[data-panel="1"] .card-title{
  font-size: 20px !important; margin-bottom: 6px !important;
}
body[data-panel="1"] .section-h{
  font-size: 15px !important;
  margin-top: 10px !important; margin-bottom: 4px !important;
}
body[data-panel="1"] ul li{
  font-size: 14px !important; line-height: 1.4 !important; margin: 3px 0 !important;
}
body[data-panel="1"] .hero-title{
  font-size: 18px !important; margin-bottom: 8px !important;
}
</style>
"""
st.markdown(base_css, unsafe_allow_html=True)

# Inject attribuut in body → zodat CSS weet of panel=1
if panel:
    st.markdown("<script>document.body.setAttribute('data-panel','1');</script>", unsafe_allow_html=True)

# ---------- Icons ----------
DRESS_SVG = """<svg viewBox="0 0 24 24" fill="#556BFF" width="22" height="22"><path d="M8 3l1.5 3-2 3 2 11h5l2-11-2-3L16 3h-2l-1 2-1-2H8z"/></svg>"""

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

# ---------- LLM call ----------
def get_advice_json(link: str) -> dict:
    product_name = _product_name(link)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            response_format={"type":"json_object"},
            messages=[
                {"role":"system","content":"Je bent een stylist. Schrijf kort en duidelijk in B1-Nederlands."},
                {"role":"user","content":f"Geef kort stijl-advies (JSON) voor {link}"}
            ],
            temperature=0.4, max_tokens=500,
        )
        data = json.loads(resp.choices[0].message.content)
        data.setdefault("headline", product_name or "Snel advies")
        return data
    except Exception:
        return {
            "headline": product_name or "Snel advies",
            "personal_advice": {
                "for_you": ["Kies casual stijl", "Hou kleuren rustig", "Kies zachte tinten"],
                "avoid": ["Vermijd te drukke prints", "Vermijd harde contrasten"],
                "colors": ["Neutraal: ecru", "Accent: olijf"],
                "combine": ["Jeans", "Sneakers"]
            }
        }

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

# ---------- APP FLOW ----------
if link_qs and auto:
    data = get_advice_json(link_qs)
    render_single_card(data, link_qs)
else:
    st.markdown("""
    <div class="card">
      <div class="card-title">👗 Fashion AI Stylist</div>
      <div class="card-sub">
        Plak een productlink om advies te krijgen.
      </div>
    </div>
    """, unsafe_allow_html=True)
