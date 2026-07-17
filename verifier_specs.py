import sqlite3

connexion = sqlite3.connect("produits.db")
curseur = connexion.cursor()
curseur.execute("""
    SELECT nom, ecran, ram, stockage 
    FROM produits 
    WHERE site = 'Boulanger' AND (ecran IS NULL OR ram IS NULL OR stockage IS NULL) 
    LIMIT 10
""")
for row in curseur.fetchall():
    print(row)
connexion.close()