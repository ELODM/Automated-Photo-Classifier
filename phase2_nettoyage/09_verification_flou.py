# Verification du rapport de detection des floues
# On relit le JSON et on affiche bien chaque photo a verifier dans Immich

import json
import os
from datetime import datetime


print("=" * 60)
print("  VERIFICATION DETECTION FLOU AVANCEE")
print(f"  Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)


# on charge le rapport
with open("/home/info/photo-ia/resultats/rapport_flou_avance.json", "r") as f:
    mon_rapport = json.load(f)


liste_floues = mon_rapport.get("floues", [])
nb_total_analysees = mon_rapport.get("analysees", 0)

print(f"\n  Photos analysees: {nb_total_analysees}")
print(f"  Photos floues detectees: {len(liste_floues)}")


# si aucune floue detectee tant mieux
if len(liste_floues) == 0:
    print("\n  Aucune photo floue detectee avec les 3 methodes.")
    print("  Le stock est globalement net.")
else:
    print("\n" + "-" * 60)
    print("  PHOTOS FLOUES A VERIFIER DANS IMMICH")
    print("-" * 60)

    for numero, photo in enumerate(liste_floues):
        score_lap = photo.get("laplacien", 0)
        score_sob = photo.get("sobel", 0)
        score_fft = photo.get("fft", 0)
        dim = photo.get("dimensions", "?")
        nom = photo.get("fichier", "?")

        # niveau de confiance selon le score Laplacien
        if score_lap < 10:
            niveau_confiance = "CERTAINE (tres floue)"
        elif score_lap < 30:
            niveau_confiance = "HAUTE (floue)"
        else:
            niveau_confiance = "MOYENNE (a verifier)"

        print(f"\n  Photo {numero + 1}: {nom}")
        print(f"    Dimensions  : {dim}")
        print(f"    Laplacien   : {score_lap:>7.2f} (bas = flou)")
        print(f"    Sobel       : {score_sob:>8.2f} (bas = flou)")
        print(f"    FFT         : {score_fft:>6.2f} (bas = flou)")
        print(f"    Confiance   : {niveau_confiance}")
        print(f"    -> Cherchez '{nom}' dans Immich pour verifier")


# explication pour l'utilisateur
print("\n" + "-" * 60)
print("  COMMENT VERIFIER")
print("-" * 60)
print("  1. Ouvrez http://10.20.210.13:2283")
print("  2. Cherchez le nom de chaque fichier")
print("  3. Regardez si la photo est vraiment floue")
print("  4. Si OUI -> on la supprime")
print("  5. Si NON -> faux positif, on la garde")


# resume de la classification
if len(liste_floues) > 0:
    vraies_floues = [f["fichier"] for f in liste_floues if f.get("laplacien", 0) < 20]
    a_verifier = [f["fichier"] for f in liste_floues if f.get("laplacien", 0) >= 20]
    print(f"\n  Resume :")
    print(f"    Quasi certaines (lap < 20) : {len(vraies_floues)}")
    print(f"    A verifier (lap 20-50)     : {len(a_verifier)}")


# explication de la fiabilite
print("\n" + "=" * 60)
print("  FIABILITE DE LA METHODE")
print("=" * 60)
print("  3 methodes concordantes = tres peu de faux positifs")
print("  Laplacien seul : beaucoup de faux positifs (ciel, mer)")
print("  Laplacien + Sobel + FFT : detection fiable")
print("=" * 60)
