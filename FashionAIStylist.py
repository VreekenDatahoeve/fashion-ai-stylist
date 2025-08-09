# app.py (OpenAI SDK >= 1.0)
import os
import streamlit as st
from openai import OpenAI

# --- API key lezen (env of Streamlit secrets) ---
API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not API_KEY:
    st.error("Geen OpenAI API-sleutel gevonden. Zet OPENAI_API_KEY in Secrets.")
    st.stop()

client = OpenAI(api_key=API_KEY)

# --- Pagina-instellingen ---
st.set_page_config(page_title="AI Stylingadvies", page_icon="👗", layout="centered")

# --- Query params (bookmarklet) ---  ✅ nieuwe API
qp = st.query_params
link_qs = (qp.get("u", "") or "").strip()             # product-URL uit bookmarklet
auto = str(qp.get("auto", "0")) == "1"                # auto-run toggle

# --- Bookmarklet uitleg/knop (VUL JE EIGEN URL IN) ---
APP_URL = "https://fashion-ai-stylis-ifidobqmkgjtn7gjxgrudb.streamlit.app/"
bookmarklet = (
    f"javascript:(()=>{{window.open('{APP_URL}/?u='+encodeURIComponent(location.href)+'&auto=1','_blank');}})();"
)
st.markdown(
    f'**Bookmarklet:** sleep deze <a href="{bookmarklet}">AI-stylist</a> naar je bladwijzerbalk en klik erop op een productpagina.',
    unsafe_allow_html=True
)
st.caption("Tip: bladwijzerbalk aanzetten met Ctrl+Shift+B (Mac: Cmd+Shift+B).")

st.title("👗 AI Stylingadvies op basis van kledinglink")
st.write("Plak een link naar een kledingstuk of gebruik de bookmarklet. Beantwoord een paar korte vragen voor persoonlijk advies.")

# --- Helper om advies te draaien ---
def run_advice(link, lichaamsvorm, huidskleur, lengte, gelegenheid, gevoel):
    prompt = f"""
Je bent een ervaren fashion stylist. Analyseer dit kledingstuk: {link}
Profiel: figuur={lichaamsvorm}, huidskleur={huidskleur}, lengte={lengte},
gelegenheid={gelegenheid}, intentie={gevoel}.
Geef ALLEEN markdown met exact deze kopjes:
## Beoordeling (kort)
## Stijl- en kleuradvies
## Combinaties
## Stijlscore
## Alternatieven (geen links)
    """
    with st.spinner("AI is je persoonlijke stylingadvies aan het genereren..."):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Wees concreet, modern en beknopt."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=700,
        )
    advies = resp.choices[0].message.content
    st.markdown("### ✨ Resultaat")
    st.markdown(advies)

# --- Auto-run als link via bookmarklet komt ---
if link_qs and auto:
    st.success("🔗 Link ontvangen via bookmarklet")
    run_advice(
        link_qs,
        lichaamsvorm="Weet ik niet",
        huidskleur="Medium",
        lengte="1.60 - 1.75m",
        gelegenheid="Vrije tijd",
        gevoel="Casual",
    )
else:
    # --- Formulier (handmatige invoer) ---
    with st.form("kledingadvies_form"):
        link = st.text_input("🔗 Plak hier de link naar het kledingstuk",
                             value=link_qs or "", placeholder="https://...")
        col1, col2, col3 = st.columns(3)
        with col1:
            lichaamsvorm = st.selectbox("👤 Lichaamsvorm", ["Zandloper", "Peer", "Rechthoek", "Appel", "Weet ik niet"])
        with col2:
            huidskleur = st.selectbox("🎨 Huidskleur", ["Licht", "Medium", "Donker"])
        with col3:
            gelegenheid = st.selectbox("🎯 Gelegenheid", ["Werk", "Feest", "Vrije tijd", "Bruiloft", "Date"])
        with st.expander("⚙️ Geavanceerd (optioneel)"):
            lengte = st.selectbox("📏 Lengte", ["< 1.60m", "1.60 - 1.75m", "> 1.75m"])
            gevoel = st.selectbox("🧠 Gevoel", ["Zelfverzekerd", "Speels", "Elegant", "Casual", "Trendy"])
        submitted = st.form_submit_button("Vraag AI om advies")

    if submitted and link:
        run_advice(link, lichaamsvorm, huidskleur, lengte, gelegenheid, gevoel)

st.caption("💡 Demo gebruikt gpt-4o-mini. Pas aan indien gewenst.")
