"""
AutoEdge — ai_chat.py
Streamlit chatinterface voor de AI-agent.
Wordt geïmporteerd in app.py als extra pagina.
"""

import streamlit as st
from ai_agent import chat


def toon_ai_pagina():
    st.markdown("### 🤖 AutoEdge AI Assistent")
    st.caption("Stel vragen in gewone taal over de occasiemarkt. "
               "De assistent heeft toegang tot alle wagens in je database.")

    st.divider()

    # Voorbeeldvragen
    st.markdown("**Voorbeeldvragen:**")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🏆 Beste deals nu", use_container_width=True):
            st.session_state.ai_input = "Wat zijn de beste deals in de database?"
    with col2:
        if st.button("📊 Marktoverzicht", use_container_width=True):
            st.session_state.ai_input = "Geef me een overzicht van de markt"
    with col3:
        if st.button("⚠️ Risicovol", use_container_width=True):
            st.session_state.ai_input = "Welke wagens hebben de meeste risico's?"

    st.divider()

    # Chat geschiedenis initialiseren
    if "ai_berichten" not in st.session_state:
        st.session_state.ai_berichten = []
    if "ai_input" not in st.session_state:
        st.session_state.ai_input = ""

    # Chat geschiedenis tonen
    for bericht in st.session_state.ai_berichten:
        if bericht["role"] == "user":
            with st.chat_message("user"):
                st.markdown(bericht["content"])
        elif bericht["role"] == "assistant":
            with st.chat_message("assistant", avatar="🚗"):
                st.markdown(bericht["content"])

    # Input
    vraag = st.chat_input("Stel een vraag over de occasiemarkt...",
                          key="chat_input")

    # Voorbeeldvraag invullen via knop
    if st.session_state.ai_input and not vraag:
        vraag = st.session_state.ai_input
        st.session_state.ai_input = ""

    if vraag:
        # Gebruikersbericht tonen
        with st.chat_message("user"):
            st.markdown(vraag)

        st.session_state.ai_berichten.append({
            "role": "user", "content": vraag
        })

        # AI antwoord genereren
        with st.chat_message("assistant", avatar="🚗"):
            with st.spinner("Aan het analyseren..."):
                try:
                    antwoord, bijgewerkte_berichten = chat(
                        st.session_state.ai_berichten
                    )
                    st.session_state.ai_berichten = bijgewerkte_berichten
                    st.markdown(antwoord)
                except Exception as e:
                    st.error(f"Fout: {e}")

        st.rerun()

    # Gesprek wissen
    if st.session_state.ai_berichten:
        if st.button("🗑️ Gesprek wissen", use_container_width=True):
            st.session_state.ai_berichten = []
            st.rerun()
