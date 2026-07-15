import csv
import requests
import sqlite3
import re
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def extraire_specs_grosbill(titre):
    specs = {}

    ecran = re.search(r'(\d+\.?\d*)"', titre)
    specs["ecran"] = float(ecran.group(1)) if ecran else None

    ram_matches = re.findall(r'(\d+)\s?Go', titre)
    specs["ram"] = int(ram_matches[0]) if ram_matches else None

    stockage_to = re.search(r'(\d+)\s?To', titre)
    if stockage_to:
        specs["stockage"] = int(stockage_to.group(1)) * 1000
    elif len(ram_matches) > 1:
        specs["stockage"] = int(ram_matches[1])
    else:
        specs["stockage"] = None

    return specs

def scraper_liste_produits(url_categorie):
    response = requests.get(url_categorie, headers=HEADERS)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    liens = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/pc-portable/" in href and href.endswith(".aspx"):
            if href.startswith("/"):
                href = "https://www.grosbill.com" + href
            liens.add(href)

    return list(liens)

def scraper_fiche_produit(url):
    response = requests.get(url, headers=HEADERS)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    def get_meta(nom_property):
        tag = soup.find("meta", property=nom_property)
        return tag["content"] if tag else None

    marque = get_meta("product:brand")
    prix_str = get_meta("product:price:amount")
    h1 = soup.find("h1")
    titre = h1.text.strip() if h1 else get_meta("og:title")

    if not (marque and prix_str and titre):
        return None

    prix = float(prix_str)
    specs = extraire_specs_grosbill(titre)

    return {
        "nom": titre,
        "prix": prix,
        "marque": marque,
        "description": titre,
        **specs
    }

def sauvegarder_csv(produits, nom_fichier):
    with open(nom_fichier, mode="w", newline="", encoding="utf-8") as fichier:
        writer = csv.writer(fichier)
        writer.writerow(["nom", "prix", "marque", "ecran", "ram", "stockage", "description"])
        for p in produits:
            writer.writerow([
                p["nom"], p["prix"], p["marque"],
                p["ecran"], p["ram"], p["stockage"], p["description"]
            ])
    print(f"✅ {len(produits)} produits sauvegardés dans '{nom_fichier}'")

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


# --- Script principal ---
if __name__ == "__main__":
    url_categorie = "https://www.grosbill.com/pc-portable-40.aspx"

    print("🔎 Récupération des liens produits...")
    liens = scraper_liste_produits(url_categorie)
    print(f"→ {len(liens)} fiches produits trouvées\n")

    produits = []
    for lien in liens[:15]:  # on limite à 15 pour le premier test
        print(f"Scraping : {lien}")
        produit = scraper_fiche_produit(lien)
        if produit:
            produits.append(produit)

    print(f"\n✅ {len(produits)} produits extraits avec succès\n")
    for p in produits:
        print(f"{p['nom'][:50]:50} | {p['prix']}€ | Écran:{p['ecran']} | RAM:{p['ram']}Go | Stockage:{p['stockage']}Go")

    sauvegarder_csv(produits, "produits_grosbill.csv")
    sauvegarder_bdd(produits, "GrosBill")