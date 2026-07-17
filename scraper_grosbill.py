def scraper_fiche_produit(url):
    response = requests.get(url, headers=HEADERS)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    h1 = soup.find("h1")
    if not h1:
        return None

    strong = h1.find("strong")
    marque = strong.text.strip() if strong else h1.text.split()[0]
    nom = re.sub(r'\s+', ' ', h1.text).strip()

    texte_complet = soup.get_text(separator=" ")

    # Zone des vraies caractéristiques (2e occurrence de "Processeur")
    positions_processeur = [m.start() for m in re.finditer(r'Processeur', texte_complet)]
    if len(positions_processeur) >= 2:
        zone_specs = texte_complet[positions_processeur[1] - 300: positions_processeur[1] + 500]
    else:
        zone_specs = texte_complet
    specs = extraire_specs_boulanger(zone_specs)

    # Prix : premier prix trouvé après le h1 (juste après "Ajouter au panier")
    pattern_prix = re.compile(r'(\d{1,3}(?:[\s\xa0]\d{3})*,\d{2})\s?€')
    idx_h1 = texte_complet.find("Ajouter au panier")
    zone_prix = texte_complet[idx_h1:idx_h1 + 200] if idx_h1 != -1 else texte_complet
    matches = pattern_prix.findall(zone_prix)

    if not matches:
        return None
    prix = float(matches[0].replace("\xa0", "").replace(" ", "").replace(",", "."))

    return {
        "nom": nom,
        "prix": prix,
        "marque": marque,
        "description": zone_specs.strip()[:300],
        **specs
    }