import sqlite3
import html
import re

connexion = sqlite3.connect("produits.db")
connexion.row_factory = sqlite3.Row
curseur = connexion.cursor()

curseur.execute("SELECT * FROM produits")
tous = [dict(r) for r in curseur.fetchall()]

def normaliser(nom):
    nom = html.unescape(nom)
    nom = re.sub(r'\s+', ' ', nom).strip().lower()
    return nom

def score_completude(p):
    # Plus il y a de champs remplis, plus le score est élevé
    return sum(1 for champ in ["ecran", "ram", "stockage"] if p[champ] is not None)

meilleurs = {}  # (nom_normalise, site) -> meilleur produit trouvé

for p in tous:
    cle = (normaliser(p["nom"]), p["site"])
    if cle not in meilleurs or score_completude(p) > score_completude(meilleurs[cle]):
        meilleurs[cle] = p

ids_a_garder = {p["id"] for p in meilleurs.values()}
a_supprimer = [p["id"] for p in tous if p["id"] not in ids_a_garder]

print(f"{len(a_supprimer)} doublons à supprimer sur {len(tous)} produits")

for id_a_supprimer in a_supprimer:
    curseur.execute("DELETE FROM produits WHERE id = ?", (id_a_supprimer,))

connexion.commit()
connexion.close()
print("✅ Nettoyage terminé (version conservée = la plus complète)")