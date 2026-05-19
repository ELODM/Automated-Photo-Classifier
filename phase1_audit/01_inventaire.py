# Script pour faire l'inventaire des photos de la DREAL
# C'est mon premier script pour le stage, il regarde la base de donnees Immich

import json
import subprocess
from datetime import datetime


# petite fonction pour lancer une requete SQL dans le docker postgres
def faire_requete_sql(ma_requete):
    # j'utilise docker exec pour parler a la base
    commande = [
        "docker", "exec", "immich_postgres",
        "psql", "-U", "postgres", "-d", "immich",
        "-t", "-A", "-c", ma_requete
    ]
    resultat = subprocess.check_output(commande)
    # on decode parce que ca sort en bytes
    return resultat.decode().strip()


print("=== INVENTAIRE DU STOCK PHOTO DREAL ===")
maintenant = datetime.now()
print(f"Date: {maintenant.strftime('%d/%m/%Y %H:%M')}")


# on compte combien il y a de trucs en tout
nombre_total = faire_requete_sql('SELECT COUNT(*) FROM asset')
# on compte les images
nombre_images = faire_requete_sql("SELECT COUNT(*) FROM asset WHERE type='IMAGE'")
# et les videos
nombre_videos = faire_requete_sql("SELECT COUNT(*) FROM asset WHERE type='VIDEO'")

print(f"\nTotal assets: {nombre_total}")
print(f"Images: {nombre_images}")
print(f"Videos: {nombre_videos}")


# maintenant on regarde les formats de fichiers (jpg, png, etc)
print("\n=== FORMATS ===")
requete_formats = """SELECT LOWER(SPLIT_PART("originalPath", '.', -1)) as ext, COUNT(*) as nb FROM asset GROUP BY ext ORDER BY nb DESC LIMIT 20"""
les_formats = faire_requete_sql(requete_formats)

# on coupe ligne par ligne pour afficher proprement
for ligne in les_formats.split('\n'):
    if '|' in ligne:
        extension, combien = ligne.split('|')
        print(f"  {extension.strip():10s}: {combien.strip()}")


# combien de photos ont les coordonnees GPS
print("\n=== METADONNEES GPS ===")
photos_avec_gps = faire_requete_sql("SELECT COUNT(*) FROM asset_exif WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
total_exif = faire_requete_sql("SELECT COUNT(*) FROM asset_exif")
print(f"  Avec GPS: {photos_avec_gps}/{total_exif}")


# combien ont une date dans les EXIF
print("\n=== METADONNEES DATE ===")
photos_avec_date = faire_requete_sql("""SELECT COUNT(*) FROM asset_exif WHERE "dateTimeOriginal" IS NOT NULL""")
print(f"  Avec date EXIF: {photos_avec_date}/{total_exif}")


# la liste des albums
print("\n=== ALBUMS ===")
liste_albums = faire_requete_sql("""SELECT "albumName", "assetCount" FROM album""")
for ligne in liste_albums.split('\n'):
    if '|' in ligne:
        nom_album, nb_photos = ligne.split('|')
        print(f"  - {nom_album.strip()} ({nb_photos.strip()} photos)")


# les utilisateurs qui sont dans Immich
print("\n=== UTILISATEURS ===")
liste_users = faire_requete_sql('SELECT name, email FROM "user"')
for ligne in liste_users.split('\n'):
    if '|' in ligne:
        nom, mail = ligne.split('|')
        print(f"  - {nom.strip()} ({mail.strip()})")


# la place que ca prend sur le disque
print("\n=== TAILLE SUR DISQUE ===")
taille_disque = subprocess.check_output("du -sh /mnt/immich-data/photos/", shell=True).decode().strip()
print(f"  {taille_disque}")


# je sauvegarde tout dans un fichier json pour le garder
mon_rapport = {
    "date": datetime.now().isoformat(),
    "total": int(nombre_total),
    "images": int(nombre_images),
    "videos": int(nombre_videos),
    "avec_gps": int(photos_avec_gps),
    "avec_date": int(photos_avec_date),
    "total_exif": int(total_exif)
}

# on ecrit le json dans le dossier resultats
fichier_sortie = "/home/info/photo-ia/resultats/rapport_inventaire.json"
with open(fichier_sortie, "w") as f:
    json.dump(mon_rapport, f, indent=2)

print("=== FIN INVENTAIRE ===")
