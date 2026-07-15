from fastapi import FastAPI, HTTPException
import sqlite3

app = FastAPI(title="Price Comparator API")

def connexion_bdd():
    connexion = sqlite3.connect("produits.db")
    connexion.row_factory = sqlite3.Row  # permet d'accéder aux colonnes par nom
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

    # Convertit chaque ligne SQLite en dictionnaire normal
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