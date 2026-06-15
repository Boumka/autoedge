"""
AutoEdge — langchain_chat.py
Streamlit chatinterface voor de LangChain agent met geheugen.
Vervangt ai_chat.py.
"""

import streamlit as st
from langchain_agent import maak_agent_met_geheugen, chat


def toon_langchain_pagina():
    st.markdown("### 🤖 AutoEdge AI Assistent")
    st.caption(
        "Stel vragen in gewone taal. De assistent onthoudt het gesprek, "
        "zoekt in de database en geeft persoonlijk wagenadvies."
    )

    st.divider()

    # Voorbeeldvragen
    st.markdown("**Snel starten:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔍 Beste deals nu", use_container_width=True):
            st.session_state.lc_input = "Wat zijn de beste deals in de database?"
    with col2:
        if st.button("🎯 Welke wagen past bij mij?", use_container_width=True):
            st.session_state.lc_input = "Help me kiezen welke wagen bij mij past"
    with col3:
        if st.button("📊 Marktoverzicht", use_container_width=True):
            st.session_state.lc_input = "Geef me een overzicht van de markt"

    col4, col5, col6 = st.columns(3)
    with col4:
        if st.button("🚗 Analyseer een wagen", use_container_width=True):
            st.session_state.lc_input = "Analyseer deze wagen: VW Golf 2018, 95.000 km, €14.500"
    with col5:
        if st.button("⚙️ Distributie-info", use_container_width=True):
            st.session_state.lc_input = "Heeft een VW Golf TDI een distributieriem of ketting?"
    with col6:
        if st.button("💡 Koopadvies", use_container_width=True):
            st.session_state.lc_input = "Ik rij 20.000 km per jaar, budget €15.000, wat raad je aan?"

    st.divider()

    # Agent en geheugen initialiseren
    if "lc_agent" not in st.session_state:
        st.session_state.lc_agent = maak_agent_met_geheugen()
    if "lc_berichten" not in st.session_state:
        st.session_state.lc_berichten = []
    if "lc_input" not in st.session_state:
        st.session_state.lc_input = ""

    # Chat geschiedenis tonen
    for bericht in st.session_state.lc_berichten:
        if bericht["rol"] == "gebruiker":
            with st.chat_message("user"):
                st.markdown(bericht["inhoud"])
        else:
            with st.chat_message("assistant", avatar="🚗"):
                st.markdown(bericht["inhoud"])

    # Input
    vraag = st.chat_input("Stel een vraag, plak een link, of beschrijf wat je zoekt...")

    # Voorbeeldvraag via knop
    if st.session_state.lc_input and not vraag:
        vraag = st.session_state.lc_input
        st.session_state.lc_input = ""

    if vraag:
        # Gebruikersbericht tonen
        with st.chat_message("user"):
            st.markdown(vraag)
        st.session_state.lc_berichten.append({"rol": "gebruiker", "inhoud": vraag})

        # AI antwoord
        with st.chat_message("assistant", avatar="🚗"):
            with st.spinner("Aan het analyseren..."):
                antwoord = chat(vraag, st.session_state.lc_agent)
                st.markdown(antwoord)

        st.session_state.lc_berichten.append({"rol": "assistent", "inhoud": antwoord})
        st.rerun()

    # Gesprek wissen
    if st.session_state.lc_berichten:
        st.divider()
        if st.button("🗑️ Nieuw gesprek starten", use_container_width=True):
            st.session_state.lc_berichten = []
            st.session_state.lc_agent = maak_agent_met_geheugen()
            st.rerun()

    # Wat kan de assistent?
    with st.expander("💡 Wat kan de AI-assistent?"):
        st.markdown("""
        **Zoeken & analyseren:**
        - Wagens zoeken op merk, model, prijs, km-stand
        - Deal-score berekenen voor elke wagen
        - Marktwaarde vergelijken

        **Technische info:**
        - Distributieriem of ketting per model
        - Verbruik en betrouwbaarheid per merk
        - Bekende problemen en aandachtspunten

        **Persoonlijk advies:**
        - Welke wagen past bij jouw gebruik?
        - Budget optimaliseren
        - Onderhandelingstips

        **Voorbeeldvragen:**
        - *"Zoek een Golf onder €15.000 met goede score"*
        - *"Heeft een Peugeot 208 1.2 een distributieriem?"*
        - *"Ik rij veel autosnelweg, wat raad je aan?"*
        - *"Analyseer: BMW 3 2018, 110.000 km, €18.500"*
        """)
