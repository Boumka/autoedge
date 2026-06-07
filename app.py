"""
AutoEdge — app.py
Streamlit dashboard voor het bekijken van deal-scores.
Opstarten met: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import db

# ─── PAGINA-INSTELLINGEN ─────────────────────────────────────────────────────

st.set_page_config(
    page_title="AutoEdge",
    page_icon="🚗",
    layout="wide",
)

# ─── STIJL ───────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .score-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 14px;
    }
    .uitstekend  { background: #EAF3DE; color: #27500A; }
    .goed        { background: #E1F5EE; color: #085041; }
    .marktconform{ background: #FAEEDA; color: #633806; }
    .opgepast    { background: #FCEBEB; color: #791F1F; }
    .metric-card {
        background: #F8F8F8;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ─── DATA LADEN ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def laad_listings():
    rijen = db.fetchall("""
        SELECT
            l.id,
            l.merk,
            l.model,
            l.bouwjaar,
            l.km,
            l.prijs,
            l.brandstof,
            l.transmissie,
            l.regio,
            l.beschrijving,
            l.url,
            l.online_sinds,
            s.deal_score,
            s.marktwaarde,
            s.prijs_afwijking_pct,
            s.winst_potentieel,
            s.score_prijs,
            s.score_km,
            s.score_staat,
            s.score_urgentie,
            s.risico_vlaggen
        FROM listings l
        JOIN scores s ON s.listing_id = l.id
        WHERE l.actief = TRUE
        ORDER BY s.deal_score DESC
    """)
    return pd.DataFrame(rijen)


def score_kleur(score):
    if score >= 75: return "uitstekend"
    if score >= 55: return "goed"
    if score >= 35: return "marktconform"
    return "opgepast"


def score_verdict(score):
    if score >= 75: return "Uitstekende deal"
    if score >= 55: return "Goede deal"
    if score >= 35: return "Marktconform"
    return "Opgepast"


# ─── HEADER ──────────────────────────────────────────────────────────────────

col_logo, col_titel = st.columns([1, 8])
with col_logo:
    st.markdown("## 🚗")
with col_titel:
    st.markdown("## AutoEdge")
    st.caption("TradingView voor Belgische occasiewagens")

st.divider()

# ─── DATA LADEN ──────────────────────────────────────────────────────────────

df = laad_listings()

if df.empty:
    st.warning("Geen advertenties gevonden. Voer eerst `python testdata.py` uit.")
    st.stop()

# ─── SIDEBAR FILTERS ─────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🔍 Filters")

    merken = ["Alle"] + sorted(df["merk"].dropna().unique().tolist())
    merk_filter = st.selectbox("Merk", merken)

    min_score = st.slider("Minimum deal-score", 0, 100, 0, step=5)

    prijs_max = st.number_input(
        "Maximum prijs (€)",
        min_value=0,
        max_value=100000,
        value=int(df["prijs"].max()) if not df.empty else 50000,
        step=500,
    )

    km_max = st.number_input(
        "Maximum km-stand",
        min_value=0,
        max_value=300000,
        value=200000,
        step=5000,
    )

    brandstof_opties = ["Alle"] + sorted(df["brandstof"].dropna().unique().tolist())
    brandstof_filter = st.selectbox("Brandstof", brandstof_opties)

    st.divider()
    st.caption(f"📊 {len(df)} advertenties in database")

# ─── FILTERS TOEPASSEN ───────────────────────────────────────────────────────

gefilterd = df.copy()

if merk_filter != "Alle":
    gefilterd = gefilterd[gefilterd["merk"] == merk_filter]

gefilterd = gefilterd[gefilterd["deal_score"] >= min_score]
gefilterd = gefilterd[gefilterd["prijs"] <= prijs_max]
gefilterd = gefilterd[gefilterd["km"] <= km_max]

if brandstof_filter != "Alle":
    gefilterd = gefilterd[gefilterd["brandstof"] == brandstof_filter]

# ─── STATISTIEKEN ────────────────────────────────────────────────────────────

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Gevonden", f"{len(gefilterd)} wagens")
with col2:
    if not gefilterd.empty:
        st.metric("Beste score", f"{int(gefilterd['deal_score'].max())}/100")
with col3:
    if not gefilterd.empty:
        st.metric("Gem. prijs", f"€{gefilterd['prijs'].mean():,.0f}")
with col4:
    if not gefilterd.empty:
        goede_deals = len(gefilterd[gefilterd["deal_score"] >= 55])
        st.metric("Goede deals", f"{goede_deals} wagens")

st.divider()

# ─── LIJST OF DETAIL ─────────────────────────────────────────────────────────

if "geselecteerd_id" not in st.session_state:
    st.session_state.geselecteerd_id = None

if st.session_state.geselecteerd_id:
    # ── DETAILPAGINA ──────────────────────────────────────────────────────────

    if st.button("← Terug naar lijst"):
        st.session_state.geselecteerd_id = None
        st.rerun()

    rij = df[df["id"].astype(str) == st.session_state.geselecteerd_id]
    if rij.empty:
        st.error("Advertentie niet gevonden.")
        st.stop()

    w = rij.iloc[0]
    kleur = score_kleur(w["deal_score"])
    verdict = score_verdict(w["deal_score"])

    st.markdown(f"## {w['merk']} {w['model']} ({w['bouwjaar']})")
    st.markdown(
        f'<span class="score-pill {kleur}">{verdict} — {int(w["deal_score"])}/100</span>',
        unsafe_allow_html=True,
    )
    st.markdown("")

    col_links, col_rechts = st.columns([3, 2])

    with col_links:
        st.markdown("#### 📋 Advertentiedetails")
        detail_data = {
            "Vraagprijs":   f"€{w['prijs']:,.0f}",
            "Km-stand":     f"{int(w['km']):,} km",
            "Bouwjaar":     int(w["bouwjaar"]),
            "Brandstof":    w["brandstof"],
            "Transmissie":  w["transmissie"],
            "Regio":        w["regio"],
        }
        for label, waarde in detail_data.items():
            c1, c2 = st.columns([2, 3])
            c1.markdown(f"**{label}**")
            c2.markdown(str(waarde))

        st.markdown("#### 📝 Beschrijving")
        st.markdown(w["beschrijving"] if w["beschrijving"] else "_Geen beschrijving_")

    with col_rechts:
        st.markdown("#### 💰 Analyse")

        marktwaarde = float(w["marktwaarde"]) if w["marktwaarde"] else 0
        prijs = float(w["prijs"])
        afwijking = float(w["prijs_afwijking_pct"]) if w["prijs_afwijking_pct"] else 0
        winst = float(w["winst_potentieel"]) if w["winst_potentieel"] else 0

        st.metric("Marktwaarde", f"€{marktwaarde:,.0f}")
        kleur_delta = "normal" if afwijking >= 0 else "inverse"
        st.metric(
            "Verschil met markt",
            f"€{abs(marktwaarde - prijs):,.0f}",
            delta=f"{afwijking:.1f}%",
            delta_color=kleur_delta,
        )
        st.metric(
            "Winstpotentieel (flip)",
            f"€{winst:,.0f}" if winst > 0 else "Negatief",
        )

        st.markdown("#### 📊 Score-opbouw")
        score_data = {
            "Prijs (max 40)":    int(w["score_prijs"]) if w["score_prijs"] else 0,
            "Km-stand (max 25)": int(w["score_km"]) if w["score_km"] else 0,
            "Staat (max 20)":    int(w["score_staat"]) if w["score_staat"] else 0,
            "Urgentie (max 15)": int(w["score_urgentie"]) if w["score_urgentie"] else 0,
        }
        maxima = [40, 25, 20, 15]
        for (label, waarde), maximum in zip(score_data.items(), maxima):
            st.markdown(f"**{label}**: {waarde}/{maximum}")
            st.progress(waarde / maximum)

        st.markdown("#### 🚩 Risicovlaggen")
        vlaggen = w["risico_vlaggen"] if w["risico_vlaggen"] else []
        for vlag in vlaggen:
            st.markdown(f"- {vlag}")

else:
    # ── LIJSTOVERZICHT ────────────────────────────────────────────────────────

    st.markdown(f"### Gevonden wagens ({len(gefilterd)})")

    if gefilterd.empty:
        st.info("Geen wagens gevonden met deze filters.")
    else:
        for _, rij in gefilterd.iterrows():
            kleur = score_kleur(rij["deal_score"])
            verdict = score_verdict(rij["deal_score"])

            with st.container():
                col_score, col_info, col_prijs, col_actie = st.columns([1, 4, 2, 1])

                with col_score:
                    st.markdown(
                        f'<div style="text-align:center; padding-top:8px;">'
                        f'<span class="score-pill {kleur}">{int(rij["deal_score"])}</span>'
                        f'<br><small style="color:#888">{verdict[:8]}...</small></div>',
                        unsafe_allow_html=True,
                    )

                with col_info:
                    st.markdown(
                        f"**{rij['merk']} {rij['model']}** ({int(rij['bouwjaar'])})"
                    )
                    st.caption(
                        f"🔋 {rij['brandstof']}  •  ⚙️ {rij['transmissie']}  "
                        f"•  📍 {rij['regio']}  •  {int(rij['km']):,} km"
                    )

                with col_prijs:
                    marktwaarde = float(rij["marktwaarde"]) if rij["marktwaarde"] else 0
                    st.markdown(f"**€{float(rij['prijs']):,.0f}**")
                    afwijking = float(rij["prijs_afwijking_pct"]) if rij["prijs_afwijking_pct"] else 0
                    kleur_tekst = "green" if afwijking >= 0 else "red"
                    teken = "▼" if afwijking >= 0 else "▲"
                    st.markdown(
                        f'<small style="color:{kleur_tekst}">{teken} {abs(afwijking):.1f}% vs markt</small>',
                        unsafe_allow_html=True,
                    )

                with col_actie:
                    if st.button("Detail →", key=f"btn_{rij['id']}"):
                        st.session_state.geselecteerd_id = str(rij["id"])
                        st.rerun()

                st.divider()
