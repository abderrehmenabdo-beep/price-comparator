from fastapi import FastAPI, HTTPException
import sqlite3

app = FastAPI(title="Price Comparator API")

def connexion_bdd():
    connexion = sqlite3.connect("produits.db")
    connexion.row_factory = sqlite3.Row
    return connexion

@app.get("/")
def accueil():
    return {"message": "Bienvenue sur l'API Price Comparator"}

@app.get("/produits")
def lister_produits():
    connexion = connexion_bdd()
    curseur = connexion.cursor()
    curseur.execute("SELECT * FROM produits")
    lignes = curseur.fetchall()
    connexion.close()
    return [dict(ligne) for ligne in lignes]

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

    return score / total_criteres if total_criteres > 0 else 0


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