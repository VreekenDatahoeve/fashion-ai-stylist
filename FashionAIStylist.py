# app.py (geüpdatet voor nieuwe OpenAI SDK >= 1.0)
import os
import streamlit as st
from openai import OpenAI

# --- API key lezen (env of Streamlit secrets) ---
API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("Geen OpenAI API-sleutel gevonden. Zet deze in env of .streamlit/secrets.toml.")

client = OpenAI(api_key=API_KEY)

# --- Pagina-instellingen ---
st.set_page_config(page_title="AI Stylingadvies", page_icon="👗", layout="centered")

st.title("👗 AI Stylingadvies op basis van kledinglink")
st.write("Plak een link naar een kledingstuk, beantwoord een paar korte vragen, en ontvang persoonlijk kledingadvies.")

# --- Formulier ---
with st.form("kledingadvies_form"):
    link = st.text_input("🔗 Plak hier de link naar het kledingstuk")

    lichaamsvorm = st.selectbox("👤 Wat is je lichaamsvorm?", ["Zandloper", "Peer", "Rechthoek", "Appel", "Weet ik niet"])
    huidskleur = st.selectbox("🎨 Wat is je huidskleur?", ["Licht", "Medium", "Donker"])
    lengte = st.selectbox("📏 Hoe lang ben je?", ["< 1.60m", "1.60 - 1.75m", "> 1.75m"])
    gelegenheid = st.selectbox("🎯 Voor welke gelegenheid wil je dit dragen?", ["Werk", "Feest", "Vrije tijd", "Bruiloft", "Date"])
    gevoel = st.selectbox("🧠 Hoe wil je je voelen in deze outfit?", ["Zelfverzekerd", "Speels", "Elegant", "Casual", "Trendy"])

    submitted = st.form_submit_button("Vraag AI om advies")

# --- Prompt genereren en versturen ---
if submitted and link:
    with st.spinner("AI is je persoonlijke stylingadvies aan het genereren..."):
        prompt = f"""
        Geef gepersonaliseerd kledingadvies op basis van het volgende kledingstuk: {link}.
        De gebruiker heeft een {lichaamsvorm.lower()} figuur, een {huidskleur.lower()} huidskleur en is {lengte} lang.
        Het kledingstuk wordt overwogen voor een {gelegenheid.lower()} en de gebruiker wil zich {gevoel.lower()} voelen.

        Geef:
        - Een beoordeling van het kledingstuk voor dit profiel
        - Tips voor styling en kleurcombinaties
        - Suggesties voor accessoires of schoenen
        - Eventueel 2 alternatieve stijlen
        """
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Je bent een ervaren fashion stylist."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=700,
            )
            advies = resp.choices[0].message.content
            st.markdown("### 👠 Jouw AI-stylingadvies")
            st.write(advies)
        except Exception as e:
            st.error(f"Er ging iets mis bij het ophalen van stylingadvies: {e}")

# --- Tip/voetnoot ---
st.caption("💡 Deze demo gebruikt het model gpt-4o-mini. Pas dit aan als je een ander model wilt.")