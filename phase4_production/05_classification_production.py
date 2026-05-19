# Script de classification en production - le gros script qui fait tout
# Il classe toutes les photos de photos_sbep avec LLaVA-Phi3
#
# Ce que ca fait pour chaque photo :
#  1. Sauvegarde le resultat dans un JSON
#  2. Ecrit la description dans Immich (table asset_exif)
#  3. Cree un album par categorie et y met la photo
#  4. Si la confiance est trop basse, met aussi la photo dans un album "A verifier"
#
# Bonus : si le script plante, il sait reprendre la ou il s'est arrete

import os
import json
import base64
import requests
import subprocess
import time
from datetime import datetime, timedelta


# ==========================================================
# PARAMETRES QU'ON PEUT CHANGER
# ==========================================================
LIMITE_PHOTOS = None  # None = toutes les photos, sinon on met un nombre
TIMEOUT_PAR_PHOTO = 600  # 10 min max par photo sinon on abandonne
SEUIL_CONFIANCE_MIN = 0.70  # en dessous, la photo va dans "A verifier"


# ==========================================================
# PARAMETRES TECHNIQUES (ne pas changer)
# ==========================================================
URL_OLLAMA = "http://localhost:11435/api/generate"
NOM_MODELE = "llava-phi3:3.8b"
DOSSIER_PHOTOS = "/mnt/immich-data/photos_sbep/"
DOSSIER_RESULTATS = "/home/info/photo-ia/resultats/"

FICHIER_SORTIE_JSON = os.path.join(DOSSIER_RESULTATS, "classification_production.json")
FICHIER_DE_LOG = os.path.join(DOSSIER_RESULTATS, "classification_production.log")


# parametres Immich
URL_API_IMMICH = "http://localhost:2283/api"
MA_CLE_API = "VOTRE_CLE_API_ICI"
PREFIXE_NOM_ALBUM = "Photo-IA - "


# le prompt qu'on envoie a LLaVA
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


# fonction pour afficher un message et le sauvegarder dans le log
def afficher_log(message):
    horodatage = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ligne_complete = f"[{horodatage}] {message}"
    print(ligne_complete, flush=True)
    # on ajoute aussi au fichier log
    with open(FICHIER_DE_LOG, "a", encoding="utf-8") as f:
        f.write(ligne_complete + "\n")


# si on a deja un fichier de resultats, on le charge pour reprendre
def charger_les_resultats_deja_faits():
    if not os.path.exists(FICHIER_SORTIE_JSON):
        return set(), []
    try:
        with open(FICHIER_SORTIE_JSON, "r", encoding="utf-8") as f:
            donnees = json.load(f)
        liste_resultats = donnees.get("resultats", [])
        # on construit un set avec les noms de fichiers deja traites (recherche plus rapide)
        fichiers_deja_traites = {r["fichier"] for r in liste_resultats if "fichier" in r}
        return fichiers_deja_traites, liste_resultats
    except Exception as erreur:
        afficher_log(f"ATTENTION: impossible de charger les resultats existants: {erreur}")
        return set(), []


# sauvegarde tout dans le JSON
def sauvegarder_les_resultats(liste_resultats, date_debut, nb_total):
    donnees = {
        "date_debut": date_debut.isoformat(),
        "date_maj": datetime.now().isoformat(),
        "modele": NOM_MODELE,
        "seuil_confiance": SEUIL_CONFIANCE_MIN,
        "total_cible": nb_total,
        "total_traites": len(liste_resultats),
        "resultats": liste_resultats
    }
    with open(FICHIER_SORTIE_JSON, "w", encoding="utf-8") as f:
        json.dump(donnees, f, indent=2, ensure_ascii=False)


# envoie une photo a LLaVA-Phi3
def classifier_une_photo(chemin_photo):
    with open(chemin_photo, "rb") as fichier:
        image_base64 = base64.b64encode(fichier.read()).decode("utf-8")

    debut = time.time()
    reponse = requests.post(
        URL_OLLAMA,
        json={
            "model": NOM_MODELE,
            "prompt": LE_PROMPT,
            "images": [image_base64],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1}
        },
        timeout=TIMEOUT_PAR_PHOTO
    )
    duree_secondes = time.time() - debut
    reponse.raise_for_status()
    return json.loads(reponse.json()["response"]), duree_secondes


# cherche l'id Immich d'une photo a partir de son nom
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
def ecrire_description_immich(asset_id, ma_description):
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

    # si on l'a deja vu dans cette session on rend direct
    if nom_complet_album in dico_cache:
        return dico_cache[nom_complet_album]

    entetes = {"x-api-key": MA_CLE_API, "Content-Type": "application/json"}

    # on regarde si l'album existe deja dans Immich
    try:
        reponse = requests.get(f"{URL_API_IMMICH}/albums", headers=entetes, timeout=10)
        for album in reponse.json():
            if album.get("albumName") == nom_complet_album:
                dico_cache[nom_complet_album] = album["id"]
                return album["id"]
    except Exception as erreur:
        afficher_log(f"  ERREUR recherche album: {erreur}")

    # sinon on cree un nouvel album
    try:
        # description differente pour l'album "A verifier"
        description_album = f"Photos classifiees automatiquement par Photo-IA - categorie {nom_categorie}"
        if nom_categorie == "A verifier":
            description_album = f"Photos dont la classification a une confiance inferieure a {SEUIL_CONFIANCE_MIN}, a valider par un agent DREAL"

        reponse = requests.post(
            f"{URL_API_IMMICH}/albums",
            headers=entetes,
            json={"albumName": nom_complet_album, "description": description_album},
            timeout=10
        )
        if reponse.status_code in (200, 201):
            id_nouvel_album = reponse.json()["id"]
            dico_cache[nom_complet_album] = id_nouvel_album
            afficher_log(f"  Nouvel album cree: {nom_complet_album}")
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


def main():
    # on cree le dossier resultats si il existe pas
    os.makedirs(DOSSIER_RESULTATS, exist_ok=True)

    debut_du_script = datetime.now()
    afficher_log("=" * 70)
    afficher_log("  PHOTO-IA DREAL - CLASSIFICATION PRODUCTION")
    afficher_log(f"  Modele: {NOM_MODELE}")
    afficher_log(f"  LIMITE_PHOTOS: {LIMITE_PHOTOS if LIMITE_PHOTOS else 'aucune (toutes les photos)'}")
    afficher_log(f"  Seuil confiance: {SEUIL_CONFIANCE_MIN} (en dessous = album A verifier)")
    afficher_log("=" * 70)


    # ETAPE 1 : on verifie que Ollama est bien lance
    afficher_log("[1] Verification Ollama...")
    try:
        reponse = requests.get("http://localhost:11435/api/tags", timeout=5)
        liste_modeles_dispo = [m["name"] for m in reponse.json().get("models", [])]
        if not any("phi3" in m for m in liste_modeles_dispo):
            afficher_log(f"ERREUR: llava-phi3 introuvable dans {liste_modeles_dispo}")
            return
        afficher_log("  OK LLaVA-Phi3 pret")
    except Exception as erreur:
        afficher_log(f"ERREUR Ollama: {erreur}")
        return


    # ETAPE 2 : on liste toutes les photos a traiter
    afficher_log("[2] Listage photos...")
    extensions_ok = ('.jpg', '.jpeg', '.png')
    # on trie pour avoir un ordre stable entre les sessions (important pour la reprise)
    toutes_les_photos = sorted([
        f for f in os.listdir(DOSSIER_PHOTOS)
        if f.lower().endswith(extensions_ok)
        and os.access(os.path.join(DOSSIER_PHOTOS, f), os.R_OK)
    ])
    afficher_log(f"  {len(toutes_les_photos)} photos trouvees au total")


    # ETAPE 3 : on regarde si on a un script qui a deja tourne avant
    afficher_log("[3] Verification mode reprise...")
    photos_deja_faites, mes_resultats = charger_les_resultats_deja_faits()
    if photos_deja_faites:
        afficher_log(f"  Reprise detectee : {len(photos_deja_faites)} photos deja traitees")
    else:
        afficher_log("  Premier lancement")

    # on filtre pour ne garder que les photos pas encore traitees
    photos_restantes = [p for p in toutes_les_photos if p not in photos_deja_faites]

    # si on a mis une limite on coupe
    if LIMITE_PHOTOS is not None:
        if LIMITE_PHOTOS > len(photos_deja_faites):
            photos_restantes = photos_restantes[:LIMITE_PHOTOS - len(photos_deja_faites)]
        else:
            photos_restantes = []

    afficher_log(f"  Photos a traiter cette session : {len(photos_restantes)}")

    if not photos_restantes:
        afficher_log("  Rien a faire, arret")
        return


    # ETAPE 4 : la grosse boucle de classification
    afficher_log(f"[4] Classification en cours...")
    afficher_log("=" * 70)

    nb_erreurs = 0
    nb_a_verifier = 0
    debut_de_la_session = time.time()
    cache_des_albums = {}  # pour pas recreer les memes albums plusieurs fois

    for numero_dans_session, nom_photo in enumerate(photos_restantes, 1):
        chemin_complet = os.path.join(DOSSIER_PHOTOS, nom_photo)
        # numero global = ceux deja traites + ceux de cette session
        numero_global = len(photos_deja_faites) + numero_dans_session

        try:
            # on demande la classification a l'IA
            reponse_ia, duree = classifier_une_photo(chemin_complet)
            categorie = reponse_ia.get("category", "paysage")
            description_fr = reponse_ia.get("description_fr", "")
            confiance = float(reponse_ia.get("confidence", 0.5))

            # on retrouve l'id Immich de la photo
            asset_id = chercher_asset_id(nom_photo)

            # par defaut on a rien fait
            description_ecrite = False
            photo_ajoutee_album = False
            photo_ajoutee_a_verifier = False

            if asset_id:
                # on ecrit la description dans Immich
                description_ecrite = ecrire_description_immich(asset_id, description_fr)

                # on cree/recupere l'album de la categorie et on ajoute la photo
                id_album = trouver_ou_creer_album(categorie, cache_des_albums)
                if id_album:
                    photo_ajoutee_album = ajouter_photo_a_album(id_album, asset_id)

                # si la confiance est trop basse, on met aussi dans "A verifier"
                if confiance < SEUIL_CONFIANCE_MIN:
                    nb_a_verifier += 1
                    id_album_verif = trouver_ou_creer_album("A verifier", cache_des_albums)
                    if id_album_verif:
                        photo_ajoutee_a_verifier = ajouter_photo_a_album(id_album_verif, asset_id)

            # on sauvegarde le resultat de cette photo
            resultat_photo = {
                "fichier": nom_photo,
                "categorie": categorie,
                "description_fr": description_fr,
                "confiance": confiance,
                "duree_sec": round(duree, 1),
                "asset_id": asset_id,
                "description_immich": description_ecrite,
                "ajoute_album": photo_ajoutee_album,
                "a_verifier": photo_ajoutee_a_verifier,
                "date": datetime.now().isoformat()
            }
            mes_resultats.append(resultat_photo)

            # on sauvegarde apres CHAQUE photo (au cas ou le script plante)
            sauvegarder_les_resultats(mes_resultats, debut_du_script, len(toutes_les_photos))

            suffixe = " [A VERIFIER]" if photo_ajoutee_a_verifier else ""
            afficher_log(
                f"[{numero_global}/{len(toutes_les_photos)}] {nom_photo[:25]:25s} -> {categorie:18s} "
                f"({confiance:.2f}) {duree:.0f}s{suffixe}"
            )

        except Exception as erreur:
            # en cas d'erreur on l'enregistre quand meme et on continue
            nb_erreurs += 1
            afficher_log(f"[{numero_global}/{len(toutes_les_photos)}] {nom_photo[:25]:25s} -> ERREUR: {str(erreur)[:60]}")
            mes_resultats.append({
                "fichier": nom_photo,
                "erreur": str(erreur)[:200],
                "date": datetime.now().isoformat()
            })
            sauvegarder_les_resultats(mes_resultats, debut_du_script, len(toutes_les_photos))
            # on attend 5 secondes avant la prochaine photo (au cas ou ce soit un probleme de serveur)
            time.sleep(5)

        # toutes les 50 photos on fait un point d'avancement
        if numero_dans_session % 50 == 0:
            duree_ecoulee = time.time() - debut_de_la_session
            moyenne = duree_ecoulee / numero_dans_session
            # estimation du temps restant
            secondes_restantes = (len(photos_restantes) - numero_dans_session) * moyenne
            heure_de_fin_estimee = datetime.now() + timedelta(seconds=secondes_restantes)
            afficher_log("-" * 70)
            afficher_log(f"  PROGRESSION: {numero_dans_session}/{len(photos_restantes)} ({100 * numero_dans_session / len(photos_restantes):.1f}%)")
            afficher_log(f"  Temps moyen: {moyenne:.0f}s/photo | Erreurs: {nb_erreurs} | A verifier: {nb_a_verifier}")
            afficher_log(f"  Fin estimee: {heure_de_fin_estimee.strftime('%Y-%m-%d %H:%M')}")
            afficher_log("-" * 70)


    # bilan final
    afficher_log("=" * 70)
    afficher_log("  TERMINE")
    afficher_log(f"  Photos traitees cette session: {len(photos_restantes) - nb_erreurs}")
    afficher_log(f"  Photos en basse confiance (A verifier): {nb_a_verifier}")
    afficher_log(f"  Erreurs: {nb_erreurs}")
    afficher_log(f"  Total traites (cumule): {len(mes_resultats)}")
    afficher_log(f"  Duree totale: {(time.time() - debut_de_la_session) / 3600:.1f}h")
    afficher_log(f"  Rapport: {FICHIER_SORTIE_JSON}")
    afficher_log("=" * 70)


if __name__ == "__main__":
    main()
