from link_analyse import haal_advertentie_op, extraheer_item_id

url = "https://www.2dehands.be/v/auto-s/bmw/m2379821961-bmw-316i-compact"
raw = haal_advertentie_op(url)

print("Raw resultaat:")
if raw:
    for k, v in raw.items():
        if k == "description":
            print(f"  {k}: {str(v)[:100]}...")
        else:
            print(f"  {k}: {v}")
else:
    print("  None teruggegeven!")
