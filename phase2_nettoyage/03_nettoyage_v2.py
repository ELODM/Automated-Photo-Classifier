# Version 2 du script de nettoyage
# J'ai ajoute des criteres en plus parce que la V1 detectait trop de faux positifs

import json
import subprocess
import os
from datetime import datetime


# meme fonction qu'avant pour parler a postgres
def faire_requete_sql(ma_requete):
    commande = [
        "docker", "exec", "immich_postgres",
        "psql", "-U", "postgres", "-d", "immich",
        "-t", "-A", "-c", ma_requete
    ]
    resultat = subprocess.check_output(commande)
    return resultat.decode().strip()


print("=" * 60)
print("  NETTOYAGE V2 - CORRECTIONS APPLIQUEES")
print(f"  Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)


mon_rapport = {
    "date": datetime.now().isoformat(),
    "parasites": [],
    "trop_petits": [],
    "doublons_visuels": [],
    "corrompus": [],
    "floues": []
}


# ETAPE 1 : GIF parasites - cette fois j'ajoute le critere de dimensions
print("\n[1/5] GIF parasites (< 10 Ko ET dimensions < 50x50)...")
requete_parasites = """SELECT a.id, a."originalFileName", ae."fileSizeInByte", ae."exifImageWidth", ae."exifImageHeight" FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE LOWER(a."originalPath") LIKE '%.gif' AND ae."fileSizeInByte" < 10240 AND (ae."exifImageWidth" < 50 OR ae."exifImageHeight" < 50 OR ae."exifImageWidth" IS NULL)"""
les_parasites = faire_requete_sql(requete_parasites)

compteur = 0
for ligne in les_parasites.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        if len(morceaux) >= 3:
            mon_rapport["parasites"].append({
                "id": morceaux[0].strip(),
                "nom": morceaux[1].strip(),
                "taille": morceaux[2].strip()
            })
            compteur += 1
print(f"  -> {compteur} GIF parasites confirmes")


# ETAPE 2 : trop petits - on rajoute aussi un critere de dimensions
print("\n[2/5] Fichiers trop petits (< 5 Ko, dimensions < 100x100)...")
requete_petits = """SELECT a.id, a."originalFileName", ae."fileSizeInByte" FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE ae."fileSizeInByte" < 5120 AND ae."fileSizeInByte" > 0 AND LOWER(a."originalPath") NOT LIKE '%.gif' AND (ae."exifImageWidth" < 100 OR ae."exifImageHeight" < 100 OR ae."exifImageWidth" IS NULL) AND a.type = 'IMAGE'"""
les_petits = faire_requete_sql(requete_petits)

compteur = 0
for ligne in les_petits.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        if len(morceaux) >= 3:
            mon_rapport["trop_petits"].append({
                "id": morceaux[0].strip(),
                "nom": morceaux[1].strip(),
                "taille": morceaux[2].strip()
            })
            compteur += 1
print(f"  -> {compteur} fichiers trop petits confirmes")


# ETAPE 3 : near-doublons (meme nom + meme taille = probablement la meme photo)
print("\n[3/5] Near-doublons (meme nom + meme taille)...")
requete_doublons = """SELECT a."originalFileName", ae."fileSizeInByte", COUNT(*) as nb FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE a.type = 'IMAGE' GROUP BY a."originalFileName", ae."fileSizeInByte" HAVING COUNT(*) > 1 ORDER BY nb DESC LIMIT 50"""
les_doublons = faire_requete_sql(requete_doublons)

compteur = 0
total_doublons = 0
for ligne in les_doublons.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        if len(morceaux) >= 3:
            nb_copies = int(morceaux[2].strip()) if morceaux[2].strip().isdigit() else 0
            if nb_copies > 1:
                compteur += 1
                total_doublons += (nb_copies - 1)
                mon_rapport["doublons_visuels"].append({
                    "nom": morceaux[0].strip(),
                    "taille": morceaux[1].strip(),
                    "copies": nb_copies
                })
print(f"  -> {compteur} groupes de doublons potentiels")
print(f"  -> {total_doublons} fichiers en double")


# ETAPE 4 : corrompus - seulement les images, pas les videos
print("\n[4/5] Fichiers corrompus (images uniquement, pas videos)...")
nb_corrompus = 0
try:
    from PIL import Image
    dossier_photos = '/mnt/immich-data/photos/'
    extensions_image = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff')
    liste_fichiers = [f for f in os.listdir(dossier_photos) if f.lower().endswith(extensions_image)][:500]
    for nom_fichier in liste_fichiers:
        chemin = os.path.join(dossier_photos, nom_fichier)
        if os.path.isfile(chemin) and os.access(chemin, os.R_OK):
            try:
                image = Image.open(chemin)
                image.verify()
            except Exception as e:
                # je veux pas garder les erreurs de permission
                if "Permission" not in str(e):
                    mon_rapport["corrompus"].append({
                        "fichier": nom_fichier,
                        "raison": str(e)[:60]
                    })
                    nb_corrompus += 1
    print(f"  -> {nb_corrompus} vrais corrompus sur {len(liste_fichiers)} images testees")
except ImportError:
    print("  -> Pillow non disponible")


# ETAPE 5 : floues - je baisse le seuil et j'ignore les petites images
print("\n[5/5] Photos floues (seuil abaisse a 50, minimum 500x500 px)...")
nb_floues = 0
SEUIL_FLOU = 50.0
try:
    import cv2
    dossier_photos = '/mnt/immich-data/photos/'
    liste_fichiers = [f for f in os.listdir(dossier_photos) if f.lower().endswith(('.png', '.jpg', '.jpeg'))][:300]
    for nom_fichier in liste_fichiers:
        chemin = os.path.join(dossier_photos, nom_fichier)
        try:
            image = cv2.imread(chemin)
            if image is not None:
                hauteur, largeur = image.shape[:2]
                # j'ignore les petites images parce que sinon le score est fausse
                if largeur >= 500 and hauteur >= 500:
                    image_grise = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    score_flou = cv2.Laplacian(image_grise, cv2.CV_64F).var()
                    if score_flou < SEUIL_FLOU:
                        mon_rapport["floues"].append({
                            "fichier": nom_fichier,
                            "score": round(score_flou, 2),
                            "dimensions": f"{largeur}x{hauteur}"
                        })
                        nb_floues += 1
        except:
            pass
    print(f"  -> {nb_floues} photos floues (seuil={SEUIL_FLOU}, min 500x500)")
except ImportError:
    print("  -> OpenCV non disponible")


# bilan
print("\n" + "=" * 60)
print("  RESUME V2 (corrige)")
print("=" * 60)
print(f"  Parasites confirmes : {len(mon_rapport['parasites'])}")
print(f"  Trop petits confirms: {len(mon_rapport['trop_petits'])}")
print(f"  Near-doublons       : {total_doublons} fichiers")
print(f"  Vrais corrompus     : {len(mon_rapport['corrompus'])}")
print(f"  Vraies floues       : {len(mon_rapport['floues'])}")

total_tout = (len(mon_rapport['parasites'])
              + len(mon_rapport['trop_petits'])
              + total_doublons
              + len(mon_rapport['corrompus'])
              + len(mon_rapport['floues']))
print(f"  TOTAL               : {total_tout} candidats")
print("\n  Aucun fichier supprime. Validation requise.")


with open("/home/info/photo-ia/resultats/rapport_nettoyage_v2.json", "w") as f:
    json.dump(mon_rapport, f, indent=2)
print("  Rapport V2 sauvegarde.")
print("=" * 60)
