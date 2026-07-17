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

vus = {}  # (nom_normalise, site) -> id à garder
a_supprimer = []

for p in tous:
    cle = (normaliser(p["nom"]), p["site"])
    if cle in vus:
        # Doublon détecté : on supprime celui-ci (garde le premier vu)
        a_supprimer.append(p["id"])
    else:
        vus[cle] = p["id"]

print(f"{len(a_supprimer)} doublons détectés sur {len(tous)} produits")

for id_a_supprimer in a_supprimer:
    curseur.execute("DELETE FROM produits WHERE id = ?", (id_a_supprimer,))

connexion.commit()
connexion.close()
print("✅ Nettoyage terminé")