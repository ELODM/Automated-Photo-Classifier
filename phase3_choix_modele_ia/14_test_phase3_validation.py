# Test final de validation pour la phase 3
# On teste sur 15 photos pour voir si on peut valider le modele LLaVA
# On sauvegarde le rapport en JSON et en TXT (pour le lire facilement)

import os
import json
import base64
import random
import requests
from datetime import datetime
from collections import Counter


# parametres
URL_OLLAMA = "http://localhost:11434/api/generate"
NOM_MODELE = "llava:7b"
DOSSIER_PHOTOS = "/mnt/immich-data/photos_sbep/"
NB_PHOTOS_TEST = 15


# le prompt qu'on envoie a LLaVA
LE_PROMPT = """You are analyzing photos for DREAL Corse, the French environmental agency.

Classify this photo into EXACTLY ONE category from this list:
faune, flore, littoral, montagne, milieu_aquatique, zone_humide, paysage, batiment, infrastructure, pollution, aerien, document, portrait, energie, risque_naturel

Meanings:
- faune: wildlife, animals
- flore: plants, flowers, trees
- littoral: coastline, beach, cliffs
- montagne: mountains, peaks
- milieu_aquatique: rivers, lakes
- zone_humide: wetlands, marshes
- paysage: general landscape
- batiment: buildings
- infrastructure: roads, bridges, harbors
- pollution: waste, damage
- aerien: aerial view
- document: document, map, text
- portrait: people
- energie: power, wind turbines
- risque_naturel: fire, flood

Respond ONLY with JSON:
{"category": "one_from_list", "description_fr": "description in French", "confidence": 0.8}"""


# encode une image en base64
def encoder_image(chemin_image):
    with open(chemin_image, "rb") as fichier:
        return base64.b64encode(fichier.read()).decode("utf-8")


# envoie la photo a LLaVA et recupere la reponse
def classifier_photo(chemin_image):
    image_base64 = encoder_image(chemin_image)
    donnees = {
        "model": NOM_MODELE,
        "prompt": LE_PROMPT,
        "images": [image_base64],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1}
    }
    debut = datetime.now()
    reponse = requests.post(URL_OLLAMA, json=donnees, timeout=600)
    duree = (datetime.now() - debut).total_seconds()
    reponse.raise_for_status()
    return json.loads(reponse.json()["response"]), duree


def main():
    print("=" * 70)
    print("  TEST VALIDATION PHASE 3 - 15 PHOTOS")
    print(f"  Debut: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70)

    # on liste toutes les photos disponibles
    extensions_image = ('.jpg', '.jpeg', '.png')
    toutes_les_photos = [
        os.path.join(DOSSIER_PHOTOS, f)
        for f in os.listdir(DOSSIER_PHOTOS)
        if f.lower().endswith(extensions_image)
        and os.access(os.path.join(DOSSIER_PHOTOS, f), os.R_OK)
    ]
    print(f"\n[1] {len(toutes_les_photos)} photos trouvees")

    if len(toutes_les_photos) < NB_PHOTOS_TEST:
        print(f"  ERREUR: moins de {NB_PHOTOS_TEST} photos")
        return

    # selection aleatoire (avec seed pour la reproductibilite)
    random.seed(100)
    mon_echantillon = random.sample(toutes_les_photos, NB_PHOTOS_TEST)
    print(f"\n[2] Echantillon de {NB_PHOTOS_TEST} photos selectionnees")


    # classification
    print(f"\n[3] Classification en cours...")
    print(f"    Duree estimee: ~{NB_PHOTOS_TEST * 4} min ({NB_PHOTOS_TEST} x 4 min)")
    print()

    mes_resultats = []
    for numero, chemin in enumerate(mon_echantillon, 1):
        nom_court = os.path.basename(chemin)
        heure = datetime.now().strftime('%H:%M:%S')
        print(f"  [{numero:2d}/{NB_PHOTOS_TEST}] {heure} | {nom_court[:40]:40s}", end=" ", flush=True)
        try:
            reponse_ia, duree = classifier_photo(chemin)
            cat = reponse_ia.get("category", "?")
            conf = reponse_ia.get("confidence", 0)
            print(f"-> {cat:20s} ({conf:.2f}) en {duree:.0f}s")
            mes_resultats.append({
                "fichier": nom_court,
                "duree_sec": round(duree, 1),
                "categorie": cat,
                "description_fr": reponse_ia.get("description_fr", ""),
                "confiance": conf
            })
        except Exception as erreur:
            print(f"-> ERREUR: {str(erreur)[:40]}")
            mes_resultats.append({"fichier": nom_court, "erreur": str(erreur)})


    # calcul des statistiques
    print("\n" + "=" * 70)
    print("  RESUME DU TEST")
    print("=" * 70)

    photos_reussies = [r for r in mes_resultats if "categorie" in r]
    nb_erreurs = len(mes_resultats) - len(photos_reussies)

    print(f"\n  Photos testees       : {NB_PHOTOS_TEST}")
    print(f"  Classifiees          : {len(photos_reussies)}")
    print(f"  Erreurs              : {nb_erreurs}")

    if photos_reussies:
        duree_totale = sum(r["duree_sec"] for r in photos_reussies)
        duree_moyenne = duree_totale / len(photos_reussies)
        print(f"\n  Duree totale         : {duree_totale/60:.1f} min")
        print(f"  Duree moyenne/photo  : {duree_moyenne:.1f} sec")
        # on fait des projections pour estimer le temps total
        print(f"  Extrapolation 200 photos: {duree_moyenne * 200 / 3600:.1f} heures")
        print(f"  Extrapolation 7104 photos: {duree_moyenne * 7104 / 3600:.0f} heures")

        # repartition par categorie
        print(f"\n  Categories detectees:")
        comptage = Counter(r["categorie"] for r in photos_reussies)
        for cat, nb in comptage.most_common():
            print(f"    {cat:<20s} : {nb}")

        # repartition des confiances
        print(f"\n  Distribution confiances:")
        nb_haute = sum(1 for r in photos_reussies if r["confiance"] >= 0.7)
        nb_moy = sum(1 for r in photos_reussies if 0.3 <= r["confiance"] < 0.7)
        nb_basse = sum(1 for r in photos_reussies if r["confiance"] < 0.3)
        print(f"    Haute (>=0.7)   : {nb_haute}")
        print(f"    Moyenne (0.3-0.7): {nb_moy}")
        print(f"    Basse (<0.3)    : {nb_basse}")


    # sauvegarde JSON
    os.makedirs("/home/info/photo-ia/resultats", exist_ok=True)
    chemin_json = "/home/info/photo-ia/resultats/rapport_phase3_validation.json"
    with open(chemin_json, "w", encoding="utf-8") as f:
        json.dump({
            "date": datetime.now().isoformat(),
            "modele": NOM_MODELE,
            "nb_photos": NB_PHOTOS_TEST,
            "nb_succes": len(photos_reussies),
            "nb_erreurs": nb_erreurs,
            "resultats": mes_resultats
        }, f, indent=2, ensure_ascii=False)
    print(f"\n  Rapport JSON: {chemin_json}")


    # sauvegarde TXT (plus lisible pour un humain)
    chemin_txt = "/home/info/photo-ia/resultats/rapport_phase3_validation.txt"
    with open(chemin_txt, "w", encoding="utf-8") as f:
        f.write("RAPPORT VALIDATION PHASE 3 - PHOTO-IA DREAL\n")
        f.write("=" * 70 + "\n")
        f.write(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
        f.write(f"Modele: {NOM_MODELE}\n")
        f.write(f"Photos testees: {NB_PHOTOS_TEST}\n")
        f.write(f"Classifiees: {len(photos_reussies)}\n")
        f.write("=" * 70 + "\n\n")
        for r in photos_reussies:
            f.write(f"Fichier     : {r['fichier']}\n")
            f.write(f"Categorie   : {r['categorie']}\n")
            f.write(f"Confiance   : {r['confiance']:.2f}\n")
            f.write(f"Description : {r['description_fr']}\n")
            f.write("-" * 70 + "\n")
    print(f"  Rapport TXT : {chemin_txt}")
    print("\n" + "=" * 70)
    print(f"  FIN: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
