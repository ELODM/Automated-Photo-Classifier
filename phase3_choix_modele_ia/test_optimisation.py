# Test d'optimisation : est-ce que reduire la taille de l'image accelere LLaVA ?
# On teste avec l'image originale puis en 224x224 pour comparer

import os
import json
import base64
import requests
from datetime import datetime
from PIL import Image
from io import BytesIO


# notre photo de test
LA_PHOTO = "/mnt/immich-data/photos_sbep/422.jpg"


# le prompt qu'on utilise (court pour aller plus vite)
LE_PROMPT_COURT = """Classify: faune, flore, littoral, montagne, paysage, batiment, infrastructure, pollution, document, portrait. JSON: {"category":"x","confidence":0.8}"""


# TEST 1 : on envoie l'image originale (sans rien modifier)
print("=== Test 1: Original (reference) ===")
with open(LA_PHOTO, "rb") as fichier:
    image_originale_base64 = base64.b64encode(fichier.read()).decode("utf-8")

debut_test1 = datetime.now()
reponse1 = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llava:7b",
        "prompt": LE_PROMPT_COURT,
        "images": [image_originale_base64],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 50}
    },
    timeout=600
)
duree_test1 = (datetime.now() - debut_test1).total_seconds()
print(f"Temps: {duree_test1:.0f}s")
print(f"Reponse: {reponse1.json().get('response','?')[:100]}")


# TEST 2 : on envoie l'image redimensionnee a 224x224
print("\n=== Test 2: Image 224x224 ===")
image_redimensionnee = Image.open(LA_PHOTO).convert("RGB").resize((224, 224))

# on la convertit en JPEG en memoire (sans la sauvegarder sur disque)
buffer_image = BytesIO()
image_redimensionnee.save(buffer_image, format="JPEG", quality=70)
image_petite_base64 = base64.b64encode(buffer_image.getvalue()).decode("utf-8")

print(f"Taille base64: {len(image_petite_base64)} vs {len(image_originale_base64)} (original)")

debut_test2 = datetime.now()
reponse2 = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llava:7b",
        "prompt": LE_PROMPT_COURT,
        "images": [image_petite_base64],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 50}
    },
    timeout=600
)
duree_test2 = (datetime.now() - debut_test2).total_seconds()
print(f"Temps: {duree_test2:.0f}s")
print(f"Reponse: {reponse2.json().get('response','?')[:100]}")


# on calcule le gain de temps
pourcentage_gain = ((duree_test1 - duree_test2) / duree_test1) * 100
print(f"\nGain: {pourcentage_gain:.0f}%")
print(f"  Original: {duree_test1:.0f}s")
print(f"  224x224:  {duree_test2:.0f}s")
