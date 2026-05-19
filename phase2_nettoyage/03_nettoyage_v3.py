# Version 3 (finale je crois) du script de nettoyage
# J'ai change la facon de detecter les corrompus (j'utilise la BDD au lieu de Pillow)

import json
import subprocess
import os
from datetime import datetime


def faire_requete_sql(ma_requete):
    commande = [
        "docker", "exec", "immich_postgres",
        "psql", "-U", "postgres", "-d", "immich",
        "-t", "-A", "-c", ma_requete
    ]
    return subprocess.check_output(commande).decode().strip()


print("=" * 60)
print("  NETTOYAGE V3 - VERSION FINALE")
print(f"  Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)


mon_rapport = {
    "date": datetime.now().isoformat(),
    "parasites": [],
    "trop_petits": [],
    "doublons": [],
    "corrompus": [],
    "floues": []
}


# ETAPE 1 : GIF parasites
print("\n[1/5] GIF parasites (< 10 Ko ET < 50x50 pixels)...")
requete = """SELECT a.id, a."originalFileName", ae."fileSizeInByte", ae."exifImageWidth", ae."exifImageHeight" FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE LOWER(a."originalPath") LIKE '%.gif' AND ae."fileSizeInByte" < 10240 AND (ae."exifImageWidth" < 50 OR ae."exifImageHeight" < 50 OR ae."exifImageWidth" IS NULL)"""
resultat_parasites = faire_requete_sql(requete)

compteur = 0
for ligne in resultat_parasites.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        if len(morceaux) >= 3:
            mon_rapport["parasites"].append({
                "id": morceaux[0].strip(),
                "nom": morceaux[1].strip()
            })
            compteur += 1
print(f"  -> {compteur} parasites confirmes")


# ETAPE 2 : trop petits
print("\n[2/5] Fichiers trop petits (< 5 Ko ET < 100x100 px)...")
requete = """SELECT a.id, a."originalFileName", ae."fileSizeInByte" FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE ae."fileSizeInByte" < 5120 AND ae."fileSizeInByte" > 0 AND LOWER(a."originalPath") NOT LIKE '%.gif' AND (ae."exifImageWidth" < 100 OR ae."exifImageHeight" < 100 OR ae."exifImageWidth" IS NULL) AND a.type = 'IMAGE'"""
resultat_petits = faire_requete_sql(requete)

compteur = 0
for ligne in resultat_petits.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        if len(morceaux) >= 3:
            mon_rapport["trop_petits"].append({
                "id": morceaux[0].strip(),
                "nom": morceaux[1].strip()
            })
            compteur += 1
print(f"  -> {compteur} trop petits confirmes")


# ETAPE 3 : near-doublons
print("\n[3/5] Near-doublons (meme nom + meme taille)...")
requete = """SELECT a."originalFileName", ae."fileSizeInByte", COUNT(*) as nb FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE a.type = 'IMAGE' GROUP BY a."originalFileName", ae."fileSizeInByte" HAVING COUNT(*) > 1 ORDER BY nb DESC LIMIT 50"""
resultat_doublons = faire_requete_sql(requete)

compteur = 0
total_dbl = 0
for ligne in resultat_doublons.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        if len(morceaux) >= 3:
            nb_copies = int(morceaux[2].strip()) if morceaux[2].strip().isdigit() else 0
            if nb_copies > 1:
                compteur += 1
                total_dbl += (nb_copies - 1)
                mon_rapport["doublons"].append({
                    "nom": morceaux[0].strip(),
                    "copies": nb_copies
                })
print(f"  -> {compteur} groupes, {total_dbl} fichiers en double")


# ETAPE 4 : corrompus via la BDD
# l'idee : si Immich n'a pas pu generer la miniature ou l'EXIF, c'est probablement corrompu
print("\n[4/5] Corrompus (via base de donnees - sans miniature)...")
requete = """SELECT a.id, a."originalFileName" FROM asset a WHERE a.type = 'IMAGE' AND a.id NOT IN (SELECT "assetId" FROM asset_file WHERE type = 'thumbnail') LIMIT 100"""
resultat_corrompus = faire_requete_sql(requete)

compteur = 0
for ligne in resultat_corrompus.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        if len(morceaux) >= 2:
            mon_rapport["corrompus"].append({
                "id": morceaux[0].strip(),
                "nom": morceaux[1].strip()
            })
            compteur += 1

# si on n'a rien trouve avec les miniatures on essaie sans EXIF
if compteur == 0:
    requete2 = """SELECT a.id, a."originalFileName" FROM asset a LEFT JOIN asset_exif ae ON a.id = ae."assetId" WHERE a.type = 'IMAGE' AND ae."assetId" IS NULL LIMIT 100"""
    resultat_corrompus2 = faire_requete_sql(requete2)
    for ligne in resultat_corrompus2.split('\n'):
        if '|' in ligne:
            morceaux = ligne.split('|')
            if len(morceaux) >= 2:
                mon_rapport["corrompus"].append({
                    "id": morceaux[0].strip(),
                    "nom": morceaux[1].strip()
                })
                compteur += 1
print(f"  -> {compteur} potentiellement corrompus (sans miniature ou sans EXIF)")


# ETAPE 5 : floues, version avec seuil strict
print("\n[5/5] Photos floues (Laplacien, fichiers accessibles uniquement)...")
nb_floues = 0
SEUIL_STRICT = 30.0
try:
    import cv2
    dossier_photos = '/mnt/immich-data/photos/'
    liste_fichiers = [f for f in os.listdir(dossier_photos) if f.lower().endswith(('.jpg', '.jpeg'))]
    nb_analysees = 0
    for nom_fichier in liste_fichiers[:500]:
        chemin = os.path.join(dossier_photos, nom_fichier)
        # on saute les fichiers qu'on ne peut pas lire
        if not os.access(chemin, os.R_OK):
            continue
        try:
            image = cv2.imread(chemin)
            if image is None:
                continue
            hauteur, largeur = image.shape[:2]
            # on ignore les petites images
            if largeur < 500 or hauteur < 500:
                continue
            image_grise = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # je redimensionne pour avoir un score comparable entre toutes les photos
            image_grise = cv2.resize(image_grise, (500, 500))
            score = cv2.Laplacian(image_grise, cv2.CV_64F).var()
            nb_analysees += 1
            if score < SEUIL_STRICT:
                mon_rapport["floues"].append({
                    "fichier": nom_fichier,
                    "score": round(score, 2),
                    "dim": f"{largeur}x{hauteur}"
                })
                nb_floues += 1
        except:
            pass
    print(f"  -> {nb_floues} floues sur {nb_analysees} analysees (seuil strict={SEUIL_STRICT})")
except ImportError:
    print("  -> OpenCV non disponible")


# bilan final
print("\n" + "=" * 60)
print("  RESUME V3 FINAL")
print("=" * 60)
print(f"  Parasites       : {len(mon_rapport['parasites'])}")
print(f"  Trop petits     : {len(mon_rapport['trop_petits'])}")
print(f"  Near-doublons   : {total_dbl} fichiers")
print(f"  Corrompus       : {len(mon_rapport['corrompus'])}")
print(f"  Floues          : {len(mon_rapport['floues'])}")

total_final = (len(mon_rapport['parasites'])
               + len(mon_rapport['trop_petits'])
               + total_dbl
               + len(mon_rapport['corrompus'])
               + len(mon_rapport['floues']))
print(f"  TOTAL           : {total_final} candidats")
print("\n  Aucun fichier supprime. Validation requise.")


with open("/home/info/photo-ia/resultats/rapport_nettoyage_v3.json", "w") as f:
    json.dump(mon_rapport, f, indent=2)
print("  Rapport V3 sauvegarde.")
print("=" * 60)
