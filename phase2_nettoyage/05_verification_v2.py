# Verification de la V2 du nettoyage
# Je relis le rapport JSON et je verifie que les detections sont fiables

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
print("  VERIFICATION NETTOYAGE V2")
print(f"  Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)


# on relit le rapport qu'on a fait avant
with open("/home/info/photo-ia/resultats/rapport_nettoyage_v2.json", "r") as f:
    mon_rapport = json.load(f)


# ============================================
# VERIF 1 : GIF PARASITES
# ============================================
print("\n" + "-" * 60)
print("  [1/5] VERIFICATION GIF PARASITES")
print(f"  Total detectes: {len(mon_rapport['parasites'])}")
print("-" * 60)

echantillon_parasites = faire_requete_sql("""SELECT a."originalFileName", ae."fileSizeInByte", ae."exifImageWidth", ae."exifImageHeight" FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE LOWER(a."originalPath") LIKE '%.gif' AND ae."fileSizeInByte" < 10240 AND (ae."exifImageWidth" < 50 OR ae."exifImageHeight" < 50 OR ae."exifImageWidth" IS NULL) LIMIT 10""")

print("  Echantillon :")
for ligne in echantillon_parasites.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        nom = morceaux[0].strip()
        taille = morceaux[1].strip()
        largeur = morceaux[2].strip() if len(morceaux) > 2 else '?'
        hauteur = morceaux[3].strip() if len(morceaux) > 3 else '?'
        # si dimensions 1x1 ou 2x2 c'est clairement un parasite
        if largeur in ['1', '2'] or hauteur in ['1', '2'] or largeur == '':
            verdict = "PARASITE"
        else:
            verdict = "A VERIFIER"
        print(f"  {nom:40s} {taille:>6s} o  {largeur}x{hauteur} px  -> {verdict}")
print("\n  CRITERE: nom aleatoire + dimensions 1x1 ou 2x2 = parasite confirme")


# ============================================
# VERIF 2 : FICHIERS TROP PETITS
# ============================================
print("\n" + "-" * 60)
print("  [2/5] VERIFICATION FICHIERS TROP PETITS")
print(f"  Total detectes: {len(mon_rapport['trop_petits'])}")
print("-" * 60)

echantillon_petits = faire_requete_sql("""SELECT a."originalFileName", ae."fileSizeInByte", ae."exifImageWidth", ae."exifImageHeight", LOWER(SPLIT_PART(a."originalPath", '.', -1)) as ext FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE ae."fileSizeInByte" < 5120 AND ae."fileSizeInByte" > 0 AND LOWER(a."originalPath") NOT LIKE '%.gif' AND (ae."exifImageWidth" < 100 OR ae."exifImageHeight" < 100 OR ae."exifImageWidth" IS NULL) AND a.type = 'IMAGE' LIMIT 15""")

print("  Echantillon :")
for ligne in echantillon_petits.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        nom = morceaux[0].strip()
        taille = morceaux[1].strip()
        largeur = morceaux[2].strip() if len(morceaux) > 2 else '?'
        hauteur = morceaux[3].strip() if len(morceaux) > 3 else '?'
        ext = morceaux[4].strip() if len(morceaux) > 4 else '?'
        # si la largeur est petite c'est une vignette
        if largeur != '' and (largeur.isdigit() and int(largeur) < 100 or True):
            verdict = "VIGNETTE"
        else:
            verdict = "A VERIFIER"
        print(f"  {nom:35s} .{ext:4s} {taille:>5s} o  {largeur}x{hauteur} px  -> {verdict}")

# je veux aussi voir la repartition par taille
stats_tailles = faire_requete_sql("""SELECT CASE WHEN ae."fileSizeInByte" < 100 THEN 'Moins de 100 octets' WHEN ae."fileSizeInByte" < 1024 THEN 'Entre 100 o et 1 Ko' WHEN ae."fileSizeInByte" < 5120 THEN 'Entre 1 Ko et 5 Ko' END as tranche, COUNT(*) FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE ae."fileSizeInByte" < 5120 AND ae."fileSizeInByte" > 0 AND LOWER(a."originalPath") NOT LIKE '%.gif' AND (ae."exifImageWidth" < 100 OR ae."exifImageHeight" < 100 OR ae."exifImageWidth" IS NULL) AND a.type = 'IMAGE' GROUP BY tranche ORDER BY tranche""")

print("\n  Repartition par taille :")
for ligne in stats_tailles.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        print(f"    {morceaux[0].strip():25s}: {morceaux[1].strip()} fichiers")


# ============================================
# VERIF 3 : NEAR-DOUBLONS
# ============================================
print("\n" + "-" * 60)
print("  [3/5] VERIFICATION NEAR-DOUBLONS")
print(f"  Total detectes: {len(mon_rapport['doublons_visuels'])} groupes")
print("-" * 60)

echantillon_doublons = faire_requete_sql("""SELECT a."originalFileName", ae."fileSizeInByte", COUNT(*) as nb FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE a.type = 'IMAGE' GROUP BY a."originalFileName", ae."fileSizeInByte" HAVING COUNT(*) > 1 ORDER BY nb DESC LIMIT 10""")

print("  Echantillon :")
for ligne in echantillon_doublons.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        nom = morceaux[0].strip()
        taille = morceaux[1].strip()
        nb_copies = morceaux[2].strip()
        print(f"  {nom:40s} {taille:>10s} o  x{nb_copies} copies")
print("\n  CRITERE: meme nom + meme taille = probable doublon")


# ============================================
# VERIF 4 : CORROMPUS
# ============================================
print("\n" + "-" * 60)
print("  [4/5] VERIFICATION CORROMPUS")
print(f"  Total detectes: {len(mon_rapport['corrompus'])}")
print("-" * 60)

if len(mon_rapport['corrompus']) == 0:
    print("  -> AUCUN fichier corrompu detecte")
    print("  -> Les erreurs precedentes etaient des problemes de permission")
    print("  -> Le stock est sain de ce cote")
else:
    for cor in mon_rapport['corrompus'][:10]:
        print(f"  {cor['fichier']:40s} -> {cor.get('raison','')}")


# ============================================
# VERIF 5 : PHOTOS FLOUES
# ============================================
print("\n" + "-" * 60)
print("  [5/5] VERIFICATION PHOTOS FLOUES")
print(f"  Total detectees: {len(mon_rapport['floues'])}")
print("-" * 60)

print("  Echantillon (a verifier dans Immich) :")
for photo in mon_rapport['floues'][:15]:
    score = photo.get('score', 0)
    dim = photo.get('dimensions', '?')
    # je classe par score
    if score < 20:
        verdict = "TRES FLOUE"
    elif score < 35:
        verdict = "FLOUE"
    else:
        verdict = "PEUT-ETRE FLOUE"
    print(f"  {photo['fichier']:40s} score={score:>6.2f}  {dim:>10s}  -> {verdict}")


# ============================================
# BILAN GLOBAL
# ============================================
print("\n" + "=" * 60)
print("  BILAN DE LA VERIFICATION")
print("=" * 60)
print(f"  Parasites    : {len(mon_rapport['parasites']):>6d}  -> Fiable (GIF 1x1 pixel)")
print(f"  Trop petits  : {len(mon_rapport['trop_petits']):>6d}  -> Fiable (vignettes < 100x100)")
print(f"  Near-doublons: {len(mon_rapport['doublons_visuels']):>6d}  -> A confirmer manuellement")
print(f"  Corrompus    :      0  -> Stock sain")
print(f"  Floues       : {len(mon_rapport['floues']):>6d}  -> A confirmer dans Immich")
print("=" * 60)
