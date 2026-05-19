# Script de classification avec MobileNetV3
# Premier essai pour classer les photos avec un modele connu (entrainé sur ImageNet)
# Spoiler : ca marche pas tres bien pour les categories DREAL

import tensorflow as tf
import numpy as np
import json
import subprocess
import os
import requests
from datetime import datetime
from PIL import Image
from io import BytesIO
from categories import CATEGORIES


# parametres Immich (au cas ou on en aurait besoin)
URL_IMMICH = "http://10.20.210.13:2283/api"
MA_CLE_API = "VOTRE_CLE_API_ICI"
mes_entetes = {"x-api-key": MA_CLE_API}


print("=" * 60)
print("  CLASSIFICATION IA - PHOTO-IA DREAL CORSE")
print(f"  Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)


# ETAPE 1 : on charge le modele
print("\n[1/4] Chargement du modele MobileNetV3...")
le_modele = tf.keras.applications.MobileNetV3Large(
    weights="/home/info/photo-ia/weights_mobilenet_v3_large_224_1.0_float.h5",
    include_top=True,
    input_shape=(224, 224, 3)
)
print("  Modele charge avec succes")


# je charge la liste des 1000 classes d'ImageNet
with open("/home/info/.keras/datasets/imagenet_class_index.json") as fichier_index:
    INDEX_IMAGENET = json.load(fichier_index)


# table de correspondance : pour chaque categorie DREAL, les mots-cles ImageNet associes
# l'idee : si le modele dit "bird" on classe en "faune", si il dit "beach" on classe en "littoral", etc.
CORRESPONDANCE_IMAGENET_VERS_DREAL = {
    "faune": ["bird", "fish", "snake", "lizard", "turtle", "dog", "cat", "horse", "deer", "bear", "wolf", "fox", "rabbit", "mouse", "frog", "butterfly", "bee", "ant", "spider", "eagle", "hawk", "owl", "parrot", "flamingo", "pelican", "heron", "crane", "swan", "duck", "goose", "chicken", "hen", "cock", "peacock", "jellyfish", "starfish", "sea_urchin", "coral", "shark", "whale", "dolphin", "seal", "otter", "goldfish", "tench", "crab", "lobster", "snail", "slug", "worm"],
    "flore": ["flower", "daisy", "rose", "sunflower", "tulip", "lily", "orchid", "mushroom", "tree", "palm", "oak", "pine", "acorn", "leaf", "hay", "grass"],
    "littoral": ["beach", "seashore", "coast", "cliff", "sandbar", "coral_reef", "sea", "ocean", "wave", "lighthouse"],
    "montagne": ["mountain", "alp", "volcano", "ridge", "valley", "cliff", "rock", "stone"],
    "milieu_aquatique": ["river", "lake", "pond", "stream", "waterfall", "dam", "reservoir"],
    "batiment": ["building", "house", "church", "castle", "palace", "mosque", "monastery", "tower", "skyscraper", "barn", "greenhouse", "prison", "library", "school"],
    "infrastructure": ["bridge", "road", "highway", "street", "railroad", "station", "airport", "dock", "pier", "dam", "car", "truck", "bus", "train", "boat", "ship"],
    "pollution": ["garbage", "trash", "dump", "waste", "oil", "smoke", "smog"],
    "aerien": ["aerial", "satellite", "map"],
    "document": ["envelope", "book", "notebook", "newspaper", "magazine", "menu", "web_site", "monitor", "screen", "keyboard"],
    "portrait": ["person", "face", "man", "woman", "child", "baby", "crowd", "suit", "tie", "dress"],
    "energie": ["windmill", "solar", "power_line", "electric"],
    "risque_naturel": ["fire", "flood", "volcano", "avalanche", "tornado", "storm", "lightning"],
    "paysage": ["landscape", "valley", "field", "meadow", "garden", "park", "forest", "jungle", "desert", "prairie", "lakeside", "promontory"],
    "zone_humide": ["marsh", "swamp", "bog", "wetland"]
}


# cette fonction prend les predictions du modele et trouve la categorie DREAL
def trouver_categorie_dreal(les_predictions):
    # on prend les 5 meilleures predictions du modele
    indices_top5 = np.argsort(les_predictions[0])[::-1][:5]
    top5_decodees = [("n", INDEX_IMAGENET[str(i)][1], les_predictions[0][i]) for i in indices_top5]

    meilleure_categorie = "paysage"  # par defaut
    meilleur_score = 0

    # pour chaque prediction on regarde si elle matche une categorie DREAL
    for _, label_imagenet, score in top5_decodees:
        label_minuscule = label_imagenet.lower()
        for nom_categorie, liste_mots_cles in CORRESPONDANCE_IMAGENET_VERS_DREAL.items():
            for mot_cle in liste_mots_cles:
                if mot_cle in label_minuscule:
                    if score > meilleur_score:
                        meilleur_score = score
                        meilleure_categorie = nom_categorie

    return meilleure_categorie, meilleur_score, top5_decodees


# ETAPE 2 : on recupere la liste des photos
print("\n[2/4] Recuperation des photos depuis le disque...")
dossier_photos = "/mnt/immich-data/photos/"
extensions_ok = ('.jpg', '.jpeg', '.png')

liste_fichiers = [
    f for f in os.listdir(dossier_photos)
    if f.lower().endswith(extensions_ok)
    and os.access(os.path.join(dossier_photos, f), os.R_OK)
]
print(f"  {len(liste_fichiers)} photos trouvees")


# ETAPE 3 : on classifie chaque photo
print("\n[3/4] Classification en cours...")
mes_resultats = []
nb_erreurs = 0
NB_MAX_PHOTOS = min(len(liste_fichiers), 500)

for numero, nom_fichier in enumerate(liste_fichiers[:NB_MAX_PHOTOS]):
    try:
        chemin = os.path.join(dossier_photos, nom_fichier)
        # on ouvre l'image et on la prepare pour le modele
        image = Image.open(chemin).convert("RGB")
        image = image.resize((224, 224))  # le modele veut du 224x224
        tableau_image = np.array(image) / 255.0
        tableau_image = np.expand_dims(tableau_image, axis=0)
        tableau_image = tf.keras.applications.mobilenet_v3.preprocess_input(tableau_image * 255)

        # on demande au modele de predire
        predictions = le_modele.predict(tableau_image, verbose=0)
        categorie, score_confiance, top5 = trouver_categorie_dreal(predictions)

        mes_resultats.append({
            "fichier": nom_fichier,
            "categorie": categorie,
            "categorie_nom": CATEGORIES[categorie]["nom"],
            "confiance": round(float(score_confiance), 4),
            "top5_imagenet": [(label, round(float(s), 4)) for _, label, s in top5],
            "service": CATEGORIES[categorie]["service"]
        })

        # affichage tous les 10 pour pas spam
        if (numero + 1) % 10 == 0:
            print(f"  {numero + 1}/{NB_MAX_PHOTOS} classifiees...")
    except Exception as erreur:
        nb_erreurs += 1

print(f"  Termine: {len(mes_resultats)} classifiees, {nb_erreurs} erreurs")


# ETAPE 4 : on calcule les stats
print("\n[4/4] Statistiques de classification...")
from collections import Counter
stats_par_categorie = Counter(r["categorie"] for r in mes_resultats)

print(f"\n  {'Categorie':<25s} {'Nombre':>8s} {'%':>8s}")
print("  " + "-" * 45)
for nom_cat, nb in stats_par_categorie.most_common():
    pourcentage = round(nb / len(mes_resultats) * 100, 1)
    nom_complet = CATEGORIES[nom_cat]["nom"]
    print(f"  {nom_complet:<25s} {nb:>8d} {pourcentage:>7.1f}%")


# repartition par niveau de confiance
nb_confiance_haute = len([r for r in mes_resultats if r["confiance"] > 0.7])
nb_confiance_moyenne = len([r for r in mes_resultats if 0.3 <= r["confiance"] <= 0.7])
nb_confiance_basse = len([r for r in mes_resultats if r["confiance"] < 0.3])

print(f"\n  Confiance haute (> 70%)  : {nb_confiance_haute}")
print(f"  Confiance moyenne (30-70%): {nb_confiance_moyenne}")
print(f"  Confiance basse (< 30%)  : {nb_confiance_basse}")
print(f"  -> Les photos avec confiance basse iront dans l'album 'A verifier'")


# sauvegarde du rapport
mon_rapport = {
    "date": datetime.now().isoformat(),
    "modele": "MobileNetV3Large",
    "total_classifiees": len(mes_resultats),
    "erreurs": nb_erreurs,
    "statistiques": dict(stats_par_categorie),
    "resultats": mes_resultats[:100]  # on garde que 100 pour pas que le JSON soit trop gros
}

with open("/home/info/photo-ia/resultats/rapport_classification.json", "w") as f:
    json.dump(mon_rapport, f, indent=2, ensure_ascii=False)

print(f"\n  Rapport sauvegarde dans resultats/rapport_classification.json")
print("=" * 60)
