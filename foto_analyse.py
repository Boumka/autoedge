"""
AutoEdge — foto_analyse.py
Analyseert foto's van wagens via Google Gemini Vision.
Detecteert schade, krassen, roest en beoordeelt de algemene staat.

Gebruik:
  python foto_analyse.py foto.jpg
  Of geïmporteerd in app.py via toon_foto_pagina()
"""

import os
import base64
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# ─── GEMINI CLIENT ───────────────────────────────────────────────────────────

def get_gemini_client():
    """Maakt een Gemini client aan."""
    from google import genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY niet gevonden in .env")
    return genai.Client(api_key=api_key)


# ─── PROMPTS ─────────────────────────────────────────────────────────────────

ANALYSE_PROMPT = """
Je bent een expert autokeuring-inspecteur. Analyseer deze foto van een tweedehands wagen.

Geef een gedetailleerde analyse in het Nederlands met:

1. **ALGEMENE STAAT** (uitstekend/goed/matig/slecht)
   - Eerste indruk van de carrosserie

2. **GEDETECTEERDE SCHADE**
   - Krassen (locatie en ernst)
   - Deuken (locatie en ernst)
   - Roest (locatie en ernst)
   - Overschildering of herstelde schade
   - Andere zichtbare problemen

3. **POSITIEVE PUNTEN**
   - Wat ziet er goed uit

4. **RISICO-INDICATOREN**
   - Tekenen die wijzen op een verborgen probleem
   - Verdachte elementen

5. **STAAT-SCORE** (0-100)
   - 90-100: Nieuwstaat
   - 70-89: Uitstekend
   - 50-69: Goed
   - 30-49: Matig
   - 0-29: Slecht

6. **AANBEVELINGEN**
   - Wat te controleren bij bezichtiging
   - Welke kosten je kunt verwachten

Wees concreet en praktisch. Vermeld altijd onzekerheid als iets niet duidelijk zichtbaar is.
"""

VERGELIJK_PROMPT = """
Je bent een expert autokeuring-inspecteur. Vergelijk deze {n} foto's van dezelfde wagen.

Geef een gecombineerde analyse in het Nederlands:

1. **OVERALL STAAT** (uitstekend/goed/matig/slecht)

2. **SCHADE PER ZONE**
   - Voorzijde
   - Achterzijde  
   - Linkerzijde
   - Rechterzijde
   - Interieur (indien zichtbaar)

3. **MEEST ZORGWEKKENDE BEVINDINGEN**

4. **POSITIEVE PUNTEN**

5. **GEMIDDELDE STAAT-SCORE** (0-100)

6. **KOOPADVIES**
   - Is dit een veilige aankoop?
   - Wat zijn de verwachte herstelkosten?
   - Onderhandelingsargumenten op basis van de staat

Wees eerlijk en objectief.
"""


# ─── ANALYSE FUNCTIES ────────────────────────────────────────────────────────

def analyseer_foto(foto_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """
    Analyseert één foto via Gemini Vision.
    
    Parameters:
        foto_bytes: Foto als bytes
        mime_type: MIME type van de foto (image/jpeg, image/png, etc.)
    
    Returns:
        dict met analyse, score en samenvatting
    """
    try:
        from google import genai
        from google.genai import types

        client = get_gemini_client()

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=foto_bytes, mime_type=mime_type),
                ANALYSE_PROMPT
            ]
        )

        tekst = response.text

        # Staat-score extraheren uit de tekst
        score = _extraheer_score(tekst)
        staat = _score_naar_staat(score)

        return {
            "succes":    True,
            "analyse":   tekst,
            "score":     score,
            "staat":     staat,
            "fout":      None,
        }

    except Exception as e:
        return {
            "succes":  False,
            "analyse": None,
            "score":   None,
            "staat":   None,
            "fout":    str(e),
        }


def analyseer_meerdere_fotos(fotos: list) -> dict:
    """
    Analyseert meerdere foto's van dezelfde wagen.
    
    Parameters:
        fotos: Lijst van (bytes, mime_type) tuples
    
    Returns:
        dict met gecombineerde analyse
    """
    try:
        from google import genai
        from google.genai import types

        client = get_gemini_client()

        # Bouw inhoud op met alle foto's
        inhoud = []
        for foto_bytes, mime_type in fotos:
            inhoud.append(types.Part.from_bytes(
                data=foto_bytes,
                mime_type=mime_type
            ))

        inhoud.append(VERGELIJK_PROMPT.format(n=len(fotos)))

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=inhoud
        )

        tekst = response.text
        score = _extraheer_score(tekst)
        staat = _score_naar_staat(score)

        return {
            "succes":         True,
            "analyse":        tekst,
            "score":          score,
            "staat":          staat,
            "aantal_fotos":   len(fotos),
            "fout":           None,
        }

    except Exception as e:
        return {
            "succes":       False,
            "analyse":      None,
            "score":        None,
            "staat":        None,
            "aantal_fotos": len(fotos),
            "fout":         str(e),
        }


def analyseer_foto_url(url: str) -> dict:
    """Analyseert een foto via URL."""
    try:
        import httpx
        response = httpx.get(url, timeout=15)
        mime_type = response.headers.get("content-type", "image/jpeg").split(";")[0]
        return analyseer_foto(response.content, mime_type)
    except Exception as e:
        return {"succes": False, "analyse": None, "score": None, "staat": None, "fout": str(e)}


# ─── HULPFUNCTIES ────────────────────────────────────────────────────────────

def _extraheer_score(tekst: str) -> int:
    """Extraheert de staat-score uit de analyse tekst."""
    import re
    # Zoek patronen zoals "Score: 75", "75/100", "staat-score: 75"
    patronen = [
        r'staat[- ]score[:\s]+(\d{1,3})',
        r'score[:\s]+(\d{1,3})/100',
        r'(\d{1,3})/100',
        r'score[:\s]+(\d{1,3})',
    ]
    for patroon in patronen:
        match = re.search(patroon, tekst.lower())
        if match:
            score = int(match.group(1))
            if 0 <= score <= 100:
                return score
    return 50  # standaard als niet gevonden


def _score_naar_staat(score: int) -> str:
    """Converteert een score naar een staat-label."""
    if score >= 90:   return "Nieuwstaat"
    elif score >= 70: return "Uitstekend"
    elif score >= 50: return "Goed"
    elif score >= 30: return "Matig"
    else:             return "Slecht"


def foto_naar_bytes(pad: str) -> tuple:
    """Laadt een foto van schijf en geeft bytes + mime_type terug."""
    pad = Path(pad)
    extensie = pad.suffix.lower()
    mime_map = {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
        ".gif":  "image/gif",
    }
    mime_type = mime_map.get(extensie, "image/jpeg")
    with open(pad, "rb") as f:
        return f.read(), mime_type


# ─── STREAMLIT PAGINA ────────────────────────────────────────────────────────

def toon_foto_pagina():
    """Streamlit pagina voor foto-analyse."""
    import streamlit as st

    st.markdown("### 📸 Foto-analyse")
    st.caption("Upload foto's van een wagen en AI analyseert automatisch de staat, "
               "schade en risico's.")

    st.divider()

    # Upload
    fotos = st.file_uploader(
        "Upload foto's van de wagen",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="Upload meerdere foto's voor een completere analyse (voor, achter, zijkanten)"
    )

    if not fotos:
        st.info("Upload minimaal één foto om te beginnen.")
        return

    # Foto's tonen
    st.markdown(f"**{len(fotos)} foto('s) geselecteerd**")
    cols = st.columns(min(len(fotos), 4))
    for i, foto in enumerate(fotos[:4]):
        with cols[i]:
            st.image(foto, use_column_width=True)

    if len(fotos) > 4:
        st.caption(f"+ {len(fotos) - 4} foto('s) meer")

    st.divider()

    if st.button("🔍 Analyseer foto's", type="primary", use_container_width=True):
        with st.spinner("AI analyseert de foto's... dit duurt 10-20 seconden"):
            try:
                # Foto's inladen
                foto_data = []
                for foto in fotos:
                    bytes_data = foto.read()
                    mime_type = f"image/{foto.name.split('.')[-1].lower()}"
                    if mime_type == "image/jpg":
                        mime_type = "image/jpeg"
                    foto_data.append((bytes_data, mime_type))

                # Analyse uitvoeren
                if len(foto_data) == 1:
                    resultaat = analyseer_foto(foto_data[0][0], foto_data[0][1])
                else:
                    resultaat = analyseer_meerdere_fotos(foto_data)

                if not resultaat["succes"]:
                    st.error(f"Analyse mislukt: {resultaat['fout']}")
                    return

                # Resultaat tonen
                st.divider()
                st.markdown("#### 📊 Analyseresultaat")

                col1, col2 = st.columns(2)
                with col1:
                    score = resultaat["score"]
                    kleur = "🟢" if score >= 70 else "🟡" if score >= 50 else "🔴"
                    st.metric("Staat-score", f"{score}/100")
                    st.markdown(f"**{kleur} {resultaat['staat']}**")
                with col2:
                    if len(fotos) > 1:
                        st.metric("Geanalyseerde foto's", len(fotos))

                st.markdown("#### 🔍 Gedetailleerde analyse")
                st.markdown(resultaat["analyse"])

                # Impact op deal-score
                st.divider()
                st.markdown("#### 💡 Impact op deal-score")
                if score >= 70:
                    st.success("Goede staat — positief effect op deal-score")
                elif score >= 50:
                    st.warning("Matige staat — neutrale impact op deal-score")
                else:
                    st.error("Slechte staat — negatief effect op deal-score. "
                             "Onderhandel over de prijs!")

            except Exception as e:
                st.error(f"Fout: {e}")


# ─── COMMAND LINE TEST ───────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoEdge foto-analyse")
    parser.add_argument("foto", nargs="?", help="Pad naar foto")
    args = parser.parse_args()

    if args.foto:
        print(f"\nAnalyseren: {args.foto}")
        foto_bytes, mime_type = foto_naar_bytes(args.foto)
        resultaat = analyseer_foto(foto_bytes, mime_type)
        if resultaat["succes"]:
            print(f"\nStaat: {resultaat['staat']} ({resultaat['score']}/100)")
            print(f"\n{resultaat['analyse']}")
        else:
            print(f"Fout: {resultaat['fout']}")
    else:
        print("Gebruik: python foto_analyse.py foto.jpg")
        print("Of importeer toon_foto_pagina() in app.py")
