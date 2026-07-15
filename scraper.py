import csv
import requests
import sqlite3
import re
from bs4 import BeautifulSoup

def extraire_specs(description):
    specs = {}

    ecran = re.search(r'(\d+\.?\d*)"', description)
    specs["ecran"] = float(ecran.group(1)) if ecran else None

    # RAM : toujours le premier GB mentionné
    ram_matches = re.findall(r'(\d+)GB', description)
    specs["ram"] = int(ram_matches[0]) if ram_matches else None

    # Stockage : priorité au TB s'il existe (1TB = 1000GB)
    stockage_tb = re.search(r'(\d+)TB', description)
    if stockage_tb:
        specs["stockage"] = int(stockage_tb.group(1)) * 1000
    elif len(ram_matches) > 1:
        # 2e GB trouvé, uniquement si ce n'est pas la VRAM d'une carte graphique
        # (on vérifie qu'il n'est pas juste avant "GB" collé à un nom de GPU connu)
        if not re.search(r'(Radeon|GeForce|GTX|Intel HD).{0,10}' + ram_matches[1] + r'GB', description):
            specs["stockage"] = int(ram_matches[1])
        else:
            specs["stockage"] = None
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
def creer_base():
    connexion = sqlite3.connect("produits.db")
    curseur = connexion.cursor()

    curseur.execute("""
        CREATE TABLE IF NOT EXISTS produits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            prix REAL NOT NULL,
            marque TEXT,
            ecran REAL,
            ram INTEGER,
            stockage INTEGER,
            description TEXT,
            site TEXT,
            UNIQUE(nom, site)
        )
    """)

    connexion.commit()
    connexion.close()
    print("✅ Base de données 'produits.db' prête")
def sauvegarder_bdd(produits, nom_site):
    connexion = sqlite3.connect("produits.db")
    curseur = connexion.cursor()

    for p in produits:
        curseur.execute("""
            INSERT OR REPLACE INTO produits (nom, prix, marque, ecran, ram, stockage, description, site)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (p["nom"], p["prix"], p["marque"], p["ecran"], p["ram"], p["stockage"], p["description"], nom_site))

    connexion.commit()
    connexion.close()
    print(f"✅ {len(produits)} produits synchronisés dans la base (site : {nom_site})")
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
# --- Sauvegarde des résultats en CSV ---
def sauvegarder_csv(produits, nom_fichier):
    with open(nom_fichier, mode="w", newline="", encoding="utf-8") as fichier:
        writer = csv.writer(fichier)
        # Ligne d'en-tête
        writer.writerow(["nom", "prix", "marque", "ecran", "ram", "stockage", "description"])
        # Une ligne par produit
        for p in produits:
            writer.writerow([
                p["nom"], p["prix"], p["marque"],
                p["ecran"], p["ram"], p["stockage"], p["description"]
            ])
    print(f"\n✅ {len(produits)} produits sauvegardés dans '{nom_fichier}'")

sauvegarder_csv(site_a, "produits_site_a.csv")
sauvegarder_csv(site_b, "produits_site_b.csv")
creer_base()
sauvegarder_bdd(site_a, "Site A")
sauvegarder_bdd(site_b, "Site B")