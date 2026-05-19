# Petit script pour tester l'API d'Immich
# Je verifie que la cle marche et que je peux acceder aux infos

import requests
import json


# parametres
URL_IMMICH = "http://10.20.210.13:2283/api"
MA_CLE_API = "VOTRE_CLE_API_ICI"

mes_entetes = {"x-api-key": MA_CLE_API}


# 1. test de connexion : on demande la version
reponse_version = requests.get(f"{URL_IMMICH}/server/version", headers=mes_entetes)
print("=== VERSION IMMICH ===")
print(json.dumps(reponse_version.json(), indent=2))


# 2. on regarde les statistiques du serveur
reponse_stats = requests.get(f"{URL_IMMICH}/server/statistics", headers=mes_entetes)
print("\n=== STATISTIQUES ===")
print(json.dumps(reponse_stats.json(), indent=2))


# 3. on teste la recherche CLIP avec des mots-cles metier DREAL
# CLIP c'est le modele de recherche d'Immich par texte
liste_termes_test = [
    "oiseau", "montagne", "littoral", "fleur", "foret",
    "pollution", "batiment", "riviere", "plage", "route"
]
print("\n=== TEST RECHERCHE CLIP ===")
for terme in liste_termes_test:
    reponse_recherche = requests.post(
        f"{URL_IMMICH}/search/smart",
        headers=mes_entetes,
        json={"query": terme}
    )
    donnees = reponse_recherche.json()
    nb_resultats = len(donnees.get("assets", {}).get("items", []))
    print(f"  {terme:15s} -> {nb_resultats} resultats")


# 4. on regarde la liste des albums qui existent deja
reponse_albums = requests.get(f"{URL_IMMICH}/albums", headers=mes_entetes)
liste_albums = reponse_albums.json()
print(f"\n=== ALBUMS ({len(liste_albums)}) ===")
for un_album in liste_albums:
    nom_album = un_album.get('albumName', 'Sans nom')
    nb_photos = un_album.get('assetCount', 0)
    print(f"  - {nom_album} ({nb_photos} photos)")


# 5. on regarde les tags qui existent
reponse_tags = requests.get(f"{URL_IMMICH}/tags", headers=mes_entetes)
liste_tags = reponse_tags.json()
print(f"\n=== TAGS ({len(liste_tags)}) ===")
for un_tag in liste_tags[:20]:
    nom_tag = un_tag.get('name', 'Sans nom')
    print(f"  - {nom_tag}")
