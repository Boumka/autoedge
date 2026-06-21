import httpx
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept":     "text/html",
    "Referer":    "https://www.2dehands.be/",
}

url = "https://www.2dehands.be/v/auto-s/bmw/m2379821961-bmw-316i-compact"
r = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
print("Status:", r.status_code)
print("Lengte:", len(r.text))

km_matches = re.findall(r'\d{1,3}[\.\s]?\d{3}\s*km', r.text, re.IGNORECASE)
print("KM matches:", km_matches[:10])

jaar_matches = re.findall(r'\b(19[89][0-9]|20[0-2][0-9])\b', r.text)
print("Jaar matches:", set(jaar_matches))

# Print eerste 2000 chars om te zien wat er werkelijk staat
print("\n--- EERSTE 2000 KARAKTERS ---")
print(r.text[:2000])

print("\n--- ZOEKEN NAAR KENMERKEN BLOK ---")
import re

# Zoek context rond 'Kilometerstand'
idx = r.text.find("Kilometerstand")
if idx > -1:
    print("Context rond 'Kilometerstand':")
    print(r.text[idx-50:idx+200])
else:
    print("'Kilometerstand' niet gevonden in HTML")

idx2 = r.text.find("Bouwjaar")
if idx2 > -1:
    print("\nContext rond 'Bouwjaar':")
    print(r.text[idx2-50:idx2+200])
else:
    print("'Bouwjaar' niet gevonden in HTML")

print("\n--- ZOEKEN NAAR MILEAGE BLOK ---")
idx3 = r.text.find("mileage")
if idx3 > -1:
    print(r.text[idx3:idx3+500])

print("\n--- TEST REGEX MATCH ---")
import re
bouwjaar_match = re.search(
    r'CarAttributesMainGroup-label">Bouwjaar</div>'
    r'<div class="CarAttributesMainGroup-value">\s*(\d{4})',
    r.text
)
print("Bouwjaar match:", bouwjaar_match)
if bouwjaar_match:
    print("Waarde:", bouwjaar_match.group(1))

km_match = re.search(
    r'CarAttributesMainGroup-label">Kilometerstand</div>'
    r'<div class="CarAttributesMainGroup-value">\s*([\d.,\s]+)',
    r.text
)
print("KM match:", km_match)
if km_match:
    print("Waarde:", km_match.group(1))

# Print de exacte rauwe tekst rond Bouwjaar nogmaals, met repr() om verborgen karakters te zien
idx = r.text.find("Bouwjaar")
print("\nRAW (repr) rond Bouwjaar:")
print(repr(r.text[idx-30:idx+150]))
