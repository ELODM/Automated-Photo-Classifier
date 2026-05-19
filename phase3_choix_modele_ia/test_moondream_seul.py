# Test isole de Moondream pour voir si il marche bien tout seul
# Je veux juste savoir s'il decrit bien une photo

import base64
import requests
import json
from datetime import datetime


# la photo qu'on veut tester
LA_PHOTO = "/mnt/immich-data/photos_sbep/422.jpg"


# on lit la photo et on l'encode en base64
with open(LA_PHOTO, "rb") as fichier:
    image_base64 = base64.b64encode(fichier.read()).decode("utf-8")


print("=== Test Moondream seul ===")
debut = datetime.now()

# on demande a Moondream de decrire la photo
reponse = requests.post(
    "http://localhost:11435/api/generate",
    json={
        "model": "moondream:1.8b",
        "prompt": "What do you see in this image? One sentence.",
        "images": [image_base64],
        "stream": False
    },
    timeout=600
)
duree_secondes = (datetime.now() - debut).total_seconds()
les_donnees = reponse.json()

print(f"Temps: {duree_secondes:.0f}s")
print(f"Reponse: {les_donnees.get('response', 'PAS DE REPONSE')}")
