# Test de LLaVA-Phi3 sur 15 photos (au depart j'avais prevu 5 mais j'en ai fait 15)
# On regarde la vitesse moyenne et les categories detectees

import os
import json
import base64
import random
import requests
from datetime import datetime
from collections import Counter


# parametres
URL_OLLAMA = "http://localhost:11435/api/generate"
NOM_MODELE = "llava-phi3:3.8b"
DOSSIER_PHOTOS = "/mnt/immich-data/photos_sbep/"
NB_PHOTOS = 15


# le prompt qu'on envoie a l'IA
LE_PROMPT = """You are analyzing photos for DREAL Corse, the French environmental agency in Corsica.

Classify this photo into EXACTLY ONE category from:
faune, flore, littoral, montagne, milieu_aquatique, zone_humide, paysage, batiment, infrastructure, pollution, aerien, document, portrait, energie, risque_naturel

Meanings:
- faune: wildlife, animals
- flore: plants, trees, vegetation
- littoral: coastline, beach, cliffs
- montagne: mountains, peaks
- milieu_aquatique: rivers, lakes
- zone_humide: wetlands, marshes
- paysage: general landscape
- batiment: buildings, houses
- infrastructure: roads, bridges, signs
- pollution: waste, damage
- aerien: aerial view
- document: scanned document, text, map
- portrait: people
- energie: power lines, solar
- risque_naturel: fire, flood

Respond ONLY with JSON:
{"category": "x", "description_fr": "description in French", "confidence": 0.8}"""


# fonction pour envoyer une photo a l'IA
def classifier(chemin_image):
    with open(chemin_image, "rb") as fichier:
        image_base64 = base64.b64encode(fichier.read()).decode("utf-8")

    debut = datetime.now()
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
        timeout=600
    )
    duree = (datetime.now() - debut).total_seconds()
    reponse.raise_for_status()
    return json.loads(reponse.json()["response"]), duree


print("=" * 70)
print(f"  TEST LLaVA-Phi3 - {NB_PHOTOS} PHOTOS")
print(f"  Debut: {datetime.now().strftime('%H:%M:%S')}")
print("=" * 70)


# on liste les photos disponibles
extensions_image = ('.jpg', '.jpeg', '.png')
toutes_les_photos = [
    os.path.join(DOSSIER_PHOTOS, f)
    for f in os.listdir(DOSSIER_PHOTOS)
    if f.lower().endswith(extensions_image)
    and os.access(os.path.join(DOSSIER_PHOTOS, f), os.R_OK)
]
print(f"\n[1] {len(toutes_les_photos)} photos trouvees")


# on tire un echantillon au hasard
random.seed(42)
mon_echantillon = random.sample(toutes_les_photos, NB_PHOTOS)

print(f"\n[2] Echantillon:")
for numero, chemin in enumerate(mon_echantillon, 1):
    nom_court = os.path.basename(chemin)
    taille_ko = os.path.getsize(chemin) / 1024
    print(f"    {numero}. {nom_court} ({taille_ko:.0f} Ko)")


# on classifie chaque photo
print(f"\n[3] Classification en cours...")
mes_resultats = []

for numero, chemin in enumerate(mon_echantillon, 1):
    nom_court = os.path.basename(chemin)
    print(f"\n  [{numero}/{NB_PHOTOS}] {nom_court}")
    try:
        reponse_ia, duree = classifier(chemin)
        print(f"  OK en {duree:.0f}s")
        print(f"     Categorie   : {reponse_ia.get('category', '?')}")
        print(f"     Description : {reponse_ia.get('description_fr', '?')}")
        print(f"     Confiance   : {reponse_ia.get('confidence', '?')}")
        mes_resultats.append({
            "fichier": nom_court,
            "duree_sec": duree,
            "classification": reponse_ia
        })
    except Exception as erreur:
        print(f"  ERREUR: {erreur}")
        mes_resultats.append({"fichier": nom_court, "erreur": str(erreur)})


# resume avec les stats
print("\n" + "=" * 70)
print("  RESUME")
print("=" * 70)

photos_reussies = [r for r in mes_resultats if "classification" in r]

if photos_reussies:
    duree_moyenne = sum(r["duree_sec"] for r in photos_reussies) / len(photos_reussies)
    print(f"\n  Photos classifiees  : {len(photos_reussies)}/{NB_PHOTOS}")
    print(f"  Duree moyenne       : {duree_moyenne:.0f}s/photo")

    # projection pour les 6139 photos
    print(f"\n  Projection 6139 photos:")
    print(f"    Total: {duree_moyenne * 6139 / 3600:.0f}h ({duree_moyenne * 6139 / 86400:.1f} jours)")
    print(f"    Week-end 60h: {duree_moyenne * 6139 / 60 / 60:.1f} week-ends")
    print(f"    Nuits 12h: {duree_moyenne * 6139 / 3600 / 12:.0f} nuits")

    # repartition par categorie
    print(f"\n  Categories detectees:")
    comptage = Counter(r["classification"].get("category", "?") for r in photos_reussies)
    for cat, nb in comptage.most_common():
        print(f"    {cat:<20s} : {nb}")


# sauvegarde des resultats
os.makedirs("/home/info/photo-ia/resultats", exist_ok=True)
with open("/home/info/photo-ia/resultats/test_phi3_5photos.json", "w", encoding="utf-8") as f:
    json.dump({
        "date": datetime.now().isoformat(),
        "modele": NOM_MODELE,
        "resultats": mes_resultats
    }, f, indent=2, ensure_ascii=False)

print(f"\n  Rapport: /home/info/photo-ia/resultats/test_phi3_5photos.json")
print(f"  Fin: {datetime.now().strftime('%H:%M:%S')}")
print("=" * 70)
