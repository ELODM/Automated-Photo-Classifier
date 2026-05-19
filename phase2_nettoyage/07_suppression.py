# Script pour vraiment supprimer les fichiers a probleme dans Immich
# ATTENTION : ca passe les fichiers dans la corbeille (30 jours avant suppression vraie)

import json
import requests
import os
from datetime import datetime


# parametres de l'API Immich
URL_API_IMMICH = "http://10.20.210.13:2283/api"
MA_CLE_API = "VOTRE_CLE_API_ICI"
mes_entetes = {"x-api-key": MA_CLE_API, "Content-Type": "application/json"}

# si je mets True ca fait juste une simulation, rien n'est supprime pour de vrai
MODE_SIMULATION = False


print("=" * 60)
if MODE_SIMULATION:
    print("  SUPPRESSION - MODE SIMULATION")
else:
    print("  SUPPRESSION - MODE REEL")
print(f"  Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)


# on charge le rapport du nettoyage V3
with open("/home/info/photo-ia/resultats/rapport_nettoyage_v3.json", "r") as f:
    mon_rapport = json.load(f)


# on charge aussi le rapport des floues avancees s'il existe
liste_floues_avancees = []
chemin_rapport_flou = "/home/info/photo-ia/resultats/rapport_flou_avance.json"
if os.path.exists(chemin_rapport_flou):
    with open(chemin_rapport_flou, "r") as f:
        donnees_flou = json.load(f)
        liste_floues_avancees = donnees_flou.get("floues", [])


print(f"\n  Sources utilisees :")
print(f"    rapport_nettoyage_v3.json (parasites, petits, doublons, corrompus)")
print(f"    rapport_flou_avance.json (floues 3 methodes)")
print(f"\n  Parasites       : {len(mon_rapport['parasites'])}")
print(f"  Trop petits     : {len(mon_rapport['trop_petits'])}")
print(f"  Doublons        : {len(mon_rapport['doublons'])} (NON supprime - manuel)")
print(f"  Corrompus       : {len(mon_rapport['corrompus'])}")
print(f"  Floues avancees : {len(liste_floues_avancees)}")


# fonction qui supprime une liste d'ids via l'API d'Immich
def supprimer_les_fichiers(liste_ids, nom_categorie):
    if len(liste_ids) == 0:
        print(f"  {nom_categorie}: aucun fichier")
        return 0

    # en mode simulation on fait rien on dit juste ce qui aurait ete fait
    if MODE_SIMULATION:
        print(f"  [SIMULATION] {nom_categorie}: {len(liste_ids)} seraient supprimes")
        return len(liste_ids)

    nb_supprimes = 0
    # on envoie par paquets de 50 (sinon l'API risque de saturer)
    for i in range(0, len(liste_ids), 50):
        mon_paquet = liste_ids[i:i+50]
        try:
            reponse = requests.delete(
                f"{URL_API_IMMICH}/assets",
                headers=mes_entetes,
                json={"ids": mon_paquet, "force": False}
            )
            if reponse.status_code in [200, 204]:
                nb_supprimes += len(mon_paquet)
                print(f"    Batch {i//50 + 1}: {len(mon_paquet)} supprimes")
            else:
                print(f"    Batch {i//50 + 1}: ERREUR {reponse.status_code}")
        except Exception as erreur:
            print(f"    ERREUR: {erreur}")
    return nb_supprimes


# ETAPE 1 : suppression des parasites
print("\n" + "-" * 60)
print("  [1/4] PARASITES GIF")
ids_parasites = [p["id"] for p in mon_rapport["parasites"] if "id" in p]
nb_suppr_parasites = supprimer_les_fichiers(ids_parasites, "Parasites")


# ETAPE 2 : suppression des trop petits
print("\n" + "-" * 60)
print("  [2/4] FICHIERS TROP PETITS")
ids_petits = [p["id"] for p in mon_rapport["trop_petits"] if "id" in p]
nb_suppr_petits = supprimer_les_fichiers(ids_petits, "Trop petits")


# ETAPE 3 : suppression des corrompus
print("\n" + "-" * 60)
print("  [3/4] CORROMPUS")
ids_corrompus = [p["id"] for p in mon_rapport["corrompus"] if "id" in p]
nb_suppr_corrompus = supprimer_les_fichiers(ids_corrompus, "Corrompus")


# ETAPE 4 : suppression des floues (si on a les ids)
print("\n" + "-" * 60)
print("  [4/4] PHOTOS FLOUES (3 methodes)")
ids_floues = []
for flou in liste_floues_avancees:
    if "id" in flou:
        ids_floues.append(flou["id"])

if len(ids_floues) > 0:
    nb_suppr_floues = supprimer_les_fichiers(ids_floues, "Floues confirmees")
else:
    # on n'a que le nom du fichier pas l'id, il faut le faire a la main
    print(f"  {len(liste_floues_avancees)} floues detectees sur disque (pas d'ID Immich)")
    print(f"  -> A supprimer manuellement dans Immich :")
    for flou in liste_floues_avancees[:10]:
        print(f"     Cherchez : {flou.get('fichier', '?')}")
    nb_suppr_floues = 0


# rappel pour les doublons (on les supprime pas automatiquement)
print("\n" + "-" * 60)
print("  NON SUPPRIMES (verification manuelle requise)")
print(f"  Doublons : {len(mon_rapport['doublons'])} groupes")


# bilan
total_supprimes = nb_suppr_parasites + nb_suppr_petits + nb_suppr_corrompus + nb_suppr_floues
print("\n" + "=" * 60)
print("  BILAN")
print("=" * 60)
print(f"  Parasites   : {nb_suppr_parasites}")
print(f"  Trop petits : {nb_suppr_petits}")
print(f"  Corrompus   : {nb_suppr_corrompus}")
print(f"  Floues      : {nb_suppr_floues}")
print(f"  TOTAL       : {total_supprimes}")

if MODE_SIMULATION:
    print("\n  SIMULATION - rien n'a ete supprime")
    print("  Changez MODE_SIMULATION = False apres validation Pierre-Ange")
else:
    print("\n  Fichiers dans la CORBEILLE Immich (30 jours)")


# on garde une trace de la suppression dans un log
mon_log = {
    "date": datetime.now().isoformat(),
    "mode": "simulation" if MODE_SIMULATION else "reel",
    "parasites": nb_suppr_parasites,
    "trop_petits": nb_suppr_petits,
    "corrompus": nb_suppr_corrompus,
    "floues": nb_suppr_floues,
    "total": total_supprimes
}
with open("/home/info/photo-ia/resultats/log_suppression.json", "w") as f:
    json.dump(mon_log, f, indent=2)
print("  Log sauvegarde.")
print("=" * 60)
