from fastapi import FastAPI, HTTPException
import sqlite3
from typing import Optional
import re


app = FastAPI(title="Price Comparator API")

def connexion_bdd():
    connexion = sqlite3.connect("produits.db")
    connexion.row_factory = sqlite3.Row
    return connexion

@app.get("/")
def accueil():
    return {"message": "Bienvenue sur l'API Price Comparator"}

@app.get("/produits")
def lister_produits(prix_min: Optional[float] = None, prix_max: Optional[float] = None):
    connexion = connexion_bdd()
    curseur = connexion.cursor()

    requete = "SELECT * FROM produits WHERE 1=1"
    parametres = []

    if prix_min is not None:
        requete += " AND prix >= ?"
        parametres.append(prix_min)

    if prix_max is not None:
        requete += " AND prix <= ?"
        parametres.append(prix_max)

    curseur.execute(requete, parametres)
    lignes = curseur.fetchall()
    connexion.close()

    return [dict(ligne) for ligne in lignes]
@app.get("/produits/site/{nom_site}")
def produits_par_site(nom_site: str):
    connexion = connexion_bdd()
    curseur = connexion.cursor()
    curseur.execute("SELECT * FROM produits WHERE site = ? COLLATE NOCASE", (nom_site,))
    lignes = curseur.fetchall()
    connexion.close()

    if not lignes:
        raise HTTPException(status_code=404, detail=f"Aucun produit trouvé pour le site '{nom_site}'")

    return [dict(ligne) for ligne in lignes]
@app.get("/stats")
def statistiques():
    connexion = connexion_bdd()
    curseur = connexion.cursor()

    # Nombre total de produits
    curseur.execute("SELECT COUNT(*) FROM produits")
    total_produits = curseur.fetchone()[0]

    # Répartition par site
    curseur.execute("SELECT site, COUNT(*) FROM produits GROUP BY site")
    par_site = {site: nombre for site, nombre in curseur.fetchall()}

    # Prix moyen, min, max
    curseur.execute("SELECT AVG(prix), MIN(prix), MAX(prix) FROM produits")
    prix_moyen, prix_min, prix_max = curseur.fetchone()

    # Répartition par marque (top 5)
    curseur.execute("SELECT marque, COUNT(*) as nb FROM produits GROUP BY marque ORDER BY nb DESC LIMIT 5")
    top_marques = {marque: nombre for marque, nombre in curseur.fetchall()}

    # Nombre de produits avec specs complètes
    curseur.execute("""
        SELECT COUNT(*) FROM produits 
        WHERE ecran IS NOT NULL AND ram IS NOT NULL AND stockage IS NOT NULL
    """)
    produits_complets = curseur.fetchone()[0]

    connexion.close()

    return {
        "total_produits": total_produits,
        "par_site": par_site,
        "prix": {
            "moyen": round(prix_moyen, 2) if prix_moyen else None,
            "min": prix_min,
            "max": prix_max
        },
        "top_5_marques": top_marques,
        "qualite_donnees": {
            "produits_avec_specs_completes": produits_complets,
            "pourcentage_complet": round(produits_complets / total_produits * 100, 1) if total_produits else 0
        }
    }
@app.get("/produits/{produit_id}")
def obtenir_produit(produit_id: int):
    connexion = connexion_bdd()
    curseur = connexion.cursor()
    curseur.execute("SELECT * FROM produits WHERE id = ?", (produit_id,))
    ligne = curseur.fetchone()
    connexion.close()
    if ligne is None:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    return dict(ligne)

@app.get("/produits/recherche/{terme}")
def rechercher_produits(terme: str):
    connexion = connexion_bdd()
    curseur = connexion.cursor()
    curseur.execute("SELECT * FROM produits WHERE nom LIKE ?", (f"%{terme}%",))
    lignes = curseur.fetchall()
    connexion.close()
    return [dict(ligne) for ligne in lignes]


# ==== NOUVEAU CODE À AJOUTER ICI, EN DESSOUS DE TOUT CE QUI PRÉCÈDE ====

def score_matching(p1, p2):
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

    # Nouveau : critère GPU, cherché dans le nom ET la description
    texte1 = p1["nom"] + " " + (p1.get("description") or "")
    texte2 = p2["nom"] + " " + (p2.get("description") or "")
    gpu1 = extraire_gpu(texte1)
    gpu2 = extraire_gpu(texte2)
    if gpu1 or gpu2:
        total_criteres += 1
        if gpu1 and gpu2 and gpu1 == gpu2:
            score += 1
    return score / total_criteres if total_criteres > 0 else 0

def extraire_gpu(nom):
    match = re.search(r'(RTX\s?\d{3,4}(?:\s?Ti)?|GTX\s?\d{3,4}|Radeon\s?\w*\s?\d*)', nom, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).upper().replace(" ", "")

@app.get("/comparaison")
def comparer_prix(seuil: float = 0.99):
    connexion = connexion_bdd()
    curseur = connexion.cursor()
    curseur.execute("SELECT * FROM produits")
    tous_produits = [dict(ligne) for ligne in curseur.fetchall()]
    connexion.close()

    sites = {}
    for p in tous_produits:
        sites.setdefault(p["site"], []).append(p)

    noms_sites = list(sites.keys())
    if len(noms_sites) < 2:
        return {"message": "Pas assez de sites différents en base pour comparer", "comparaisons": []}

    resultats = []
    for i in range(len(noms_sites)):
        for j in range(i + 1, len(noms_sites)):
            site_a_nom = noms_sites[i]
            site_b_nom = noms_sites[j]

            for p1 in sites[site_a_nom]:
                for p2 in sites[site_b_nom]:
                    score = score_matching(p1, p2)
                    if score >= seuil:
                        moins_cher = site_a_nom if p1["prix"] < p2["prix"] else site_b_nom
                        economie = round(abs(p1["prix"] - p2["prix"]), 2)

                        resultats.append({
                            "produit_1": {"id": p1["id"], "nom": p1["nom"], "prix": p1["prix"], "site": site_a_nom},
                            "produit_2": {"id": p2["id"], "nom": p2["nom"], "prix": p2["prix"], "site": site_b_nom},
                            "score_similarite": round(score, 2),
                            "meilleure_offre": moins_cher,
                            "economie": economie
                        })

    return {"nombre_comparaisons": len(resultats), "comparaisons": resultats}