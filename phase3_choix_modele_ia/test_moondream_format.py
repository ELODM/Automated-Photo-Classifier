# Petit test pour comprendre comment Moondream renvoie ses reponses
# J'avais des problemes avec le format JSON donc je veux voir ce qu'il renvoie vraiment

import base64
import requests
import json
from datetime import datetime


# une photo de test
LA_PHOTO = "/mnt/immich-data/photos_sbep/422.jpg"


# on encode l'image en base64
with open(LA_PHOTO, "rb") as fichier:
    image_base64 = base64.b64encode(fichier.read()).decode("utf-8")


# test avec un prompt qui demande une seule categorie
print("=== Test 1: format=json ===")
debut = datetime.now()
reponse = requests.post(
    "http://localhost:11435/api/generate",
    json={
        "model": "moondream:1.8b",
        "prompt": "Classify: faune, flore, littoral, paysage, batiment, infrastructure, pollution, document, portrait. One word only.",
        "images": [image_base64],
        "stream": False
    },
    timeout=600
)
duree_secondes = (datetime.now() - debut).total_seconds()
les_donnees = reponse.json()

print(f"Temps: {duree_secondes:.0f}s")
print(f"Cles dans la reponse: {list(les_donnees.keys())}")
print(f"response = {les_donnees.get('response', 'ABSENT')}")
print(f"message = {les_donnees.get('message', 'ABSENT')}")
print(f"JSON complet: {json.dumps(les_donnees, indent=2)[:500]}")
