"""
AutoEdge — login.py
Login pagina met e-mail/wachtwoord + Google SSO (na hosting).
"""

import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")


def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def check_url_token():
    """Vangt het OAuth token op uit de URL parameters na Google login."""
    try:
        params = st.query_params
        if "access_token" in params:
            supabase = get_supabase()
            supabase.auth.set_session(
                params["access_token"],
                params.get("refresh_token", "")
            )
            st.query_params.clear()
            return True
    except Exception:
        pass
    return False


def check_sessie():
    """Controleert of de gebruiker ingelogd is via session_state."""
    if "user" in st.session_state and st.session_state["user"]:
        return st.session_state["user"]
    return None


def toon_login_pagina():
    """Toont de login pagina met e-mail/wachtwoord."""
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 3rem;">🚗</h1>
        <h2 style="font-size: 2rem; font-weight: 600;">AutoEdge</h2>
        <p style="color: gray; font-size: 1.1rem;">TradingView voor Belgische occasiewagens</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Inloggen", "Registreren"])

        with tab1:
            st.markdown("")
            email = st.text_input("E-mailadres", key="login_email")
            wachtwoord = st.text_input("Wachtwoord", type="password", key="login_ww")
            st.markdown("")

            if st.button("Inloggen", use_container_width=True, type="primary"):
                if not email or not wachtwoord:
                    st.error("Vul je e-mailadres en wachtwoord in.")
                else:
                    supabase = get_supabase()
                    try:
                        r = supabase.auth.sign_in_with_password({
                            "email": email,
                            "password": wachtwoord
                        })
                        st.session_state["user"] = r.user
                        st.rerun()
                    except Exception:
                        st.error("Verkeerd e-mailadres of wachtwoord.")

        with tab2:
            st.markdown("")
            email_r = st.text_input("E-mailadres", key="reg_email")
            ww_r = st.text_input("Wachtwoord (min. 6 tekens)", type="password", key="reg_ww")
            st.markdown("")

            if st.button("Account aanmaken", use_container_width=True, type="primary"):
                if not email_r or not ww_r:
                    st.error("Vul alle velden in.")
                elif len(ww_r) < 6:
                    st.error("Wachtwoord moet minstens 6 tekens zijn.")
                else:
                    supabase = get_supabase()
                    try:
                        supabase.auth.sign_up({
                            "email": email_r,
                            "password": ww_r
                        })
                        st.success("✓ Account aangemaakt! Controleer je e-mail om te bevestigen.")
                    except Exception as e:
                        st.error(f"Fout: {e}")

        st.markdown("")
        st.caption("Door in te loggen ga je akkoord met onze voorwaarden en privacybeleid.")

    st.markdown("")
    st.divider()

    st.markdown("### Wat krijg je toegang tot?")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 📊 Deal-scores")
        st.caption("AI berekent de marktwaarde en geeft een score van 0-100 voor elke wagen.")
    with col2:
        st.markdown("#### 🔔 Alerts")
        st.caption("Krijg meteen een melding via Telegram als een wagen jouw criteria matcht.")
    with col3:
        st.markdown("#### 🤖 AI Advisor")
        st.caption("Stel vragen in gewone taal en krijg persoonlijk wagenadvies.")


def uitloggen():
    """Logt de gebruiker uit."""
    supabase = get_supabase()
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state.clear()
    st.rerun()
