import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

url = "https://www.boulanger.com/ref/1233474"
response = requests.get(url, headers=HEADERS)
soup = BeautifulSoup(response.text, "html.parser")

scripts = soup.find_all("script", type="application/ld+json")
print(f"{len(scripts)} balises JSON-LD trouvées\n")

for i, s in enumerate(scripts):
    print(f"--- Script {i} (500 premiers caractères) ---")
    print(s.string[:500] if s.string else "(vide)")
    print()
import json

produit_json = json.loads(scripts[2].string)
print(json.dumps(produit_json, indent=2, ensure_ascii=False))