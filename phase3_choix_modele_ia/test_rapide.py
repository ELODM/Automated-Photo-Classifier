# Petit test rapide pour voir si LLaVA et Moondream tournent bien
# Je leur demande juste de decrire ce qu'ils voient

import base64
import requests
import json


# notre photo de test
LA_PHOTO = "/mnt/immich-data/photos_sbep/422.jpg"


# on encode l'image en base64
with open(LA_PHOTO, "rb") as fichier:
    image_base64 = base64.b64encode(fichier.read()).decode("utf-8")


# test 1 : LLaVA 7b
print("=== LLaVA ===")
try:
    reponse_llava = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llava:7b",
            "prompt": "What do you see?",
            "images": [image_base64],
            "stream": False
        },
        timeout=600
    )
    les_donnees = reponse_llava.json()
    print(json.dumps(les_donnees, indent=2)[:500])
except Exception as erreur:
    print(f"ERREUR: {erreur}")


# test 2 : Moondream 1.8b
print("\n=== Moondream ===")
try:
    reponse_moon = requests.post(
        "http://localhost:11435/api/generate",
        json={
            "model": "moondream:1.8b",
            "prompt": "What do you see?",
            "images": [image_base64],
            "stream": False
        },
        timeout=600
    )
    les_donnees = reponse_moon.json()
    print(json.dumps(les_donnees, indent=2)[:500])
except Exception as erreur:
    print(f"ERREUR: {erreur}")
