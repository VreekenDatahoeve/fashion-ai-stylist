# app.py
import os, re, random, json, io, base64
import streamlit as st
from urllib.parse import urlparse, quote
from html import escape as html_escape
from openai import OpenAI

# ========= Instellingen =========
APP_URL = "https://fashion-ai-stylis-ifidobqmkgjtn7gjxgrudb.streamlit.app"  # <-- JOUW URL (geen trailing slash)
MODEL   = "gpt-4o-mini"
SHOW_AVATAR = True   # zet False om te verbergen
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
html, body, [class*="stApp"]{ font-family:"Inter", system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }

/* Paarse gradient background */
[data-testid="stAppViewContainer"]{
  background: radial-gradient(1200px 600px at 50% -100px, #C8B9FF 0%, #AA98FF 30%, #8F7DFF 60%, #7A66F7 100%);
}
[data-testid="stHeader"] { display:none; }
footer { visibility:hidden; }

/* Layout breedte */
.block-container{ max-width: 860px; padding-top: 8px !important; padding-bottom: 96px !important; }

/* Info-chip bovenaan */
.note-chip{
  display:block;
  margin: 6px 0 14px;
  padding: 10px 14px;
  border-radius: 14px;
  background: rgba(255,255,255,0.6);
  border: 1px solid rgba(255,255,255,0.75);
  color:#2d2a6c;
  font-weight:600;
  box-shadow: 0 10px 24px rgba(40,12,120,0.15);
  backdrop-filter: blur(4px);
}

/* Cards */
.card{
  background:#ffffff;
  border-radius: 22px;
  padding: 18px 18px 18px 18px;
  box-shadow: 0 16px 40px rgba(23,0,75,0.18);
  border: 1px solid #EFEBFF;
  margin-top: 12px;
}
.card-title{
  font-size: 22px; font-weight: 800; color:#2d2a6c; margin:0 0 10px;
  display:flex; gap:10px; align-items:center;
}
.card-title .icon{ width:22px; height:22px; display:inline-block; }

/* Advieskaart: tekst links, avatar rechts */
.advice-grid{
  display:grid;
  grid-template-columns: 1fr 220px; /* avatar breedte */
  gap: 12px;
  align-items: start;
}
.advice-copy{ min-width:0; color:#2b2b46; }
.avatar-box{ display:flex; justify-content:center; position:relative; z-index:0; }
.avatar-box img{
  width:100%; height:auto; border-radius:24px;
  box-shadow: 0 10px 30px rgba(23,0,75,.15);
  object-fit:contain; background:transparent;
}

/* Lijsten: compact en met en-dash vibe */
ul{ margin: 0 0 0 1.15rem; padding:0; }
li{ margin: 4px 0; }
.section-title{ font-weight:800; margin:10px 0 2px; color:#2d2a6c; }

/* Pills */
.pills{ display:flex; gap:10px; flex-wrap:wrap; margin-top: 8px; }
.pill{
  background:#F6F5FF; color:#2b2b46; border:1px solid #E7E5FF;
  padding:10px 14px; border-radius: 999px; font-weight:700; text-decoration:none;
  box-shadow: 0 6px 14px rgba(23,0,75,0.10);
}
.pill:hover{ transform: translateY(-1px); }

/* Sticky CTA onderin */
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

h1, h2, h3 { letter-spacing:-.02em; }
.small-note{ color:#6B7280; font-size: 13px; }

@media (max-width: 720px){
  .advice-grid{ grid-template-columns: 1fr; }
  .avatar-box{ order:-1; margin-bottom: 6px; }
}
</style>
""", unsafe_allow_html=True)

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
    st.session_state.show_prefs = prefs_q  # open als ?prefs=1

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

# ---------- CTA onderin -> zet prefs=1 en reload ----------
st.markdown("""
<button class="cta" onclick="
  const u = new URL(window.location);
  u.searchParams.set
