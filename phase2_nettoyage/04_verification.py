# Script de verification : on regarde des echantillons pour valider ce qu'on a detecte
# Comme ca on est sur que le nettoyage ne va pas supprimer des photos importantes

import subprocess
import os
import json
from datetime import datetime


def faire_requete_sql(ma_requete):
    commande = [
        "docker", "exec", "immich_postgres",
        "psql", "-U", "postgres", "-d", "immich",
        "-t", "-A", "-c", ma_requete
    ]
    return subprocess.check_output(commande).decode().strip()


print("=" * 60)
print("  VERIFICATION DU NETTOYAGE - ECHANTILLONS")
print(f"  Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)


# ============================================
# VERIFICATION 1 : GIF PARASITES
# ============================================
print("\n" + "-" * 60)
print("  [1/5] ECHANTILLON GIF PARASITES (10 premiers)")
print("-" * 60)
echantillon_parasites = faire_requete_sql("""SELECT a."originalFileName", ae."fileSizeInByte", ae."exifImageWidth", ae."exifImageHeight" FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE LOWER(a."originalPath") LIKE '%.gif' AND ae."fileSizeInByte" < 10240 LIMIT 10""")

for ligne in echantillon_parasites.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        nom = morceaux[0].strip()
        taille = morceaux[1].strip()
        largeur = morceaux[2].strip() if len(morceaux) > 2 else '?'
        hauteur = morceaux[3].strip() if len(morceaux) > 3 else '?'
        print(f"  {nom:40s} {taille:>6s} octets  {largeur}x{hauteur} px")
print(f"\n  Si les noms sont aleatoires et la taille < 1Ko = PARASITES CONFIRMES")


# ============================================
# VERIFICATION 2 : FICHIERS TROP PETITS
# ============================================
print("\n" + "-" * 60)
print("  [2/5] ECHANTILLON FICHIERS TROP PETITS (15 premiers)")
print("-" * 60)
echantillon_petits = faire_requete_sql("""SELECT a."originalFileName", ae."fileSizeInByte", LOWER(SPLIT_PART(a."originalPath", '.', -1)) as ext, ae."exifImageWidth", ae."exifImageHeight" FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE ae."fileSizeInByte" < 5120 AND ae."fileSizeInByte" > 0 AND LOWER(a."originalPath") NOT LIKE '%.gif' LIMIT 15""")

for ligne in echantillon_petits.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        nom = morceaux[0].strip()
        taille = morceaux[1].strip()
        ext = morceaux[2].strip() if len(morceaux) > 2 else '?'
        largeur = morceaux[3].strip() if len(morceaux) > 3 else '?'
        hauteur = morceaux[4].strip() if len(morceaux) > 4 else '?'
        print(f"  {nom:40s} .{ext:4s} {taille:>6s} octets  {largeur}x{hauteur} px")
print(f"\n  Si dimensions tres petites (1x1, 10x10) = VIGNETTES/ICONES CONFIRMES")


# ============================================
# VERIFICATION 3 : DOUBLONS
# ============================================
print("\n" + "-" * 60)
print("  [3/5] VERIFICATION DOUBLONS")
print("-" * 60)
total_checksums = faire_requete_sql('SELECT COUNT(*) FROM asset WHERE checksum IS NOT NULL')
checksums_uniques = faire_requete_sql('SELECT COUNT(DISTINCT checksum) FROM asset WHERE checksum IS NOT NULL')

print(f"  Total assets avec checksum : {total_checksums}")
print(f"  Checksums uniques          : {checksums_uniques}")
# si l'un est plus grand que l'autre, c'est qu'il y a des doublons
difference = int(total_checksums) - int(checksums_uniques)
print(f"  Doublons potentiels        : {difference}")

if difference > 0:
    print("\n  Exemple de doublons :")
    exemples_doublons = faire_requete_sql("""SELECT checksum, COUNT(*) as nb FROM asset WHERE checksum IS NOT NULL GROUP BY checksum HAVING COUNT(*) > 1 ORDER BY nb DESC LIMIT 5""")
    for ligne in exemples_doublons.split('\n'):
        if '|' in ligne:
            morceaux = ligne.split('|')
            print(f"    Checksum {morceaux[0].strip()[:20]}... -> {morceaux[1].strip()} copies")
else:
    print("  -> AUCUN DOUBLON : chaque photo est unique")


# ============================================
# VERIFICATION 4 : FICHIERS CORROMPUS
# ============================================
print("\n" + "-" * 60)
print("  [4/5] ECHANTILLON FICHIERS CORROMPUS")
print("-" * 60)
try:
    from PIL import Image
    dossier = '/mnt/immich-data/photos/'
    liste_fichiers = os.listdir(dossier)[:500]
    liste_corrompus = []
    for nom_fichier in liste_fichiers:
        chemin = os.path.join(dossier, nom_fichier)
        if os.path.isfile(chemin):
            try:
                image = Image.open(chemin)
                image.verify()
            except Exception as e:
                liste_corrompus.append((nom_fichier, str(e)[:80]))
                print(f"  CORROMPU: {nom_fichier}")
                print(f"           Raison: {str(e)[:80]}")
    print(f"\n  {len(liste_corrompus)} corrompus sur {len(liste_fichiers)} testes")
    if len(liste_corrompus) == 0:
        print("  -> AUCUN CORROMPU dans cet echantillon")
except ImportError:
    print("  Pillow non disponible")


# ============================================
# VERIFICATION 5 : PHOTOS FLOUES
# ============================================
print("\n" + "-" * 60)
print("  [5/5] ECHANTILLON PHOTOS FLOUES")
print("-" * 60)
try:
    import cv2
    dossier = '/mnt/immich-data/photos/'
    liste_fichiers = [f for f in os.listdir(dossier) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))][:200]
    liste_floues = []
    liste_nettes = []
    for nom_fichier in liste_fichiers:
        chemin = os.path.join(dossier, nom_fichier)
        try:
            image = cv2.imread(chemin)
            if image is not None:
                image_grise = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                score = cv2.Laplacian(image_grise, cv2.CV_64F).var()
                if score < 100:
                    liste_floues.append((nom_fichier, score))
                else:
                    liste_nettes.append((nom_fichier, score))
        except:
            pass

    print("  Photos FLOUES (score < 100) :")
    for nom, sc in liste_floues[:10]:
        print(f"    {nom:40s} score = {sc:.2f}")

    print(f"\n  Photos NETTES (les meilleures) :")
    # je trie par score decroissant pour voir les plus nettes en premier
    liste_nettes.sort(key=lambda x: x[1], reverse=True)
    for nom, sc in liste_nettes[:5]:
        print(f"    {nom:40s} score = {sc:.2f}")

    print(f"\n  {len(liste_floues)} floues / {len(liste_fichiers)} analysees")

except ImportError:
    print("  OpenCV non disponible")
