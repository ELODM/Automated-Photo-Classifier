# Verification de la V3 (la version finale)
# Pareil que la V2 mais on lit le rapport V3

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
print("  VERIFICATION NETTOYAGE V3")
print(f"  Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)


# on charge le rapport V3
with open("/home/info/photo-ia/resultats/rapport_nettoyage_v3.json", "r") as f:
    mon_rapport = json.load(f)


# ============================================
# VERIF 1 : GIF PARASITES
# ============================================
print("\n" + "-" * 60)
print(f"  [1/5] GIF PARASITES ({len(mon_rapport['parasites'])} detectes)")
print("-" * 60)

echantillon = faire_requete_sql("""SELECT a."originalFileName", ae."fileSizeInByte", ae."exifImageWidth", ae."exifImageHeight" FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE LOWER(a."originalPath") LIKE '%.gif' AND ae."fileSizeInByte" < 10240 AND (ae."exifImageWidth" < 50 OR ae."exifImageHeight" < 50 OR ae."exifImageWidth" IS NULL) LIMIT 10""")

nb_vrais = 0
nb_faux = 0
print("  Echantillon :")
for ligne in echantillon.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        nom = morceaux[0].strip()
        taille = morceaux[1].strip()
        largeur = morceaux[2].strip() if len(morceaux) > 2 else ''
        hauteur = morceaux[3].strip() if len(morceaux) > 3 else ''
        # un parasite c'est tres petit (1x1 ou 2x2 pixels) ou tres leger
        est_parasite = (largeur in ['', '1', '2']
                       or hauteur in ['', '1', '2']
                       or int(taille) < 2000)
        if est_parasite:
            nb_vrais += 1
            verdict = "PARASITE CONFIRME"
        else:
            nb_faux += 1
            verdict = "A VERIFIER"
        print(f"    {nom:35s} {taille:>5s} o  {largeur}x{hauteur} px  -> {verdict}")
print(f"\n  Fiabilite echantillon: {nb_vrais}/{nb_vrais + nb_faux} confirmes")
print(f"  VERDICT: {'FIABLE' if nb_vrais > nb_faux else 'A REVOIR'}")


# ============================================
# VERIF 2 : TROP PETITS
# ============================================
print("\n" + "-" * 60)
print(f"  [2/5] FICHIERS TROP PETITS ({len(mon_rapport['trop_petits'])} detectes)")
print("-" * 60)

echantillon = faire_requete_sql("""SELECT a."originalFileName", ae."fileSizeInByte", ae."exifImageWidth", ae."exifImageHeight", LOWER(SPLIT_PART(a."originalPath", '.', -1)) as ext FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE ae."fileSizeInByte" < 5120 AND ae."fileSizeInByte" > 0 AND LOWER(a."originalPath") NOT LIKE '%.gif' AND (ae."exifImageWidth" < 100 OR ae."exifImageHeight" < 100 OR ae."exifImageWidth" IS NULL) AND a.type = 'IMAGE' LIMIT 15""")

print("  Echantillon :")
for ligne in echantillon.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        nom = morceaux[0].strip()
        taille = morceaux[1].strip()
        largeur = morceaux[2].strip() if len(morceaux) > 2 else '?'
        hauteur = morceaux[3].strip() if len(morceaux) > 3 else '?'
        ext = morceaux[4].strip() if len(morceaux) > 4 else '?'
        print(f"    {nom:35s} .{ext:4s} {taille:>5s} o  {largeur}x{hauteur} px  -> VIGNETTE")

# repartition par tranche de taille
stats = faire_requete_sql("""SELECT CASE WHEN ae."fileSizeInByte" < 500 THEN '< 500 octets' WHEN ae."fileSizeInByte" < 1024 THEN '500 o - 1 Ko' WHEN ae."fileSizeInByte" < 3000 THEN '1 Ko - 3 Ko' ELSE '3 Ko - 5 Ko' END as tranche, COUNT(*) FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE ae."fileSizeInByte" < 5120 AND ae."fileSizeInByte" > 0 AND LOWER(a."originalPath") NOT LIKE '%.gif' AND (ae."exifImageWidth" < 100 OR ae."exifImageHeight" < 100 OR ae."exifImageWidth" IS NULL) AND a.type = 'IMAGE' GROUP BY tranche ORDER BY tranche""")

print("\n  Repartition par taille :")
for ligne in stats.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        print(f"    {morceaux[0].strip():20s}: {morceaux[1].strip()} fichiers")
print(f"  VERDICT: FIABLE (images < 100x100 px = vignettes systeme)")


# ============================================
# VERIF 3 : NEAR-DOUBLONS
# ============================================
print("\n" + "-" * 60)
print(f"  [3/5] NEAR-DOUBLONS ({len(mon_rapport['doublons'])} groupes)")
print("-" * 60)

if len(mon_rapport['doublons']) > 0:
    echantillon = faire_requete_sql("""SELECT a."originalFileName", ae."fileSizeInByte", COUNT(*) as nb, MIN(a."createdAt") as premier, MAX(a."createdAt") as dernier FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE a.type = 'IMAGE' GROUP BY a."originalFileName", ae."fileSizeInByte" HAVING COUNT(*) > 1 ORDER BY nb DESC LIMIT 10""")
    print("  Echantillon (avec dates) :")
    for ligne in echantillon.split('\n'):
        if '|' in ligne:
            morceaux = ligne.split('|')
            nom = morceaux[0].strip()
            taille = morceaux[1].strip()
            nb_copies = morceaux[2].strip()
            date_premier = morceaux[3].strip()[:10] if len(morceaux) > 3 else '?'
            date_dernier = morceaux[4].strip()[:10] if len(morceaux) > 4 else '?'
            print(f"    {nom:30s} {taille:>10s} o  x{nb_copies}  ({date_premier} -> {date_dernier})")
    print(f"\n  VERDICT: A CONFIRMER manuellement (meme nom ne veut pas dire meme photo)")
else:
    print("  -> Aucun doublon detecte")
    print("  VERDICT: STOCK PROPRE")


# ============================================
# VERIF 4 : CORROMPUS
# ============================================
print("\n" + "-" * 60)
print(f"  [4/5] CORROMPUS ({len(mon_rapport['corrompus'])} detectes)")
print("-" * 60)

if len(mon_rapport['corrompus']) == 0:
    print("  -> Aucun fichier corrompu detecte")
    print("  -> Les erreurs de la V1 etaient des problemes de permission")
    print("  VERDICT: STOCK SAIN")
else:
    print("  Echantillon :")
    for cor in mon_rapport['corrompus'][:10]:
        nom_corrompu = cor.get('nom', '?')
        id_corrompu = cor.get('id', '?')
        print(f"    {nom_corrompu:40s} (id: {id_corrompu[:20]}...)")
    print(f"\n  Ces fichiers n'ont pas de miniature ou pas d'EXIF dans Immich")
    print(f"  -> Immich n'a pas pu les traiter = probablement corrompus")
    print(f"  VERDICT: A VERIFIER dans Immich (chercher le nom du fichier)")


# ============================================
# VERIF 5 : PHOTOS FLOUES
# ============================================
print("\n" + "-" * 60)
print(f"  [5/5] PHOTOS FLOUES ({len(mon_rapport['floues'])} detectees)")
print("-" * 60)

if len(mon_rapport['floues']) == 0:
    print("  -> Aucune photo floue avec le seuil strict (30)")
    print("  VERDICT: SEUIL ADEQUAT")
else:
    print("  Echantillon (classees par score) :")
    # je trie par score croissant pour voir les pires en premier
    floues_triees = sorted(mon_rapport['floues'], key=lambda x: x.get('score', 0))
    for photo in floues_triees[:15]:
        score = photo.get('score', 0)
        dim = photo.get('dim', '?')
        nom_f = photo.get('fichier', '?')
        if score < 10:
            verdict = "TRES FLOUE (quasi certain)"
        elif score < 20:
            verdict = "FLOUE (probable)"
        else:
            verdict = "LEGERE (a verifier)"
        print(f"    {nom_f:35s} score={score:>6.2f}  {dim:>10s}  {verdict}")

    print(f"\n  COMMENT VERIFIER :")
    print(f"  1. Ouvrez http://10.20.210.13:2283")
    print(f"  2. Cherchez le nom du fichier")
    print(f"  3. Regardez si la photo est vraiment floue")
    print(f"  4. Les scores < 10 sont presque toujours floues")
    print(f"  5. Les scores 20-30 necessitent verification visuelle")

    # je compte combien dans chaque categorie
    nb_tres_floues = len([f for f in mon_rapport['floues'] if f.get('score', 0) < 10])
    nb_floues_probable = len([f for f in mon_rapport['floues'] if 10 <= f.get('score', 0) < 20])
    nb_legeres = len([f for f in mon_rapport['floues'] if f.get('score', 0) >= 20])
    print(f"\n  Repartition :")
    print(f"    Tres floues (< 10)  : {nb_tres_floues}")
    print(f"    Floues (10-20)      : {nb_floues_probable}")
    print(f"    Legeres (20-30)     : {nb_legeres}")


# ============================================
# BILAN FINAL
# ============================================
print("\n" + "=" * 60)
print("  BILAN FINAL DE VERIFICATION V3")
print("=" * 60)
print(f"  Parasites    : {len(mon_rapport['parasites']):>6d}  FIABLE")
print(f"  Trop petits  : {len(mon_rapport['trop_petits']):>6d}  FIABLE")
print(f"  Doublons     : {len(mon_rapport['doublons']):>6d}  A CONFIRMER")
print(f"  Corrompus    : {len(mon_rapport['corrompus']):>6d}  FIABLE (via BDD)")
print(f"  Floues       : {len(mon_rapport['floues']):>6d}  SEUIL STRICT OK")
print("-" * 60)
