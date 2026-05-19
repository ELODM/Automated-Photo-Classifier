# Test de LLaVA-Phi3 3.8b sur une seule photo
# Le but : voir si c'est plus rapide que LLaVA 7b (qui prend 250 secondes)

import base64
import requests
import json
from datetime import datetime


# photo de test
LA_PHOTO = "/mnt/immich-data/photos_sbep/422.jpg"


# on encode la photo en base64
with open(LA_PHOTO, "rb") as fichier:
    image_base64 = base64.b64encode(fichier.read()).decode("utf-8")


print("=== Test LLaVA-Phi3 3.8b ===")
debut = datetime.now()

reponse = requests.post(
    "http://localhost:11435/api/generate",
    json={
        "model": "llava-phi3:3.8b",
        "prompt": "Classify this photo into ONE category: faune, flore, littoral, montagne, paysage, batiment, infrastructure, pollution, document, portrait. Respond with JSON: {\"category\": \"x\", \"description_fr\": \"x\", \"confidence\": 0.8}",
        "images": [image_base64],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1}
    },
    timeout=600
)
duree_secondes = (datetime.now() - debut).total_seconds()
les_donnees = reponse.json()


print(f"\nTemps: {duree_secondes:.0f}s")
print(f"Reponse: {les_donnees.get('response', '?')}")


# on compare avec LLaVA 7b
print(f"\n=== Comparaison ===")
print(f"  LLaVA 7b (actuel): ~250s/photo")
print(f"  LLaVA-Phi3:        {duree_secondes:.0f}s/photo")
pourcentage_gain = ((250 - duree_secondes) / 250) * 100
print(f"  Gain:              {pourcentage_gain:.0f}%")


# on projette le temps total pour traiter les 6139 photos du stock
print(f"\n=== Projection 6139 photos ===")
nb_heures = (duree_secondes * 6139) / 3600
nb_jours = nb_heures / 24
nb_weekends = nb_heures / 60
print(f"  Duree totale: {nb_heures:.0f}h ({nb_jours:.1f} jours)")
print(f"  Week-ends (60h):  {nb_weekends:.1f}")
print(f"  Nuits cron (12h): {nb_heures / 12:.0f}")
