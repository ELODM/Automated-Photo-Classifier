# Comparatif entre LLaVA 7b et Moondream 1.8b
# Je teste les 2 modeles sur les memes 5 photos pour voir lequel est mieux

import os
import json
import base64
import random
import requests
from datetime import datetime


DOSSIER_PHOTOS = "/mnt/immich-data/photos_sbep/"


# le prompt qu'on envoie aux deux modeles (en court parce que Moondream comprend pas trop les longs)
LE_PROMPT = """Classify this photo into ONE category:
faune, flore, littoral, montagne, milieu_aquatique, zone_humide, paysage, batiment, infrastructure, pollution, aerien, document, portrait, energie, risque_naturel

Respond ONLY with JSON:
{"category": "one", "description_fr": "desc", "confidence": 0.8}"""


# on liste les photos disponibles
extensions_ok = ('.jpg', '.jpeg', '.png')
toutes_les_photos = [
    os.path.join(DOSSIER_PHOTOS, f)
    for f in os.listdir(DOSSIER_PHOTOS)
    if f.lower().endswith(extensions_ok)
    and os.access(os.path.join(DOSSIER_PHOTOS, f), os.R_OK)
]


# on tire 5 photos au hasard (avec seed pour avoir toujours les memes)
random.seed(42)
mes_photos = random.sample(toutes_les_photos, 5)


print("=" * 70)
print("  COMPARATIF LLaVA 7b vs MOONDREAM 1.8b")
print(f"  Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 70)


print("\n  Photos selectionnees:")
for numero, chemin in enumerate(mes_photos, 1):
    nom_court = os.path.basename(chemin)
    taille_ko = os.path.getsize(chemin) / 1024
    print(f"    {numero}. {nom_court} ({taille_ko:.0f} Ko)")


# les 2 modeles a tester
liste_modeles = [
    {"nom": "LLaVA 7b", "url": "http://localhost:11434", "model": "llava:7b"},
    {"nom": "Moondream 1.8b", "url": "http://localhost:11435", "model": "moondream:1.8b"},
]


# pour stocker les resultats de chaque modele
resultats_par_modele = {}


# on boucle sur les 2 modeles
for un_modele in liste_modeles:
    print(f"\n{'='*70}")
    print(f"  MODELE: {un_modele['nom']}")
    print(f"{'='*70}")

    liste_temps = []
    liste_categories = []

    for numero, chemin in enumerate(mes_photos, 1):
        nom_court = os.path.basename(chemin)
        taille_ko = os.path.getsize(chemin) / 1024

        # on encode l'image en base64
        with open(chemin, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

        debut = datetime.now()
        try:
            reponse = requests.post(
                f"{un_modele['url']}/api/generate",
                json={
                    "model": un_modele["model"],
                    "prompt": LE_PROMPT,
                    "images": [image_base64],
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1}
                },
                timeout=600
            )
            duree_secondes = (datetime.now() - debut).total_seconds()
            res = json.loads(reponse.json()["response"])
            categorie = res.get("category", "?")
            description = res.get("description_fr", "?")
            confiance = res.get("confidence", "?")
            liste_temps.append(duree_secondes)
            liste_categories.append(categorie)
            print(f"  [{numero}/5] {nom_court:35s} ({taille_ko:6.0f}Ko) -> {categorie:15s} ({confiance}) en {duree_secondes:.0f}s")
        except Exception as erreur:
            duree_secondes = (datetime.now() - debut).total_seconds()
            liste_temps.append(duree_secondes)
            liste_categories.append("ERREUR")
            print(f"  [{numero}/5] {nom_court:35s} -> ERREUR en {duree_secondes:.0f}s: {str(erreur)[:50]}")

    moyenne = sum(liste_temps) / len(liste_temps)
    resultats_par_modele[un_modele["nom"]] = {"moyenne": moyenne, "categories": liste_categories}
    print(f"\n  Moyenne: {moyenne:.0f}s/photo")


# comparaison finale entre les 2 modeles
print(f"\n{'='*70}")
print("  COMPARAISON FINALE")
print(f"{'='*70}")

for nom_modele, data in resultats_par_modele.items():
    moy = data["moyenne"]
    print(f"\n  {nom_modele}:")
    print(f"    Moyenne/photo  : {moy:.0f}s")
    print(f"    200 photos     : {moy * 200 / 3600:.1f}h")
    print(f"    6139 photos    : {moy * 6139 / 3600:.0f}h ({moy * 6139 / 86400:.0f} jours)")


# on compare si les 2 modeles sont d'accord ou pas
print(f"\n  Accord entre les 2 modeles:")
cats_llava = resultats_par_modele["LLaVA 7b"]["categories"]
cats_moon = resultats_par_modele["Moondream 1.8b"]["categories"]

nb_accord = sum(1 for a, b in zip(cats_llava, cats_moon) if a == b)
print(f"    {nb_accord}/5 photos classifiees pareil")

for numero, (chemin, cat_l, cat_m) in enumerate(zip(mes_photos, cats_llava, cats_moon)):
    nom_court = os.path.basename(chemin)
    si_accord = "=" if cat_l == cat_m else "DIFFERENT"
    print(f"    {nom_court:35s} LLaVA={cat_l:15s} Moon={cat_m:15s} {si_accord}")

print(f"\n{'='*70}")
