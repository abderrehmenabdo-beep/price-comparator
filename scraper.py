import requests
import re
from bs4 import BeautifulSoup

def extraire_specs(description):
    specs = {}

    ecran = re.search(r'(\d+\.?\d*)"', description)
    specs["ecran"] = float(ecran.group(1)) if ecran else None

    ram_matches = re.findall(r'(\d+)GB', description)
    specs["ram"] = int(ram_matches[0]) if ram_matches else None

    # Stockage : gérer GB et TB (converti en GB pour comparer sur la même unité)
    stockage_gb = re.search(r'(\d+)GB', description[description.find(",", description.find("GB")):]) if ram_matches else None
    stockage_tb = re.search(r'(\d+)TB', description)

    if len(ram_matches) > 1:
        specs["stockage"] = int(ram_matches[1])
    elif stockage_tb:
        specs["stockage"] = int(stockage_tb.group(1)) * 1000  # TB -> GB
    else:
        specs["stockage"] = None

    return specs

def scraper_produits(url):
    response = requests.get(url)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    produits = []
    for bloc in soup.find_all("div", class_="product-wrapper"):
        nom = bloc.find("a", class_="title").text.strip()
        prix = float(bloc.find("h4", class_="price").text.strip().replace("$", ""))
        description_tag = bloc.find("p", class_="description")
        description = description_tag.text.strip() if description_tag else ""

        marque = nom.split()[0]  # ex: "Packard" ou "ThinkPad" — premier mot du nom
        specs = extraire_specs(description)

        produits.append({
            "nom": nom,
            "prix": prix,
            "description": description,
            "marque": marque,
            **specs
        })
    return produits

def score_matching(p1, p2):
    # La marque doit correspondre, sinon on rejette direct le match
    if p1["marque"].lower() != p2["marque"].lower():
        return 0

    score = 0
    total_criteres = 0

    if p1["ecran"] and p2["ecran"]:
        total_criteres += 1
        if abs(p1["ecran"] - p2["ecran"]) <= 0.5:
            score += 1

    if p1["ram"] and p2["ram"]:
        total_criteres += 1
        if p1["ram"] == p2["ram"]:
            score += 1

    if p1["stockage"] and p2["stockage"]:
        total_criteres += 1
        if p1["stockage"] == p2["stockage"]:
            score += 1

    return score / total_criteres if total_criteres > 0 else 0

# --- Comparaison ---
site_a_url = "https://webscraper.io/test-sites/e-commerce/static/computers/laptops"
site_b_url = "https://webscraper.io/test-sites/e-commerce/static/computers/laptops?page=2"

site_a = scraper_produits(site_a_url)
site_b = scraper_produits(site_b_url)

print("=== Détail des specs extraites (Site A) ===\n")
for p in site_a:
    print(f"{p['nom']:20} | Écran: {p['ecran']} | RAM: {p['ram']}GB | Stockage: {p['stockage']}GB")

print("\n=== Correspondances structurées (specs identiques) ===\n")
SEUIL = 0.99  # on exige une correspondance quasi parfaite sur les specs

for p1 in site_a:
    for p2 in site_b:
        score = score_matching(p1, p2)
        if score >= SEUIL:
            moins_cher = "Site A" if p1["prix"] < p2["prix"] else "Site B"
            print(f"'{p1['nom']}' ({p1['prix']}$) <-> '{p2['nom']}' ({p2['prix']}$)")
            print(f"  Specs communes : {p1['ecran']}\" / {p1['ram']}GB RAM / {p1['stockage']}GB stockage")
            print(f"  Meilleure offre : {moins_cher}")
            print("-" * 50)
# --- TEST DE VALIDATION : chaque produit doit matcher avec lui-même ---
print("\n=== Test de validation : auto-comparaison (Site A contre lui-même) ===\n")

tests_reussis = 0
tests_total = len(site_a)

for produit in site_a:
    score = score_matching(produit, produit)
    statut = "✅ OK" if score == 1.0 else "❌ ÉCHEC"
    if score == 1.0:
        tests_reussis += 1
    print(f"{statut} | '{produit['nom']}' matché avec lui-même | Score : {score:.2f}")

print(f"\nRésultat : {tests_reussis}/{tests_total} tests réussis")

if tests_reussis == tests_total:
    print("✅ La logique de matching est cohérente : un produit identique obtient toujours un score parfait.")
else:
    print("⚠️ Certains produits ne matchent pas avec eux-mêmes — il y a un bug à corriger (probablement des specs manquantes/None).")