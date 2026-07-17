import csv
import requests
import sqlite3
import re
import time
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def extraire_specs_rdc(texte):
    specs = {}

    ecran = re.search(r'(\d+\.?\d*)"', texte)
    specs["ecran"] = float(ecran.group(1)) if ecran else None

    ram_matches = re.findall(r'(\d+)\s?Go', texte)
    specs["ram"] = int(ram_matches[0]) if ram_matches else None

    stockage_to = re.search(r'(\d+)\s?To', texte)
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
        if "/p/" in href and href.endswith(".html"):
            if href.startswith("/"):
                href = "https://www.rueducommerce.fr" + href
            liens.add(href)

    return list(liens)

def scraper_fiche_produit(url):
    response = requests.get(url, headers=HEADERS)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    h1 = soup.find("h1")
    h2 = soup.find("h2")

    if not h1 or not h2:
        return None

    nom = h1.text.strip()
    description = h2.text.strip()
    marque = nom.split()[0]

    # On cherche le premier prix qui apparaît après le h1 dans l'ordre du document
    pattern_prix = re.compile(r'(\d{1,3}(?:\s\d{3})*,\d{2})\s?€')
    prix = None
    for noeud in h1.find_all_next(string=pattern_prix):
        match = pattern_prix.search(noeud)
        if match:
            prix_texte = match.group(1).replace("\xa0", "").replace(" ", "").replace(",", ".")
            prix = float(prix_texte)
            break

    if prix is None:
        return None

    specs = extraire_specs_rdc(description)

    return {
        "nom": nom,
        "prix": prix,
        "marque": marque,
        "description": description,
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
    url_categorie = "https://www.rueducommerce.fr/r/70151/pc-portable/"

    print("🔎 Récupération des liens produits...")
    liens = scraper_liste_produits(url_categorie)
    print(f"→ {len(liens)} fiches produits trouvées\n")

    produits = []
    for lien in liens[:40]: 
        print(f"Scraping : {lien}")
        produit = scraper_fiche_produit(lien)
        if produit:
            produits.append(produit)
        time.sleep(0.3)

    print(f"\n✅ {len(produits)} produits extraits avec succès\n")
    for p in produits:
        print(f"{p['nom'][:50]:50} | {p['prix']}€ | Écran:{p['ecran']} | RAM:{p['ram']}Go | Stockage:{p['stockage']}Go")

    sauvegarder_csv(produits, "produits_rueducommerce.csv")
    sauvegarder_bdd(produits, "Rue du Commerce")