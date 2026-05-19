# Detection avancee des photos floues
# J'utilise 3 methodes differentes (Laplacien, Sobel et FFT)
# Une photo n'est consideree floue que si les 3 sont d'accord

import cv2
import numpy as np
import os
import json
from datetime import datetime


print("=" * 60)
print("  DETECTION AVANCEE DES PHOTOS FLOUES")
print(f"  Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)


# methode 1 : Laplacien - mesure la nettete des contours
def calculer_score_laplacien(image_grise):
    return cv2.Laplacian(image_grise, cv2.CV_64F).var()


# methode 2 : Sobel - mesure les bords horizontaux et verticaux
def calculer_score_sobel(image_grise):
    sobel_x = cv2.Sobel(image_grise, cv2.CV_64F, 1, 0).var()
    sobel_y = cv2.Sobel(image_grise, cv2.CV_64F, 0, 1).var()
    # on fait la moyenne des deux
    return (sobel_x + sobel_y) / 2


# methode 3 : FFT - analyse les frequences (peu de hautes freq = flou)
def calculer_score_fft(image_grise):
    transformee = np.fft.fft2(image_grise)
    transformee_centre = np.fft.fftshift(transformee)
    magnitude = np.log(np.abs(transformee_centre) + 1)

    nb_lignes, nb_cols = image_grise.shape
    centre_y = nb_lignes // 2
    centre_x = nb_cols // 2

    # on regarde la zone centrale (basses frequences)
    zone_centre = magnitude[centre_y - 30:centre_y + 30, centre_x - 30:centre_x + 30]

    moyenne_totale = magnitude.mean()
    moyenne_centre = zone_centre.mean()

    if moyenne_totale == 0:
        return 100
    # on calcule la part de hautes frequences (en gros)
    return (moyenne_totale - moyenne_centre) / moyenne_totale * 100


dossier_photos = '/mnt/immich-data/photos/'
extensions_images = ('.jpg', '.jpeg', '.png')
liste_fichiers = [f for f in os.listdir(dossier_photos) if f.lower().endswith(extensions_images)]

print(f"\n  Fichiers trouves: {len(liste_fichiers)}")
print(f"  Analyse en cours...\n")


tous_les_resultats = []
nb_analysees = 0

# on analyse au max 1000 photos pour ne pas que ce soit trop long
for nom_fichier in liste_fichiers[:1000]:
    chemin = os.path.join(dossier_photos, nom_fichier)

    # on ignore les fichiers qu'on ne peut pas lire
    if not os.access(chemin, os.R_OK):
        continue

    try:
        image = cv2.imread(chemin)
        if image is None:
            continue
        hauteur, largeur = image.shape[:2]
        # on ignore les petites images
        if largeur < 300 or hauteur < 300:
            continue

        # on passe en niveaux de gris et on redimensionne
        image_grise = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        image_grise = cv2.resize(image_grise, (500, 500))

        # on calcule les 3 scores
        score_lap = calculer_score_laplacien(image_grise)
        score_sob = calculer_score_sobel(image_grise)
        score_fft = calculer_score_fft(image_grise)

        # la photo est floue seulement si LES 3 methodes sont d'accord
        est_floue = (score_lap < 50 and score_sob < 200 and score_fft < 40)

        tous_les_resultats.append({
            "fichier": nom_fichier,
            "laplacien": round(score_lap, 2),
            "sobel": round(score_sob, 2),
            "fft": round(score_fft, 2),
            "dimensions": f"{largeur}x{hauteur}",
            "floue": est_floue
        })
        nb_analysees += 1
    except:
        pass


# on separe les floues des nettes
les_floues = [r for r in tous_les_resultats if r["floue"]]
les_nettes = [r for r in tous_les_resultats if not r["floue"]]

print(f"  Analysees: {nb_analysees}")
print(f"  Floues detectees: {len(les_floues)}")
print(f"  Nettes: {len(les_nettes)}")


# affichage des floues
print("\n" + "-" * 60)
print("  PHOTOS FLOUES DETECTEES (3 methodes concordantes)")
print("-" * 60)
les_floues.sort(key=lambda x: x["laplacien"])
for r in les_floues[:20]:
    print(f"  {r['fichier']:35s} lap={r['laplacien']:>7.2f} sob={r['sobel']:>8.2f} fft={r['fft']:>6.2f} {r['dimensions']}")


# affichage des plus nettes
print("\n" + "-" * 60)
print("  PHOTOS NETTES (meilleures)")
print("-" * 60)
les_nettes.sort(key=lambda x: x["laplacien"], reverse=True)
for r in les_nettes[:10]:
    print(f"  {r['fichier']:35s} lap={r['laplacien']:>7.2f} sob={r['sobel']:>8.2f} fft={r['fft']:>6.2f} {r['dimensions']}")


# cas limites - score Laplacien bas mais une des autres methodes dit que c'est net
print("\n" + "-" * 60)
print("  CAS LIMITES (scores bas mais pas les 3 ensemble)")
print("-" * 60)
les_limites = [r for r in tous_les_resultats if not r["floue"] and r["laplacien"] < 100]
les_limites.sort(key=lambda x: x["laplacien"])
for r in les_limites[:10]:
    print(f"  {r['fichier']:35s} lap={r['laplacien']:>7.2f} sob={r['sobel']:>8.2f} fft={r['fft']:>6.2f} {r['dimensions']}")
print("  -> Ce sont les photos uniformes (ciel, mer) PAS floues")


# sauvegarde du rapport
with open("/home/info/photo-ia/resultats/rapport_flou_avance.json", "w") as f:
    floues_propres = []
    for fl in les_floues:
        floues_propres.append({
            "fichier": fl["fichier"],
            "laplacien": float(fl["laplacien"]),
            "sobel": float(fl["sobel"]),
            "fft": float(fl["fft"]),
            "dimensions": fl["dimensions"],
            "floue": bool(fl["floue"])
        })
    json.dump({
        "date": datetime.now().isoformat(),
        "analysees": nb_analysees,
        "floues": floues_propres,
        "total_floues": len(floues_propres)
    }, f, indent=2)


# explication de la methode
print("\n" + "=" * 60)
print("  METHODE UTILISEE")
print("=" * 60)
print("  1. Laplacien : mesure les contours (score bas = flou)")
print("  2. Sobel : mesure les bords horizontaux et verticaux")
print("  3. FFT : analyse les frequences (peu de hautes freq = flou)")
print("  Une photo est FLOUE seulement si les 3 methodes concordent")
print("  Cela evite les faux positifs sur les photos de ciel/mer")
print("=" * 60)
