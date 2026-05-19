# Test de LLaVA sur un echantillon varie de photos
# Le but c'est de voir si LLaVA marche bien pour classer nos photos DREAL
# On prend 15 photos au hasard et on regarde le resultat
# Les resultats vont dans resultats/test_llava_echantillon.json

import os
import json
import base64
import random
import requests
from datetime import datetime
from pathlib import Path


# parametres
URL_OLLAMA = "http://localhost:11434/api/generate"
NOM_MODELE = "llava:7b"
DOSSIER_PHOTOS = "/mnt/immich-data/photos_sbep/"
NB_PHOTOS_A_TESTER = 15


# les categories DREAL qu'on veut utiliser
LISTE_CATEGORIES_DREAL = [
    "faune", "flore", "littoral", "montagne", "milieu_aquatique",
    "zone_humide", "paysage", "batiment", "infrastructure",
    "pollution", "aerien", "document", "portrait", "energie",
    "risque_naturel"
]


# le prompt qu'on envoie a LLaVA (en anglais ca marche mieux)
LE_PROMPT = f"""You are analyzing photos for DREAL Corse, the French environmental agency in Corsica.

Classify this photo into EXACTLY ONE category from this list:
{", ".join(LISTE_CATEGORIES_DREAL)}

Category meanings:
- faune: wildlife, animals (birds, fish, mammals, insects)
- flore: plants, flowers, trees, vegetation
- littoral: coastline, beach, sea cliffs, shore
- montagne: mountains, peaks, high altitude
- milieu_aquatique: rivers, lakes, streams, ponds
- zone_humide: wetlands, marshes, swamps
- paysage: general landscape, countryside
- batiment: buildings, houses, constructions
- infrastructure: roads, bridges, harbors, transport
- pollution: waste, trash, industrial damage
- aerien: aerial or satellite view
- document: scanned document, text, map
- portrait: people, human subjects
- energie: power lines, wind turbines, solar
- risque_naturel: fire, flood, landslide

Respond with ONLY a JSON object, nothing else:
{{"category": "one_category_from_list", "description_fr": "short description in French", "confidence": 0.8}}"""


# transforme une image en base64 (l'API Ollama veut ce format)
def encoder_image_en_base64(chemin_image):
    with open(chemin_image, "rb") as fichier:
        return base64.b64encode(fichier.read()).decode("utf-8")


# envoie une photo a LLaVA et recupere la classification
def classifier_photo(chemin_image):
    image_base64 = encoder_image_en_base64(chemin_image)
    donnees_envoi = {
        "model": NOM_MODELE,
        "prompt": LE_PROMPT,
        "images": [image_base64],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1}
    }
    debut = datetime.now()
    reponse = requests.post(URL_OLLAMA, json=donnees_envoi, timeout=600)
    duree_secondes = (datetime.now() - debut).total_seconds()
    reponse.raise_for_status()
    # la reponse est un JSON dans un JSON, faut deserialiser deux fois
    contenu_brut = reponse.json()["response"]
    return json.loads(contenu_brut), duree_secondes


def main():
    print("=" * 70)
    print("  TEST LLaVA SUR ECHANTILLON VARIE")
    print(f"  Modele: {NOM_MODELE}")
    print(f"  Photos: {DOSSIER_PHOTOS}")
    print("=" * 70)

    # on liste les photos disponibles
    toutes_les_photos = [
        os.path.join(DOSSIER_PHOTOS, f)
        for f in os.listdir(DOSSIER_PHOTOS)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        and os.access(os.path.join(DOSSIER_PHOTOS, f), os.R_OK)
    ]
    print(f"\n[1] {len(toutes_les_photos)} photos trouvees dans {DOSSIER_PHOTOS}")

    if len(toutes_les_photos) < NB_PHOTOS_A_TESTER:
        print(f"  ERREUR: moins de {NB_PHOTOS_A_TESTER} photos disponibles")
        return

    # on prend NB_PHOTOS_A_TESTER photos au hasard (seed pour avoir toujours les memes a chaque test)
    random.seed(42)
    mon_echantillon = random.sample(toutes_les_photos, NB_PHOTOS_A_TESTER)
    print(f"\n[2] Echantillon aleatoire de {NB_PHOTOS_A_TESTER} photos:")
    for numero, chemin in enumerate(mon_echantillon, 1):
        nom_court = os.path.basename(chemin)
        taille_ko = os.path.getsize(chemin) / 1024
        print(f"    {numero}. {nom_court} ({taille_ko:.0f} Ko)")

    # on classifie chaque photo une par une
    print(f"\n[3] Classification en cours (patience, ~3 min par photo)...")
    mes_resultats = []

    for numero, chemin in enumerate(mon_echantillon, 1):
        nom_court = os.path.basename(chemin)
        print(f"\n  [{numero}/{NB_PHOTOS_A_TESTER}] {nom_court}")
        print(f"  Envoi a LLaVA...")
        try:
            reponse_ia, duree = classifier_photo(chemin)
            print(f"  OK en {duree:.1f}s")
            print(f"     Categorie: {reponse_ia.get('category', '?')}")
            print(f"     Description: {reponse_ia.get('description_fr', '?')}")
            print(f"     Confiance: {reponse_ia.get('confidence', '?')}")
            mes_resultats.append({
                "fichier": nom_court,
                "chemin": chemin,
                "duree_sec": duree,
                "classification": reponse_ia
            })
        except Exception as erreur:
            print(f"  ERREUR: {erreur}")
            mes_resultats.append({
                "fichier": nom_court,
                "chemin": chemin,
                "erreur": str(erreur)
            })

    # affichage du resume
    print("\n" + "=" * 70)
    print("  RESUME")
    print("=" * 70)
    photos_reussies = [r for r in mes_resultats if "classification" in r]
    if photos_reussies:
        duree_moyenne = sum(r["duree_sec"] for r in photos_reussies) / len(photos_reussies)
        print(f"\n  Photos classifiees : {len(photos_reussies)}/{NB_PHOTOS_A_TESTER}")
        print(f"  Duree moyenne      : {duree_moyenne:.1f}s par photo")
        # extrapolation : combien de temps pour traiter 7,6M photos
        print(f"  Extrapolation 7,6M photos: {duree_moyenne * 7_600_000 / 86400:.0f} jours CPU")

        print(f"\n  Categories detectees:")
        from collections import Counter
        comptage_categories = Counter(r["classification"].get("category", "?") for r in photos_reussies)
        for nom_cat, nb in comptage_categories.most_common():
            print(f"    - {nom_cat}: {nb}")

    # sauvegarde des resultats
    chemin_sortie = "/home/info/photo-ia/resultats/test_llava_echantillon.json"
    os.makedirs(os.path.dirname(chemin_sortie), exist_ok=True)
    with open(chemin_sortie, "w", encoding="utf-8") as fichier_sortie:
        json.dump({
            "date": datetime.now().isoformat(),
            "modele": NOM_MODELE,
            "nb_photos": NB_PHOTOS_A_TESTER,
            "resultats": mes_resultats
        }, fichier_sortie, indent=2, ensure_ascii=False)
    print(f"\n  Rapport: {chemin_sortie}")
    print("=" * 70)


if __name__ == "__main__":
    main()
