# Demonstration pour la DREAL : on classifie 5 photos avec LLaVA-Phi3
# Le script fait 3 choses pour chaque photo :
#   1. Sauvegarder le resultat dans un JSON
#   2. Ecrire la description dans Immich (dans la table asset_exif)
#   3. Creer un album par categorie et ajouter la photo dedans

import os
import json
import base64
import requests
import subprocess
from datetime import datetime


# ==========================================================
# CONFIGURATION (mes parametres)
# ==========================================================
URL_OLLAMA = "http://localhost:11435/api/generate"
NOM_MODELE = "llava-phi3:3.8b"
DOSSIER_PHOTOS = "/mnt/immich-data/photos_sbep/"
DOSSIER_RESULTATS = "/home/info/photo-ia/resultats/"
FICHIER_SORTIE_JSON = os.path.join(DOSSIER_RESULTATS, "demo_5photos.json")

# Immich (l'API pour creer les albums)
URL_API_IMMICH = "http://localhost:2283/api"
MA_CLE_API = "VOTRE_CLE_API_ICI"
PREFIXE_NOM_ALBUM = "Photo-IA - "

# les 5 photos que je veux tester pour la demo
PHOTOS_DEMO = [
    "93880.jpg",

]

# le prompt que j'envoie a l'IA (en anglais ca marche mieux)
LE_PROMPT = """You are analyzing photos for DREAL Corse, the French environmental agency in Corsica.

Classify this photo into EXACTLY ONE category from:
faune, flore, littoral, montagne, milieu_aquatique, zone_humide, paysage, batiment, infrastructure, pollution, aerien, document, portrait, energie, risque_naturel

Category meanings:
- faune: wildlife, animals
- flore: plants, trees, vegetation
- littoral: coastline, beaches, cliffs
- montagne: mountains, peaks
- milieu_aquatique: rivers, lakes, streams
- zone_humide: wetlands, marshes
- paysage: general landscape
- batiment: buildings, houses
- infrastructure: roads, bridges, signs, harbors
- pollution: waste, damage
- aerien: aerial view
- document: scanned document, text, map
- portrait: people, human subjects
- energie: power lines, solar panels
- risque_naturel: fire, flood, landslide

Respond ONLY with JSON:
{"category": "x", "description_fr": "short description in French", "confidence": 0.85}"""


# petite fonction pour afficher un message avec l'heure (pratique pour suivre)
def afficher_log(message):
    heure = datetime.now().strftime('%H:%M:%S')
    print(f"[{heure}] {message}", flush=True)


# envoie une photo a LLaVA-Phi3 et recupere la reponse
def classifier_une_photo(chemin_photo):
    # je lis l'image et je la convertis en base64 (c'est ce que veut l'API)
    with open(chemin_photo, "rb") as fichier:
        image_en_base64 = base64.b64encode(fichier.read()).decode("utf-8")

    debut = datetime.now()
    reponse = requests.post(URL_OLLAMA, json={
        "model": NOM_MODELE,
        "prompt": LE_PROMPT,
        "images": [image_en_base64],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1}
    }, timeout=600)
    duree_secondes = (datetime.now() - debut).total_seconds()
    reponse.raise_for_status()
    # la reponse contient elle-meme un JSON dans le champ "response"
    return json.loads(reponse.json()["response"]), duree_secondes


# cherche l'id Immich d'une photo a partir de son nom de fichier
def chercher_asset_id(nom_fichier):
    commande = [
        "docker", "exec", "immich_postgres",
        "psql", "-U", "postgres", "-d", "immich", "-t", "-A",
        "-c", f"SELECT id FROM asset WHERE \"originalFileName\" = '{nom_fichier}' LIMIT 1;"
    ]
    try:
        resultat = subprocess.run(commande, capture_output=True, text=True, timeout=10)
        asset_id = resultat.stdout.strip()
        if asset_id:
            return asset_id
        return None
    except Exception as erreur:
        afficher_log(f"  ERREUR recherche assetId pour {nom_fichier}: {erreur}")
        return None


# ecrit la description dans la table asset_exif
def ecrire_description_dans_immich(asset_id, ma_description):
    # j'echappe les apostrophes sinon le SQL plante
    description_propre = ma_description.replace("'", "''")
    commande = [
        "docker", "exec", "immich_postgres",
        "psql", "-U", "postgres", "-d", "immich", "-c",
        f"INSERT INTO asset_exif (\"assetId\", description) VALUES ('{asset_id}', '{description_propre}') "
        f"ON CONFLICT (\"assetId\") DO UPDATE SET description = '{description_propre}';"
    ]
    try:
        resultat = subprocess.run(commande, capture_output=True, text=True, timeout=10)
        return resultat.returncode == 0
    except Exception as erreur:
        afficher_log(f"  ERREUR ecriture description: {erreur}")
        return False


# si l'album existe deja on prend son id, sinon on le cree
def trouver_ou_creer_album(nom_categorie, dico_cache):
    nom_complet_album = PREFIXE_NOM_ALBUM + nom_categorie

    # si on l'a deja vu on rend direct
    if nom_complet_album in dico_cache:
        return dico_cache[nom_complet_album]

    entetes = {"x-api-key": MA_CLE_API, "Content-Type": "application/json"}

    # on regarde si l'album existe deja dans Immich
    try:
        reponse = requests.get(f"{URL_API_IMMICH}/albums", headers=entetes, timeout=10)
        for album in reponse.json():
            if album.get("albumName") == nom_complet_album:
                dico_cache[nom_complet_album] = album["id"]
                afficher_log(f"  Album existant trouve: {nom_complet_album}")
                return album["id"]
    except Exception as erreur:
        afficher_log(f"  ERREUR recherche album: {erreur}")

    # on cree un nouvel album
    try:
        reponse = requests.post(
            f"{URL_API_IMMICH}/albums",
            headers=entetes,
            json={
                "albumName": nom_complet_album,
                "description": f"Photos classifiees automatiquement par Photo-IA dans la categorie {nom_categorie}"
            },
            timeout=10
        )
        if reponse.status_code in (200, 201):
            id_nouvel_album = reponse.json()["id"]
            dico_cache[nom_complet_album] = id_nouvel_album
            afficher_log(f"  Album cree: {nom_complet_album}")
            return id_nouvel_album
    except Exception as erreur:
        afficher_log(f"  ERREUR creation album: {erreur}")
    return None


# ajoute une photo a un album via l'API
def ajouter_photo_a_album(id_album, id_photo):
    entetes = {"x-api-key": MA_CLE_API, "Content-Type": "application/json"}
    try:
        reponse = requests.put(
            f"{URL_API_IMMICH}/albums/{id_album}/assets",
            headers=entetes,
            json={"ids": [id_photo]},
            timeout=10
        )
        return reponse.status_code in (200, 201)
    except Exception as erreur:
        afficher_log(f"  ERREUR ajout album: {erreur}")
        return False


# fonction principale
def main():
    # on cree le dossier resultats s'il n'existe pas
    os.makedirs(DOSSIER_RESULTATS, exist_ok=True)

    afficher_log("=" * 70)
    afficher_log("  PHOTO-IA DREAL - DEMONSTRATION SUR 5 PHOTOS")
    afficher_log(f"  Modele: {NOM_MODELE}")
    afficher_log("=" * 70)

    # je verifie qu'Ollama est bien lance avant de continuer
    afficher_log("\n[1/4] Verification Ollama...")
    try:
        reponse = requests.get("http://localhost:11435/api/tags", timeout=5)
        liste_modeles = [m["name"] for m in reponse.json().get("models", [])]
        if not any("phi3" in m for m in liste_modeles):
            afficher_log(f"  ERREUR: llava-phi3 introuvable dans {liste_modeles}")
            return
        afficher_log("  OK, LLaVA-Phi3 est pret")
    except Exception as erreur:
        afficher_log(f"  ERREUR connexion Ollama: {erreur}")
        return

    # on regarde si les photos existent bien
    afficher_log("\n[2/4] Verification des 5 photos...")
    photos_qui_existent = []
    for nom in PHOTOS_DEMO:
        chemin_complet = os.path.join(DOSSIER_PHOTOS, nom)
        if os.path.exists(chemin_complet):
            taille_ko = os.path.getsize(chemin_complet) / 1024
            afficher_log(f"  OK {nom} ({taille_ko:.0f} Ko)")
            photos_qui_existent.append((nom, chemin_complet))
        else:
            afficher_log(f"  MANQUE {nom}")
    if len(photos_qui_existent) < 5:
        afficher_log("  ATTENTION: il manque des photos, on continue avec celles trouvees")

    # traitement de chaque photo
    afficher_log(f"\n[3/4] Traitement de {len(photos_qui_existent)} photos...")
    afficher_log("=" * 70)

    tous_les_resultats = []
    cache_des_albums = {}  # pour eviter de recreer le meme album plusieurs fois

    for numero, (nom, chemin) in enumerate(photos_qui_existent, 1):
        afficher_log(f"\nPhoto {numero}/{len(photos_qui_existent)}: {nom}")

        # ETAPE A : la classification avec l'IA
        afficher_log(f"  Etape A: Classification en cours (environ 2 minutes)...")
        try:
            reponse_ia, duree = classifier_une_photo(chemin)
            categorie = reponse_ia.get("category", "paysage")
            description_fr = reponse_ia.get("description_fr", "")
            confiance = float(reponse_ia.get("confidence", 0.5))
            afficher_log(f"  OK Categorie: {categorie}")
            afficher_log(f"     Description: {description_fr}")
            afficher_log(f"     Confiance: {confiance:.2f}")
            afficher_log(f"     Duree: {duree:.0f}s")
        except Exception as erreur:
            afficher_log(f"  ERREUR classification: {erreur}")
            tous_les_resultats.append({"fichier": nom, "erreur": str(erreur)})
            continue

        # ETAPE B : retrouver l'id Immich
        afficher_log(f"  Etape B: Recherche de la photo dans Immich...")
        asset_id = chercher_asset_id(nom)
        if not asset_id:
            afficher_log(f"  ATTENTION: photo non trouvee dans Immich, descriptions et albums skippes")
            tous_les_resultats.append({
                "fichier": nom,
                "categorie": categorie,
                "description_fr": description_fr,
                "confiance": confiance,
                "note": "photo non presente dans Immich"
            })
            continue
        afficher_log(f"  OK assetId trouve")

        # ETAPE C : ecrire la description dans la BDD
        afficher_log(f"  Etape C: Ecriture description dans Immich...")
        if ecrire_description_dans_immich(asset_id, description_fr):
            afficher_log(f"  OK description ecrite dans asset_exif")
        else:
            afficher_log(f"  ERREUR ecriture description")

        # ETAPE D : creer l'album et y mettre la photo
        afficher_log(f"  Etape D: Gestion album {PREFIXE_NOM_ALBUM}{categorie}...")
        id_album = trouver_ou_creer_album(categorie, cache_des_albums)
        if id_album:
            if ajouter_photo_a_album(id_album, asset_id):
                afficher_log(f"  OK photo ajoutee a l'album")
            else:
                afficher_log(f"  ERREUR ajout photo a l'album")

        # on sauvegarde le resultat de la photo
        tous_les_resultats.append({
            "fichier": nom,
            "categorie": categorie,
            "description_fr": description_fr,
            "confiance": confiance,
            "duree_sec": round(duree, 1),
            "asset_id": asset_id,
            "album_id": id_album,
            "date": datetime.now().isoformat()
        })

    # sauvegarde dans un fichier JSON
    afficher_log(f"\n[4/4] Sauvegarde du rapport JSON...")
    with open(FICHIER_SORTIE_JSON, "w", encoding="utf-8") as fichier_sortie:
        json.dump({
            "date": datetime.now().isoformat(),
            "modele": NOM_MODELE,
            "nb_photos": len(tous_les_resultats),
            "resultats": tous_les_resultats
        }, fichier_sortie, indent=2, ensure_ascii=False)
    afficher_log(f"  OK JSON sauvegarde dans {FICHIER_SORTIE_JSON}")

    # affichage du resume
    afficher_log("\n" + "=" * 70)
    afficher_log("  RESUME DE LA DEMONSTRATION")
    afficher_log("=" * 70)
    afficher_log(f"\n  Photos traitees: {len(tous_les_resultats)}")
    afficher_log(f"  Albums crees: {len(cache_des_albums)}")
    for nom_album in cache_des_albums:
        afficher_log(f"    - {nom_album}")
    afficher_log(f"\n  Pour voir les resultats:")
    afficher_log(f"    1. JSON: cat {FICHIER_SORTIE_JSON}")
    afficher_log(f"    2. Descriptions: ouvrir Immich et cliquer sur une photo")
    afficher_log(f"    3. Albums: aller dans la section Albums d'Immich")
    afficher_log("=" * 70)


if __name__ == "__main__":
    main()
