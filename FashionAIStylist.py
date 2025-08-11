import random
import streamlit as st

# Voorbeeld openingszinnen
openings = [
    "Looks nice!",
    "Wow!",
    "Stylish pick!",
    "Love it!",
    "That’s bold!"
]

# Simulatie van itemnaam (in de echte app haal je deze uit de link)
item_name = "black chunky sneakers"

# Korte AI-advieszin (in de echte app komt dit uit je AI-output)
short_advice = "perfect for casual and streetwear looks."

# Random opening kiezen
opening_text = random.choice(openings)

# Tekstballon renderen (licht transparant via CSS)
st.markdown("""
    <style>
    .speech-bubble {
        background: rgba(255,255,255,0.6);
        border-radius: 12px;
        padding: 12px 16px;
        font-size: 1.1em;
        font-weight: 500;
        max-width: 400px;
    }
    </style>
""", unsafe_allow_html=True)

# Dynamische tekst plaatsen
st.markdown(
    f"<div class='speech-bubble'>{opening_text} This {item_name} is {short_advice}</div>",
    unsafe_allow_html=True
)
