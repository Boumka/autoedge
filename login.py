"""
AutoEdge — login.py
Login pagina met e-mail/wachtwoord + persistente sessie.
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
    """
    Controleert of de gebruiker ingelogd is.
    Probeert eerst session_state, dan Supabase sessie.
    """
    # 1. Eerst uit session_state
    if "user" in st.session_state and st.session_state["user"]:
        return st.session_state["user"]

    # 2. Dan uit Supabase sessie (persistent over reruns)
    try:
        supabase = get_supabase()
        sessie = supabase.auth.get_session()
        if sessie and sessie.user:
            st.session_state["user"] = sessie.user
            st.session_state["access_token"] = sessie.access_token
            st.session_state["refresh_token"] = sessie.refresh_token
            return sessie.user
    except Exception:
        pass

    return None


def herstel_sessie():
    """Probeert de sessie te herstellen via refresh token."""
    try:
        if "refresh_token" in st.session_state and st.session_state["refresh_token"]:
            supabase = get_supabase()
            r = supabase.auth.refresh_session(st.session_state["refresh_token"])
            if r and r.user:
                st.session_state["user"] = r.user
                st.session_state["access_token"] = r.session.access_token
                st.session_state["refresh_token"] = r.session.refresh_token
                return r.user
    except Exception:
        pass
    return None


def toon_login_pagina():
    """Toont de login pagina met e-mail/wachtwoord."""

    # Logo en titel
    with open("logo.svg", "r") as f:
        svg = f.read()
    st.markdown(
        f'<div style="text-align:center;padding:1rem 0">{svg}</div>',
        unsafe_allow_html=True
    )

    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Inloggen", "Registreren"])

        with tab1:
            st.markdown("")
            email = st.text_input("E-mailadres", key="login_email",
                                  placeholder="jouw@email.com")
            wachtwoord = st.text_input("Wachtwoord", type="password",
                                       key="login_ww", placeholder="••••••••")
            st.markdown("")

            if st.button("Inloggen", use_container_width=True, type="primary", key="btn_login"):
                if not email or not wachtwoord:
                    st.error("Vul je e-mailadres en wachtwoord in.")
                else:
                    with st.spinner("Inloggen..."):
                        supabase = get_supabase()
                        try:
                            r = supabase.auth.sign_in_with_password({
                                "email": email,
                                "password": wachtwoord
                            })
                            if r and r.user:
                                st.session_state["user"] = r.user
                                st.session_state["access_token"] = r.session.access_token
                                st.session_state["refresh_token"] = r.session.refresh_token
                                st.success("✓ Ingelogd!")
                                st.rerun()
                            else:
                                st.error("Inloggen mislukt — probeer opnieuw.")
                        except Exception as e:
                            fout = str(e).lower()
                            if "invalid" in fout or "credentials" in fout:
                                st.error("Verkeerd e-mailadres of wachtwoord.")
                            elif "email" in fout and "confirm" in fout:
                                st.warning("Bevestig eerst je e-mailadres via de link in je inbox.")
                            else:
                                st.error(f"Fout: {e}")

        with tab2:
            st.markdown("")
            email_r = st.text_input("E-mailadres", key="reg_email",
                                    placeholder="jouw@email.com")
            ww_r = st.text_input("Wachtwoord (min. 6 tekens)", type="password",
                                  key="reg_ww", placeholder="••••••••")
            akkoord = st.checkbox(
                "Ik ga akkoord met de [voorwaarden](https://autoedge.streamlit.app) en het [privacybeleid](https://autoedge.streamlit.app)"
            )
            st.markdown("")

            if st.button("Account aanmaken", use_container_width=True,
                         type="primary", key="btn_register"):
                if not email_r or not ww_r:
                    st.error("Vul alle velden in.")
                elif len(ww_r) < 6:
                    st.error("Wachtwoord moet minstens 6 tekens zijn.")
                elif not akkoord:
                    st.error("Ga akkoord met de voorwaarden om te registreren.")
                else:
                    with st.spinner("Account aanmaken..."):
                        supabase = get_supabase()
                        try:
                            supabase.auth.sign_up({
                                "email": email_r,
                                "password": ww_r
                            })
                            st.success(
                                "✓ Account aangemaakt! Controleer je e-mail voor de bevestigingslink."
                            )
                            st.info("Na bevestiging kun je inloggen via het 'Inloggen' tabblad.")
                        except Exception as e:
                            st.error(f"Fout: {e}")

    st.markdown("")
    st.divider()

    # Features preview
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
    for key in ["user", "access_token", "refresh_token"]:
        st.session_state.pop(key, None)
    st.rerun()
