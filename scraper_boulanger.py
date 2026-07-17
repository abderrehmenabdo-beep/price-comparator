import csv
import requests
import sqlite3
import re
import json
import html
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def extraire_gpu(texte):
    match = re.search(r'(RTX\s?\d{3,4}(?:\s?Ti)?|GTX\s?\d{3,4}|Radeon\s?\w*\s?\d*)', texte, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).upper().replace(" ", "")

def trouver_valeur_propriete(additional_properties, nom_recherche):
    for prop in additional_properties:
        nom_prop = html.unescape(prop.get("name", ""))
        if nom_recherche.lower() in nom_prop.lower():
            return html.unescape(prop.get("value", ""))
    return None

def scraper_liste_produits(url_categorie):
    response = requests.get(url_categorie, headers=HEADERS)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    liens = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.match(r'^(/ref/\d+|https://www\.boulanger\.com/ref/\d+)', href):
            if href.startswith("/"):
                href = "https://www.boulanger.com" + href
            liens.add(href.split("?")[0])

    return list(liens)

def scraper_fiche_produit(url):
    response = requests.get(url, headers=HEADERS)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    scripts = soup.find_all("script", type="application/ld+json")

    produit_json = None
    for s in scripts:
        if not s.string:
            continue
        try:
            data = json.loads(s.string)
        except json.JSONDecodeError:
            continue
        if data.get("@type") == "Product":
            produit_json = data
            break

    if not produit_json:
        return None

    nom = html.unescape(produit_json.get("name", "").strip())
    marque = produit_json.get("brand", {}).get("name", "")
    prix = produit_json.get("offers", {}).get("price")

    if not (nom and marque and prix):
        return None

    prix = float(prix)

    props = produit_json.get("additionalProperty", [])

    # Écran
    ecran_texte = trouver_valeur_propriete(props, "Taille de") or ""
    ecran_match = re.search(r'(\d+[,.]?\d*)"', ecran_texte)
    ecran = float(ecran_match.group(1).replace(",", ".")) if ecran_match else None

    # RAM
    ram_texte = trouver_valeur_propriete(props, "Mémoire vive") or ""
    ram_match = re.search(r'(\d+)\s?Go', ram_texte)
    ram = int(ram_match.group(1)) if ram_match else None

    # Stockage
    stockage_texte = trouver_valeur_propriete(props, "capacité totale de stockage") or ""
    stockage_to = re.search(r'(\d+)\s?To', stockage_texte)
    stockage_go = re.search(r'(\d+)\s?Go', stockage_texte)
    if stockage_to:
        stockage = int(stockage_to.group(1)) * 1000
    elif stockage_go:
        stockage = int(stockage_go.group(1))
    else:
        stockage = None

    # GPU (pour le critère de matching)
    gpu_texte = trouver_valeur_propriete(props, "Contrôleur graphique") or trouver_valeur_propriete(props, "Carte graphique") or ""
    description = f"{nom} {gpu_texte}"

    return {
        "nom": nom,
        "prix": prix,
        "marque": marque,
        "ecran": ecran,
        "ram": ram,
        "stockage": stockage,
        "description": description
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
    url_categorie = "https://www.boulanger.com/c/tous-les-ordinateurs-portables"

    print("🔎 Récupération des liens produits...")
    liens = scraper_liste_produits(url_categorie)
    print(f"→ {len(liens)} fiches produits trouvées\n")

    produits = []
    for lien in liens[:15]:
        print(f"Scraping : {lien}")
        produit = scraper_fiche_produit(lien)
        if produit:
            produits.append(produit)

    print(f"\n✅ {len(produits)} produits extraits avec succès\n")
    for p in produits:
        print(f"{p['nom'][:50]:50} | {p['prix']}€ | Écran:{p['ecran']} | RAM:{p['ram']}Go | Stockage:{p['stockage']}Go")

    sauvegarder_csv(produits, "produits_boulanger.csv")
    sauvegarder_bdd(produits, "Boulanger")