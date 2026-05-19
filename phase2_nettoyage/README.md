# Phase 2 — Nettoyage du stock photo

## Objectif

L'audit de la phase 1 a révélé un stock pollué par des **fichiers parasites** (vignettes système, GIF d'interface, doublons, fichiers corrompus, photos floues). Cette phase identifie et supprime ces parasites avant de lancer la classification, pour ne pas faire travailler l'IA sur des fichiers inutiles.

Cinq familles de fichiers à supprimer ont été identifiées :
1. GIF parasites (très petits, < 10 Ko, dimensions < 50×50 px)
2. Fichiers trop petits (vignettes système hors GIF)
3. Doublons (même nom + même taille en octets)
4. Fichiers corrompus (sans miniature ou sans EXIF dans Immich)
5. Photos floues (détectées par 3 méthodes : Laplacien + Sobel + FFT)

## Démarche d'itération

Cette phase a été développée en **3 versions successives** pour améliorer la détection. C'est volontaire : chaque version a permis de comprendre les limites de la précédente et d'ajuster les seuils.

| Version | Script | Évolution |
|---|---|---|
| v1 | `03_nettoyage.py` + `04_verification.py` | Première détection : GIF parasites uniquement |
| v2 | `03_nettoyage_v2.py` + `05_verification_v2.py` | Ajout de la détection des doublons et fichiers corrompus |
| **v3 (finale)** | `03_nettoyage_v3.py` + `06_verification_v3.py` | Ajustement des seuils, ajout de la détection de flou rapide |

La version **v3 est celle qui a été utilisée en production**. Les v1 et v2 sont conservées pour montrer la démarche d'amélioration.

## Tous les scripts de la phase

| Script | Rôle |
|---|---|
| `03_nettoyage.py` | Détection v1 |
| `04_verification.py` | Vérification v1 |
| `03_nettoyage_v2.py` | Détection v2 |
| `05_verification_v2.py` | Vérification v2 |
| `03_nettoyage_v3.py` | **Détection v3 (utilisée en production)** |
| `06_verification_v3.py` | **Vérification v3** |
| `04_demo_5photos.py` | Démonstration de nettoyage sur 5 photos (utilisée lors de la présentation au CODIR DREAL) |
| `08_detection_flou.py` | Détection avancée du flou par 3 méthodes combinées (Laplacien + Sobel + FFT) |
| `09_verification_flou.py` | Vérification des résultats de détection du flou |
| `07_suppression.py` | Suppression effective via l'API Immich (mode `DRY_RUN = True` par défaut) |

## Ordre d'exécution recommandé (version finale)

```bash
# Détection
python3 03_nettoyage_v3.py
python3 06_verification_v3.py     # vérifie les chiffres avant suppression

# Détection avancée du flou (3 méthodes)
python3 08_detection_flou.py
python3 09_verification_flou.py

# Suppression (DRY_RUN = True par défaut dans le script)
python3 07_suppression.py
```

> Important : `07_suppression.py` est en mode **simulation** par défaut. Pour passer en mode réel, modifier `DRY_RUN = False` après validation des chiffres par le tuteur entreprise.

## Méthode des 3 critères concordants pour le flou

Pour détecter le flou, **trois méthodes** sont combinées dans `08_detection_flou.py` :

1. **Variance du Laplacien** : mesure la quantité de contours dans l'image
2. **Variance des Sobel X/Y** : mesure les bords horizontaux et verticaux
3. **FFT (transformée de Fourier)** : proportion de hautes fréquences

Une photo n'est déclarée floue que si les **trois méthodes** concordent. Cela évite les faux positifs sur les photos uniformes (ciel, mer) qui ont peu de contours mais ne sont pas floues.

## Résultats obtenus (voir `resultats/`)

| Fichier | Contenu |
|---|---|
| `rapport_flou_avance.json` | Photos floues détectées par les 3 méthodes |
| `log_suppression.json` | Bilan des suppressions effectuées |
| `demo_5photos.json` | Démonstration sur 5 photos (CODIR) |

> Les 3 rapports volumineux `rapport_nettoyage_v1/v2/v3.json` (jusqu'à 34 Mo chacun) ne sont pas livrés dans cette archive car ils sont reproductibles depuis le serveur. Ils contiennent la liste exhaustive des fichiers à supprimer dans chaque catégorie.

## Chiffres clés

Au total, **~100 740 fichiers parasites** ont été supprimés lors de cette phase, après validation par Pierre-Ange Martos (tuteur entreprise). Les fichiers ont été placés dans la corbeille Immich (30 jours de rétention) avant suppression définitive.
