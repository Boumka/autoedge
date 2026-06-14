"""
AutoEdge — invoer.py
Pagina voor handmatige invoer van advertenties.
Wordt geïmporteerd in app.py als extra pagina.
"""

import streamlit as st
from datetime import date
import db
import scoring


def toon_invoer_pagina():
    st.markdown("### ➕ Advertentie handmatig invoeren")
    st.caption("Vind je een interessante wagen op 2dehands.be of Autovlan? "
               "Voer de gegevens hier in en AutoEdge berekent meteen de deal-score.")

    st.divider()

    # ─── FORMULIER ───────────────────────────────────────────────────────────

    col1, col2 = st.columns(2)

    with col1:
        merk = st.text_input("Merk *", placeholder="bv. VW, BMW, Toyota")
        bouwjaar = st.number_input("Bouwjaar *", min_value=2000, max_value=2025,
                                   value=2018, step=1)
        brandstof = st.selectbox("Brandstof",
                                 ["benzine", "diesel", "hybride", "elektrisch", "lpg"])
        regio = st.text_input("Regio", placeholder="bv. Gent, Antwerpen, Brussel")

    with col2:
        model = st.text_input("Model *", placeholder="bv. Golf, 3-reeks, Yaris")
        km = st.number_input("Kilometerstand *", min_value=0, max_value=500000,
                             value=80000, step=1000)
        transmissie = st.selectbox("Transmissie", ["manueel", "automaat"])
        prijs = st.number_input("Vraagprijs (€) *", min_value=500, max_value=200000,
                                value=12000, step=500)

    url = st.text_input("Link naar advertentie",
                        placeholder="https://www.2dehands.be/...")

    beschrijving = st.text_area("Beschrijving advertentie",
                                placeholder="Kopieer hier de beschrijving van de advertentie...",
                                height=120)

    online_sinds = st.date_input("Online sinds", value=date.today())
    dagen_online = (date.today() - online_sinds).days

    st.markdown("")

    # ─── BEREKENEN ───────────────────────────────────────────────────────────

    if st.button("🔍 Bereken deal-score", type="primary", use_container_width=True):

        if not merk or not model or not prijs or not km:
            st.error("Vul minstens merk, model, kilometerstand en prijs in.")
            return

        # Score berekenen
        score = scoring.deal_score({
            "merk":         merk,
            "model":        model,
            "bouwjaar":     bouwjaar,
            "km":           km,
            "prijs":        prijs,
            "beschrijving": beschrijving,
            "dagen_online": dagen_online,
        })

        # Resultaat tonen
        st.divider()
        st.markdown("#### 📊 Resultaat")

        kleur_map = {
            "Uitstekende deal": "🟢",
            "Goede deal":       "🟡",
            "Marktconform":     "🟠",
            "Opgepast":         "🔴",
        }
        icoon = kleur_map.get(score["verdict"], "⚪")

        col_score, col_info = st.columns([1, 2])

        with col_score:
            st.metric("Deal-score", f"{score['deal_score']}/100")
            st.markdown(f"**{icoon} {score['verdict']}**")

        with col_info:
            st.metric("Marktwaarde", f"€{score['marktwaarde']:,.0f}")
            afwijking = score["prijs_afwijking_pct"]
            teken = "▼" if afwijking >= 0 else "▲"
            kleur = "green" if afwijking >= 0 else "red"
            st.markdown(
                f'<p>Verschil met markt: '
                f'<span style="color:{kleur};font-weight:bold;">'
                f'{teken} {abs(afwijking):.1f}%</span></p>',
                unsafe_allow_html=True,
            )
            winst = score["winst_potentieel"]
            st.metric("Winstpotentieel (flip)",
                      f"€{winst:,.0f}" if winst > 0 else "Negatief")

        # Score-opbouw
        st.markdown("#### Score-opbouw")
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Prijs", f"{score['score_prijs']}/40")
        col_b.metric("Km-stand", f"{score['score_km']}/25")
        col_c.metric("Staat", f"{score['score_staat']}/20")
        col_d.metric("Urgentie", f"{score['score_urgentie']}/15")

        # Risicovlaggen
        st.markdown("#### Signalen")
        for vlag in score["risico_vlaggen"]:
            st.markdown(f"- {vlag}")

        # Opslaan in database
        st.divider()
        if st.button("💾 Opslaan in database", use_container_width=True):
            _sla_op(merk, model, bouwjaar, km, prijs, brandstof,
                    transmissie, regio, beschrijving, url, dagen_online, score)


def _sla_op(merk, model, bouwjaar, km, prijs, brandstof,
            transmissie, regio, beschrijving, url, dagen_online, score):
    """Slaat de advertentie en score op in de database."""
    import uuid
    external_id = f"MANUEEL-{uuid.uuid4().hex[:8].upper()}"

    result = db.fetchone("""
        INSERT INTO listings (
            source, external_id, merk, model, bouwjaar, km, prijs,
            brandstof, transmissie, regio, beschrijving, url,
            online_sinds
        ) VALUES (
            'manueel', %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            NOW() - INTERVAL '%s days'
        )
        RETURNING id
    """, (
        external_id, merk, model, bouwjaar, km, prijs,
        brandstof, transmissie, regio, beschrijving, url,
        dagen_online,
    ))

    if result:
        scoring.sla_score_op(str(result["id"]), score)
        st.success(f"✓ Opgeslagen! {merk} {model} staat nu in je dashboard.")
        # Cache wissen zodat dashboard ververst
        st.cache_data.clear()
    else:
        st.error("Opslaan mislukt — probeer opnieuw.")
