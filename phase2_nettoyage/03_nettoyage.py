# Script pour faire le nettoyage du stock photo
# Premiere version - je detecte les fichiers a probleme

import json
import subprocess
import os
from datetime import datetime


# fonction pour faire une requete SQL dans le docker postgres d'Immich
def faire_requete_sql(ma_requete):
    commande = [
        "docker", "exec", "immich_postgres",
        "psql", "-U", "postgres", "-d", "immich",
        "-t", "-A", "-c", ma_requete
    ]
    resultat = subprocess.check_output(commande)
    return resultat.decode().strip()


print("=" * 60)
print("  NETTOYAGE DU STOCK PHOTO - DREAL CORSE")
maintenant = datetime.now()
print(f"  Date: {maintenant.strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)


# je prepare un dictionnaire pour stocker tout ce que je trouve
mon_rapport = {
    "date": datetime.now().isoformat(),
    "parasites": [],
    "trop_petits": [],
    "doublons": [],
    "corrompus": [],
    "floues": []
}


# ETAPE 1 : les petits GIF parasites (genre les pixels invisibles des mails)
print("\n[1/5] Detection des fichiers parasites (GIF < 10 Ko)...")
requete_parasites = """SELECT a.id, a."originalFileName", ae."fileSizeInByte" FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE LOWER(a."originalPath") LIKE '%.gif' AND ae."fileSizeInByte" < 10240"""
les_parasites = faire_requete_sql(requete_parasites)

nb_parasites = 0
for ligne in les_parasites.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        if len(morceaux) >= 3:
            # je recupere l'id, le nom et la taille
            taille_int = int(morceaux[2].strip()) if morceaux[2].strip().isdigit() else 0
            mon_rapport["parasites"].append({
                "id": morceaux[0].strip(),
                "nom": morceaux[1].strip(),
                "taille": taille_int
            })
            nb_parasites += 1
print(f"  -> {nb_parasites} fichiers GIF parasites detectes")


# ETAPE 2 : les autres fichiers trop petits (vignettes etc)
print("\n[2/5] Detection des fichiers trop petits (< 5 Ko)...")
requete_petits = """SELECT a.id, a."originalFileName", ae."fileSizeInByte" FROM asset a JOIN asset_exif ae ON a.id = ae."assetId" WHERE ae."fileSizeInByte" < 5120 AND ae."fileSizeInByte" > 0 AND LOWER(a."originalPath") NOT LIKE '%.gif'"""
les_petits = faire_requete_sql(requete_petits)

nb_petits = 0
for ligne in les_petits.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        if len(morceaux) >= 3:
            taille_int = int(morceaux[2].strip()) if morceaux[2].strip().isdigit() else 0
            mon_rapport["trop_petits"].append({
                "id": morceaux[0].strip(),
                "nom": morceaux[1].strip(),
                "taille": taille_int
            })
            nb_petits += 1
print(f"  -> {nb_petits} fichiers trop petits detectes")


# ETAPE 3 : les doublons (meme checksum = meme contenu exact)
print("\n[3/5] Detection des doublons (meme checksum)...")
requete_doublons = """SELECT checksum, COUNT(*) as nb FROM asset WHERE checksum IS NOT NULL GROUP BY checksum HAVING COUNT(*) > 1 ORDER BY nb DESC LIMIT 500"""
les_doublons = faire_requete_sql(requete_doublons)

nb_groupes_doublons = 0
total_fichiers_doublons = 0
for ligne in les_doublons.split('\n'):
    if '|' in ligne:
        morceaux = ligne.split('|')
        if len(morceaux) >= 2:
            nb_copies = int(morceaux[1].strip()) if morceaux[1].strip().isdigit() else 0
            if nb_copies > 1:
                nb_groupes_doublons += 1
                # on garde nb-1 fichiers a supprimer (on garde toujours un original)
                total_fichiers_doublons += (nb_copies - 1)
                mon_rapport["doublons"].append({
                    "checksum": morceaux[0].strip(),
                    "copies": nb_copies,
                    "a_supprimer": nb_copies - 1
                })
print(f"  -> {nb_groupes_doublons} groupes de doublons")
print(f"  -> {total_fichiers_doublons} fichiers en double")


# ETAPE 4 : fichiers corrompus (j'utilise Pillow pour tester si l'image s'ouvre)
print("\n[4/5] Detection des fichiers corrompus...")
nb_corrompus = 0
try:
    from PIL import Image
    dossier_photos = "/mnt/immich-data/photos/"
    # je prends que les 500 premiers pour ne pas tout scanner
    liste_fichiers = os.listdir(dossier_photos)[:500]
    for nom_fichier in liste_fichiers:
        chemin = os.path.join(dossier_photos, nom_fichier)
        if os.path.isfile(chemin):
            try:
                image = Image.open(chemin)
                image.verify()  # ca leve une exception si corrompu
            except Exception:
                mon_rapport["corrompus"].append({"fichier": nom_fichier})
                nb_corrompus += 1
    print(f"  -> {nb_corrompus} corrompus sur {len(liste_fichiers)} analyses")
except ImportError:
    print("  -> Pillow non disponible")


# ETAPE 5 : photos floues (avec OpenCV et la variance du Laplacien)
print("\n[5/5] Detection des photos floues...")
nb_floues = 0
SEUIL_FLOU = 100.0  # en dessous c'est flou (j'ai trouve ca sur internet)
try:
    import cv2
    dossier_photos = "/mnt/immich-data/photos/"
    # je prends que les images (pas les videos)
    liste_fichiers = [f for f in os.listdir(dossier_photos) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))][:200]
    for nom_fichier in liste_fichiers:
        chemin = os.path.join(dossier_photos, nom_fichier)
        try:
            image = cv2.imread(chemin)
            if image is not None:
                # on passe en gris puis on calcule le score
                image_grise = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                score_flou = cv2.Laplacian(image_grise, cv2.CV_64F).var()
                if score_flou < SEUIL_FLOU:
                    mon_rapport["floues"].append({
                        "fichier": nom_fichier,
                        "score": round(score_flou, 2)
                    })
                    nb_floues += 1
        except Exception:
            pass
    print(f"  -> {nb_floues} floues sur {len(liste_fichiers)} analysees")
except ImportError:
    print("  -> OpenCV non disponible")


# resume de tout
print("\n" + "=" * 60)
print("  RESUME")
print("=" * 60)
print(f"  Parasites       : {len(mon_rapport['parasites'])}")
print(f"  Trop petits     : {len(mon_rapport['trop_petits'])}")
print(f"  Doublons        : {total_fichiers_doublons} fichiers")
print(f"  Corrompus       : {len(mon_rapport['corrompus'])}")
print(f"  Floues          : {len(mon_rapport['floues'])}")

total_candidats = (len(mon_rapport['parasites'])
                   + len(mon_rapport['trop_petits'])
                   + total_fichiers_doublons
                   + len(mon_rapport['corrompus'])
                   + len(mon_rapport['floues']))
print(f"  TOTAL           : {total_candidats} candidats")
print("\n  Aucun fichier supprime. Validation requise.")


# on sauvegarde le rapport
with open("/home/info/photo-ia/resultats/rapport_nettoyage.json", "w") as f:
    json.dump(mon_rapport, f, indent=2)


print("=" * 60)
