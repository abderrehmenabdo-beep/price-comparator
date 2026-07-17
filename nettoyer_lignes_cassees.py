import sqlite3

connexion = sqlite3.connect("produits.db")
curseur = connexion.cursor()

# Supprime les lignes dont le nom contient des tabulations/retours à la ligne bruts
# (restes de l'ancienne version du scraper Boulanger, avant le passage au JSON-LD)
curseur.execute("SELECT COUNT(*) FROM produits WHERE nom LIKE '%' || CHAR(10) || '%' OR nom LIKE '%' || CHAR(9) || '%'")
nb = curseur.fetchone()[0]
print(f"{nb} lignes cassées trouvées")

curseur.execute("DELETE FROM produits WHERE nom LIKE '%' || CHAR(10) || '%' OR nom LIKE '%' || CHAR(9) || '%'")
connexion.commit()
connexion.close()
print("✅ Lignes cassées supprimées")